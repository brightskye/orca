from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.retry import create_retry_spool
from orca_memory.runtime import LocalRuntime, WorkItem
from orca_memory.attention import collect_attention


def _batch() -> ConversationBatch:
    text = "Permitted redacted Owner evidence."
    return ConversationBatch(
        "codex-local", "conversation-runtime",
        (
            NormalizedTurn(
                "codex-local", "conversation-runtime", "turn-1",
                "2026-08-30T10:00:00Z", "codex://runtime/turn-1", text,
                hashlib.sha256(text.encode()).hexdigest(),
            ),
        ),
    )


class RuntimeTests(unittest.TestCase):
    def test_work_item_rejects_invalid_trigger_source_kind_and_locator(self) -> None:
        common = (
            "work_safe", "explicit-save", "codex-local", "conversation-runtime",
            "rollout-pointer", "/tmp/rollout.jsonl", 0, "general", "general",
        )
        with self.assertRaisesRegex(ValueError, "invalid runtime work item"):
            WorkItem(common[0], "not-a-trigger", *common[2:])
        with self.assertRaisesRegex(ValueError, "invalid runtime work item"):
            WorkItem(common[0], common[1], common[2], common[3], "not-a-source", *common[5:])
        with self.assertRaisesRegex(ValueError, "absolute path"):
            WorkItem(common[0], common[1], common[2], common[3], common[4], "relative.jsonl", *common[6:])
        with self.assertRaisesRegex(ValueError, "direct private spool path"):
            WorkItem(
                common[0], common[1], common[2], common[3], "retry-spool", "../outside.json",
                *common[6:],
            )

    def test_retry_spool_symlink_cannot_escape_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            outside = Path(directory) / "outside"
            created = datetime(2026, 8, 30, tzinfo=timezone.utc)
            spool = create_retry_spool(
                _batch(), runtime_dir=outside, spool_id="external", now=created
            )
            local_retry = root / "retry-spool"
            local_retry.mkdir(parents=True)
            os.symlink(spool.path, local_retry / "linked.json")
            item = WorkItem(
                "work_link", "session-end", "codex-local", "conversation-runtime",
                "retry-spool", "retry-spool/linked.json", 0, "unassigned", "unassigned",
            )
            runtime = LocalRuntime(root)
            runtime._write_queue(item)

            with self.assertRaisesRegex(ValueError, "escapes the runtime root"):
                runtime.run_once(lambda *_: self.fail("escaped retry spool was opened"))

    def test_retry_spool_directory_symlink_cannot_escape_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            outside = Path(directory) / "outside"
            created = datetime(2026, 8, 30, tzinfo=timezone.utc)
            spool = create_retry_spool(
                _batch(), runtime_dir=outside, spool_id="external", now=created
            )
            root.mkdir(parents=True)
            os.symlink(spool.path.parent, root / "retry-spool")
            item = WorkItem(
                "work_link", "session-end", "codex-local", "conversation-runtime",
                "retry-spool", "retry-spool/external.json", 0, "unassigned", "unassigned",
            )
            runtime = LocalRuntime(root)
            runtime._write_queue(item)

            with self.assertRaisesRegex(ValueError, "escapes the runtime root"):
                runtime.run_once(lambda *_: self.fail("escaped retry spool was opened"))

    def test_expired_retry_spool_is_removed_and_receipt_stays_content_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            created = datetime(2026, 8, 30, tzinfo=timezone.utc)
            expired = datetime(2026, 9, 2, tzinfo=timezone.utc)
            runtime = LocalRuntime(root, clock=lambda: expired)
            item = runtime.enqueue_session_end(
                _batch(), now=created, scope_kind="unassigned", scope_id="unassigned"
            )
            spool_path = root / item.source_locator
            self.assertIn("Permitted redacted Owner evidence.", spool_path.read_text())

            self.assertEqual(
                runtime.run_once(lambda *_: self.fail("expired spool was processed")),
                "failed",
            )

            self.assertFalse(spool_path.exists())
            self.assertEqual(runtime.pending(), ())
            receipt_path = next((root / "receipts").glob("retry-*.json"))
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["reason"], "retention-expired")
            self.assertNotIn("Permitted redacted Owner evidence.", receipt_path.read_text())
            status = collect_attention(root / "vault", root)
            self.assertEqual(status.items[0].item_class, "failed-operation")
            self.assertNotIn("Permitted redacted Owner evidence.", status.render())

    def test_expiry_catches_orphaned_spool_after_retry_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            created = datetime(2026, 8, 30, tzinfo=timezone.utc)
            current = [created]
            runtime = LocalRuntime(root, clock=lambda: current[0])
            item = runtime.enqueue_session_end(
                _batch(), now=created, scope_kind="unassigned", scope_id="unassigned"
            )

            fail = lambda *_: (_ for _ in ()).throw(RuntimeError("private"))
            self.assertEqual(runtime.run_once(fail), "retry")
            self.assertEqual(runtime.run_once(fail), "retry")
            self.assertEqual(runtime.run_once(fail), "failed")
            spool_path = root / item.source_locator
            self.assertTrue(spool_path.exists())

            current[0] = datetime(2026, 9, 2, tzinfo=timezone.utc)
            self.assertEqual(
                runtime.run_once(lambda *_: self.fail("orphaned spool was processed")),
                "failed",
            )
            self.assertFalse(spool_path.exists())

    def test_duplicate_hook_queues_once_and_worker_cleans_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = LocalRuntime(Path(directory))
            first = runtime.enqueue_session_end(
                _batch(), now=datetime(2026, 8, 30, tzinfo=timezone.utc),
                scope_kind="unassigned", scope_id="unassigned",
            )
            second = runtime.enqueue_session_end(
                _batch(), now=datetime(2026, 8, 30, tzinfo=timezone.utc),
                scope_kind="unassigned", scope_id="unassigned",
            )
            calls = []
            self.assertEqual(first, second)
            self.assertEqual(len(runtime.pending()), 1)
            self.assertEqual(runtime.run_once(lambda item, batch: calls.append((item, batch))), "success")
            self.assertEqual(len(calls), 1)
            self.assertEqual(runtime.pending(), ())
            self.assertFalse((Path(directory) / first.source_locator).exists())

    def test_crash_retries_three_times_then_content_free_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = LocalRuntime(root)
            runtime.enqueue_pointer(
                trigger="explicit-save", connector_id="codex-local",
                conversation_id="conversation-runtime", source_path=root / "rollout.jsonl",
                start_offset=0, scope_kind="general", scope_id="general",
            )
            def fail(item, batch):
                raise RuntimeError("private failure detail")
            self.assertEqual(runtime.run_once(fail), "retry")
            self.assertEqual(runtime.run_once(fail), "retry")
            self.assertEqual(runtime.run_once(fail), "failed")
            receipt = next((root / "receipts").glob("failure-*.json")).read_text()
            self.assertNotIn("private failure", receipt)
            self.assertEqual(runtime.pending(), ())
            status = collect_attention(root / "vault", root)
            self.assertEqual(status.items[0].item_class, "failed-operation")
            self.assertNotIn("private failure", status.render())

    def test_lock_contention_and_idle_make_no_handler_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = LocalRuntime(root)
            lock = root / "locks/processor.lock"
            lock.parent.mkdir(parents=True)
            descriptor = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                self.assertEqual(runtime.run_once(lambda *_: self.fail("called")), "locked")
            finally:
                os.close(descriptor)
            self.assertEqual(runtime.run_once(lambda *_: self.fail("called")), "idle")

    def test_catch_up_uses_same_path_and_empty_discovery_is_idle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = LocalRuntime(root)
            calls = []
            self.assertEqual(runtime.catch_up(lambda: (), lambda *_: calls.append(1)), "idle")
            item = WorkItem(
                "work_catch", "catch-up", "codex-local", "conversation-runtime",
                "rollout-pointer", str(root / "rollout.jsonl"), 0,
                "unassigned", "unassigned",
            )
            self.assertEqual(
                runtime.catch_up(lambda: (item,), lambda work, batch: calls.append(work.work_id)),
                "success",
            )
            self.assertEqual(calls, ["work_catch"])


if __name__ == "__main__":
    unittest.main()
