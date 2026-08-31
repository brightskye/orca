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
from orca_memory.candidates import CandidateProposal, KnowledgeCandidate, candidate_placement
from orca_memory.cli import main
from orca_memory.configuration import load_configuration
from orca_memory.conflicts import ConflictProposal, start_conflict
from orca_memory.conversation import (
    ConversationBatch,
    NormalizedTurn,
    codex_session_metadata,
)
from orca_memory.interaction import InteractionScope, ObservationProposal
from orca_memory.memory import MemoryRecord, parse_record, record_relative_path
from orca_memory.owner_review import OwnerReviewPublisher
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


class _FlakyProvider(_Provider):
    def distill(self, request):
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("transient provider failure")
        self.calls -= 1
        return super().distill(request)


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
    lifecycle_enabled: bool = False,
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
        "lifecycle": {"enabled": lifecycle_enabled},
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

    def test_cli_records_explicit_general_scope_choice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(root)
            output = io.StringIO()

            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--host-config",
                            str(root / "host.yaml"),
                            "--registered-adapter",
                            "fake-local",
                            "scope",
                            "general",
                            "--conversation-id",
                            "conversation-general",
                        ]
                    ),
                    0,
                )

            self.assertEqual(
                json.loads(output.getvalue()),
                {
                    "conversation_id": "conversation-general",
                    "scope": "general",
                    "stored": True,
                },
            )
            self.assertEqual(
                LocalRuntime(configuration.host.runtime_path).scope_choice(
                    "conversation-general"
                ),
                "general",
            )

    def test_cli_registers_and_relinks_project_roots_recoverably(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _configuration(root)
            first = root / "first-project"
            second = root / "second-checkout"
            first.mkdir()
            second.mkdir()
            common = [
                "--host-config",
                str(root / "host.yaml"),
                "--registered-adapter",
                "fake-local",
            ]
            output = io.StringIO()

            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        common
                        + [
                            "project",
                            "register",
                            "--root",
                            str(first),
                            "--alias",
                            "Orca",
                        ]
                    ),
                    0,
                )
            registration = json.loads(output.getvalue())
            self.assertEqual(registration["action"], "register")
            self.assertEqual(registration["project_alias"], "Orca")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        common
                        + [
                            "project",
                            "relink",
                            "--root",
                            str(second),
                            "--project-id",
                            registration["project_id"],
                        ]
                    ),
                    0,
                )
            relink = json.loads(output.getvalue())
            self.assertEqual(relink["action"], "relink")
            configuration = load_configuration(
                root / "host.yaml",
                registered_provider_adapters={"codex-cli", "fake-local"},
            )
            self.assertEqual(len(configuration.project_registry.records), 1)
            self.assertEqual(len(configuration.host.project_root_mappings), 2)
            self.assertEqual(
                {mapping.project_id for mapping in configuration.host.project_root_mappings},
                {registration["project_id"]},
            )

    def test_cli_worker_drains_multiple_configured_codex_rollouts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root, adapter="codex-cli", model="gpt-5.6-luna"
            )
            common = ["--host-config", str(root / "host.yaml")]
            for index in range(2):
                conversation_id = f"conversation-cli-worker-{index}"
                rollout = root / "rollouts" / f"worker-{index}.jsonl"
                rows = (
                    {
                        "type": "session_meta",
                        "payload": {
                            "id": conversation_id,
                            "thread_source": "user",
                        },
                    },
                    {
                        "type": "event_msg",
                        "timestamp": "2026-08-30T10:00:00Z",
                        "payload": {
                            "type": "item_completed",
                            "item": {
                                "id": f"owner-worker-{index}",
                                "type": "UserMessage",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": f"Keep local runtime item {index} bounded.",
                                    }
                                ],
                            },
                        },
                    },
                )
                rollout.write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
                )
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main(
                            common
                            + [
                                "queue-pointer",
                                "--trigger",
                                "explicit-save",
                                "--conversation-id",
                                conversation_id,
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
                2,
            )
            self.assertEqual(LocalRuntime(configuration.host.runtime_path).pending(), ())

    def test_cli_worker_retries_transient_failure_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root, adapter="codex-cli", model="gpt-5.6-luna"
            )
            rollout = root / "rollouts" / "retry-worker.jsonl"
            rollout.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in (
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "conversation-cli-retry",
                                "thread_source": "user",
                            },
                        },
                        {
                            "type": "event_msg",
                            "payload": {
                                "type": "item_completed",
                                "item": {
                                    "id": "owner-retry",
                                    "type": "UserMessage",
                                    "content": [
                                        {"type": "input_text", "text": "Retry this safely."}
                                    ],
                                },
                            },
                        },
                    )
                ),
                encoding="utf-8",
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
                            "conversation-cli-retry",
                            "--source",
                            str(rollout),
                            "--scope",
                            "general",
                        ]
                    ),
                    0,
                )
            provider = _FlakyProvider()
            delays: list[float] = []
            with patch(
                "orca_memory.cli.CodexCliSemanticProvider", return_value=provider
            ), patch("orca_memory.cli.time.sleep", side_effect=delays.append):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(common + ["worker", "--reasoning-effort", "xhigh"]),
                        0,
                    )

            self.assertEqual(json.loads(output.getvalue()), {"worker": "success"})
            self.assertEqual(provider.calls, 3)
            self.assertEqual(delays, [1.0, 2.0])
            self.assertEqual(LocalRuntime(configuration.host.runtime_path).pending(), ())

    def test_cli_worker_rechecks_disabled_lifecycle_before_automatic_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root, adapter="codex-cli", model="gpt-5.6-luna"
            )
            source = root / "rollouts" / "disabled-worker.jsonl"
            source.write_text("{}\n", encoding="utf-8")
            runtime = LocalRuntime(configuration.host.runtime_path)
            runtime.enqueue_pointer(
                trigger="pre-compact",
                connector_id="codex-local",
                conversation_id="conversation-disabled",
                source_path=source,
                start_offset=0,
                scope_kind="unassigned",
                scope_id="unassigned",
            )
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
                                "worker",
                                "--reasoning-effort",
                                "xhigh",
                            ]
                        ),
                        0,
                    )

            self.assertEqual(json.loads(output.getvalue()), {"worker": "disabled"})
            self.assertEqual(provider.calls, 0)
            self.assertEqual(runtime.pending()[0].attempts, 0)

    def test_cli_catch_up_is_disabled_before_rollout_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _configuration(root, adapter="codex-cli", model="gpt-5.6-luna")
            provider = _Provider()
            with patch(
                "orca_memory.cli.codex_session_metadata",
                side_effect=AssertionError("disabled catch-up accessed rollouts"),
            ), patch("orca_memory.cli.CodexCliSemanticProvider", return_value=provider):
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
                {"configured_interval_minutes": 15, "queued": 0, "worker": "disabled"},
            )
            self.assertEqual(provider.calls, 0)

    def test_cli_catch_up_processes_only_explicitly_scoped_new_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root,
                adapter="codex-cli",
                model="gpt-5.6-luna",
                lifecycle_enabled=True,
            )
            rollout = root / "rollouts" / "catch-up.jsonl"
            rows = (
                {
                    "type": "session_meta",
                    "payload": {
                        "id": "conversation-catch-up",
                        "thread_source": "user",
                        "cwd": str(root),
                    },
                },
                {
                    "type": "event_msg",
                    "timestamp": "2026-08-30T10:00:00Z",
                    "payload": {
                        "type": "item_completed",
                        "item": {
                            "id": "owner-catch-up",
                            "type": "UserMessage",
                            "content": [{"type": "input_text", "text": "Catch up safely."}],
                        },
                    },
                },
            )
            rollout.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            runtime = LocalRuntime(configuration.host.runtime_path)
            runtime.set_scope_choice("conversation-catch-up", "general")
            provider = _Provider()
            command = [
                "--host-config",
                str(root / "host.yaml"),
                "catch-up",
                "--reasoning-effort",
                "xhigh",
                "--max-sources",
                "1",
            ]

            with patch("orca_memory.cli.CodexCliSemanticProvider", return_value=provider):
                first = io.StringIO()
                with redirect_stdout(first):
                    self.assertEqual(main(command), 0)
                second = io.StringIO()
                with redirect_stdout(second):
                    self.assertEqual(main(command), 0)

            self.assertEqual(json.loads(first.getvalue())["queued"], 1)
            self.assertEqual(json.loads(first.getvalue())["worker"], "success")
            self.assertEqual(
                json.loads(second.getvalue()),
                {"configured_interval_minutes": 15, "queued": 0, "worker": "idle"},
            )
            self.assertEqual(provider.calls, 1)
            self.assertEqual(
                runtime.source_offset("codex-local", "conversation-catch-up", rollout),
                rollout.stat().st_size,
            )

    def test_cli_catch_up_skips_unassigned_history_without_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root,
                adapter="codex-cli",
                model="gpt-5.6-luna",
                lifecycle_enabled=True,
            )
            rollout = root / "rollouts" / "unassigned-history.jsonl"
            rollout.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in (
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "conversation-unassigned-history",
                                "thread_source": "user",
                                "cwd": str(root),
                            },
                        },
                        {
                            "type": "event_msg",
                            "payload": {
                                "type": "item_completed",
                                "item": {
                                    "id": "private-owner-history",
                                    "type": "UserMessage",
                                    "content": [
                                        {"type": "input_text", "text": "Do not send this."}
                                    ],
                                },
                            },
                        },
                    )
                ),
                encoding="utf-8",
            )
            provider = _Provider()

            with patch("orca_memory.cli.CodexCliSemanticProvider", return_value=provider):
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
            self.assertEqual(
                LocalRuntime(configuration.host.runtime_path).source_offset(
                    "codex-local", "conversation-unassigned-history", rollout
                ),
                0,
            )

    def test_cli_catch_up_advances_non_owner_history_without_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root,
                adapter="codex-cli",
                model="gpt-5.6-luna",
                lifecycle_enabled=True,
            )
            runtime = LocalRuntime(configuration.host.runtime_path)
            runtime.set_scope_choice("conversation-subagent-history", "general")
            rollout = root / "rollouts" / "subagent-history.jsonl"
            rollout.write_text(
                json.dumps(
                    {
                        "type": "session_meta",
                        "payload": {
                            "id": "conversation-subagent-history",
                            "thread_source": "subagent",
                            "cwd": str(root),
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            provider = _Provider()

            with patch("orca_memory.cli.CodexCliSemanticProvider", return_value=provider):
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

            self.assertEqual(provider.calls, 0)
            self.assertEqual(
                runtime.source_offset(
                    "codex-local", "conversation-subagent-history", rollout
                ),
                rollout.stat().st_size,
            )

    def test_cli_catch_up_rejects_symlink_and_continues_after_malformed_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(
                root,
                adapter="codex-cli",
                model="gpt-5.6-luna",
                lifecycle_enabled=True,
            )
            rollout_root = root / "rollouts"
            outside = root / "outside.jsonl"
            outside.write_text("private outside data\n", encoding="utf-8")
            (rollout_root / "00-outside.jsonl").symlink_to(outside)
            (rollout_root / "01-malformed.jsonl").write_text(
                "not-json\n", encoding="utf-8"
            )
            valid = rollout_root / "02-valid.jsonl"
            valid.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in (
                        {
                            "type": "session_meta",
                            "payload": {
                                "id": "conversation-valid-history",
                                "thread_source": "user",
                                "cwd": str(root),
                            },
                        },
                        {
                            "type": "event_msg",
                            "payload": {
                                "type": "item_completed",
                                "item": {
                                    "id": "owner-valid-history",
                                    "type": "UserMessage",
                                    "content": [
                                        {"type": "input_text", "text": "Safe input."}
                                    ],
                                },
                            },
                        },
                    )
                ),
                encoding="utf-8",
            )
            runtime = LocalRuntime(configuration.host.runtime_path)
            runtime.set_scope_choice("conversation-valid-history", "general")
            provider = _Provider()
            metadata_reads: list[Path] = []

            def guarded_metadata(path: Path):
                self.assertTrue(path.is_relative_to(rollout_root.resolve()))
                metadata_reads.append(path)
                return codex_session_metadata(path)

            with (
                patch("orca_memory.cli.CodexCliSemanticProvider", return_value=provider),
                patch("orca_memory.cli.codex_session_metadata", side_effect=guarded_metadata),
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

            self.assertEqual(json.loads(output.getvalue())["worker"], "success")
            self.assertEqual(provider.calls, 1)
            self.assertNotIn(outside.resolve(), metadata_reads)
            self.assertEqual(
                len(list((configuration.host.runtime_path / "receipts").glob("discovery-*.json"))),
                2,
            )

    def test_cli_candidate_approve_uses_explicit_recoverable_owner_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(root, adapter="codex-cli")
            candidate = KnowledgeCandidate.from_proposal(
                CandidateProposal(
                    "fact",
                    "Release policy",
                    "Use the verified release procedure.",
                    "general",
                    "general",
                ),
                candidate_id="cand_cli_review",
                created_at="2026-08-30T09:00:00Z",
            )
            path = candidate_placement(configuration.host.vault_path, candidate).path
            path.parent.mkdir(parents=True)
            path.write_text(candidate.render(), encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--host-config",
                            str(root / "host.yaml"),
                            "candidate",
                            "approve",
                            "cand_cli_review",
                        ]
                    ),
                    0,
                )

            result = json.loads(output.getvalue())
            self.assertEqual(result["status"], "approved-for-manual-apply")
            self.assertEqual(
                KnowledgeCandidate.parse(path.read_text(encoding="utf-8")).status,
                "approved-for-manual-apply",
            )
            self.assertTrue(
                (configuration.host.vault_path / result["receipt"]).is_file()
            )

    def test_cli_backup_requires_lifecycle_disabled_before_gpg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _configuration(root, adapter="codex-cli", lifecycle_enabled=True)
            with patch(
                "orca_memory.cli.create_backup",
                side_effect=AssertionError("backup ran while lifecycle was enabled"),
            ):
                with self.assertRaisesRegex(ValueError, "disable lifecycle"):
                    main(
                        [
                            "--host-config",
                            str(root / "host.yaml"),
                            "backup",
                            "create",
                            "--recipient",
                            "owner@example.invalid",
                            "--output",
                            str((root / "backup.gpg").resolve()),
                        ]
                    )

    def test_cli_conflict_select_uses_explicit_recoverable_owner_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(root, adapter="codex-cli")
            current = MemoryRecord(
                memory_id="mem_cli_review",
                kind="decision",
                subject="Release route",
                scope="general",
                scope_id="general",
                status="current",
                source_updated_at="2026-08-30T08:00:00Z",
                created_at="2026-08-30T08:00:00Z",
                updated_at="2026-08-30T08:00:00Z",
                current="Use route A.",
            )
            conflict = start_conflict(
                current,
                ConflictProposal(
                    "mem_cli_review",
                    "decision",
                    "Release route",
                    "general",
                    "general",
                    "Route B",
                    "Use route B.",
                    "2026-08-30T09:00:00Z",
                ),
                updated_at="2026-08-30T09:01:00Z",
            )
            path = configuration.host.vault_path / record_relative_path(conflict)
            path.parent.mkdir(parents=True)
            path.write_text(conflict.render(), encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--host-config",
                            str(root / "host.yaml"),
                            "conflict",
                            "select",
                            "mem_cli_review",
                            "--variant",
                            "v2",
                        ]
                    ),
                    0,
                )

            result = json.loads(output.getvalue())
            self.assertEqual(result["outcome"], "selected:v2")
            resolved = parse_record(path.read_text(encoding="utf-8"))
            self.assertEqual(resolved.status, "current")
            self.assertEqual(resolved.current, "Use route B.")
            self.assertTrue(
                (configuration.host.vault_path / result["receipt"]).is_file()
            )

    def test_cli_owner_review_recovery_accepts_only_operation_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configuration = _configuration(root, adapter="codex-cli")
            candidate = KnowledgeCandidate.from_proposal(
                CandidateProposal(
                    "fact", "Recovery", "Recover the fixed plan.", "general", "general"
                ),
                candidate_id="cand_cli_recovery",
                created_at="2026-08-31T09:00:00Z",
            )
            path = candidate_placement(configuration.host.vault_path, candidate).path
            path.parent.mkdir(parents=True)
            path.write_text(candidate.render(), encoding="utf-8")

            def stop(point: str) -> None:
                if point == "after-receipt":
                    raise RuntimeError("stop")

            with self.assertRaises(RuntimeError):
                OwnerReviewPublisher(
                    configuration.host.vault_path,
                    configuration.host.runtime_path,
                    fault=stop,
                ).candidate_disposition(
                    "cand_cli_recovery",
                    target_status="rejected",
                    operation_id="review_cli_recovery",
                    changed_at=datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc),
                )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "--host-config",
                            str(root / "host.yaml"),
                            "recovery",
                            "owner-review",
                            "review_cli_recovery",
                        ]
                    ),
                    0,
                )

            self.assertEqual(json.loads(output.getvalue())["result"], "reconciled")
            self.assertEqual(
                KnowledgeCandidate.parse(path.read_text(encoding="utf-8")).status,
                "rejected",
            )
            with self.assertRaisesRegex(ValueError, "invalid recovery operation"):
                main(
                    [
                        "--host-config",
                        str(root / "host.yaml"),
                        "recovery",
                        "owner-review",
                        "../escape",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
