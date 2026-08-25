from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cairn.locking import VaultBusyError, vault_writer_lock
from cairn.vault import parse_note

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_ROOT = PROJECT_ROOT / "prototype" / "integration"
sys.path.insert(0, str(INTEGRATION_ROOT))

import integration_adapter
from integration_adapter import (
    CodexCliSemanticProvider,
    DECISION_SCHEMA,
    apply_ingestion,
    collect_events,
    load_decisions,
    normalize_codex,
    normalize_hermes,
)


def _write_jsonl(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")


def _codex_rows(*, thread_source: str = "user") -> list[dict]:
    return [
        {
            "type": "session_meta",
            "payload": {
                "id": "codex-session",
                "cwd": "/workspace/runtime-fit",
                "thread_source": thread_source,
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "<recommended_plugins>injected</recommended_plugins>"}],
            },
        },
        {
            "type": "event_msg",
            "timestamp": "2026-08-23T00:00:00Z",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "UserMessage",
                    "id": "codex-event",
                    "content": [{"type": "text", "text": "Authored Codex memory."}],
                },
            },
        },
    ]


def _hermes_session() -> dict:
    return {
        "id": "hermes-session",
        "cwd": "/workspace/runtime-fit",
        "messages": [
            {"id": 1, "role": "user", "content": "Authored Hermes memory.", "timestamp": 1787484099.0},
            {"id": 2, "role": "assistant", "content": "Not candidate input."},
            {"id": 3, "role": "tool", "content": "Not candidate input."},
        ],
    }


class NormalizerTests(unittest.TestCase):
    def test_codex_uses_only_structural_user_message_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "codex.jsonl"
            _write_jsonl(path, _codex_rows())
            events = normalize_codex(path)
            self.assertEqual([event.text for event in events], ["Authored Codex memory."])
            self.assertNotIn("recommended_plugins", events[0].text)

    def test_codex_windows_cwd_has_stable_project_leaf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "codex.jsonl"
            rows = _codex_rows()
            rows[0]["payload"]["cwd"] = r"C:\workspace\runtime-fit"
            _write_jsonl(path, rows)
            self.assertEqual(normalize_codex(path)[0].project, "runtime-fit")

    def test_codex_subagent_session_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approval-review.jsonl"
            _write_jsonl(path, _codex_rows(thread_source="subagent"))
            self.assertEqual(normalize_codex(path), [])

    def test_hermes_preserves_session_and_message_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hermes.jsonl"
            _write_jsonl(path, [_hermes_session()])
            events = normalize_hermes(path)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].key, ("hermes", "hermes-session", "1"))
            self.assertEqual(events[0].source_uri, "hermes://session/hermes-session/message/1")


