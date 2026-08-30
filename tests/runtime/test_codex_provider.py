from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from orca_memory.codex_provider import CodexCliSemanticProvider, CodexProviderError
from orca_memory.conversation import NormalizedTurn
from orca_memory.processor import ProcessingInput
from orca_memory.segmentation import SourceSegment


def _request(text: str = "Remember that status updates should stay concise.") -> ProcessingInput:
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
    def test_invocation_is_ephemeral_isolated_exact_model_and_parses_proposal(self) -> None:
        runner = _SuccessfulRunner(_empty_proposal())
        provider = CodexCliSemanticProvider(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            command_runner=runner,
        )
        proposal = provider.distill(_request())
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
        self.assertIn("exactly one of value or direction", kwargs["input"])
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(runner.cwd_was_dir)

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


if __name__ == "__main__":
    unittest.main()
