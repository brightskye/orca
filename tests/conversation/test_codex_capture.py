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
        {
            "type": "response_item",
            "timestamp": "2026-08-25T10:01:00Z",
            "payload": {
                "type": "message",
                "id": "message-789",
                "status": "completed",
                "role": "assistant",
                "phase": "final_answer",
                "content": [{"type": "output_text", "text": "Visible answer."}],
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
            self.assertEqual(len(batch.turns), 2)
            self.assertEqual(batch.turns[0].text, "Remember api_key=[REDACTED]")
            self.assertEqual(batch.turns[0].source_role, "owner")
            self.assertEqual(batch.turns[1].source_role, "assistant")
            self.assertEqual(batch.turns[0].redaction_policy, "orca-secret-containment/0.1")

    def test_only_positive_owner_event_is_normalized_in_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rollout = root / "rollout.jsonl"
            _write_rollout(rollout)

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertEqual(batch.connector_id, "codex-local")
            self.assertEqual(batch.conversation_id, "session-123")
            self.assertEqual(len(batch.turns), 2)
            self.assertEqual(batch.turns[0].turn_id, "event-456")
            self.assertEqual(batch.turns[0].text, "Remember this.")
            self.assertEqual(
                batch.turns[0].content_sha256,
                "dac698d8bd84347024a8b12ece4354dbfba26c4b084d1921e264f9a909b275fd",
            )
            self.assertFalse((root / "conversations").exists())

    def test_only_explicit_final_assistant_output_is_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            _write_rollout(rollout)
            rows = [json.loads(line) for line in rollout.read_text().splitlines()]
            rows.insert(
                2,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "id": "commentary-1",
                        "status": "completed",
                        "role": "assistant",
                        "phase": "commentary",
                        "content": [{"type": "output_text", "text": "Working."}],
                    },
                },
            )
            rows.insert(
                3,
                {
                    "type": "response_item",
                    "payload": {
                        "type": "reasoning",
                        "id": "reasoning-1",
                        "summary": [{"type": "summary_text", "text": "Hidden."}],
                    },
                },
            )
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertEqual(
                [(turn.source_role, turn.text) for turn in batch.turns],
                [("owner", "Remember this."), ("assistant", "Visible answer.")],
            )

    def test_private_records_and_non_owner_sessions_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rollout = root / "rollout.jsonl"
            _write_rollout(rollout)
            rows = [json.loads(line) for line in rollout.read_text().splitlines()]
            rows[3]["payload"]["private"] = True
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")
            self.assertEqual([turn.source_role for turn in batch.turns], ["owner"])

            rows[0]["payload"]["thread_source"] = "subagent"
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            excluded = normalize_codex_rollout(rollout, connector_id="codex-local")
            self.assertEqual(excluded.conversation_id, "excluded")
            self.assertEqual(excluded.turns, ())

    def test_partial_trailing_record_waits_at_last_complete_byte(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            _write_rollout(rollout)
            complete_size = rollout.stat().st_size
            with rollout.open("ab") as handle:
                handle.write(b'{"type":"event_msg","payload":')

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertTrue(batch.has_partial_tail)
            self.assertEqual(batch.processed_through, complete_size)
            self.assertEqual(len(batch.turns), 2)

    def test_malformed_complete_supported_record_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            _write_rollout(rollout)
            with rollout.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "type": "event_msg",
                            "payload": {
                                "type": "item_completed",
                                "item": {"type": "UserMessage", "content": []},
                            },
                        }
                    )
                    + "\n"
                )

            with self.assertRaisesRegex(ValueError, "lacks an id"):
                normalize_codex_rollout(rollout, connector_id="codex-local")

    def test_duplicate_supported_identity_and_malformed_complete_json_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            _write_rollout(rollout)
            rows = [json.loads(line) for line in rollout.read_text().splitlines()]
            duplicate = json.loads(json.dumps(rows[2]))
            rows.append(duplicate)
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "duplicate Codex"):
                normalize_codex_rollout(rollout, connector_id="codex-local")

            rollout.write_text('{"type":\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                normalize_codex_rollout(rollout, connector_id="codex-local")

    def test_private_session_excludes_all_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            _write_rollout(rollout)
            rows = [json.loads(line) for line in rollout.read_text().splitlines()]
            rows[0]["payload"]["privacy"] = "private"
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )

            batch = normalize_codex_rollout(rollout, connector_id="codex-local")

            self.assertEqual(batch.conversation_id, "session-123")
            self.assertEqual(batch.turns, ())

    def test_start_offset_reads_only_the_requested_complete_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rollout = Path(directory) / "rollout.jsonl"
            _write_rollout(rollout)
            raw_lines = rollout.read_bytes().splitlines(keepends=True)
            assistant_offset = sum(len(line) for line in raw_lines[:3])

            batch = normalize_codex_rollout(
                rollout,
                connector_id="codex-local",
                start_offset=assistant_offset,
            )

            self.assertEqual([turn.source_role for turn in batch.turns], ["assistant"])
            self.assertEqual(batch.processed_through, rollout.stat().st_size)
            with self.assertRaisesRegex(ValueError, "record boundary"):
                normalize_codex_rollout(
                    rollout,
                    connector_id="codex-local",
                    start_offset=assistant_offset + 1,
                )

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