class LockedIngestionTests(unittest.TestCase):
    def test_codex_provider_runs_one_pass_and_binds_exact_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rules_path = root / "rules.md"
            rules_path.write_text(
                "Return grounded memory only. Evaluate each event independently.\n",
                encoding="utf-8",
            )
            codex_path = root / "codex.jsonl"
            _write_jsonl(codex_path, _codex_rows())
            events = collect_events([codex_path], [])
            decisions_path = root / "provider-decisions.json"

            def provider_run(command, **kwargs):
                response_path = Path(command[command.index("--output-last-message") + 1])
                response_path.write_text(
                    json.dumps(
                        {
                            "decisions": [
                                {
                                    "event_index": 0,
                                    "content": "The authored Codex memory is durable.",
                                    "intent": "implicit",
                                    "candidate_type": "project_state",
                                    "proposed_scope": "project-specific",
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                self.assertIn("This invocation is the single semantic pass", kwargs["input"])
                self.assertIn("Evaluate each event independently", kwargs["input"])
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            provider = CodexCliSemanticProvider(
                rules_path=rules_path,
                model="test-model",
                executable="codex-test",
            )
            with patch("integration_adapter.subprocess.run", side_effect=provider_run) as run:
                provider.create_decisions(events, decisions_path)
            self.assertEqual(run.call_count, 1)
            semantic_pass, decisions = load_decisions(decisions_path, events)
            self.assertEqual(semantic_pass["passes"], 1)
            self.assertEqual(semantic_pass["provider"], "openai-codex-cli")
            self.assertEqual(decisions[0].event.source_uri, "codex://session/codex-session/event/codex-event")
            self.assertEqual(decisions[0].event.text_sha256, events[0].text_sha256)

    def test_provider_backed_apply_retains_decision_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_path = root / "codex.jsonl"
            _write_jsonl(codex_path, _codex_rows())
            events = collect_events([codex_path], [])
            decisions_path = root / "provider-decisions.json"

            class FixedProvider:
                def create_decisions(self, selected_events, output_path):
                    event = selected_events[0]
                    output_path.write_text(
                        json.dumps(
                            {
                                "schema": DECISION_SCHEMA,
                                "semantic_pass": {
                                    "passes": 1,
                                    "provider": "fixed-provider",
                                    "model": "fixed-test",
                                    "contract": "provider-test",
                                    "performed_at": "2026-08-23T00:00:00Z",
                                },
                                "decisions": [
                                    {
                                        "source": {
                                            "harness": event.harness,
                                            "session_id": event.session_id,
                                            "event_id": event.event_id,
                                            "source_text_sha256": event.text_sha256,
                                        },
                                        "content": "Provider-backed memory.",
                                        "intent": "implicit",
                                        "candidate_type": "project_state",
                                        "proposed_scope": "project-specific",
                                    }
                                ],
                            }
                        ),
                        encoding="utf-8",
                    )

            result = apply_ingestion(
                events=events,
                provider=FixedProvider(),
                semantic_output=decisions_path,
                vault_root=root / "vault",
                state_root=root / "state",
            )
            self.assertTrue(decisions_path.is_file())
            self.assertEqual(result["selected_decisions"], 1)
            self.assertEqual(len(result["written"]), 1)

    def test_decisions_materialize_with_exact_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_path = root / "codex.jsonl"
            hermes_path = root / "hermes.jsonl"
            _write_jsonl(codex_path, _codex_rows())
            _write_jsonl(hermes_path, [_hermes_session()])
            events = collect_events([codex_path], [hermes_path])
            decisions_path = root / "decisions.json"
            decisions_path.write_text(
                json.dumps(
                    {
                        "schema": DECISION_SCHEMA,
                        "semantic_pass": {
                            "passes": 1,
                            "provider": "test",
                            "model": "fixed-test",
                            "contract": "runtime-fit-test",
                            "performed_at": "2026-08-23T00:00:00Z",
                        },
                        "decisions": [
                            {
                                "source": {
                                    "harness": event.harness,
                                    "session_id": event.session_id,
                                    "event_id": event.event_id,
                                    "source_text_sha256": event.text_sha256,
                                },
                                "content": f"Distilled {event.harness} memory.",
                                "intent": "implicit" if event.harness == "codex" else "explicit",
                                "candidate_type": "workflow",
                                "proposed_scope": "owner-global",
                            }
                            for event in events
                        ],
                    }
                ),
                encoding="utf-8",
            )
            real_ingest = integration_adapter.ingest_transcripts

            def ingest_while_locked(*args, **kwargs):
                with self.assertRaises(VaultBusyError):
                    with vault_writer_lock(root / "vault", operation="contention-probe"):
                        pass
                return real_ingest(*args, **kwargs)

            with patch("integration_adapter.ingest_transcripts", side_effect=ingest_while_locked):
                result = apply_ingestion(
                    events=events,
                    decisions_path=decisions_path,
                    vault_root=root / "vault",
                    state_root=root / "state",
                )
            self.assertEqual(result["distiller_calls"], 2)
            self.assertEqual(len(result["written"]), 2)
            notes = [parse_note(Path(path).read_text(encoding="utf-8")) for path in result["written"]]
            self.assertEqual({note.frontmatter["harness"] for note in notes}, {"codex", "hermes"})
            self.assertEqual({note.frontmatter["source_event_id"] for note in notes}, {"codex-event", "1"})
            self.assertTrue(all(note.frontmatter["authority"] == "candidate" for note in notes))
            self.assertTrue(all(note.frontmatter["orca_state"] == "new" for note in notes))

    def test_changed_source_hash_fails_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codex_path = root / "codex.jsonl"
            _write_jsonl(codex_path, _codex_rows())
            events = collect_events([codex_path], [])
            decisions_path = root / "decisions.json"
            decisions_path.write_text(
                json.dumps(
                    {
                        "schema": DECISION_SCHEMA,
                        "semantic_pass": {
                            "passes": 1,
                            "provider": "test",
                            "model": "fixed-test",
                            "contract": "runtime-fit-test",
                            "performed_at": "2026-08-23T00:00:00Z",
                        },
                        "decisions": [
                            {
                                "source": {
                                    "harness": "codex",
                                    "session_id": "codex-session",
                                    "event_id": "codex-event",
                                    "source_text_sha256": "0" * 64,
                                },
                                "content": "Should not write.",
                                "intent": "implicit",
                                "candidate_type": "workflow",
                                "proposed_scope": "owner-global",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "source text changed"):
                apply_ingestion(
                    events=events,
                    decisions_path=decisions_path,
                    vault_root=root / "vault",
                    state_root=root / "state",
                )
            self.assertFalse((root / "vault").exists())


if __name__ == "__main__":
    unittest.main()
