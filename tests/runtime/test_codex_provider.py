from __future__ import annotations

import hashlib
from dataclasses import replace
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from orca_memory.codex_provider import CodexCliSemanticProvider, CodexProviderError
from orca_memory.codex_isolation import CodexIsolationError
from orca_memory.conversation import NormalizedTurn
from orca_memory.memory import MemoryRecord, RecordProposal, validate_operation
from orca_memory.processor import ProcessingInput
from orca_memory.segmentation import SourceSegment


def _request(
    text: str = "Remember that status updates should stay concise.",
    *,
    previous_continuation: str | None = None,
    input_tokens: int = 20_000,
) -> ProcessingInput:
    turn = NormalizedTurn(
        "codex-local",
        "conversation-provider",
        "turn-owner",
        "2026-08-30T10:00:00Z",
        "codex://provider/turn-owner",
        text,
        hashlib.sha256(text.encode()).hexdigest(),
    )
    segment = SourceSegment(
        turn,
        text,
        1,
        1,
        0,
        len(text.encode()),
        "0" * 64,
    )
    return ProcessingInput(
        (segment,),
        (),
        previous_continuation,
        None,
        scope_kind="general",
        scope_id="general",
        input_tokens=input_tokens,
    )


def _segmented_request() -> ProcessingInput:
    visible = "visible-segment-marker"
    hidden = "hidden-full-turn-marker"
    text = f"{visible} {hidden}"
    turn = NormalizedTurn(
        "codex-local",
        "conversation-provider",
        "turn-owner",
        "2026-08-30T10:00:00Z",
        "codex://provider/turn-owner",
        text,
        hashlib.sha256(text.encode()).hexdigest(),
    )
    segment = SourceSegment(
        turn,
        visible,
        1,
        2,
        0,
        len(visible.encode()),
        "0" * 64,
    )
    return ProcessingInput(
        (segment,), (), None, None, scope_kind="general", scope_id="general"
    )


def _empty_proposal() -> dict:
    return {
        "continuation": {
            "purpose": "Preserve useful Owner context",
            "current_state": "The bounded provider returned one proposal.",
            "important_outcomes": [],
            "open_questions": [],
            "next_steps": [],
            "relevant_artifacts": [],
        },
        "record_proposals": [],
        "project_summary": None,
        "candidate_operations": [],
        "conflict_proposals": [],
        "supersede_proposals": [],
        "abstentions": [],
        "observation_proposals": [],
    }


class _SuccessfulRunner:
    def __init__(self, value: dict) -> None:
        self.value = value
        self.calls = []
        self.cwd_was_dir = False

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        self.cwd_was_dir = kwargs["cwd"].is_dir()
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(self.value), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="private stdout", stderr="")


class CodexProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        # Proposal tests replace only the OS launch seam; a separate integration
        # test exercises the real qualified CLI inside bubblewrap.
        boundary = patch("orca_memory.codex_provider.isolated_command", side_effect=lambda command, root: (command, {}))
        boundary.start()
        self.addCleanup(boundary.stop)

    def test_invocation_is_ephemeral_isolated_exact_model_and_parses_proposal(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            command_runner=runner,
        )
        proposal = provider.distill(
            _request(
                previous_continuation=(
                    "Earlier outcome: keep the current boundary because it protects continuity."
                )
            )
        )
        self.assertEqual(proposal.continuation.purpose, "Preserve useful Owner context")
        command, kwargs = runner.calls[0]
        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        self.assertEqual(command[command.index("--model") + 1], "gpt-5.6-luna")
        self.assertIn('model_reasoning_effort="xhigh"', command)
        self.assertEqual(command[-1], "-")
        self.assertNotIn("status updates should stay concise", " ".join(command))
        self.assertIn("status updates should stay concise", kwargs["input"])
        self.assertIn("Earlier outcome: keep the current boundary", kwargs["input"])
        self.assertIn("exactly one of value or direction", kwargs["input"])
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(runner.cwd_was_dir)

    def test_payload_contains_selected_segment_and_required_metadata_only(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            command_runner=runner,
        )
        provider.distill(_segmented_request())
        payload = json.loads(runner.calls[0][1]["input"].split("Processing input:\n", 1)[1])
        segment = payload["owner_evidence"][0]
        self.assertEqual(segment["text"], "visible-segment-marker")
        self.assertEqual(segment["turn_id"], "turn-owner")
        self.assertEqual(segment["segment"]["index"], 1)
        self.assertNotIn("turn", segment)
        self.assertNotIn("hidden-full-turn-marker", runner.calls[0][1]["input"])

    def test_serialized_prompt_and_schema_overflow_fail_before_command(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            command_runner=runner,
        )
        request = _request(input_tokens=1_000)
        self.assertLess(len(request.owner_evidence[0].text.encode()), request.input_tokens)
        with self.assertRaisesRegex(CodexProviderError, "configured ceiling"):
            provider.distill(request)
        self.assertEqual(runner.calls, [])

    def test_pending_candidate_identity_and_meaning_reach_provider(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(model="gpt-5.6-luna", reasoning_effort="low", command_runner=runner)
        request = replace(_request(), related_candidates=({
            "candidate_id": "cand_existing", "candidate_kind": "lesson",
            "subject": "Trial outcome", "proposal": "Start with one controlled trial.",
            "scope": "general", "scope_id": "general", "status": "pending",
            "context": "Awaiting review.",
        },))
        provider.distill(request)
        payload = json.loads(runner.calls[0][1]["input"].split("Processing input:\n", 1)[1])
        self.assertEqual(payload["related_candidates"][0]["candidate_id"], "cand_existing")
        self.assertEqual(payload["related_candidates"][0]["proposal"], "Start with one controlled trial.")
        self.assertEqual(payload["owner_evidence"][0]["segment_ref"], "turn-owner#1")

    def test_secret_like_input_is_rejected_before_provider_call(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            command_runner=runner,
        )
        with self.assertRaisesRegex(CodexProviderError, "secret containment"):
            provider.distill(_request("Use password=hunter2 for this system."))
        self.assertEqual(runner.calls, [])

    def test_related_record_fields_can_support_without_reconstructing_markdown(self) -> None:
        record = MemoryRecord(
            memory_id="mem_export", kind="decision", subject="Export format",
            scope="general", scope_id="general", status="current",
            source_updated_at="2026-08-30T10:00:00Z",
            created_at="2026-08-30T10:00:00Z", updated_at="2026-08-30T10:00:00Z",
            current="Use Markdown.", context="Readable in plain-text editors.",
            implications="Compare examples.\n\nKeep JSON as a later idea.",
        )
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna", reasoning_effort="low", command_runner=runner,
        )
        provider.distill(replace(_request(), related_records=(record,)))
        payload = json.loads(runner.calls[0][1]["input"].split("Processing input:\n", 1)[1])
        supplied = payload["related_records"][0]
        fields = {name: supplied[name] for name in (
            "kind", "subject", "scope", "scope_id", "status", "source_updated_at",
            "workstreams", "current", "context", "implications", "final", "closure",
        )}
        proposal = RecordProposal(
            operation="support", target_memory_id=supplied["memory_id"], **fields,
        )
        self.assertTrue(validate_operation("support", existing=record, proposal=proposal))
        self.assertNotIn("body", supplied)

    def test_provider_failure_and_invalid_output_do_not_expose_private_text(self) -> None:
        def failed(command, **kwargs):
            return subprocess.CompletedProcess(command, 7, stdout="private output", stderr="private error")

        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna", reasoning_effort="xhigh", command_runner=failed
        )
        with self.assertRaises(CodexProviderError) as failure:
            provider.distill(_request())
        self.assertNotIn("private", str(failure.exception))

        runner = _SuccessfulRunner({"unexpected": "private provider content"})
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna", reasoning_effort="xhigh", command_runner=runner
        )
        with self.assertRaises(CodexProviderError) as invalid:
            provider.distill(_request())
        self.assertNotIn("private provider content", str(invalid.exception))

        invalid_observation = _empty_proposal()
        invalid_observation["observation_proposals"] = [
            {
                "dimension": "technical-depth",
                "context": "explanation",
                "scope": {"type": "global", "agent_id": None, "project_id": None},
                "evidence_class": "direct-correction",
                "feedback_turn_id": "turn-owner",
                "evaluated_assistant_turn_ids": ["turn-assistant"],
                "preceding_request_turn_id": "turn-request",
                "value": "plain-language",
                "direction": "decrease",
                "lasting": True,
                "replaces_prior": False,
            }
        ]
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            command_runner=_SuccessfulRunner(invalid_observation),
        )
        with self.assertRaisesRegex(CodexProviderError, "invalid proposal"):
            provider.distill(_request())

    def test_reasoning_effort_never_falls_back_silently(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported Codex reasoning effort"):
            CodexCliSemanticProvider(model="gpt-5.6-luna", reasoning_effort="automatic")

    def test_unavailable_isolation_never_falls_back_to_unconfined_execution(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(model="gpt-5.6-luna", reasoning_effort="low", command_runner=runner)
        with patch("orca_memory.codex_provider.isolated_command", side_effect=CodexIsolationError("unavailable")):
            with self.assertRaisesRegex(CodexProviderError, "failed safely"):
                provider.distill(_request())
        self.assertEqual(runner.calls, [])


@unittest.skipUnless(os.environ.get("ORCA_RUN_CODEX_ISOLATION_DRILL") == "1", "opt-in qualified Codex isolation drill")
class CodexIsolationTests(unittest.TestCase):
    def test_real_cli_blocks_tools_and_host_files_without_a_model_or_owner_credentials(self) -> None:
        calls = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                calls.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                if len(calls) == 1:
                    item = {
                        "type": "custom_tool_call", "id": "ct_1", "call_id": "call_1",
                        "name": "exec", "namespace": "functions",
                        "input": 'text(await tools.exec_command({cmd: "cat /outside-marker"}));',
                    }
                else:
                    item = {
                        "type": "message", "id": "msg_1", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text", "text": json.dumps(_empty_proposal()), "annotations": []}],
                    }
                response = {
                    "id": "resp_" + str(len(calls)), "object": "response", "created_at": 1,
                    "status": "completed", "output": [item],
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
                }
                events = [
                    {"type": "response.output_item.added", "output_index": 0, "item": item},
                    {"type": "response.output_item.done", "output_index": 0, "item": item},
                    {"type": "response.completed", "response": response},
                ]
                data = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory(prefix="orca-isolation-drill-") as directory:
            root = Path(directory)
            home = root / "codex-home"
            home.mkdir(mode=0o700)
            (home / "auth.json").write_text("{}", encoding="utf-8")
            outside = root / "outside-marker"
            outside.write_text("ORCA_PRIVATE_FILE_SENTINEL", encoding="utf-8")
            server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.server_close)
            self.addCleanup(thread.join, 5)
            self.addCleanup(server.shutdown)
            attempts = []

            def runner(command, **kwargs):
                config = {
                    "model_provider": "probe", "model_providers.probe.name": "probe",
                    "model_providers.probe.base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "model_providers.probe.wire_api": "responses",
                    "model_providers.probe.requires_openai_auth": False,
                    "model_providers.probe.request_max_retries": 0,
                    "model_providers.probe.stream_max_retries": 0,
                }
                extra = [part for key, value in config.items() for part in ("-c", key + "=" + json.dumps(value))]
                if attempts:
                    # Make trusted Codex itself attempt a read, independently of tool blocking.
                    extra.extend(("-c", "model_instructions_file=" + json.dumps(str(outside))))
                attempts.append(command)
                return subprocess.run(command[:-1] + extra + command[-1:], **kwargs)

            with patch.dict(os.environ, {"CODEX_HOME": str(home), "ORCA_ENV_SENTINEL": "ORCA_PRIVATE_ENV_SENTINEL"}):
                provider = CodexCliSemanticProvider(model="gpt-5.6-luna", reasoning_effort="low", command_runner=runner, timeout_seconds=30)
                self.assertIsNotNone(provider.distill(_request()).continuation)
                self.assertEqual(len(calls), 2)
                tool_outputs = [item.get("output") for item in calls[-1]["input"] if item.get("type") == "custom_tool_call_output"]
                self.assertIn("code-mode host is disabled", tool_outputs)
                self.assertNotIn("ORCA_PRIVATE_FILE_SENTINEL", json.dumps(calls))
                self.assertNotIn("ORCA_PRIVATE_ENV_SENTINEL", json.dumps(calls))
                with self.assertRaises(CodexProviderError):
                    provider.distill(_request())
                self.assertEqual(len(calls), 2, "host file read must fail before model request")
                self.assertEqual(outside.read_text(), "ORCA_PRIVATE_FILE_SENTINEL")


if __name__ == "__main__":
    unittest.main()
