"""Capture immutable conversation evidence from authorized connectors."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from orca_memory.privacy import REDACTION_POLICY, redact_secrets


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class NormalizedTurn:
    """One permitted redacted source turn supplied transiently to Processor."""

    connector_id: str
    conversation_id: str
    turn_id: str
    occurred_at: str | None
    source_uri: str
    text: str
    content_sha256: str
    redaction_policy: str = REDACTION_POLICY


@dataclass(frozen=True)
class ConversationBatch:
    """Chronological normalized turns from one supported conversation."""

    connector_id: str
    conversation_id: str
    turns: tuple[NormalizedTurn, ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for turn in self.turns:
            if turn.connector_id != self.connector_id:
                raise ValueError("turn connector does not match conversation batch")
            if turn.conversation_id != self.conversation_id:
                raise ValueError("turn conversation does not match conversation batch")
            if turn.turn_id in seen:
                raise ValueError(f"duplicate turn in conversation batch: {turn.turn_id}")
            seen.add(turn.turn_id)


def normalize_codex_rollout(
    rollout_path: Path,
    *,
    connector_id: str,
) -> ConversationBatch:
    """Read eligible Codex Owner turns without creating another raw archive."""

    _require_safe_id(connector_id, "connector_id")
    rows = _read_jsonl(rollout_path)
    metadata = next(
        (row.get("payload") for row in rows if row.get("type") == "session_meta"),
        None,
    )
    if not isinstance(metadata, dict):
        raise ValueError(f"missing Codex session_meta: {rollout_path}")
    if metadata.get("thread_source") != "user":
        return ConversationBatch(connector_id, "excluded", ())

    conversation_id = metadata.get("id") or metadata.get("session_id")
    if not isinstance(conversation_id, str) or not conversation_id:
        raise ValueError(f"missing Codex session id: {rollout_path}")
    _require_safe_id(conversation_id, "session_id")

    turns: list[NormalizedTurn] = []
    seen_turn_ids: set[str] = set()
    for row in rows:
        event = _owner_message(row)
        if event is None:
            continue
        turn_id, source_text = event
        if turn_id in seen_turn_ids:
            raise ValueError(f"duplicate Codex UserMessage id {turn_id}: {rollout_path}")
        seen_turn_ids.add(turn_id)
        text = redact_secrets(source_text)
        turns.append(
            NormalizedTurn(
                connector_id=connector_id,
                conversation_id=conversation_id,
                turn_id=turn_id,
                occurred_at=row.get("timestamp")
                if isinstance(row.get("timestamp"), str)
                else None,
                source_uri=f"codex://session/{conversation_id}/event/{turn_id}",
                text=text,
                content_sha256=_sha256(text),
            )
        )
    return ConversationBatch(connector_id, conversation_id, tuple(turns))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
            rows.append(value)
    return rows


def _owner_message(row: dict[str, Any]) -> tuple[str, str] | None:
    if row.get("type") != "event_msg":
        return None
    payload = row.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "item_completed":
        return None
    item = payload.get("item")
    if not isinstance(item, dict) or item.get("type") != "UserMessage":
        return None
    event_id = item.get("id")
    if not isinstance(event_id, str) or not event_id:
        return None
    blocks = item.get("content")
    if not isinstance(blocks, list):
        return None
    text = "\n".join(
        block["text"]
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") in {"input_text", "text"}
        and isinstance(block.get("text"), str)
    ).strip()
    return (event_id, text) if text else None


def _require_safe_id(value: str, field: str) -> None:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid {field}: {value!r}")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
