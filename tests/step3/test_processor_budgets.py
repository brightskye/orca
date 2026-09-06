from __future__ import annotations

import hashlib
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.memory import ProjectSummary, RecordProposal
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


class SizedProvider(RecordingProvider):
    def input_size(self, request):
        # Simulate fixed prompt/schema overhead that leaves no room for the
        # optional related context while all required context still fits.
        return request.input_tokens + (1 if request.related_records else 0)


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
        self.assertEqual(provider.request.scope_kind, "general")
        self.assertEqual(provider.request.scope_id, "general")

    def test_configured_input_ceiling_is_carried_to_provider_request(self) -> None:
        provider = RecordingProvider(ProcessingProposal(None))
        budgets = BudgetConfig(
            new_evidence_tokens=10,
            preceding_turn_tokens=0,
            continuation_summary_tokens=0,
            project_summary_tokens=0,
            related_records_tokens=0,
            total_input_tokens=50,
        )
        Processor(provider).process(
            _batch(),
            previous_continuation=None,
            project_id=None,
            scope_kind="general",
            scope_id="general",
            budgets=budgets,
        )
        self.assertEqual(provider.request.input_tokens, 50)

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

    def test_project_summary_rendering_does_not_double_count_model_output(self) -> None:
        summary = ProjectSummary(
            project_id="proj-orca",
            purpose="Export format",
            current_state="Markdown remains the first export format. " * 48,
        )
        provider = RecordingProvider(ProcessingProposal(None, project_summary=summary))
        result = Processor(provider).process(
            _batch(), previous_continuation=None, project_id="proj-orca",
            scope_kind="project", scope_id="proj-orca",
        )
        self.assertEqual(result.project_summary, summary)
        self.assertIn(summary.current_state, summary.body)
        oversized = ProjectSummary(
            project_id="proj-orca", purpose="Export format",
            current_state=summary.current_state * 3,
        )
        with self.assertRaisesRegex(ValueError, "semantic_output_tokens"):
            Processor(RecordingProvider(ProcessingProposal(None, project_summary=oversized))).process(
                _batch(), previous_continuation=None, project_id="proj-orca",
                scope_kind="project", scope_id="proj-orca",
            )

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

    def test_semantic_operation_citations_are_exact_and_timestamp_is_source_derived(self) -> None:
        proposal = RecordProposal(
            operation="add",
            kind="decision",
            subject="A source-backed decision",
            scope="general",
            scope_id="general",
            current="Use the cited source.",
            source_updated_at="2020-01-01T00:00:00Z",
            source_segment_refs=("turn-1#1",),
        )
        provider = RecordingProvider(ProcessingProposal(None, (proposal,)))
        result = Processor(provider).process(
            _batch(),
            previous_continuation=None,
            project_id=None,
            scope_kind="general",
            scope_id="general",
        )
        self.assertEqual(result.record_proposals[0].source_segment_refs, ("turn-1#1",))
        self.assertEqual(
            result.record_proposals[0].source_updated_at,
            "2026-08-30T10:00:00Z",
        )

    def test_semantic_operation_must_cite_current_owner_segment(self) -> None:
        proposal = RecordProposal(
            operation="add",
            kind="decision",
            subject="A source-backed decision",
            scope="general",
            scope_id="general",
            current="Use the cited source.",
        )
        provider = RecordingProvider(ProcessingProposal(None, (proposal,)))
        with self.assertRaisesRegex(ValueError, "cite at least one source segment"):
            Processor(provider).process(
                _batch(),
                previous_continuation=None,
                project_id=None,
                scope_kind="general",
                scope_id="general",
            )

    def test_semantic_operation_cannot_cite_assistant_context(self) -> None:
        owner = _batch().turns[0]
        assistant = NormalizedTurn(
            "codex-local",
            "conversation-budget",
            "turn-answer",
            "2026-08-30T10:01:00Z",
            "codex://provider/turn-answer",
            "assistant context",
            hashlib.sha256(b"assistant context").hexdigest(),
            source_role="assistant",
        )
        proposal = RecordProposal(
            operation="add",
            kind="decision",
            subject="A source-backed decision",
            scope="general",
            scope_id="general",
            current="Use the cited source.",
            source_segment_refs=("turn-answer#1",),
        )
        provider = RecordingProvider(ProcessingProposal(None, (proposal,)))
        with self.assertRaisesRegex(ValueError, "missing or non-Owner"):
            Processor(provider).process(
                ConversationBatch("codex-local", "conversation-budget", (owner, assistant)),
                previous_continuation=None,
                project_id=None,
                scope_kind="general",
                scope_id="general",
            )

    def test_source_timestamp_order_uses_absolute_time_for_offsets(self) -> None:
        first = NormalizedTurn(
            "codex-local",
            "conversation-offsets",
            "turn-a",
            "2026-08-30T10:00:00+02:00",
            "codex://provider/turn-a",
            "first",
            hashlib.sha256(b"first").hexdigest(),
        )
        second = NormalizedTurn(
            "codex-local",
            "conversation-offsets",
            "turn-b",
            "2026-08-30T09:30:00Z",
            "codex://provider/turn-b",
            "second",
            hashlib.sha256(b"second").hexdigest(),
        )
        proposal = RecordProposal(
            operation="add",
            kind="decision",
            subject="An offset-aware decision",
            scope="general",
            scope_id="general",
            current="Use the later source.",
            source_segment_refs=("turn-a#1", "turn-b#1"),
        )
        provider = RecordingProvider(ProcessingProposal(None, (proposal,)))
        processed = Processor(provider).process(
            ConversationBatch("codex-local", "conversation-offsets", (first, second)),
            previous_continuation=None,
            project_id=None,
            scope_kind="general",
            scope_id="general",
        )
        self.assertEqual(
            processed.record_proposals[0].source_updated_at,
            "2026-08-30T09:30:00Z",
        )

    def test_provider_fixed_overhead_drops_lowest_optional_related_context(self) -> None:
        provider = SizedProvider(ProcessingProposal(None))
        Processor(provider).process(
            _batch(),
            previous_continuation=None,
            project_id=None,
            scope_kind="general",
            scope_id="general",
            preceding_turn="optional overlap",
            related_records=(
                {
                    "memory_id": "mem-related",
                    "scope": "general",
                    "scope_id": "general",
                    "status": "current",
                    "body": "An optional related memory.",
                },
            ),
        )
        self.assertEqual(provider.request.related_records, ())
        self.assertEqual(provider.request.preceding_turn, "optional overlap")


if __name__ == "__main__":
    unittest.main()
