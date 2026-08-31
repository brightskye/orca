"""Private one-shot runtime handoff, queue, lock, and catch-up primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Callable, Literal

from orca_memory.conversation import ConversationBatch
from orca_memory.retry import (
    begin_retry,
    complete_retry,
    create_retry_spool,
    expire_retry,
    load_retry_spool,
)


WORK_SCHEMA = "orca-runtime-work/0.1"
SCOPE_CHOICE_SCHEMA = "orca-conversation-scope-choice/0.1"
SOURCE_CURSOR_SCHEMA = "orca-source-cursor/0.1"
_TRIGGERS = frozenset({"pre-compact", "session-end", "explicit-save", "catch-up"})
_SOURCE_KINDS = frozenset({"rollout-pointer", "retry-spool"})
_SAFE_WORK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_SPOOL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json$")


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    trigger: Literal["pre-compact", "session-end", "explicit-save", "catch-up"]
    connector_id: str
    conversation_id: str
    source_kind: Literal["rollout-pointer", "retry-spool"]
    source_locator: str
    start_offset: int
    scope_kind: Literal["project", "general", "unassigned"]
    scope_id: str
    project_alias: str | None = None
    attempts: int = 0
    schema: str = WORK_SCHEMA

    def __post_init__(self) -> None:
        if (
            self.schema != WORK_SCHEMA
            or not isinstance(self.work_id, str)
            or not _SAFE_WORK_ID.fullmatch(self.work_id)
            or not isinstance(self.trigger, str)
            or self.trigger not in _TRIGGERS
            or not isinstance(self.connector_id, str)
            or not self.connector_id.strip()
            or not isinstance(self.conversation_id, str)
            or not self.conversation_id.strip()
            or not isinstance(self.source_kind, str)
            or self.source_kind not in _SOURCE_KINDS
            or not isinstance(self.source_locator, str)
            or not self.source_locator
            or "\x00" in self.source_locator
            or not isinstance(self.start_offset, int)
            or isinstance(self.start_offset, bool)
            or self.start_offset < 0
            or not isinstance(self.attempts, int)
            or isinstance(self.attempts, bool)
            or not 0 <= self.attempts <= 3
        ):
            raise ValueError("invalid runtime work item")
        if self.source_kind == "rollout-pointer":
            if not Path(self.source_locator).is_absolute():
                raise ValueError("rollout pointer must be an absolute path")
        elif not _valid_retry_locator(self.source_locator):
            raise ValueError("retry spool locator must be a direct private spool path")
        if not isinstance(self.scope_kind, str) or not isinstance(self.scope_id, str):
            raise ValueError("runtime scope identity must be text")
        if self.project_alias is not None and not isinstance(self.project_alias, str):
            raise ValueError("runtime project alias must be text")
        if self.scope_kind == "project":
            if not self.scope_id or not self.project_alias or not self.project_alias.strip():
                raise ValueError("project work requires identity and alias")
        elif self.scope_kind in {"general", "unassigned"}:
            if self.scope_id != self.scope_kind or self.project_alias is not None:
                raise ValueError("fixed runtime scope is invalid")
        else:
            raise ValueError("unsupported runtime scope")

    def value_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


class LocalRuntime:
    """Coordinate bounded hooks through one recoverable local worker path."""

    def __init__(
        self,
        runtime_root: Path,
        *,
        max_attempts: int = 3,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.runtime_root = runtime_root.resolve()
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool) or not 1 <= max_attempts <= 3:
            raise ValueError("Phase 1 runtime allows at most three attempts")
        self.max_attempts = max_attempts
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def enqueue_pointer(
        self,
        *,
        trigger: Literal["pre-compact", "explicit-save", "catch-up"],
        connector_id: str,
        conversation_id: str,
        source_path: Path,
        start_offset: int,
        scope_kind: Literal["project", "general", "unassigned"],
        scope_id: str,
        project_alias: str | None = None,
    ) -> WorkItem:
        if not source_path.is_absolute():
            raise ValueError("runtime source pointer must be absolute")
        identity = _work_id(connector_id, conversation_id, str(source_path.resolve()), start_offset)
        item = WorkItem(
            identity, trigger, connector_id, conversation_id, "rollout-pointer",
            str(source_path.resolve()), start_offset, scope_kind, scope_id, project_alias,
        )
        self._write_queue(item)
        return item

    def enqueue_session_end(
        self,
        batch: ConversationBatch,
        *,
        now: datetime,
        scope_kind: Literal["project", "general", "unassigned"],
        scope_id: str,
        project_alias: str | None = None,
        retention_hours: int = 72,
    ) -> WorkItem:
        digest = hashlib.sha256(
            "\0".join((batch.connector_id, batch.conversation_id, *(turn.content_sha256 for turn in batch.turns))).encode()
        ).hexdigest()[:24]
        spool_id = f"spool_{digest}"
        spool_path = self.runtime_root / "retry-spool" / f"{spool_id}.json"
        if not spool_path.exists():
            create_retry_spool(
                batch, runtime_dir=self.runtime_root, spool_id=spool_id,
                now=now, retention_hours=retention_hours,
            )
        item = WorkItem(
            f"work_{digest}", "session-end", batch.connector_id, batch.conversation_id,
            "retry-spool", spool_path.relative_to(self.runtime_root).as_posix(), 0,
            scope_kind, scope_id, project_alias,
        )
        self._write_queue(item)
        return item

    def pending(self) -> tuple[WorkItem, ...]:
        root = self._queue_root()
        if not root.exists():
            return ()
        return tuple(_load_work(path) for path in sorted(root.glob("*.json")))

    def set_scope_choice(
        self,
        conversation_id: str,
        scope_kind: Literal["general", "unassigned"],
    ) -> Path:
        """Record one explicit Owner scope choice without conversation content."""

        path = self._scope_choice_path(conversation_id)
        if scope_kind not in {"general", "unassigned"}:
            raise ValueError("conversation scope choice must be general or unassigned")
        _write_private(
            path,
            {
                "schema": SCOPE_CHOICE_SCHEMA,
                "conversation_id": conversation_id,
                "scope_kind": scope_kind,
            },
            exclusive=False,
        )
        return path

    def scope_choice(
        self, conversation_id: str
    ) -> Literal["general", "unassigned"] | None:
        """Load an explicit Owner scope choice, if one exists."""

        path = self._scope_choice_path(conversation_id)
        if not path.exists():
            return None
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError("unsafe conversation scope choice")
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or set(value) != {"schema", "conversation_id", "scope_kind"}
            or value.get("schema") != SCOPE_CHOICE_SCHEMA
            or value.get("conversation_id") != conversation_id
            or value.get("scope_kind") not in {"general", "unassigned"}
        ):
            raise ValueError("invalid conversation scope choice")
        return value["scope_kind"]

    def source_offset(
        self,
        connector_id: str,
        conversation_id: str,
        source_path: Path,
    ) -> int:
        """Return the last durably handed-off complete source byte offset."""

        path = self._source_cursor_path(connector_id, conversation_id, source_path)
        if not path.exists():
            return 0
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError("unsafe source cursor")
        value = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "schema",
            "connector_id",
            "conversation_id",
            "source_path",
            "processed_through",
        }
        if (
            not isinstance(value, dict)
            or set(value) != expected
            or value.get("schema") != SOURCE_CURSOR_SCHEMA
            or value.get("connector_id") != connector_id
            or value.get("conversation_id") != conversation_id
            or value.get("source_path") != str(source_path.resolve())
            or not isinstance(value.get("processed_through"), int)
            or isinstance(value.get("processed_through"), bool)
            or value["processed_through"] < 0
        ):
            raise ValueError("invalid source cursor")
        return value["processed_through"]

    def advance_source_offset(
        self,
        connector_id: str,
        conversation_id: str,
        source_path: Path,
        processed_through: int,
    ) -> Path:
        """Advance one source cursor monotonically after durable handoff."""

        if (
            not isinstance(processed_through, int)
            or isinstance(processed_through, bool)
            or processed_through < 0
        ):
            raise ValueError("source cursor offset must be nonnegative")
        current = self.source_offset(connector_id, conversation_id, source_path)
        if processed_through < current:
            raise ValueError("source cursor cannot move backward")
        path = self._source_cursor_path(connector_id, conversation_id, source_path)
        _write_private(
            path,
            {
                "schema": SOURCE_CURSOR_SCHEMA,
                "connector_id": connector_id,
                "conversation_id": conversation_id,
                "source_path": str(source_path.resolve()),
                "processed_through": processed_through,
            },
            exclusive=False,
        )
        return path

    def record_discovery_failure(self, source_path: Path) -> str:
        """Record one content-free catch-up discovery failure."""

        failure_id = self._discovery_failure_id(source_path)
        path = self.runtime_root / "receipts" / f"discovery-{failure_id}.json"
        _write_private(
            path,
            {
                "schema": "orca-runtime-discovery-failure/0.1",
                "failure_id": failure_id,
                "reason": "invalid-source",
            },
            exclusive=False,
        )
        return failure_id

    def clear_discovery_failure(self, source_path: Path) -> None:
        """Clear a discovery receipt after the same source validates again."""

        failure_id = self._discovery_failure_id(source_path)
        path = self.runtime_root / "receipts" / f"discovery-{failure_id}.json"
        if path.exists():
            path.unlink()

    def run_once(
        self,
        handler: Callable[[WorkItem, ConversationBatch | None], None],
        *,
        should_process: Callable[[WorkItem], bool] | None = None,
    ) -> Literal["idle", "locked", "success", "retry", "failed", "disabled"]:
        lock_path = self.runtime_root / "locks" / "processor.lock"
        lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "locked"
            pending = self.pending()
            protected_retry_locators = {
                item.source_locator
                for item in pending
                if item.source_kind == "retry-spool"
            }
            expired_orphans = self._expire_orphan_retry_spools(protected_retry_locators)
            if not pending:
                return "failed" if expired_orphans else "idle"
            item = pending[0]
            if should_process is not None and not should_process(item):
                return "disabled"
            queue_path = self._queue_path(item.work_id)
            batch = None
            if item.source_kind == "retry-spool":
                spool_path = self._retry_spool_path(item.source_locator)
                spool = load_retry_spool(spool_path)
                now = self._now()
                if _expired(spool.expires_at, now):
                    expire_retry(spool_path, runtime_dir=self.runtime_root, now=now)
                    queue_path.unlink()
                    return "failed"
                if spool.attempts >= self.max_attempts:
                    self._write_failure_receipt(item, spool.attempts)
                    queue_path.unlink()
                    return "failed"
                spool = begin_retry(spool_path)
                batch = spool.batch
                attempts = spool.attempts
            else:
                if item.attempts >= self.max_attempts:
                    self._write_failure_receipt(item, item.attempts)
                    queue_path.unlink()
                    return "failed"
                attempts = item.attempts + 1
            attempted = WorkItem(**{**item.value_dict(), "attempts": attempts})
            _write_private(queue_path, attempted.value_dict(), exclusive=False)
            try:
                handler(attempted, batch)
            except Exception:
                if attempts >= self.max_attempts:
                    self._write_failure_receipt(item, attempts)
                    queue_path.unlink()
                    return "failed"
                return "retry"
            if item.source_kind == "retry-spool":
                complete_retry(self._retry_spool_path(item.source_locator))
            queue_path.unlink()
            return "success"
        finally:
            os.close(descriptor)

    def run_bounded(
        self,
        handler: Callable[[WorkItem, ConversationBatch | None], None],
        *,
        max_items: int = 20,
        should_process: Callable[[WorkItem], bool] | None = None,
    ) -> Literal[
        "idle", "locked", "success", "retry", "failed", "pending", "disabled"
    ]:
        """Process queued work until empty, blocked, or the safety limit is reached."""

        if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items <= 0:
            raise ValueError("worker max_items must be positive")
        completed = 0
        failed = False
        while completed < max_items:
            result = self.run_once(handler, should_process=should_process)
            if result == "success":
                completed += 1
                continue
            if result == "failed":
                completed += 1
                failed = True
                continue
            if result == "idle":
                if failed:
                    return "failed"
                return "success" if completed else "idle"
            return result
        if self.pending():
            return "pending"
        return "failed" if failed else "success"

    def catch_up(
        self,
        discover: Callable[[], tuple[WorkItem, ...]],
        handler: Callable[[WorkItem, ConversationBatch | None], None],
    ) -> Literal[
        "idle", "locked", "success", "retry", "failed", "pending", "disabled"
    ]:
        discovered = discover()
        for item in discovered:
            if item.trigger != "catch-up":
                raise ValueError("catch-up discovery returned another trigger")
            self._write_queue(item)
        return self.run_bounded(handler)

    def _write_queue(self, item: WorkItem) -> None:
        path = self._queue_path(item.work_id)
        if path.exists():
            current = _load_work(path)
            comparable = {key: value for key, value in current.value_dict().items() if key != "attempts"}
            proposed = {key: value for key, value in item.value_dict().items() if key != "attempts"}
            if comparable != proposed:
                raise ValueError("duplicate runtime work identity conflicts")
            return
        _write_private(path, item.value_dict(), exclusive=True)

    def _queue_path(self, work_id: str) -> Path:
        queue_root = self._queue_root()
        path = (queue_root / f"{work_id}.json").resolve(strict=False)
        if path.parent != queue_root:
            raise ValueError("runtime queue path escapes the runtime root")
        return path

    def _queue_root(self) -> Path:
        configured = self.runtime_root / "queue"
        queue_root = configured.resolve(strict=False)
        if queue_root.parent != self.runtime_root:
            raise ValueError("runtime queue path escapes the runtime root")
        return queue_root

    def _scope_choice_path(self, conversation_id: str) -> Path:
        if not isinstance(conversation_id, str) or not _SAFE_WORK_ID.fullmatch(conversation_id):
            raise ValueError("invalid conversation identity for scope choice")
        root = (self.runtime_root / "scope-choices").resolve(strict=False)
        if root.parent != self.runtime_root:
            raise ValueError("runtime scope-choice path escapes the runtime root")
        path = (root / f"{conversation_id}.json").resolve(strict=False)
        if path.parent != root:
            raise ValueError("runtime scope-choice path escapes the runtime root")
        return path

    def _source_cursor_path(
        self,
        connector_id: str,
        conversation_id: str,
        source_path: Path,
    ) -> Path:
        if (
            not isinstance(connector_id, str)
            or not _SAFE_WORK_ID.fullmatch(connector_id)
            or not isinstance(conversation_id, str)
            or not _SAFE_WORK_ID.fullmatch(conversation_id)
            or not source_path.is_absolute()
        ):
            raise ValueError("invalid source cursor identity")
        root = (self.runtime_root / "source-cursors").resolve(strict=False)
        if root.parent != self.runtime_root:
            raise ValueError("runtime source-cursor path escapes the runtime root")
        digest = hashlib.sha256(
            json.dumps(
                [connector_id, conversation_id, str(source_path.resolve())],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        path = (root / f"{digest}.json").resolve(strict=False)
        if path.parent != root:
            raise ValueError("runtime source-cursor path escapes the runtime root")
        return path

    def _discovery_failure_id(self, source_path: Path) -> str:
        if not isinstance(source_path, Path) or not source_path.is_absolute():
            raise ValueError("discovery source path must be absolute")
        return hashlib.sha256(str(source_path.resolve(strict=False)).encode()).hexdigest()[:24]

    def _retry_spool_path(self, locator: str) -> Path:
        if not _valid_retry_locator(locator):
            raise ValueError("retry spool locator is invalid")
        path = (self.runtime_root / Path(*PurePosixPath(locator).parts)).resolve(strict=False)
        retry_root = self._retry_root()
        if path.parent != retry_root:
            raise ValueError("retry spool path escapes the runtime root")
        return path

    def _retry_root(self) -> Path:
        configured = self.runtime_root / "retry-spool"
        retry_root = configured.resolve(strict=False)
        if retry_root.parent != self.runtime_root:
            raise ValueError("retry spool path escapes the runtime root")
        return retry_root

    def _expire_orphan_retry_spools(self, protected_locators: set[str]) -> bool:
        root = self._retry_root()
        if not root.exists():
            return False
        now = self._now()
        expired = False
        for path in sorted(root.glob("*.json")):
            locator = PurePosixPath("retry-spool", path.name).as_posix()
            if locator in protected_locators:
                continue
            spool_path = self._retry_spool_path(locator)
            spool = load_retry_spool(spool_path)
            if _expired(spool.expires_at, now):
                expire_retry(spool_path, runtime_dir=self.runtime_root, now=now)
                expired = True
        return expired

    def _now(self) -> datetime:
        now = self._clock()
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("runtime clock must return a timezone-aware datetime")
        return now

    def _write_failure_receipt(self, item: WorkItem, attempts: int) -> None:
        receipt = {
            "schema": "orca-runtime-failure/0.1",
            "work_id": item.work_id,
            "reason": "attempts-exhausted",
            "attempts": attempts,
        }
        path = self.runtime_root / "receipts" / f"failure-{item.work_id}.json"
        if not path.exists():
            _write_private(path, receipt, exclusive=True)


def _work_id(connector_id: str, conversation_id: str, locator: str, offset: int) -> str:
    digest = hashlib.sha256(
        json.dumps([connector_id, conversation_id, locator, offset], separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return f"work_{digest}"


def _load_work(path: Path) -> WorkItem:
    if path.is_symlink():
        raise ValueError("runtime queue symlinks are not permitted")
    if path.stat().st_mode & 0o077:
        raise ValueError("unsafe runtime queue permissions")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != set(WorkItem.__dataclass_fields__):
        raise ValueError("invalid runtime queue schema")
    return WorkItem(**value)


def _valid_retry_locator(locator: str) -> bool:
    parsed = PurePosixPath(locator)
    return (
        not parsed.is_absolute()
        and len(parsed.parts) == 2
        and parsed.parts[0] == "retry-spool"
        and bool(_SAFE_SPOOL_NAME.fullmatch(parsed.parts[1]))
    )


def _expired(expires_at: str, now: datetime) -> bool:
    try:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid retry spool expiry") from exc
    if expires.tzinfo is None:
        raise ValueError("retry spool expiry must be timezone-aware")
    return now.astimezone(timezone.utc) >= expires.astimezone(timezone.utc)


def _write_private(path: Path, value: object, *, exclusive: bool) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


__all__ = [
    "LocalRuntime",
    "SCOPE_CHOICE_SCHEMA",
    "SOURCE_CURSOR_SCHEMA",
    "WorkItem",
    "WORK_SCHEMA",
]
