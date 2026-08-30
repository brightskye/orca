from __future__ import annotations

import hashlib
import unittest

from orca_memory.conversation import NormalizedTurn
from orca_memory.segmentation import (
    DEFAULT_BUDGETS,
    SEGMENTATION_POLICY,
    TOKEN_ESTIMATOR_VERSION,
    BudgetConfig,
    BudgetUsage,
    ProcessingChunk,
    chunk_turns,
    estimate_tokens,
    measure_context,
    parameters_sha256,
    segment_turn,
    select_related_records,
    validate_budget_usage,
)


class SegmentationTests(unittest.TestCase):
    def _turn(
        self,
        turn_id: str,
        text: str,
        *,
        occurred_at: str | None = "2026-08-30T10:00:00Z",
    ) -> NormalizedTurn:
        return NormalizedTurn(
            connector_id="codex-local",
            conversation_id="conversation-segmentation",
            turn_id=turn_id,
            occurred_at=occurred_at,
            source_uri=f"codex://session/conversation-segmentation/event/{turn_id}",
            text=text,
            content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    def test_default_budgets_are_immutable_and_match_contract(self):
        self.assertEqual(DEFAULT_BUDGETS.new_evidence_tokens, 8_000)
        self.assertEqual(DEFAULT_BUDGETS.preceding_turn_tokens, 1_000)
        self.assertEqual(DEFAULT_BUDGETS.continuation_summary_tokens, 2_000)
        self.assertEqual(DEFAULT_BUDGETS.project_summary_tokens, 2_000)
        self.assertEqual(DEFAULT_BUDGETS.related_records_tokens, 5_000)
        self.assertEqual(DEFAULT_BUDGETS.related_record_count, 5)
        self.assertEqual(DEFAULT_BUDGETS.total_input_tokens, 20_000)
        self.assertEqual(DEFAULT_BUDGETS.semantic_output_tokens, 4_000)
        with self.assertRaises((AttributeError, TypeError)):
            DEFAULT_BUDGETS.new_evidence_tokens = 1
        for values in (
            {"new_evidence_tokens": 20_001},
            {"related_record_count": 6},
            {"related_records_tokens": 5_001},
            {"total_input_tokens": 0},
            {"semantic_output_tokens": -1},
        ):
            with self.assertRaises(ValueError):
                BudgetConfig(**values)

    def test_byte_conservative_estimator_is_deterministic_for_unicode(self):
        self.assertEqual(estimate_tokens("hello"), 5)
        self.assertEqual(estimate_tokens("a😀"), len("a😀".encode("utf-8")))
        self.assertEqual(estimate_tokens("a😀"), estimate_tokens("a😀"))
        with self.assertRaises(TypeError):
            estimate_tokens(b"not text")

    def test_unsegmented_turn_has_uniform_source_segment_metadata(self):
        turn = self._turn("turn-1", "short evidence")
        segments = segment_turn(turn, max_segment_tokens=100)
        self.assertEqual(len(segments), 1)
        segment = segments[0]
        self.assertEqual(segment.index, 1)
        self.assertEqual(segment.count, 1)
        self.assertEqual(segment.start_byte, 0)
        self.assertEqual(segment.end_byte, len(turn.text.encode()))
        self.assertEqual(segment.text, turn.text)
        self.assertEqual(segment.turn_content_sha256, turn.content_sha256)
        self.assertEqual(segment.policy_version, SEGMENTATION_POLICY)
        self.assertEqual(segment.parameters_sha256, parameters_sha256(
            max_segment_tokens=100,
            token_estimator_version=TOKEN_ESTIMATOR_VERSION,
        ))
        receipt = segment.as_manifest_source("src-001")
        self.assertEqual(receipt["source_ref"], "src-001")
        self.assertEqual(receipt["segment"], segment.segment)

    def test_oversized_turn_splits_utf8_without_truncation_or_invalid_ranges(self):
        text = "ab😀cdéef"
        turn = self._turn("turn-1", text)
        segments = segment_turn(turn, max_segment_tokens=5)
        self.assertGreater(len(segments), 1)
        self.assertEqual("".join(segment.text for segment in segments), text)
        self.assertEqual(
            b"".join(segment.text.encode("utf-8") for segment in segments),
            text.encode("utf-8"),
        )
        self.assertEqual([segment.index for segment in segments], list(range(1, len(segments) + 1)))
        self.assertTrue(all(segment.count == len(segments) for segment in segments))
        self.assertEqual(segments[0].start_byte, 0)
        for previous, current in zip(segments, segments[1:]):
            self.assertEqual(previous.end_byte, current.start_byte)
        self.assertEqual(segments[-1].end_byte, len(text.encode("utf-8")))
        self.assertTrue(all(segment.token_count <= 5 for segment in segments))

    def test_too_small_bound_fails_closed_instead_of_truncating_character(self):
        with self.assertRaisesRegex(ValueError, "UTF-8 character"):
            segment_turn(self._turn("turn-1", "😀"), max_segment_tokens=3)

    def test_chunks_pack_turns_only_at_boundaries_and_preserve_order(self):
        turns = (
            self._turn("turn-1", "aaaa"),
            self._turn("turn-2", "bbbb"),
            self._turn("turn-3", "cccc"),
        )
        chunks = chunk_turns(turns, BudgetConfig(new_evidence_tokens=8))
        self.assertEqual(len(chunks), 2)
        self.assertIsInstance(chunks[0], ProcessingChunk)
        self.assertEqual([turn.turn_id for turn in chunks[0].turns], ["turn-1", "turn-2"])
        self.assertEqual([turn.turn_id for turn in chunks[1].turns], ["turn-3"])
        self.assertEqual([s.text for chunk in chunks for s in chunk.segments], ["aaaa", "bbbb", "cccc"])
        self.assertTrue(all(chunk.token_count <= 8 for chunk in chunks))

    def test_chunks_segment_oversized_turn_and_do_not_drop_following_turn(self):
        turns = (self._turn("turn-1", "abcdefghij"), self._turn("turn-2", "xy"))
        chunks = chunk_turns(turns, BudgetConfig(new_evidence_tokens=4))
        self.assertEqual(
            "".join(segment.text for chunk in chunks for segment in chunk.segments),
            "abcdefghijxy",
        )
        self.assertEqual(chunks[-1].turns[-1].turn_id, "turn-2")

    def test_chunker_rejects_mixed_inputs_duplicates_and_reverse_timestamps(self):
        with self.assertRaises(ValueError):
            chunk_turns((), DEFAULT_BUDGETS)
        with self.assertRaises(ValueError):
            chunk_turns((self._turn("turn-1", "a"), self._turn("turn-1", "a")))
        reverse = (
            self._turn("turn-1", "a", occurred_at="2026-08-30T11:00:00Z"),
            self._turn("turn-2", "b", occurred_at="2026-08-30T10:00:00Z"),
        )
        with self.assertRaisesRegex(ValueError, "chronological"):
            chunk_turns(reverse)

    def test_budget_usage_validates_each_category_and_total(self):
        usage = BudgetUsage(
            new_evidence_tokens=8_000,
            preceding_turn_tokens=1_000,
            continuation_summary_tokens=2_000,
            project_summary_tokens=2_000,
            related_records_tokens=5_000,
            semantic_output_tokens=4_000,
        )
        self.assertEqual(usage.total_input_tokens, 18_000)
        self.assertIs(validate_budget_usage(usage), usage)
        self.assertEqual(
            validate_budget_usage({"new_evidence_tokens": 1}),
            validate_budget_usage(BudgetUsage(new_evidence_tokens=1)),
        )
        with self.assertRaises(ValueError):
            validate_budget_usage(BudgetUsage(new_evidence_tokens=8_001))
        with self.assertRaises(ValueError):
            validate_budget_usage(BudgetUsage(semantic_output_tokens=4_001))
        with self.assertRaises(ValueError):
            validate_budget_usage(BudgetUsage(
                new_evidence_tokens=8_000,
                preceding_turn_tokens=4_000,
                continuation_summary_tokens=4_000,
                project_summary_tokens=4_000,
                related_records_tokens=4_001,
            ))

    def test_measure_context_is_repeatable_and_reports_complete_input(self):
        usage = measure_context(
            new_evidence=("owner", "evidence"),
            preceding_turn="previous",
            continuation_summary="state",
            project_summary="project",
            related_records=(
                {"body": "first"},
                {"body": "second"},
            ),
            semantic_output="output",
        )
        self.assertEqual(usage, measure_context(
            new_evidence=("owner", "evidence"),
            preceding_turn="previous",
            continuation_summary="state",
            project_summary="project",
            related_records=({"body": "first"}, {"body": "second"}),
            semantic_output="output",
        ))
        self.assertEqual(usage.total_input_tokens, 44)

    def test_related_selection_is_current_same_scope_ranked_and_bounded(self):
        records = (
            {"memory_id": "mem-1", "scope": "project", "scope_id": "proj-a", "status": "current", "body": "a" * 3_000},
            {"memory_id": "mem-2", "scope": "project", "scope_id": "proj-a", "status": "closed", "body": "b"},
            {"memory_id": "mem-3", "scope": "general", "scope_id": "general", "status": "current", "body": "c"},
            {"memory_id": "mem-4", "scope": "project", "scope_id": "proj-a", "status": "current", "body": "d" * 2_000},
            {"memory_id": "mem-5", "scope": "project", "scope_id": "proj-a", "status": "current", "body": "e"},
            {"memory_id": "mem-6", "scope": "project", "scope_id": "proj-a", "status": "current", "body": "f"},
        )
        selected = select_related_records(records, "project", "proj-a")
        self.assertEqual([record["memory_id"] for record in selected], ["mem-1", "mem-4"])
        self.assertLessEqual(len(selected), 5)
        self.assertLessEqual(sum(estimate_tokens(record["body"]) for record in selected), 5_000)
        self.assertEqual(
            [record["memory_id"] for record in select_related_records(records, "general", "general")],
            ["mem-3"],
        )


if __name__ == "__main__":
    unittest.main()
