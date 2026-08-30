"""Place validated Step 3 artifacts and publish operational receipts safely."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable, Literal
import unicodedata
import uuid

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.privacy import contains_secret
from orca_memory.processor import ContinuationSummary, ProcessedConversation


MANIFEST_SCHEMA = "orca-run-manifest/0.1"
CHECKPOINT_SCHEMA = "orca-checkpoint/0.1"
CONTINUATION_SCHEMA = "orca-conversation-continuation/1"
_GENERIC_SLUGS = {"memory", "record", "note", "item", "misc", "untitled"}


@dataclass(frozen=True)
class MemoryScope:
    """Governance-resolved location for one processing run."""

    kind: Literal["project", "general", "unassigned"]
    scope_id: str
    project_alias: str | None = None

    def __post_init__(self) -> None:
        if self.kind == "project":
            if not self.scope_id.strip() or not self.project_alias or not self.project_alias.strip():
                raise ValueError("project scope requires project_id and project_alias")
        elif self.kind in {"general", "unassigned"}:
            if self.scope_id != self.kind or self.project_alias is not None:
                raise ValueError(f"{self.kind} scope must use its fixed identity")
        else:
            raise ValueError(f"unsupported memory scope: {self.kind}")


@dataclass(frozen=True)
class PublicationResult:
    """Observable result of one Step 3 pipeline run."""

    status: Literal["success", "no_memory", "replay"]
    manifest_path: Path | None
    output_paths: tuple[Path, ...]
    processed_through_turn: str


class Storage:
    """Own artifact placement, manifest deduplication, and checkpoint ordering."""

    def __init__(
        self,
        vault_root: Path,
        runtime_root: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.vault_root = vault_root
        self.runtime_root = runtime_root
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)

    def select_unprocessed(self, conversation: ConversationBatch) -> ConversationBatch:
        """Return unknown turns; reject a known identity with revised content."""

        processed = self._processed_sources()
        new_turns: list[NormalizedTurn] = []
        for turn in conversation.turns:
            key = (turn.connector_id, turn.conversation_id, turn.turn_id)
            known = processed.get(key)
            current = (turn.content_sha256, turn.redaction_policy)
            if known is None:
                new_turns.append(turn)
            elif known[1] != current[1]:
                raise ValueError(
                    "redaction policy revision requires governed reprocessing for "
                    f"{turn.conversation_id}/{turn.turn_id}"
                )
            elif known[0] != current[0]:
                raise ValueError(
                    "source revision for known turn "
                    f"{turn.conversation_id}/{turn.turn_id}"
                )
        return ConversationBatch(
            conversation.connector_id,
            conversation.conversation_id,
            tuple(new_turns),
        )

    def load_continuation(self, conversation_id: str) -> str | None:
        """Load the one existing continuation by Conversation Identity."""

        suffix = _short_id(conversation_id)
        shallow_root = self.vault_root / "System" / "Orca Memory" / "shallow"
        matches = [] if not shallow_root.exists() else list(
            shallow_root.glob(f"**/conversation-summaries/*--{suffix}.md")
        )
        exact = [
            path
            for path in matches
            if f"conversation_id: {json.dumps(conversation_id)}" in path.read_text(encoding="utf-8")
        ]
        if len(exact) > 1:
            raise ValueError(f"multiple continuations for conversation {conversation_id}")
        return exact[0].read_text(encoding="utf-8") if exact else None

    def publish(
        self,
        processed: ProcessedConversation,
        *,
        scope: MemoryScope,
    ) -> PublicationResult:
        """Publish outputs, then immutable manifest, then local checkpoint."""

        now = self._clock().astimezone(timezone.utc)
        timestamp = now.isoformat().replace("+00:00", "Z")
        run_id = f"run_{self._id_factory()}"
        outputs: list[dict[str, str]] = []
        output_paths: list[Path] = []

        if processed.continuation is not None:
            path = self._continuation_path(
                scope,
                processed.conversation.conversation_id,
                processed.continuation,
            )
            payload = _render_continuation(
                processed.conversation.conversation_id,
                scope.scope_id if scope.kind == "project" else None,
                processed.continuation,
            ).encode("utf-8")
            if contains_secret(payload.decode("utf-8")):
                raise ValueError("proposed output contains a credential-like value")
            _replace_file(path, payload)
            output_paths.append(path)
            outputs.append(
                {
                    "kind": "conversation-continuation-summary",
                    "path": path.relative_to(self.vault_root).as_posix(),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
            )

        status = "success" if outputs else "no_memory"
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "run_id": run_id,
            "status": status,
            "processed_at": timestamp,
            "connector_id": processed.conversation.connector_id,
            "conversation_id": processed.conversation.conversation_id,
            "scope": {
                "type": scope.kind,
                "scope_id": scope.scope_id,
            },
            "processor": {
                "provider": processed.provider,
                "policy_version": processed.policy,
            },
            "sources": [_source_receipt(turn) for turn in processed.conversation.turns],
            "outputs": outputs,
        }
        manifest_payload = (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        manifest_path = (
            self.vault_root
            / "System"
            / "Orca Memory"
            / "manifests"
            / f"{now:%Y}"
            / f"{now:%m}"
            / f"{now:%d}"
            / f"{run_id}.json"
        )
        _publish_immutable(manifest_path, manifest_payload)

        last_turn = processed.conversation.turns[-1]
        self._write_checkpoint(last_turn, manifest_path)
        return PublicationResult(
            status=status,
            manifest_path=manifest_path,
            output_paths=tuple(output_paths),
            processed_through_turn=last_turn.turn_id,
        )

    def record_replay(self, conversation: ConversationBatch) -> PublicationResult:
        """Repair the disposable checkpoint without repeating semantic work."""

        if not conversation.turns:
            raise ValueError("replay requires at least one source turn")
        last_turn = conversation.turns[-1]
        self._write_checkpoint(last_turn, None)
        return PublicationResult("replay", None, (), last_turn.turn_id)

    def _processed_sources(self) -> dict[tuple[str, str, str], tuple[str, str]]:
        manifest_root = self.vault_root / "System" / "Orca Memory" / "manifests"
        processed: dict[tuple[str, str, str], tuple[str, str]] = {}
        if not manifest_root.exists():
            return processed
        for path in sorted(manifest_root.glob("**/*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("schema_version") != MANIFEST_SCHEMA:
                continue
            if value.get("status") not in {"success", "no_memory"}:
                continue
            connector_id = value.get("connector_id")
            conversation_id = value.get("conversation_id")
            for source in value.get("sources", []):
                if not isinstance(source, dict):
                    continue
                key = (connector_id, conversation_id, source.get("turn_id"))
                receipt = (source.get("content_sha256"), source.get("redaction_policy"))
                if not all(isinstance(item, str) for item in key + receipt):
                    continue
                known = processed.get(key)
                if known is not None and known != receipt:
                    raise ValueError(f"conflicting manifest receipts for {key}")
                processed[key] = receipt
        return processed

    def _continuation_path(
        self,
        scope: MemoryScope,
        conversation_id: str,
        summary: ContinuationSummary,
    ) -> Path:
        base = self.vault_root / "System" / "Orca Memory" / "shallow"
        if scope.kind == "project":
            base = base / "projects" / _slug(scope.project_alias or "")
        else:
            base = base / scope.kind
        directory = base / "conversation-summaries"
        suffix = _short_id(conversation_id)
        existing = [] if not directory.exists() else list(directory.glob(f"*--{suffix}.md"))
        if len(existing) > 1:
            raise ValueError(f"continuation filename collision for {conversation_id}")
        if existing:
            content = existing[0].read_text(encoding="utf-8")
            if f"conversation_id: {json.dumps(conversation_id)}" not in content:
                raise ValueError(f"continuation short-id collision for {conversation_id}")
            return existing[0]
        return directory / f"{_slug(summary.purpose)}--{suffix}.md"

    def _write_checkpoint(self, turn: NormalizedTurn, manifest_path: Path | None) -> None:
        path = (
            self.runtime_root
            / "checkpoints"
            / _slug(turn.connector_id)
            / f"{hashlib.sha256(turn.conversation_id.encode('utf-8')).hexdigest()}.json"
        )
        payload = {
            "schema_version": CHECKPOINT_SCHEMA,
            "connector_id": turn.connector_id,
            "conversation_id": turn.conversation_id,
            "processed_through_turn": turn.turn_id,
            "content_sha256": turn.content_sha256,
            "redaction_policy": turn.redaction_policy,
            "manifest_path": manifest_path.relative_to(self.vault_root).as_posix()
            if manifest_path is not None
            else None,
        }
        _replace_file(
            path,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )


def _source_receipt(turn: NormalizedTurn) -> dict[str, str | None]:
    return {
        "turn_id": turn.turn_id,
        "source_role": turn.source_role,
        "source_uri": turn.source_uri,
        "occurred_at": turn.occurred_at,
        "content_sha256": turn.content_sha256,
        "redaction_policy": turn.redaction_policy,
    }


def _render_continuation(
    conversation_id: str,
    project_id: str | None,
    summary: ContinuationSummary,
) -> str:
    lines = [
        "---",
        f"schema_version: {CONTINUATION_SCHEMA}",
        "kind: conversation-continuation-summary",
        "authority: noncanonical",
        f"conversation_id: {json.dumps(conversation_id)}",
        f"project_id: {json.dumps(project_id) if project_id is not None else 'null'}",
        "---",
        "",
        f"# {summary.purpose.strip()}",
        "",
        "## Current state",
        "",
        summary.current_state.strip(),
    ]
    for heading, values in (
        ("Important outcomes", summary.important_outcomes),
        ("Open questions", summary.open_questions),
        ("Next steps", summary.next_steps),
        ("Relevant artifacts", summary.relevant_artifacts),
    ):
        if values:
            lines.extend(("", f"## {heading}", ""))
            lines.extend(f"- {value.strip()}" for value in values)
    return "\n".join(lines) + "\n"


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).lower()
    slug = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-_")[:72].rstrip("-")
    if not slug or slug in _GENERIC_SLUGS:
        raise ValueError(f"unsafe or non-descriptive slug: {value!r}")
    return slug


def _short_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _replace_file(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _publish_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise ValueError(f"immutable manifest already exists: {path}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
