from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.retry import (
    begin_retry,
    complete_retry,
    create_retry_spool,
    expire_retry,
    load_retry_spool,
)


NOW = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)


def _batch(text: str = "Permitted api_key=[REDACTED]") -> ConversationBatch:
    return ConversationBatch(
        connector_id="codex-local",
        conversation_id="session-123",
        turns=(
            NormalizedTurn(
                connector_id="codex-local",
                conversation_id="session-123",
                turn_id="event-456",
                occurred_at="2026-08-30T11:59:00Z",
                source_uri="codex://session/session-123/event/event-456",
                source_role="owner",
                text=text,
                content_sha256="a" * 64,
            ),
        ),
        processed_through=321,
    )


class RetrySpoolTests(unittest.TestCase):
    def test_spool_contains_only_redacted_normalized_evidence_and_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)

            spool = create_retry_spool(
                _batch(), runtime_dir=runtime, spool_id="retry-1", now=NOW
            )

            self.assertEqual(spool.batch, _batch())
            self.assertEqual(spool.attempts, 0)
            self.assertEqual(spool.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(spool.path.parent.stat().st_mode & 0o777, 0o700)
            raw = spool.path.read_text(encoding="utf-8")
            self.assertIn("[REDACTED]", raw)
            self.assertNotIn("super-secret", raw)

    def test_unredacted_secret_and_unsafe_permissions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            with self.assertRaisesRegex(ValueError, "credential-like"):
                create_retry_spool(
                    _batch("api_key=super-secret-value"),
                    runtime_dir=runtime,
                    spool_id="retry-1",
                    now=NOW,
                )

            spool = create_retry_spool(
                _batch(), runtime_dir=runtime, spool_id="retry-2", now=NOW
            )
            os.chmod(spool.path, 0o644)
            with self.assertRaisesRegex(ValueError, "unsafe retry spool permissions"):
                load_retry_spool(spool.path)

    def test_only_three_automatic_attempts_and_success_removes_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            path = create_retry_spool(
                _batch(), runtime_dir=runtime, spool_id="retry-1", now=NOW
            ).path

            for expected in (1, 2, 3):
                self.assertEqual(begin_retry(path).attempts, expected)
            with self.assertRaisesRegex(ValueError, "attempts exhausted"):
                begin_retry(path)

            complete_retry(path)
            self.assertFalse(path.exists())

    def test_expiry_replaces_content_with_content_free_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            path = create_retry_spool(
                _batch(), runtime_dir=runtime, spool_id="retry-1", now=NOW
            ).path
            with self.assertRaisesRegex(ValueError, "has not expired"):
                expire_retry(path, runtime_dir=runtime, now=NOW + timedelta(hours=71))

            receipt = expire_retry(
                path, runtime_dir=runtime, now=NOW + timedelta(hours=72)
            )

            self.assertFalse(path.exists())
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
            value = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(value["reason"], "retention-expired")
            self.assertNotIn("batch", value)
            self.assertNotIn("text", receipt.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
