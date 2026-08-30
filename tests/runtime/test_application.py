from __future__ import annotations

from datetime import datetime, timezone
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from orca_memory.application import LocalOrcaApplication
from orca_memory.cli import main
from orca_memory.configuration import load_configuration
from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.interaction import InteractionScope, ObservationProposal
from orca_memory.processor import ContinuationSummary, ProcessingProposal
from orca_memory.retrieval import RecallRequest
from orca_memory.runtime import LocalRuntime
from orca_memory.storage import MemoryScope


class _Provider:
    name = "fake-local-provider/1"

    def __init__(self) -> None:
        self.calls = 0

    def distill(self, request):
        self.calls += 1
        return ProcessingProposal(
            ContinuationSummary(
                "Orca local loop",
                "The governed local runtime is ready for deterministic verification.",
            ),
            observation_proposals=(
                ObservationProposal(
                    "detail", "status-update", InteractionScope("agent", agent_id="codex"),
                    "explicit-general", "feedback", ("response",), "request",
                    value="concise", lasting=True,
                ),
            ),
        )


def _batch() -> ConversationBatch:
    values = (
        ("request", "owner", "Give a runtime status update."),
        ("response", "assistant", "Here is the detailed runtime status."),
        ("feedback", "owner", "Keep status updates concise from now on."),
    )
    turns = tuple(
        NormalizedTurn(
            "codex-local", "conversation-e2e", turn_id,
            f"2026-08-30T10:0{index}:00Z", f"codex://e2e/{turn_id}", text,
            hashlib.sha256(text.encode()).hexdigest(), source_role=role,
        )
        for index, (turn_id, role, text) in enumerate(values)
    )
    return ConversationBatch("codex-local", "conversation-e2e", turns)


def _configuration(
    root: Path,
    *,
    adapter: str = "fake-local",
    model: str = "synthetic-model",
    new_evidence_tokens: int | None = None,
):
    vault = root / "vault"
    runtime = root / "runtime"
    rollouts = root / "rollouts"
    for path in (vault, runtime, rollouts):
        path.mkdir()
    host = {
        "schema_version": 1,
        "host_id": "synthetic-host",
        "runtime": "wsl",
        "vault_path": str(vault),
        "runtime_path": str(runtime),
        "connectors": {"codex": {"rollout_store": str(rollouts)}},
        "project_root_mappings": [],
    }
    host_path = root / "host.yaml"
    host_path.write_text(yaml.safe_dump(host, sort_keys=False), encoding="utf-8")
    vault_config = {
        "schema_version": "orca-memory-config/0.1",
        "provider": {"adapter": adapter, "model": model},
        "privacy": {"redaction_policy": "orca-secret-containment/0.1"},
        "processing": {"processor_policy": "orca-processor/0.1"},
        "interaction": {
            "observation_policy": "interaction-observation/1",
            "aggregation_policy": "interaction-aggregation/1",
            "guidance_policy": "interaction-guidance/1",
        },
    }
    if new_evidence_tokens is not None:
        vault_config["budgets"] = {
            "processor": {
                "model_window_tokens": 32768,
                "input_tokens": 20000,
                "output_tokens": 4000,
                "new_evidence_tokens": new_evidence_tokens,
                "preceding_overlap_tokens": 1000,
                "continuation_summary_tokens": 2000,
                "project_summary_tokens": 2000,
                "related_records_tokens": 5000,
                "max_related_records": 5,
            },
            "recall": {
                "total_tokens": 4000,
                "per_document_tokens": 1500,
                "exact_continuation_tokens": 2000,
                "max_results": 6,
            },
            "interaction": {"auto_load_tokens": 500},
        }
    path = vault / "System/Orca Memory/orca-memory.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(vault_config, sort_keys=False), encoding="utf-8")
    return load_configuration(
        host_path, environ={}, registered_provider_adapters={adapter}
    )


