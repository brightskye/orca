"""Content-free, rebuildable local Orca Status and session reminder."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable, Literal

from orca_memory.candidates import KnowledgeCandidate
from orca_memory.conflicts import parse_conflict_record
from orca_memory.memory import parse_record
from orca_memory.retrieval import RetrievalUnavailable, load_projection_index


STATUS_SCHEMA = "orca-status/0.1"
REMINDER_SCHEMA = "orca-session-reminder/0.1"
AttentionSeverity = Literal["urgent", "action-required", "review"]
_SAFE_RECEIPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class AttentionItem:
    item_class: str
    severity: AttentionSeverity
    workflow: str
    locator: str
    first_seen_at: str
    last_seen_at: str
    occurrence_count: int = 1
    state: Literal["unresolved"] = "unresolved"

    def __post_init__(self) -> None:
        if (
            self.severity not in {"urgent", "action-required", "review"}
            or not all((self.item_class, self.workflow, self.locator))
            or self.occurrence_count < 1
            or self.state != "unresolved"
        ):
            raise ValueError("invalid Attention Item")

    @property
    def attention_id(self) -> str:
        payload = f"{self.item_class}\0{self.workflow}\0{self.locator}".encode()
        return "attn_" + hashlib.sha256(payload).hexdigest()[:20]

    def value_dict(self) -> dict[str, object]:
        return {
            "attention_id": self.attention_id,
            "class": self.item_class,
            "severity": self.severity,
            "state": self.state,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "occurrence_count": self.occurrence_count,
            "workflow": self.workflow,
            "locator": self.locator,
        }


@dataclass(frozen=True)
class OrcaStatus:
    items: tuple[AttentionItem, ...]

    def value_dict(self) -> dict[str, object]:
        by_severity = {
            severity: sum(item.severity == severity for item in self.items)
            for severity in ("urgent", "action-required", "review")
        }
        by_class = {
            item_class: sum(item.item_class == item_class for item in self.items)
            for item_class in sorted({item.item_class for item in self.items})
        }
        return {
            "schema": STATUS_SCHEMA,
            "counts": {
                "total": len(self.items),
                "by_severity": by_severity,
                "by_class": by_class,
            },
            "items": [item.value_dict() for item in self.items],
        }

    def render(self) -> str:
        value = self.value_dict()
        counts = value["counts"]
        lines = [
            "Orca Status",
            (
                f"Unresolved: {counts['total']} total; "
                f"{counts['by_severity']['urgent']} urgent, "
                f"{counts['by_severity']['action-required']} action-required, "
                f"{counts['by_severity']['review']} review."
            ),
        ]
        lines.extend(
            f"{item.attention_id} [{item.severity}] {item.workflow} {item.locator}"
            for item in self.items
        )
        return "\n".join(lines)


def collect_attention(
    vault_root: Path,
    runtime_root: Path,
    *,
    additional: Iterable[AttentionItem] = (),
) -> OrcaStatus:
    """Collect only accepted unresolved source states without changing them."""

    items = list(additional)
    retrieval_item = _retrieval_item(vault_root, runtime_root)
    if retrieval_item is not None:
        items.append(retrieval_item)
    memory_root = vault_root / "System" / "Orca Memory" / "shallow"
    if memory_root.exists():
        for path in sorted(memory_root.glob("**/*.md")):
            if path.name in {"project.md", "summary.md"} or "conversation-summaries" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
                try:
                    record = parse_record(text)
                    if record.status == "current" and record.scope == "unassigned":
                        items.append(
                            AttentionItem(
                                "unassigned", "review", "project-resolution",
                                record.memory_id, record.created_at, record.updated_at,
                            )
                        )
                except ValueError:
                    conflict = parse_conflict_record(text)
                    severity: AttentionSeverity = (
                        "action-required" if conflict.review_state == "overflow" else "review"
                    )
                    items.append(
                        AttentionItem(
                            "memory-review", severity, "memory-conflict-review",
                            conflict.memory_id, conflict.created_at, conflict.updated_at,
                        )
                    )
            except (OSError, UnicodeError, ValueError):
                items.append(_integrity_item(vault_root, path))
    candidate_root = vault_root / "System" / "Orca Memory" / "candidates" / "knowledge"
    if candidate_root.exists():
        for path in sorted(candidate_root.glob("**/*.md")):
            try:
                candidate = KnowledgeCandidate.parse(path.read_text(encoding="utf-8"))
                if candidate.status == "pending":
                    items.append(
                        AttentionItem(
                            "knowledge-review", "review", "knowledge-candidate-review",
                            candidate.candidate_id, candidate.created_at, candidate.updated_at,
                        )
                    )
            except (OSError, UnicodeError, ValueError):
                items.append(_integrity_item(vault_root, path))
    items.extend(_intent_items(runtime_root / "publications", "publication-recovery"))
    items.extend(_intent_items(runtime_root / "project-mappings", "project-mapping-recovery"))
    receipt_root = runtime_root / "receipts"
    if receipt_root.exists():
        for path in sorted(receipt_root.glob("failure-*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if (
                    not isinstance(value, dict)
                    or value.get("schema") != "orca-runtime-failure/0.1"
                    or not isinstance(value.get("work_id"), str)
                    or not _SAFE_RECEIPT_ID.fullmatch(value["work_id"])
                ):
                    raise ValueError("invalid failure receipt")
                items.append(
                    AttentionItem(
                        "failed-operation", "action-required", "runtime-retry",
                        value["work_id"], "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
                    )
                )
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                items.append(_integrity_item(runtime_root, path))
        for path in sorted(receipt_root.glob("retry-*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if (
                    not isinstance(value, dict)
                    or value.get("schema") != "orca-retry-receipt/0.1"
                    or not isinstance(value.get("receipt_id"), str)
                    or not _SAFE_RECEIPT_ID.fullmatch(value["receipt_id"])
                    or value.get("reason") != "retention-expired"
                    or not isinstance(value.get("expired_at"), str)
                ):
                    raise ValueError("invalid retry receipt")
                items.append(
                    AttentionItem(
                        "failed-operation", "action-required", "runtime-retry",
                        value["receipt_id"], "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
                    )
                )
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                items.append(_integrity_item(runtime_root, path))
    unique = {item.attention_id: item for item in items}
    return OrcaStatus(tuple(unique[key] for key in sorted(unique)))


def _retrieval_item(vault_root: Path, runtime_root: Path) -> AttentionItem | None:
    """Return one content-free item when an expected disposable index is unusable."""

    index_path = runtime_root / "retrieval" / "index.json"
    memory_root = vault_root / "System" / "Orca Memory" / "shallow"
    has_sources = memory_root.is_dir() and any(
        path.is_file() and path.name != "project.md"
        for path in memory_root.glob("**/*.md")
    )
    if not index_path.is_file() and not has_sources:
        return None
    try:
        load_projection_index(runtime_root, vault_root)
    except (OSError, UnicodeError, ValueError, RetrievalUnavailable):
        return AttentionItem(
            "stale-derived-state", "action-required", "retrieval-rebuild",
            "retrieval-index", "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
        )
    return None


def rebuild_status(
    vault_root: Path,
    runtime_root: Path,
    *,
    additional: Iterable[AttentionItem] = (),
) -> OrcaStatus:
    status = collect_attention(vault_root, runtime_root, additional=additional)
    _atomic_private_json(runtime_root / "status" / "orca-status.json", status.value_dict())
    return status


def session_reminder(status: OrcaStatus, *, runtime_root: Path, session_id: str) -> str | None:
    """Return at most one counts-only reminder for a safe session identity."""

    if not session_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for char in session_id):
        raise ValueError("invalid session identity")
    if not status.items:
        return None
    cursor = runtime_root / "reminders" / f"{session_id}.json"
    if cursor.exists():
        return None
    counts = status.value_dict()["counts"]["by_severity"]
    _atomic_private_json(
        cursor,
        {"schema": REMINDER_SCHEMA, "session_id": session_id, "shown": True},
        exclusive=True,
    )
    parts = [
        f"{counts[name]} {name}"
        for name in ("urgent", "action-required", "review")
        if counts[name]
    ]
    return f"Orca needs attention: {', '.join(parts)}. Run Orca Status."


def _intent_items(root: Path, workflow: str) -> tuple[AttentionItem, ...]:
    if not root.exists():
        return ()
    items = []
    for path in sorted(root.glob("*/intent.json")):
        locator = path.parent.name
        timestamp = "1970-01-01T00:00:00Z"
        items.append(
            AttentionItem(
                "integrity-or-recovery", "action-required", workflow,
                locator, timestamp, timestamp,
            )
        )
    return tuple(items)


def _integrity_item(root: Path, path: Path) -> AttentionItem:
    relative_hash = hashlib.sha256(path.relative_to(root).as_posix().encode()).hexdigest()[:20]
    return AttentionItem(
        "integrity-or-recovery", "urgent", "artifact-repair",
        f"artifact_{relative_hash}", "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
    )


def _atomic_private_json(path: Path, value: object, *, exclusive: bool = False) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if exclusive:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


__all__ = [
    "AttentionItem", "OrcaStatus", "collect_attention", "rebuild_status", "session_reminder"
]
