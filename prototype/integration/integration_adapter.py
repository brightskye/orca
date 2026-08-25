"""Thin, writer-locked Orca ingestion adapter for captured Codex and Hermes sessions.

The adapter deliberately separates the model-semantic decision from deterministic
materialization. ``inspect`` emits positively identified authored events. ``apply``
can either consume a retained decision artifact or invoke the Orca Codex provider
for one semantic pass. It then validates decisions against exact source hashes and
writes noncanonical Cairn Markdown while holding AgentCairn's public writer lock.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess
import tempfile
from typing import Any, Iterable, Protocol

from cairn.ingest import Candidate, DedupLedger, content_hash, ingest_transcripts, transcript_from_messages
from cairn.ingest.events import project_from_cwd
from cairn.ingest.sanitize import sanitize_text
from cairn.locking import vault_writer_lock
from cairn.vault import Note


ADAPTER_VERSION = "orca-cairn-integration/0.2.0"
DECISION_SCHEMA = "orca-semantic-decisions/0.1"
PROVIDER_CONTRACT = "orca-semantic-provider/0.1"
MEMORY_TYPES = frozenset(
    {
        "project_state",
        "decision",
        "preference",
        "procedure",
        "lesson",
        "person_context",
        "working_context",
        "general_knowledge",
    }
)
APPLICABILITY_SCOPES = frozenset({"project-specific", "owner-global", "general"})
_NON_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SourceEvent:
    harness: str
    session_id: str
    event_id: str
    text: str
    timestamp: str | None
    cwd: str | None
    project: str | None
    source_path: str
    source_uri: str

    @property
    def key(self) -> tuple[str, str, str]:
        return self.harness, self.session_id, self.event_id

    @property
    def text_sha256(self) -> str:
        return _sha256(self.text)

    def inspect_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["source_text_sha256"] = self.text_sha256
        return record


@dataclass(frozen=True)
class SemanticDecision:
    event: SourceEvent
    content: str
    intent: str
    candidate_type: str
    proposed_scope: str
    semantic_pass: dict[str, Any]


class SemanticProvider(Protocol):
    def create_decisions(self, events: list[SourceEvent], output_path: Path) -> None: ...


class CodexCliSemanticProvider:
    """One-pass Orca semantic provider using an ephemeral Codex CLI session."""

    def __init__(
        self,
        *,
        rules_path: Path,
        model: str,
        executable: str = "codex",
    ) -> None:
        self.rules_path = rules_path.resolve()
        self.model = model
        self.executable = executable

    def create_decisions(self, events: list[SourceEvent], output_path: Path) -> None:
        rules = self.rules_path.read_text(encoding="utf-8")
        rules_sha256 = _sha256(rules)
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="orca-semantic-") as directory:
            run_root = Path(directory)
            schema_path = run_root / "response.schema.json"
            response_path = run_root / "response.json"
            _write_json(schema_path, _provider_response_schema(len(events)))
            evidence = [
                {
                    "event_index": index,
                    "text": event.text,
                    "observed_project": event.project,
                }
                for index, event in enumerate(events)
            ]
            prompt = (
                f"{rules.rstrip()}\n\n"
                "Return the required JSON object for this normalized evidence. "
                "This invocation is the single semantic pass.\n\n"
                + json.dumps({"events": evidence}, ensure_ascii=False, indent=2)
            )
            command = [
                self.executable,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                self.model,
                "--cd",
                str(run_root),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(response_path),
                "-",
            ]
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip() or "no provider output"
                raise RuntimeError(f"Orca semantic provider failed: {detail}")
            try:
                response = json.loads(response_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("Orca semantic provider returned unreadable JSON") from exc

        decisions = _bind_provider_response(response, events)
        _write_json(
            output_path,
            {
                "schema": DECISION_SCHEMA,
                "semantic_pass": {
                    "passes": 1,
                    "provider": "openai-codex-cli",
                    "model": self.model,
                    "contract": PROVIDER_CONTRACT,
                    "performed_at": _utc_now(),
                    "rules": str(self.rules_path),
                    "rules_sha256": rules_sha256,
                },
                "decisions": decisions,
            },
        )


def _provider_response_schema(event_count: int) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["decisions"],
        "properties": {
            "decisions": {
                "type": "array",
                "maxItems": event_count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "event_index",
                        "content",
                        "intent",
                        "candidate_type",
                        "proposed_scope",
                    ],
                    "properties": {
                        "event_index": {"type": "integer", "minimum": 0},
                        "content": {"type": "string", "minLength": 1, "maxLength": 1200},
                        "intent": {"type": "string", "enum": ["explicit", "implicit"]},
                        "candidate_type": {"type": "string", "enum": sorted(MEMORY_TYPES)},
                        "proposed_scope": {
                            "type": "string",
                            "enum": sorted(APPLICABILITY_SCOPES),
                        },
                    },
                },
            }
        },
    }


def _bind_provider_response(response: Any, events: list[SourceEvent]) -> list[dict[str, Any]]:
    if not isinstance(response, dict) or set(response) != {"decisions"}:
        raise ValueError("semantic provider response must contain only decisions")
    raw_decisions = response["decisions"]
    if not isinstance(raw_decisions, list) or len(raw_decisions) > len(events):
        raise ValueError("semantic provider decisions must be a bounded list")
    bound: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    required = {"event_index", "content", "intent", "candidate_type", "proposed_scope"}
    for raw in raw_decisions:
        if not isinstance(raw, dict) or set(raw) != required:
            raise ValueError("semantic provider decision fields do not match contract")
        index = raw["event_index"]
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(events):
            raise ValueError("semantic provider event_index is out of range")
        if index in seen_indices:
            raise ValueError(f"duplicate semantic provider event_index {index}")
        seen_indices.add(index)
        content = raw["content"]
        if not isinstance(content, str) or not content.strip() or len(content) > 1200:
            raise ValueError(f"invalid semantic provider content for event_index {index}")
        if raw["intent"] not in {"explicit", "implicit"}:
            raise ValueError(f"invalid semantic provider intent for event_index {index}")
        if raw["candidate_type"] not in MEMORY_TYPES:
            raise ValueError(f"invalid semantic provider candidate_type for event_index {index}")
        if raw["proposed_scope"] not in APPLICABILITY_SCOPES:
            raise ValueError(f"invalid semantic provider proposed_scope for event_index {index}")
        event = events[index]
        bound.append(
            {
                "source": {
                    "harness": event.harness,
                    "session_id": event.session_id,
                    "event_id": event.event_id,
                    "source_text_sha256": event.text_sha256,
                },
                "content": " ".join(content.split()),
                "intent": raw["intent"],
                "candidate_type": raw["candidate_type"],
                "proposed_scope": raw["proposed_scope"],
            }
        )
    return bound


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _project(cwd: str | None) -> str | None:
    if not cwd:
        return None
    if "\\" in cwd or re.match(r"^[A-Za-z]:", cwd):
        return PureWindowsPath(cwd).name or None
    return project_from_cwd(cwd)


def _joined_text(blocks: Any) -> str:
    if not isinstance(blocks, list):
        return ""
    parts = [
        block.get("text")
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") in {"input_text", "output_text", "text"}
        and isinstance(block.get("text"), str)
    ]
    return sanitize_text("\n".join(parts)).strip()


def _jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected object at {path}:{line_number}")
            yield value


def normalize_codex(path: Path) -> list[SourceEvent]:
    """Return only structurally confirmed, human-authored Codex user events.

    Current Codex records a real user turn as an ``event_msg`` completed
    ``UserMessage``. Injected role=user envelopes lack that mirror. Subagent
    sessions, including approval reviewers, are excluded at session scope.
    Absence of either positive signal fails closed.
    """

    rows = list(_jsonl(path))
    meta = next((row.get("payload") for row in rows if row.get("type") == "session_meta"), None)
    if not isinstance(meta, dict):
        raise ValueError(f"missing Codex session_meta: {path}")
    if meta.get("thread_source") != "user":
        return []
    session_id = meta.get("id") or meta.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError(f"missing Codex session id: {path}")
    cwd = meta.get("cwd") if isinstance(meta.get("cwd"), str) else None
    events: list[SourceEvent] = []
    seen_ids: set[str] = set()
    for row in rows:
        if row.get("type") != "event_msg":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "item_completed":
            continue
        item = payload.get("item")
        if not isinstance(item, dict) or item.get("type") != "UserMessage":
            continue
        event_id = item.get("id")
        text = _joined_text(item.get("content"))
        if not isinstance(event_id, str) or not event_id or not text:
            continue
        if event_id in seen_ids:
            raise ValueError(f"duplicate Codex UserMessage id {event_id}: {path}")
        seen_ids.add(event_id)
        events.append(
            SourceEvent(
                harness="codex",
                session_id=session_id,
                event_id=event_id,
                text=text,
                timestamp=row.get("timestamp") if isinstance(row.get("timestamp"), str) else None,
                cwd=cwd,
                project=_project(cwd),
                source_path=str(path.resolve()),
                source_uri=f"codex://session/{session_id}/event/{event_id}",
            )
        )
    return events


def _iso_timestamp(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    return None


def normalize_hermes(path: Path) -> list[SourceEvent]:
    events: list[SourceEvent] = []
    seen: set[tuple[str, str]] = set()
    for session in _jsonl(path):
        session_id = session.get("id")
        messages = session.get("messages")
        if not isinstance(session_id, str) or not session_id or not isinstance(messages, list):
            raise ValueError(f"invalid Hermes session export: {path}")
        cwd = session.get("cwd") if isinstance(session.get("cwd"), str) else None
        for message in messages:
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            event_id = str(message.get("id")) if message.get("id") is not None else ""
            text = message.get("content")
            text = sanitize_text(text).strip() if isinstance(text, str) else ""
            if not event_id or not text:
                continue
            key = (session_id, event_id)
            if key in seen:
                raise ValueError(f"duplicate Hermes user message {session_id}/{event_id}: {path}")
            seen.add(key)
            events.append(
                SourceEvent(
                    harness="hermes",
                    session_id=session_id,
                    event_id=event_id,
                    text=text,
                    timestamp=_iso_timestamp(message.get("timestamp")),
                    cwd=cwd,
                    project=_project(cwd),
                    source_path=str(path.resolve()),
                    source_uri=f"hermes://session/{session_id}/message/{event_id}",
                )
            )
    return events


def collect_events(codex_paths: list[Path], hermes_paths: list[Path]) -> list[SourceEvent]:
    events = [event for path in codex_paths for event in normalize_codex(path)]
    events.extend(event for path in hermes_paths for event in normalize_hermes(path))
    keys = [event.key for event in events]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate normalized source event identity")
    return sorted(events, key=lambda event: event.key)


def load_decisions(path: Path, events: list[SourceEvent]) -> tuple[dict[str, Any], list[SemanticDecision]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != DECISION_SCHEMA:
        raise ValueError(f"expected decision schema {DECISION_SCHEMA}")
    semantic_pass = payload.get("semantic_pass")
    if not isinstance(semantic_pass, dict) or semantic_pass.get("passes") != 1:
        raise ValueError("semantic_pass must declare exactly one pass")
    for field in ("provider", "model", "contract", "performed_at"):
        if not isinstance(semantic_pass.get(field), str) or not semantic_pass[field]:
            raise ValueError(f"semantic_pass.{field} is required")
    event_by_key = {event.key: event for event in events}
    raw_decisions = payload.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ValueError("decisions must be a list")
    decisions: list[SemanticDecision] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in raw_decisions:
        if not isinstance(raw, dict) or not isinstance(raw.get("source"), dict):
            raise ValueError("each decision requires a source object")
        source = raw["source"]
        key = (source.get("harness"), source.get("session_id"), str(source.get("event_id")))
        if not all(isinstance(value, str) and value for value in key):
            raise ValueError("decision source identity is incomplete")
        if key in seen:
            raise ValueError(f"duplicate semantic decision for {key}")
        seen.add(key)
        event = event_by_key.get(key)
        if event is None:
            raise ValueError(f"semantic decision references unknown source event {key}")
        if source.get("source_text_sha256") != event.text_sha256:
            raise ValueError(f"source text changed for semantic decision {key}")
        content = raw.get("content")
        intent = raw.get("intent")
        candidate_type = raw.get("candidate_type")
        proposed_scope = raw.get("proposed_scope")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"empty semantic content for {key}")
        if intent not in {"explicit", "implicit"}:
            raise ValueError(f"invalid intent for {key}")
        if not isinstance(candidate_type, str) or not candidate_type:
            raise ValueError(f"candidate_type is required for {key}")
        if not isinstance(proposed_scope, str) or not proposed_scope:
            raise ValueError(f"proposed_scope is required for {key}")
        decisions.append(
            SemanticDecision(
                event=event,
                content=" ".join(content.split()),
                intent=intent,
                candidate_type=candidate_type,
                proposed_scope=proposed_scope,
                semantic_pass=dict(semantic_pass),
            )
        )
    return semantic_pass, decisions


class OrcaDecisionDistiller:
    """Cairn Distiller backed by one already-completed semantic pass."""

    def __init__(self, decisions: list[SemanticDecision]) -> None:
        self._decisions: dict[tuple[str, str, str], SemanticDecision] = {}
        self.calls = 0
        for decision in decisions:
            key = (
                decision.event.harness,
                decision.event.session_id,
                content_hash(decision.event.text),
            )
            if key in self._decisions:
                raise ValueError(f"ambiguous decision lookup key: {key}")
            self._decisions[key] = decision

    def distill(self, candidate: Candidate) -> Note:
        self.calls += 1
        key = (candidate.harness or "", candidate.session_id, content_hash(candidate.text))
        decision = self._decisions.get(key)
        if decision is None:
            raise KeyError(f"no validated semantic decision for Cairn candidate {key}")
        event = decision.event
        digest = _sha256(decision.content)
        permalink = f"orca-runtime-fit-{_slugify(decision.content)}-{digest[:8]}"
        frontmatter: dict[str, Any] = {
            "title": _title(decision.content),
            "type": "memory",
            "permalink": permalink,
            "tags": ["ingested", "orca-candidate", "runtime-fit"],
            "created": event.timestamp,
            "source": event.source_uri,
            "sources": [
                {"id": "source-event", "resource": event.source_uri},
                {"id": "source-artifact", "resource": event.source_path},
            ],
            "harness": event.harness,
            "source_session_id": event.session_id,
            "source_event_id": event.event_id,
            "source_text_sha256": event.text_sha256,
            "source_artifact": event.source_path,
            "candidate_type": decision.candidate_type,
            "memory_type": decision.candidate_type,
            "proposed_scope": decision.proposed_scope,
            "intent": decision.intent,
            "entry_mode": decision.intent,
            "authority": "candidate",
            "orca_state": "new",
            "captured_at": event.timestamp,
            "semantic_contract": decision.semantic_pass["contract"],
            "semantic_pass": decision.semantic_pass,
            "generated": {"by": f"process:{ADAPTER_VERSION}", "at": _utc_now()},
        }
        if event.project:
            frontmatter["observed_project"] = event.project
        body = f"- [context] {decision.content} #ingested #orca-candidate\n"
        return Note(permalink=permalink, frontmatter=frontmatter, body=body)


def apply_ingestion(
    *,
    events: list[SourceEvent],
    decisions_path: Path | None = None,
    provider: SemanticProvider | None = None,
    semantic_output: Path | None = None,
    vault_root: Path,
    state_root: Path,
    lock_timeout: float = 0.0,
) -> dict[str, Any]:
    if (decisions_path is None) == (provider is None):
        raise ValueError("provide exactly one of decisions_path or provider")
    if provider is not None:
        if semantic_output is None:
            raise ValueError("semantic_output is required for provider-backed ingestion")
        provider.create_decisions(events, semantic_output)
        decisions_path = semantic_output
    assert decisions_path is not None
    semantic_pass, decisions = load_decisions(decisions_path, events)
    distiller = OrcaDecisionDistiller(decisions)
    transcripts = [
        transcript_from_messages(
            [{"role": "user", "content": decision.event.text, "timestamp": decision.event.timestamp}],
            session_id=decision.event.session_id,
            cwd=decision.event.cwd,
            source_path=Path(decision.event.source_path),
            harness=decision.event.harness,
        )
        for decision in decisions
    ]
    vault_root = vault_root.resolve()
    state_root = state_root.resolve()
    state_root.mkdir(parents=True, exist_ok=True)
    os.environ["CAIRN_LOCK_DIR"] = str(state_root / "locks")
    with vault_writer_lock(
        vault_root,
        operation="orca-locked-ingest",
        timeout=lock_timeout,
    ):
        report = ingest_transcripts(
            transcripts,
            vault_root=vault_root,
            ledger=DedupLedger(state_root / "dedup-ledger.txt"),
            threshold=0.0,
            judge=None,
            distiller=distiller,
            subdir="memories",
            dry_run=False,
            consolidator=None,
            neighbor_index=None,
        )
    return {
        "adapter_version": ADAPTER_VERSION,
        "writer_lock": "cairn.locking.vault_writer_lock",
        "semantic_pass": semantic_pass,
        "normalized_events": len(events),
        "selected_decisions": len(decisions),
        "distiller_calls": distiller.calls,
        "pipeline": report.to_dict(),
        "written": [str(path.resolve()) for path in report.written],
    }


def _slugify(text: str, max_words: int = 6) -> str:
    words = _NON_SLUG.sub(" ", text.lower()).split()
    return "-".join(words[:max_words]) or "memory"


def _title(text: str, limit: int = 80) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[: limit - 1].rsplit(" ", 1)[0] + "…"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "apply"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--codex", action="append", type=Path, default=[])
        subparser.add_argument("--hermes", action="append", type=Path, default=[])
        subparser.add_argument("--output", type=Path, required=True)
        if command == "apply":
            source = subparser.add_mutually_exclusive_group(required=True)
            source.add_argument("--decisions", type=Path)
            source.add_argument("--provider", choices=("codex-cli",))
            subparser.add_argument("--provider-model", default="gpt-5.6-sol")
            subparser.add_argument(
                "--provider-rules",
                type=Path,
                default=Path(__file__).resolve().parents[1]
                / "workflows"
                / "semantic-provider-rules.md",
            )
            subparser.add_argument("--semantic-output", type=Path)
            subparser.add_argument("--vault-root", type=Path, required=True)
            subparser.add_argument("--state-root", type=Path, required=True)
            subparser.add_argument("--lock-timeout", type=float, default=0.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    events = collect_events(args.codex, args.hermes)
    if args.command == "inspect":
        _write_json(
            args.output,
            {
                "adapter_version": ADAPTER_VERSION,
                "events": [event.inspect_record() for event in events],
            },
        )
        return 0
    provider = None
    if args.provider == "codex-cli":
        if args.semantic_output is None:
            raise SystemExit("--semantic-output is required with --provider")
        provider = CodexCliSemanticProvider(
            rules_path=args.provider_rules,
            model=args.provider_model,
        )
    result = apply_ingestion(
        events=events,
        decisions_path=args.decisions,
        provider=provider,
        semantic_output=args.semantic_output,
        vault_root=args.vault_root,
        state_root=args.state_root,
        lock_timeout=args.lock_timeout,
    )
    _write_json(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