class ApplicationTests(unittest.TestCase):
    def test_clean_local_process_restart_guidance_recall_and_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(root)
            first_provider = _Provider()
            first = LocalOrcaApplication(
                configuration,
                first_provider,
                clock=lambda: datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
                id_factory=lambda: "e2e-run",
            )
            published = first.process(
                _batch(), scope=MemoryScope("general", "general")
            )
            self.assertEqual(published.status, "success")
            first.recover_and_rebuild()
            startup = first.startup(session_id="session-1", context="status-update")
            self.assertEqual(
                startup.guidance,
                "For status updates, keep the response concise and omit nonessential background.",
            )
            recalled = first.recall(RecallRequest(question="governed local runtime"))
            self.assertTrue(recalled.results)
            self.assertEqual(recalled.results[0].authority, "noncanonical")

            second_provider = _Provider()
            restarted = LocalOrcaApplication(
                configuration,
                second_provider,
                clock=lambda: datetime(2026, 8, 30, 12, 5, tzinfo=timezone.utc),
                id_factory=lambda: "unused-run",
            )
            replay = restarted.process(
                _batch(), scope=MemoryScope("general", "general")
            )
            self.assertEqual(replay.status, "replay")
            self.assertEqual(first_provider.calls, 1)
            self.assertEqual(second_provider.calls, 0)
            self.assertFalse(
                any("canonical" in path.parts for path in configuration.host.vault_path.rglob("*"))
            )

    def test_startup_does_not_require_or_trigger_semantic_recall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = _Provider()
            app = LocalOrcaApplication(_configuration(root), provider)
            startup = app.startup(session_id="session-empty", context="implementation")
            self.assertEqual(startup.guidance, "")
            self.assertIsNone(startup.reminder)
            self.assertEqual(provider.calls, 0)
            self.assertFalse((root / "runtime/retrieval/index.json").exists())

    def test_application_applies_validated_processor_segmentation_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(root, new_evidence_tokens=1)
            provider = _Provider()
            app = LocalOrcaApplication(configuration, provider)
            batch = _batch()
            owner_only = ConversationBatch(
                batch.connector_id, batch.conversation_id, (batch.turns[0],)
            )
            app.process(owner_only, scope=MemoryScope("general", "general"))
            self.assertGreater(provider.calls, 1)

    def test_local_cli_validates_rebuilds_starts_reports_and_stops(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _configuration(root)
            common = [
                "--host-config", str(root / "host.yaml"),
                "--registered-adapter", "fake-local",
            ]
            for command in (
                ["validate"],
                ["health"],
                ["rebuild"],
                ["start", "--session-id", "cli-session", "--context", "general"],
                ["status"],
                ["stop"],
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(main(common + command), 0)
                self.assertTrue(output.getvalue().strip())
            self.assertTrue((root / "runtime/retrieval/index.json").is_file())

    def test_cli_queue_and_worker_process_one_configured_codex_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root, adapter="codex-cli", model="gpt-5.6-luna"
            )
            rollout = root / "rollouts" / "worker.jsonl"
            rows = (
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "conversation-cli-worker",
                        "thread_source": "user",
                    },
                },
                {
                    "type": "event_msg",
                    "timestamp": "2026-08-30T10:00:00Z",
                    "payload": {
                        "type": "item_completed",
                        "item": {
                            "id": "owner-worker-1",
                            "type": "UserMessage",
                            "content": [
                                {"type": "input_text", "text": "Keep the local runtime bounded."}
                            ],
                        },
                    },
                },
            )
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            common = ["--host-config", str(root / "host.yaml")]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        common
                        + [
                            "queue-pointer",
                            "--trigger",
                            "explicit-save",
                            "--conversation-id",
                            "conversation-cli-worker",
                            "--source",
                            str(rollout),
                            "--scope",
                            "general",
                        ]
                    ),
                    0,
                )
            with patch("orca_memory.cli.CodexCliSemanticProvider", return_value=_Provider()) as factory:
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(common + ["worker", "--reasoning-effort", "xhigh"]), 0
                    )
                factory.assert_called_once_with(
                    model="gpt-5.6-luna", reasoning_effort="xhigh"
                )
            self.assertEqual(json.loads(output.getvalue()), {"worker": "success"})
            self.assertEqual(
                len(list(configuration.host.vault_path.rglob("conversation-summaries/*.md"))),
                1,
            )
            self.assertEqual(LocalRuntime(configuration.host.runtime_path).pending(), ())

    def test_cli_catch_up_is_bounded_and_idle_without_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _configuration(root, adapter="codex-cli", model="gpt-5.6-luna")
            provider = _Provider()
            with patch(
                "orca_memory.cli.CodexCliSemanticProvider", return_value=provider
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(
                            [
                                "--host-config",
                                str(root / "host.yaml"),
                                "catch-up",
                                "--reasoning-effort",
                                "xhigh",
                                "--max-sources",
                                "1",
                            ]
                        ),
                        0,
                    )
            self.assertEqual(
                json.loads(output.getvalue()),
                {"configured_interval_minutes": 15, "queued": 0, "worker": "idle"},
            )
            self.assertEqual(provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
