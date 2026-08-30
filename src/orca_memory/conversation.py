"""Normalize permitted Codex source records into transient conversation evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal

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
    source_role: Literal["owner", "assistant"] = "owner"
    redaction_policy: str = REDACTION_POLICY


@dataclass(frozen=True)
class ConversationBatch:
    """Chronological normalized turns from one supported conversation."""

    connector_id: str
    conversation_id: str
    turns: tuple[NormalizedTurn, ...]
    processed_through: int = 0
    has_partial_tail: bool = False

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
    start_offset: int = 0,
) -> ConversationBatch:
    """Read one bounded complete Codex range without creating a raw archive."""

    _require_safe_id(connector_id, "connector_id")
    metadata = _read_session_metadata(rollout_path)
    rows, processed_through, has_partial_tail = _read_jsonl(
        rollout_path, start_offset=start_offset
    )
    if not isinstance(metadata, dict):
        raise ValueError(f"missing Codex session_meta: {rollout_path}")
    if metadata.get("thread_source") != "user":
        return ConversationBatch(
            connector_id,
            "excluded",
            (),
            processed_through,
            has_partial_tail,
        )

    conversation_id = metadata.get("id") or metadata.get("session_id")
    if not isinstance(conversation_id, str) or not conversation_id:
        raise ValueError(f"missing Codex session id: {rollout_path}")
    _require_safe_id(conversation_id, "session_id")

    if _is_private(metadata):
        return ConversationBatch(
            connector_id,
            conversation_id,
            (),
            processed_through,
            has_partial_tail,
        )

    turns: list[NormalizedTurn] = []
    seen_turn_ids: set[str] = set()
    for row in rows:
        event = _supported_message(row)
        if event is None:
            continue
        turn_id, source_role, source_text = event
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
                source_role=source_role,
                text=text,
                content_sha256=_sha256(text),
            )
        )
    return ConversationBatch(
        connector_id,
        conversation_id,
        tuple(turns),
        processed_through,
        has_partial_tail,
    )


def _read_session_metadata(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                value = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
            if not isinstance(value, dict) or value.get("type") != "session_meta":
                raise ValueError(f"missing Codex session_meta: {path}")
            payload = value.get("payload")
            if not isinstance(payload, dict):
                raise ValueError(f"missing Codex session_meta: {path}")
            return payload
    raise ValueError(f"missing Codex session_meta: {path}")


def _read_jsonl(
    path: Path, *, start_offset: int
) -> tuple[list[dict[str, Any]], int, bool]:
    rows: list[dict[str, Any]] = []
    file_size = path.stat().st_size
    if not isinstance(start_offset, int) or not 0 <= start_offset <= file_size:
        raise ValueError(f"invalid Codex source offset: {start_offset}")
    with path.open("rb") as handle:
        if start_offset:
            handle.seek(start_offset - 1)
            if handle.read(1) not in {b"\n", b"\r"}:
                raise ValueError(f"Codex source offset is not a record boundary: {start_offset}")
        handle.seek(start_offset)
        processed_through = start_offset
        for line_number, raw_line in enumerate(handle, start=1):
            line_end = handle.tell()
            if not raw_line.strip():
                processed_through = line_end
                continue
            try:
                line = raw_line.decode("utf-8")
                value = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                if line_end == file_size and not raw_line.endswith((b"\n", b"\r")):
                    return rows, processed_through, True
                raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected object at {path}:{line_number}")
            rows.append(value)
            processed_through = line_end
    return rows, processed_through, False


def _supported_message(
    row: dict[str, Any],
) -> tuple[str, Literal["owner", "assistant"], str] | None:
    if _is_private(row):
        return None
    owner = _owner_message(row)
    if owner is not None:
        return owner[0], "owner", owner[1]
    assistant = _assistant_message(row)
    if assistant is not None:
        return assistant[0], "assistant", assistant[1]
    return None


def _owner_message(row: dict[str, Any]) -> tuple[str, str] | None:
    if row.get("type") != "event_msg":
        return None
    payload = row.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "item_completed":
        return None
    item = payload.get("item")
    if not isinstance(item, dict) or item.get("type") != "UserMessage":
        return None
    if _is_private(payload) or _is_private(item):
        return None
    event_id = item.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("supported Codex UserMessage lacks an id")
    _require_safe_id(event_id, "turn_id")
    blocks = item.get("content")
    if not isinstance(blocks, list):
        raise ValueError("supported Codex UserMessage lacks content")
    text = "\n".join(
        block["text"]
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") in {"input_text", "text"}
        and isinstance(block.get("text"), str)
    ).strip()
    if not text:
        raise ValueError("supported Codex UserMessage has no permitted text")
    return event_id, text


def _assistant_message(row: dict[str, Any]) -> tuple[str, str] | None:
    """Return only an explicitly final visible Responses-style assistant item."""

    if row.get("type") != "response_item":
        return None
    payload = row.get("payload")
    if not isinstance(payload, dict):
        return None
    if payload.get("type") != "message" or payload.get("role") != "assistant":
        return None
    if payload.get("phase") != "final_answer":
        return None
    if payload.get("status") not in {None, "completed"}:
        return None
    if _is_private(payload):
        return None
    event_id = payload.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("supported Codex assistant message lacks an id")
    _require_safe_id(event_id, "turn_id")
    blocks = payload.get("content")
    if not isinstance(blocks, list):
        raise ValueError("supported Codex assistant message lacks content")
    text = "\n".join(
        block["text"]
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") == "output_text"
        and isinstance(block.get("text"), str)
    ).strip()
    if not text:
        raise ValueError("supported Codex assistant message has no visible text")
    return event_id, text


def _is_private(value: dict[str, Any]) -> bool:
    return (
        value.get("private") is True
        or value.get("visibility") == "private"
        or value.get("privacy") in {"private", "exclude"}
    )


def _require_safe_id(value: str, field: str) -> None:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid {field}: {value!r}")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
