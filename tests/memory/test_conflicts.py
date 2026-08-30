from __future__ import annotations

import unittest

from orca_memory.conflicts import (
    ConflictProposal,
    SupersedeProposal,
    apply_conflict,
    parse_conflict_record,
    review_conflict,
    start_conflict,
    supersede,
)
from orca_memory.memory import MemoryRecord, MemoryValidationError


class ConflictTests(unittest.TestCase):
    def _current(self) -> MemoryRecord:
        return MemoryRecord(
            memory_id="mem_index",
            kind="decision",
            subject="Processed source index",
            scope="project",
            scope_id="proj_orca",
            status="current",
            source_updated_at="2026-08-30T09:00:00Z",
            created_at="2026-08-30T09:05:00Z",
            updated_at="2026-08-30T09:05:00Z",
            workstreams=("phase-1",),
            current="Use a filesystem Manifest scan.",
        )

    def _proposal(self, label: str, position: str, at: str, **values) -> ConflictProposal:
        fields = dict(
            target_memory_id="mem_index",
            kind="decision",
            subject="Processed source index",
            scope="project",
            scope_id="proj_orca",
            label=label,
            position=position,
            position_at=at,
        )
        fields.update(values)
        return ConflictProposal(**fields)

    def test_current_becomes_two_stable_variants(self) -> None:
        record = start_conflict(
            self._current(),
            self._proposal("SQLite projection", "Use only SQLite.", "2026-08-30T10:00:00Z"),
            updated_at="2026-08-30T10:01:00Z",
        )
        self.assertEqual([item.variant_id for item in record.variants], ["v1", "v2"])
        self.assertEqual(record.review_state, "none")
        self.assertIn("status: conflict", record.render())
        self.assertNotIn("source_refs", record.render())
        self.assertEqual(parse_conflict_record(record.render()), record)

    def test_third_variant_requires_review_and_fourth_overflows(self) -> None:
        two = start_conflict(
            self._current(),
            self._proposal("SQLite", "Use only SQLite.", "2026-08-30T10:00:00Z"),
            updated_at="2026-08-30T10:01:00Z",
        )
        three, overflow, outcome = apply_conflict(
            two,
            self._proposal("Both", "Use both scan and SQLite.", "2026-08-30T11:00:00Z"),
            updated_at="2026-08-30T11:01:00Z",
        )
        self.assertEqual(outcome, "conflict-recorded")
        self.assertIsNone(overflow)
        self.assertEqual(three.review_state, "required")
        four_state, overflow, _ = apply_conflict(
            three,
            self._proposal("Remote", "Use a remote index.", "2026-08-30T12:00:00Z"),
            updated_at="2026-08-30T12:01:00Z",
        )
        self.assertEqual(four_state.review_state, "overflow")
        self.assertEqual(overflow.variant_id, "v4")
        self.assertIn("authority: noncanonical", overflow.render())
        self.assertIn("candidates/conflicts/projects/orca/", overflow.relative_path("Orca").as_posix())

    def test_exact_variant_support_does_not_rewrite(self) -> None:
        record = start_conflict(
            self._current(),
            self._proposal("SQLite", "Use only SQLite.", "2026-08-30T10:00:00Z"),
            updated_at="2026-08-30T10:01:00Z",
        )
        supported, overflow, outcome = apply_conflict(
            record,
            self._proposal(
                "SQLite",
                "Use only SQLite.",
                "2026-08-30T12:00:00Z",
                target_variant_id="v2",
            ),
            updated_at="2026-08-30T12:01:00Z",
        )
        self.assertIs(supported, record)
        self.assertIsNone(overflow)
        self.assertEqual(outcome, "supported")

    def test_cross_scope_and_secret_positions_fail(self) -> None:
        with self.assertRaises(MemoryValidationError):
            start_conflict(
                self._current(),
                self._proposal(
                    "Other",
                    "Different scope.",
                    "2026-08-30T10:00:00Z",
                    scope_id="proj_other",
                ),
                updated_at="2026-08-30T10:01:00Z",
            )
        with self.assertRaises(MemoryValidationError):
            self._proposal("Unsafe", "api_key=unredacted-value", "2026-08-30T10:00:00Z")

    def test_explicit_supersede_preserves_identity_and_compact_lineage(self) -> None:
        existing = self._current()
        proposal = SupersedeProposal(
            target_memory_id=existing.memory_id,
            kind=existing.kind,
            subject=existing.subject,
            scope=existing.scope,
            scope_id=existing.scope_id,
            current="Use the receipt-backed SQLite projection.",
            source_updated_at="2026-08-30T13:00:00Z",
        )
        replaced = supersede(existing, proposal, updated_at="2026-08-30T13:01:00Z")
        self.assertEqual(replaced.memory_id, existing.memory_id)
        self.assertEqual(replaced.created_at, existing.created_at)
        self.assertIn("## Resolution lineage", replaced.render())
        self.assertIn("`v1`", replaced.render())
        with self.assertRaises(MemoryValidationError):
            SupersedeProposal(**{**proposal.__dict__, "explicit_replacement": False})

    def test_owner_review_selects_or_acknowledges_without_synthesizing(self) -> None:
        record = start_conflict(
            self._current(),
            self._proposal("SQLite", "Use only SQLite.", "2026-08-30T10:00:00Z"),
            updated_at="2026-08-30T10:01:00Z",
        )
        acknowledged = review_conflict(
            record,
            owner_confirmed=True,
            keep_unresolved=True,
            updated_at="2026-08-30T11:00:00Z",
        )
        self.assertEqual(acknowledged.review_state, "acknowledged")
        selected = review_conflict(
            record,
            owner_confirmed=True,
            select_variant_id="v2",
            updated_at="2026-08-30T11:00:00Z",
        )
        self.assertEqual(selected.status, "current")
        self.assertEqual(selected.current, "Use only SQLite.")
        self.assertIn("selected", selected.lineage[1])
        with self.assertRaises(PermissionError):
            review_conflict(
                record,
                owner_confirmed=False,
                select_variant_id="v1",
                updated_at="2026-08-30T11:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
