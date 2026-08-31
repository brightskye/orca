"""Bounded Codex lifecycle hook adapter for the private local runtime."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable, Mapping, TextIO

from orca_memory.application import LocalOrcaApplication
from orca_memory.configuration import ValidatedConfiguration, load_configuration
from orca_memory.conversation import ConversationBatch, normalize_codex_rollout
from orca_memory.projects import resolve_project
from orca_memory.runtime import LocalRuntime
from orca_memory.segmentation import chunk_turns
from orca_memory.storage import MemoryScope, Storage


CONNECTOR_ID = "codex-local"
CODEX_CLI_ADAPTER = "codex-cli"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SESSION_START_SOURCES = frozenset({"startup", "resume", "compact"})
_PRECOMPACT_TRIGGERS = frozenset({"manual", "auto"})
_PERMISSION_MODES = frozenset(
    {"default", "acceptEdits", "plan", "dontAsk", "bypassPermissions"}
)


class HookInputError(ValueError):
    """A Codex hook request is not safe to process."""


class _NoSemanticProvider:
    """Guard the SessionStart path against accidental provider invocation."""

    name = "orca-session-start/no-provider"

    def distill(self, request: object) -> object:
        raise RuntimeError("SessionStart must not invoke a semantic provider")


def handle_payload(
    payload: object,
    *,
    environ: Mapping[str, str] | None = None,
    spawn: Callable[..., object] | None = None,
) -> str | None:
    """Handle one official Codex hook payload without emitting private data.

    ``PreCompact`` queues a rollout pointer and ``SessionEnd`` persists only
    unprocessed normalized turns before starting the same detached worker used
    by the local CLI. ``SessionStart`` returns deterministic guidance and its
    counts-only reminder as hook-specific context. All semantic work remains
    in the detached, locked worker.
    """

    if not isinstance(payload, dict):
        raise HookInputError("hook payload must be an object")
    event = payload.get("hook_event_name")
    if event not in {"PreCompact", "SessionEnd", "SessionStart"}:
        raise HookInputError("unsupported hook event")
    session_id = _safe_id(payload.get("session_id"), "session_id")
    cwd = _safe_directory(payload.get("cwd"), "cwd")
    environment = dict(os.environ if environ is None else environ)
    host_config_path, repo_root = _resolve_host_config(cwd, environment)

    if event == "SessionStart":
        _validate_session_start(payload)
    elif event == "PreCompact":
        _validate_precompact(payload)
    else:
        _validate_session_end(payload)
    configuration = _load(host_config_path, environment)
    if not configuration.vault.lifecycle.enabled:
        return None
    scope = resolve_lifecycle_scope(cwd, session_id, configuration)

    if event == "SessionStart":
        transcript = _optional_transcript(payload.get("transcript_path"))
        if transcript is not None:
            _ensure_transcript_in_store(
                transcript,
                host_config_path,
                environment,
                configuration=configuration,
            )
        application = LocalOrcaApplication(configuration, _NoSemanticProvider())
        startup = application.startup(
            session_id=session_id,
            context="general",
            project_id=scope.scope_id if scope.kind == "project" else None,
            project_alias=scope.project_alias,
        )
        return "\n\n".join(
            part for part in (startup.guidance, startup.reminder) if part
        )

    transcript = _required_transcript(payload.get("transcript_path"))
    transcript = _ensure_transcript_in_store(
        transcript, host_config_path, environment, configuration=configuration
    )
    source_session_id = _session_id_from_rollout(transcript)
    if source_session_id != session_id:
        raise HookInputError("transcript session identity does not match hook input")

    runtime = LocalRuntime(
        configuration.host.runtime_path,
        max_attempts=configuration.vault.retry.max_attempts,
    )
    if event == "PreCompact":
        start_offset = runtime.source_offset(CONNECTOR_ID, session_id, transcript)
        runtime.enqueue_pointer(
            trigger="pre-compact",
            connector_id=CONNECTOR_ID,
            conversation_id=session_id,
            source_path=transcript,
            start_offset=start_offset,
            scope_kind=scope.kind,
            scope_id=scope.scope_id,
            project_alias=scope.project_alias,
        )
    else:
        start_offset = runtime.source_offset(CONNECTOR_ID, session_id, transcript)
        batch = normalize_codex_rollout(
            transcript,
            connector_id=CONNECTOR_ID,
            start_offset=start_offset,
        )
        if batch.conversation_id != session_id:
            raise HookInputError("normalized transcript identity changed")
        unprocessed = _select_unprocessed_turns(batch, configuration)
        if not unprocessed.turns:
            runtime.advance_source_offset(
                CONNECTOR_ID,
                session_id,
                transcript,
                batch.processed_through,
            )
            return None
        runtime.enqueue_session_end(
            unprocessed,
            now=datetime.now(timezone.utc),
            scope_kind=scope.kind,
            scope_id=scope.scope_id,
            project_alias=scope.project_alias,
            retention_hours=configuration.vault.retry.retention_hours,
        )
        runtime.advance_source_offset(
            CONNECTOR_ID,
            session_id,
            transcript,
            batch.processed_through,
        )
    _spawn_worker(
        host_config_path,
        repo_root,
        environment,
        spawn=subprocess.Popen if spawn is None else spawn,
    )
    return None


def main(
    *,
    stdin: TextIO | None = None,
    environ: Mapping[str, str] | None = None,
    spawn: Callable[..., object] | None = None,
) -> int:
    """Run one stdin/stdout Codex command hook transaction."""

    try:
        source = sys.stdin if stdin is None else stdin
        payload = json.load(source)
        additional_context = handle_payload(
            payload, environ=environ, spawn=spawn
        )
        if isinstance(payload, dict) and payload.get("hook_event_name") == "SessionStart":
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": additional_context or "",
                        }
                    },
                    separators=(",", ":"),
                )
            )
        return 0
    except Exception:
        # Hook stderr is visible to the operator, but never reveals source,
        # configuration, provider, or exception details from private paths.
        print("orca hook failed", file=sys.stderr)
        return 1


def _validate_precompact(payload: dict[str, Any]) -> None:
    _required_text(payload.get("model"), "model")
    _required_text(payload.get("turn_id"), "turn_id")
    trigger = payload.get("trigger")
    if trigger not in _PRECOMPACT_TRIGGERS:
        raise HookInputError("unsupported PreCompact trigger")


def _validate_session_end(payload: dict[str, Any]) -> None:
    if payload.get("reason") != "other":
        raise HookInputError("unsupported SessionEnd reason")


def _validate_session_start(payload: dict[str, Any]) -> None:
    _required_text(payload.get("model"), "model")
    permission_mode = payload.get("permission_mode")
    if permission_mode not in _PERMISSION_MODES:
        raise HookInputError("unsupported SessionStart permission mode")
    if payload.get("source") not in _SESSION_START_SOURCES:
        raise HookInputError("unsupported SessionStart source")


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise HookInputError(f"invalid {field}")
    return value


def _safe_id(value: object, field: str) -> str:
    text = _required_text(value, field)
    if not _SAFE_ID.fullmatch(text):
        raise HookInputError(f"invalid {field}")
    return text


def _safe_directory(value: object, field: str) -> Path:
    text = _required_text(value, field)
    path = Path(text)
    if not path.is_absolute():
        raise HookInputError(f"invalid {field}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise HookInputError(f"invalid {field}") from exc
    if not resolved.is_dir():
        raise HookInputError(f"invalid {field}")
    return resolved


def _required_transcript(value: object) -> Path:
    if value is None:
        raise HookInputError("transcript_path is required")
    return _transcript_path(value)


def _optional_transcript(value: object) -> Path | None:
    if value is None:
        return None
    return _transcript_path(value)


def _transcript_path(value: object) -> Path:
    text = _required_text(value, "transcript_path")
    path = Path(text)
    if not path.is_absolute():
        raise HookInputError("invalid transcript_path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise HookInputError("invalid transcript_path") from exc
    if not resolved.is_file():
        raise HookInputError("invalid transcript_path")
    return resolved


def _resolve_host_config(cwd: Path, environment: Mapping[str, str]) -> tuple[Path, Path]:
    configured = environment.get("ORCA_HOST_CONFIG")
    if configured is not None:
        path = Path(_required_text(configured, "ORCA_HOST_CONFIG"))
        if not path.is_absolute():
            raise HookInputError("ORCA_HOST_CONFIG must be absolute")
        try:
            path = path.resolve(strict=True)
        except OSError as exc:
            raise HookInputError("ORCA_HOST_CONFIG is unavailable") from exc
        if not path.is_file():
            raise HookInputError("ORCA_HOST_CONFIG is unavailable")
    else:
        repo_root = _repo_root(cwd)
        path = repo_root / "config" / "host.yaml"
        if not path.is_file():
            raise HookInputError("repo-local host configuration is missing")
        path = path.resolve()
    return path, _repo_root(cwd)


def _repo_root(cwd: Path) -> Path:
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    # Tests and installed entry points may not have a Git marker; the package
    # checkout is still a stable working directory for the detached worker.
    return Path(__file__).resolve().parents[2]


def _load(host_config_path: Path, environment: Mapping[str, str]) -> ValidatedConfiguration:
    return load_configuration(
        host_config_path,
        environ=environment,
        registered_provider_adapters={CODEX_CLI_ADAPTER},
    )


def resolve_lifecycle_scope(
    cwd: Path,
    session_id: str,
    configuration: ValidatedConfiguration,
) -> MemoryScope:
    workspace_root = _workspace_root(cwd)
    resolution = resolve_project(
        workspace_root,
        configuration.host.project_root_mappings,
        configuration.project_registry,
        owner_choice="unassigned",
    )
    if resolution.allows_project_processing:
        assert resolution.project_id is not None
        assert resolution.project_alias is not None
        return MemoryScope(
            "project",
            resolution.project_id,
            resolution.project_alias,
        )
    if resolution.status == "error":
        raise HookInputError("configured project scope cannot be resolved")
    choice = LocalRuntime(configuration.host.runtime_path).scope_choice(session_id)
    if choice == "general":
        return MemoryScope("general", "general")
    return MemoryScope("unassigned", "unassigned")


def _workspace_root(cwd: Path) -> Path:
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".git").exists():
            return candidate
    return cwd


def _select_unprocessed_turns(
    batch: ConversationBatch, configuration: ValidatedConfiguration
) -> ConversationBatch:
    """Retain turns with any unprocessed deterministic segment.

    A previous bounded worker may have published an early segment of an
    oversized turn before interruption.  The retry spool must retain that
    turn so the worker can replay its complete identity while Storage skips
    the already-proven segment and processes the remainder.
    """

    if not batch.turns:
        return batch

    budgets = configuration.vault.budgets.processor.as_processing_budget()
    segments = tuple(
        segment
        for chunk in chunk_turns(batch.turns, budgets)
        for segment in chunk.segments
    )
    selected = Storage(
        configuration.host.vault_path,
        configuration.host.runtime_path,
    ).select_unprocessed_segments(segments)
    selected_turn_ids = {segment.turn_id for segment in selected}
    return ConversationBatch(
        batch.connector_id,
        batch.conversation_id,
        tuple(turn for turn in batch.turns if turn.turn_id in selected_turn_ids),
        batch.processed_through,
        batch.has_partial_tail,
    )


def _ensure_transcript_in_store(
    transcript: Path,
    host_config_path: Path,
    environment: Mapping[str, str],
    *,
    configuration: ValidatedConfiguration | None = None,
) -> Path:
    configuration = configuration or _load(host_config_path, environment)
    root = configuration.host.codex_rollout_store.resolve()
    try:
        permitted = transcript.resolve(strict=True)
    except OSError as exc:
        raise HookInputError("invalid transcript_path") from exc
    if not permitted.is_file() or not permitted.is_relative_to(root):
        raise HookInputError("transcript is outside configured rollout store")
    return permitted


def _session_id_from_rollout(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                value = json.loads(raw_line.decode("utf-8"))
                if not isinstance(value, dict) or value.get("type") != "session_meta":
                    raise HookInputError("rollout metadata is invalid")
                metadata = value.get("payload")
                if not isinstance(metadata, dict):
                    raise HookInputError("rollout metadata is invalid")
                return _safe_id(
                    metadata.get("id") or metadata.get("session_id"),
                    "rollout session_id",
                )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HookInputError("rollout metadata is invalid") from exc
    raise HookInputError("rollout metadata is missing")


def _spawn_worker(
    host_config_path: Path,
    repo_root: Path,
    environment: Mapping[str, str],
    *,
    spawn: Callable[..., object],
) -> None:
    command = [
        sys.executable,
        "-m",
        "orca_memory.cli",
        "--host-config",
        str(host_config_path),
        "worker",
        "--reasoning-effort",
        "xhigh",
    ]
    spawn(
        command,
        cwd=str(repo_root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
        env=dict(environment),
    )


__all__ = ["handle_payload", "main", "resolve_lifecycle_scope"]


if __name__ == "__main__":
    raise SystemExit(main())
