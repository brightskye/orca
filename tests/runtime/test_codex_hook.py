from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from orca_memory.attention import OrcaStatus
from orca_memory.application import StartupContext
from orca_memory.codex_hook import handle_payload, main
from orca_memory.configuration import load_configuration
from orca_memory.conversation import normalize_codex_rollout
from orca_memory.provenance import segmented_source
from orca_memory.segmentation import segment_turn_with_budget


def _configuration(root: Path, *, lifecycle_enabled: bool = True) -> Path:
    vault = root / "vault"
    runtime = root / "runtime"
    rollouts = root / "rollouts"
    for path in (vault, runtime, rollouts):
        path.mkdir()
    host_path = root / "config" / "host.yaml"
    host_path.parent.mkdir()
    host_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "host_id": "hook-test-host",
                "runtime": "wsl",
                "vault_path": str(vault),
                "runtime_path": str(runtime),
                "connectors": {"codex": {"rollout_store": str(rollouts)}},
                "project_root_mappings": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    vault_config = vault / "System" / "Orca Memory" / "orca-memory.yaml"
    vault_config.parent.mkdir(parents=True)
    vault_config.write_text(
        yaml.safe_dump(
            {
                "schema_version": "orca-memory-config/0.1",
                "provider": {"adapter": "codex-cli", "model": "gpt-5.6-luna"},
                "lifecycle": {"enabled": lifecycle_enabled},
                "privacy": {"redaction_policy": "orca-secret-containment/0.1"},
                "processing": {"processor_policy": "orca-processor/0.1"},
                "interaction": {
                    "observation_policy": "interaction-observation/1",
                    "aggregation_policy": "interaction-aggregation/1",
                    "guidance_policy": "interaction-guidance/1",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    load_configuration(
        host_path, environ={}, registered_provider_adapters={"codex-cli"}
    )
    return host_path


def _write_rollout(path: Path) -> None:
    rows = [
        {
            "type": "session_meta",
            "payload": {"id": "hook-session", "thread_source": "user"},
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "UserMessage",
                    "id": "old-turn",
                    "content": [{"type": "input_text", "text": "Already handled."}],
                },
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "UserMessage",
                    "id": "new-turn",
                    "content": [{"type": "input_text", "text": "Store api_key=secret-value."}],
                },
            },
        },
    ]
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def _payload(event: str, rollout: Path, cwd: Path) -> dict[str, object]:
    value: dict[str, object] = {
        "session_id": "hook-session",
        "transcript_path": str(rollout),
        "cwd": str(cwd),
        "hook_event_name": event,
    }
    if event == "PreCompact":
        value.update(
            {
                "model": "gpt-5.6-luna",
                "trigger": "auto",
                "turn_id": "turn-hook",
            }
        )
    elif event == "SessionEnd":
        value["reason"] = "other"
    else:
        value.update(
            {
                "model": "gpt-5.6-luna",
                "permission_mode": "default",
                "source": "startup",
            }
        )
    return value


class CodexHookTests(unittest.TestCase):
    def test_example_hook_configuration_is_bounded(self) -> None:
        repository_root = Path(__file__).resolve().parents[2]
        example_path = repository_root / "config" / "codex-hooks.example.json"
        installed_path = repository_root / ".codex" / "hooks.json"
        configuration = json.loads(example_path.read_text(encoding="utf-8"))

        self.assertEqual(
            json.loads(installed_path.read_text(encoding="utf-8")),
            configuration,
        )
        self.assertEqual(
            set(configuration["hooks"]),
            {"SessionStart", "PreCompact", "SessionEnd"},
        )
        expected = {
            "SessionStart": ("startup|resume|compact", 10),
            "PreCompact": ("manual|auto", 10),
            "SessionEnd": ("other", 3),
        }
        for event, (matcher, timeout) in expected.items():
            entry = configuration["hooks"][event][0]
            command = entry["hooks"][0]
            self.assertEqual(entry["matcher"], matcher)
            self.assertEqual(command["type"], "command")
            self.assertEqual(command["timeout"], timeout)
            self.assertEqual(
                command["command"],
                'uv run --project "$(git rev-parse --show-toplevel)" orca-codex-hook',
            )

    def test_disabled_lifecycle_noops_before_transcript_access_or_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root, lifecycle_enabled=False)
            payload = _payload("SessionEnd", root / "not-readable.jsonl", root)

            with patch(
                "orca_memory.codex_hook.normalize_codex_rollout",
                side_effect=AssertionError("disabled lifecycle accessed transcript"),
            ):
                result = handle_payload(
                    payload,
                    environ={"ORCA_HOST_CONFIG": str(host_path)},
                    spawn=lambda *args, **kwargs: self.fail(
                        "disabled lifecycle spawned worker"
                    ),
                )

            self.assertIsNone(result)
            self.assertFalse((root / "runtime" / "queue").exists())
            self.assertFalse((root / "runtime" / "retry-spool").exists())

    def test_precompact_queues_pointer_and_detaches_exact_xhigh_worker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root)
            rollout = root / "rollouts" / "hook.jsonl"
            _write_rollout(rollout)
            spawned: list[tuple[object, dict[str, object]]] = []

            def fake_spawn(*args, **kwargs):
                spawned.append((args, kwargs))
                return object()

            result = handle_payload(
                _payload("PreCompact", rollout, root),
                environ={"ORCA_HOST_CONFIG": str(host_path)},
                spawn=fake_spawn,
            )

            self.assertEqual(result, None)
            self.assertEqual(len(spawned), 1)
            command = spawned[0][0][0]
            options = spawned[0][1]
            self.assertEqual(command[-3:], ["worker", "--reasoning-effort", "xhigh"])
            self.assertEqual(options["stdin"], subprocess.DEVNULL)
            self.assertEqual(options["stdout"], subprocess.DEVNULL)
            self.assertEqual(options["stderr"], subprocess.DEVNULL)
            self.assertTrue(options["start_new_session"])
            self.assertEqual(options["close_fds"], True)

            queue = list((root / "runtime" / "queue").glob("*.json"))
            self.assertEqual(len(queue), 1)
            work = json.loads(queue[0].read_text(encoding="utf-8"))
            self.assertEqual(work["trigger"], "pre-compact")
            self.assertEqual(work["source_kind"], "rollout-pointer")
            self.assertEqual(work["conversation_id"], "hook-session")

    def test_session_end_spools_only_unprocessed_redacted_turns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root)
            rollout = root / "rollouts" / "hook.jsonl"
            _write_rollout(rollout)
            manifest_root = root / "vault" / "System" / "Orca Memory" / "manifests"
            manifest_root.mkdir(parents=True)
            old_text = "Already handled."
            (manifest_root / "old.json").write_text(
                json.dumps(
                    {
                        "schema_version": "orca-run-manifest/0.1",
                        "status": "success",
                        "connector_id": "codex-local",
                        "conversation_id": "hook-session",
                        "sources": [
                            {
                                "turn_id": "old-turn",
                                "content_sha256": hashlib.sha256(old_text.encode()).hexdigest(),
                                "redaction_policy": "orca-secret-containment/0.1",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            spawned = []

            handle_payload(
                _payload("SessionEnd", rollout, root),
                environ={"ORCA_HOST_CONFIG": str(host_path)},
                spawn=lambda *args, **kwargs: spawned.append((args, kwargs)),
            )

            self.assertEqual(len(spawned), 1)
            spools = list((root / "runtime" / "retry-spool").glob("*.json"))
            self.assertEqual(len(spools), 1)
            spool_text = spools[0].read_text(encoding="utf-8")
            self.assertIn("new-turn", spool_text)
            self.assertIn("api_key=[REDACTED]", spool_text)
            self.assertNotIn("old-turn", spool_text)
            self.assertNotIn("secret-value", spool_text)

    def test_session_end_retains_turn_when_only_a_later_segment_is_unprocessed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root)
            rollout = root / "rollouts" / "segmented.jsonl"
            long_text = "x" * 8_001
            rollout.write_text(
                "".join(
                    json.dumps(row) + "\n"
                    for row in (
                        {
                            "type": "session_meta",
                            "payload": {"id": "hook-session", "thread_source": "user"},
                        },
                        {
                            "type": "event_msg",
                            "payload": {
                                "type": "item_completed",
                                "item": {
                                    "type": "UserMessage",
                                    "id": "large-turn",
                                    "content": [{"type": "input_text", "text": long_text}],
                                },
                            },
                        },
                    )
                ),
                encoding="utf-8",
            )
            configuration = load_configuration(
                host_path, environ={}, registered_provider_adapters={"codex-cli"}
            )
            batch = normalize_codex_rollout(rollout, connector_id="codex-local")
            segments = segment_turn_with_budget(
                batch.turns[0], configuration.vault.budgets.processor.as_processing_budget()
            )
            self.assertEqual(len(segments), 2)
            manifest_root = root / "vault" / "System" / "Orca Memory" / "manifests"
            manifest_root.mkdir(parents=True)
            source = segmented_source(segments[0], source_ref="src-001")
            (manifest_root / "partial.json").write_text(
                json.dumps(
                    {
                        "schema": "orca-run-manifest/0.2",
                        "status": "success",
                        "connector_id": "codex-local",
                        "conversation_id": "hook-session",
                        "sources": [source],
                        "operations": [
                            {
                                "operation_id": "op-1",
                                "operation": "add",
                                "outcome": "created",
                                "artifact_kind": "typed-memory-record",
                                "artifact_id": "mem_partial",
                                "source_refs": ["src-001"],
                                "output_refs": [],
                                "embedded_artifact": None,
                            }
                        ],
                        "outputs": [],
                    }
                ),
                encoding="utf-8",
            )
            spawned = []

            handle_payload(
                _payload("SessionEnd", rollout, root),
                environ={"ORCA_HOST_CONFIG": str(host_path)},
                spawn=lambda *args, **kwargs: spawned.append((args, kwargs)),
            )

            self.assertEqual(len(spawned), 1)
            spools = list((root / "runtime" / "retry-spool").glob("*.json"))
            self.assertEqual(len(spools), 1)
            spool = json.loads(spools[0].read_text(encoding="utf-8"))
            self.assertEqual(
                [turn["turn_id"] for turn in spool["batch"]["turns"]],
                ["large-turn"],
            )
            self.assertEqual(spool["batch"]["turns"][0]["text"], long_text)

    def test_session_start_returns_guidance_and_counts_only_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root)
            rollout = root / "rollouts" / "hook.jsonl"
            _write_rollout(rollout)
            startup = StartupContext(
                "Generally, keep the response concise.",
                "Orca needs attention: 1 review. Run Orca Status.",
                OrcaStatus(()),
            )
            with patch("orca_memory.codex_hook.LocalOrcaApplication") as application:
                application.return_value.startup.return_value = startup
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(
                            environ={"ORCA_HOST_CONFIG": str(host_path)},
                            stdin=io.StringIO(
                                json.dumps(_payload("SessionStart", rollout, root))
                            ),
                        ),
                        0,
                    )
            value = json.loads(output.getvalue())
            self.assertEqual(
                value,
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": (
                            "Generally, keep the response concise.\n\n"
                            "Orca needs attention: 1 review. Run Orca Status."
                        ),
                    }
                },
            )
            application.return_value.startup.assert_called_once()

    def test_session_start_accepts_official_compact_source_without_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root)
            value = _payload("SessionStart", root / "missing.jsonl", root)
            value["source"] = "compact"
            value["transcript_path"] = None
            startup = StartupContext("", None, OrcaStatus(()))
            with patch("orca_memory.codex_hook.LocalOrcaApplication") as application:
                application.return_value.startup.return_value = startup
                self.assertEqual(
                    handle_payload(
                        value,
                        environ={"ORCA_HOST_CONFIG": str(host_path)},
                    ),
                    "",
                )
                application.return_value.startup.assert_called_once()

    def test_transcript_outside_configured_store_is_rejected_without_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path = _configuration(root)
            outside = root / "outside.jsonl"
            _write_rollout(outside)
            with self.assertRaisesRegex(ValueError, "outside configured rollout store"):
                handle_payload(
                    _payload("PreCompact", outside, root),
                    environ={"ORCA_HOST_CONFIG": str(host_path)},
                    spawn=lambda *args, **kwargs: self.fail("unsafe hook spawned worker"),
                )

    def test_invalid_hook_input_fails_without_private_details(self) -> None:
        output = io.StringIO()
        with redirect_stderr(output):
            self.assertEqual(
                main(stdin=io.StringIO(json.dumps({"hook_event_name": "Stop"}))), 1
            )
        self.assertEqual(output.getvalue(), "orca hook failed\n")
        self.assertNotIn("/", output.getvalue())


if __name__ == "__main__":
    unittest.main()
