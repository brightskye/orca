"""Private redacted retry-spool primitives for the Conversation boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.privacy import contains_secret


RETRY_SPOOL_SCHEMA = "orca-retry-spool/0.1"
RETRY_RECEIPT_SCHEMA = "orca-retry-receipt/0.1"
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETENTION_HOURS = 72
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class RetrySpool:
    path: Path
    batch: ConversationBatch
    attempts: int
    created_at: str
    expires_at: str


def create_retry_spool(
    batch: ConversationBatch,
    *,
    runtime_dir: Path,
    spool_id: str,
    now: datetime,
    retention_hours: int = DEFAULT_RETENTION_HOURS,
) -> RetrySpool:
    """Persist only permitted redacted unprocessed evidence with mode 0600."""

    _require_safe_id(spool_id)
    if not batch.turns:
        raise ValueError("retry spool requires permitted unprocessed evidence")
    if retention_hours <= 0:
        raise ValueError("retention_hours must be positive")
    if any(contains_secret(turn.text) for turn in batch.turns):
        raise ValueError("retry spool contains credential-like text")
    created = _utc(now)
    expires = created + timedelta(hours=retention_hours)
    path = runtime_dir / "retry-spool" / f"{spool_id}.json"
    payload = {
        "schema": RETRY_SPOOL_SCHEMA,
        "attempts": 0,
        "created_at": _format_time(created),
        "expires_at": _format_time(expires),
        "batch": _batch_payload(batch),
    }
    _write_private_json(path, payload, exclusive=True)
    return load_retry_spool(path)


def load_retry_spool(path: Path) -> RetrySpool:
    """Load and validate a private retry spool without relaxing permissions."""

    if path.stat().st_mode & 0o077:
        raise ValueError(f"unsafe retry spool permissions: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != RETRY_SPOOL_SCHEMA:
        raise ValueError("invalid retry spool schema")
    attempts = value.get("attempts")
    if not isinstance(attempts, int) or not 0 <= attempts <= DEFAULT_MAX_ATTEMPTS:
        raise ValueError("invalid retry spool attempts")
    batch = _parse_batch(value.get("batch"))
    if any(contains_secret(turn.text) for turn in batch.turns):
        raise ValueError("retry spool contains credential-like text")
    created_at = value.get("created_at")
    expires_at = value.get("expires_at")
    if not isinstance(created_at, str) or not isinstance(expires_at, str):
        raise ValueError("invalid retry spool timestamps")
    _parse_time(created_at)
    _parse_time(expires_at)
    return RetrySpool(path, batch, attempts, created_at, expires_at)


def begin_retry(path: Path) -> RetrySpool:
    """Claim one of the three automatic attempts before invoking the worker."""

    spool = load_retry_spool(path)
    if spool.attempts >= DEFAULT_MAX_ATTEMPTS:
        raise ValueError("retry spool automatic attempts exhausted")
    value = json.loads(path.read_text(encoding="utf-8"))
    value["attempts"] = spool.attempts + 1
    _write_private_json(path, value, exclusive=False)
    return load_retry_spool(path)


def complete_retry(path: Path) -> None:
    """Delete redacted retry content only after the caller's durable success."""

    load_retry_spool(path)
    path.unlink()


def expire_retry(path: Path, *, runtime_dir: Path, now: datetime) -> Path:
    """Replace expired retry content with a content-free local receipt."""

    spool = load_retry_spool(path)
    expired_at = _utc(now)
    if expired_at < _parse_time(spool.expires_at):
        raise ValueError("retry spool retention has not expired")
    receipt_id = hashlib.sha256(path.name.encode("utf-8")).hexdigest()[:16]
    receipt_path = runtime_dir / "receipts" / f"retry-{receipt_id}.json"
    _write_private_json(
        receipt_path,
        {
            "schema": RETRY_RECEIPT_SCHEMA,
            "receipt_id": receipt_id,
            "reason": "retention-expired",
            "attempts": spool.attempts,
            "expired_at": _format_time(expired_at),
        },
        exclusive=True,
    )
    path.unlink()
    return receipt_path


def _batch_payload(batch: ConversationBatch) -> dict[str, Any]:
    return {
        "connector_id": batch.connector_id,
        "conversation_id": batch.conversation_id,
        "processed_through": batch.processed_through,
        "has_partial_tail": batch.has_partial_tail,
        "turns": [asdict(turn) for turn in batch.turns],
    }


def _parse_batch(value: object) -> ConversationBatch:
    if not isinstance(value, dict):
        raise ValueError("invalid retry spool batch")
    connector_id = value.get("connector_id")
    conversation_id = value.get("conversation_id")
    processed_through = value.get("processed_through", 0)
    has_partial_tail = value.get("has_partial_tail", False)
    if not isinstance(connector_id, str) or not _SAFE_ID.fullmatch(connector_id):
        raise ValueError("invalid retry spool connector identity")
    if not isinstance(conversation_id, str) or not _SAFE_ID.fullmatch(conversation_id):
        raise ValueError("invalid retry spool conversation identity")
    if not isinstance(processed_through, int) or processed_through < 0:
        raise ValueError("invalid retry spool source position")
    if not isinstance(has_partial_tail, bool):
        raise ValueError("invalid retry spool partial-tail state")
    turns_value = value.get("turns")
    if not isinstance(turns_value, list):
        raise ValueError("invalid retry spool turns")
    try:
        turns = tuple(NormalizedTurn(**turn) for turn in turns_value)
        for turn in turns:
            if turn.source_role not in {"owner", "assistant"}:
                raise ValueError("invalid retry spool source role")
            if not re.fullmatch(r"[0-9a-f]{64}", turn.content_sha256):
                raise ValueError("invalid retry spool content hash")
        return ConversationBatch(
            connector_id=connector_id,
            conversation_id=conversation_id,
            turns=turns,
            processed_through=processed_through,
            has_partial_tail=has_partial_tail,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid retry spool batch") from exc


def _write_private_json(path: Path, value: object, *, exclusive: bool) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    if exclusive:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def _require_safe_id(value: str) -> None:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"invalid spool_id: {value!r}")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("retry timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("retry timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)
