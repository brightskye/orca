from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import normalize_codex_rollout


def _write_rollout(path: Path) -> None:
    rows = [
        {
            "type": "session_meta",
            "payload": {
                "id": "session-123",
                "cwd": "/workspace/projects/orca",
                "thread_source": "user",
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Injected envelope."}],
            },
        },
        {
            "type": "event_msg",
            "timestamp": "2026-08-25T10:00:00Z",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "UserMessage",
                    "id": "event-456",
                    "content": [{"type": "text", "text": "Remember this."}],
                },
            },
        },
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


class CodexCaptureTests(unittest.TestCase):
    def test_direct_normalization_redacts_secret_without_copying_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rollout = root / "rollout.jsonl"
            _write_rollout(rollout)
            content = rollout.read_text(encoding="utf-8").replace(
                "Remember this.", "Remember api_key=super-secret-value."
            )
            rollout.write_text(content, encoding="utf-8")

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertEqual(batch.conversation_id, "session-123")
            self.assertEqual(len(batch.turns), 1)
            self.assertEqual(batch.turns[0].text, "Remember api_key=[REDACTED]")
            self.assertEqual(batch.turns[0].redaction_policy, "orca-secret-containment/0.1")

    def test_only_positive_owner_event_is_normalized_in_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rollout = root / "rollout.jsonl"
            _write_rollout(rollout)

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertEqual(batch.connector_id, "codex-local")
            self.assertEqual(batch.conversation_id, "session-123")
            self.assertEqual(len(batch.turns), 1)
            self.assertEqual(batch.turns[0].turn_id, "event-456")
            self.assertEqual(batch.turns[0].text, "Remember this.")
            self.assertEqual(
                batch.turns[0].content_sha256,
                "dac698d8bd84347024a8b12ece4354dbfba26c4b084d1921e264f9a909b275fd",
            )
            self.assertFalse((root / "conversations").exists())

    def test_repeated_normalization_is_deterministic_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rollout = root / "rollout.jsonl"
            _write_rollout(rollout)

            first = normalize_codex_rollout(rollout, connector_id="codex-local")
            second = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertEqual(second, first)
            self.assertEqual(list(root.iterdir()), [rollout])


if __name__ == "__main__":
    unittest.main()
