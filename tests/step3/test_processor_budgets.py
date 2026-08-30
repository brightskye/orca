from __future__ import annotations

import hashlib
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.processor import ContinuationSummary, ProcessingProposal, Processor
from orca_memory.segmentation import BudgetConfig


class RecordingProvider:
    name = "fake-provider/budgets"

    def __init__(self, proposal: ProcessingProposal) -> None:
        self.proposal = proposal
        self.calls = 0
        self.request = None

    def distill(self, request):
        self.calls += 1
        self.request = request
        return self.proposal


def _batch(text: str = "owner") -> ConversationBatch:
    turn = NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-budget",
        turn_id="turn-1",
        occurred_at="2026-08-30T10:00:00Z",
        source_uri="codex://session/conversation-budget/event/turn-1",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )
    return ConversationBatch("codex-local", "conversation-budget", (turn,))


class ProcessorBudgetTests(unittest.TestCase):
    def test_context_overflow_fails_before_provider_call(self) -> None:
        provider = RecordingProvider(ProcessingProposal(None))
        with self.assertRaisesRegex(ValueError, "continuation_summary_tokens"):
            Processor(provider).process(
                _batch(),
                previous_continuation="x" * 21,
                project_id=None,
                scope_kind="general",
                scope_id="general",
                budgets=BudgetConfig(continuation_summary_tokens=20),
            )
        self.assertEqual(provider.calls, 0)

    def test_optional_preceding_turn_is_removed_before_call_when_over_limit(self) -> None:
        provider = RecordingProvider(ProcessingProposal(None))
        Processor(provider).process(
            _batch(),
            previous_continuation=None,
            project_id=None,
            scope_kind="general",
            scope_id="general",
            preceding_turn="x" * 21,
            budgets=BudgetConfig(preceding_turn_tokens=20),
        )
        self.assertIsNone(provider.request.preceding_turn)

    def test_related_records_are_same_scope_current_and_bounded(self) -> None:
        provider = RecordingProvider(ProcessingProposal(None))
        records = tuple(
            {
                "memory_id": f"mem-{index}",
                "scope": "general" if index < 7 else "unassigned",
                "scope_id": "general" if index < 7 else "unassigned",
                "status": "current" if index != 1 else "closed",
                "body": "record",
            }
            for index in range(8)
        )
        Processor(provider).process(
            _batch(),
            previous_continuation=None,
            project_id=None,
            scope_kind="general",
            scope_id="general",
            related_records=records,
        )
        self.assertEqual(len(provider.request.related_records), 5)
        self.assertTrue(
            all(item["scope"] == "general" and item["status"] == "current" for item in provider.request.related_records)
        )

    def test_generated_output_overflow_is_rejected(self) -> None:
        provider = RecordingProvider(
            ProcessingProposal(
                ContinuationSummary("purpose", "x" * 101)
            )
        )
        with self.assertRaisesRegex(ValueError, "semantic_output_tokens"):
            Processor(provider).process(
                _batch(),
                previous_continuation=None,
                project_id=None,
                scope_kind="general",
                scope_id="general",
                budgets=BudgetConfig(semantic_output_tokens=100),
            )
        self.assertEqual(provider.calls, 1)

    def test_project_summary_context_is_forbidden_outside_project_scope(self) -> None:
        provider = RecordingProvider(ProcessingProposal(None))
        with self.assertRaisesRegex(ValueError, "forbidden"):
            Processor(provider).process(
                _batch(),
                previous_continuation=None,
                project_id=None,
                scope_kind="general",
                scope_id="general",
                project_summary="project state",
            )
        self.assertEqual(provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
