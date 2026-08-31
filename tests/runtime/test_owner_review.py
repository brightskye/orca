from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from orca_memory.candidates import (
    CandidateProposal,
    DispositionReceipt,
    KnowledgeCandidate,
    candidate_placement,
    plan_disposition,
)
from orca_memory.conflicts import (
    ConflictProposal,
    apply_conflict,
    parse_conflict_record,
    start_conflict,
)
from orca_memory.memory import MemoryRecord, record_relative_path
from orca_memory.owner_review import (
    OwnerReviewPlan,
    OwnerReviewPublisher,
    OwnerReviewRepairRequired,
    ReviewOutput,
)


NOW = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)


class OwnerReviewTests(unittest.TestCase):
    def _candidate(self) -> KnowledgeCandidate:
        return KnowledgeCandidate.from_proposal(
            CandidateProposal(
                "fact",
                "Deployment policy",
                "Use the governed release procedure.",
                "general",
                "general",
            ),
            candidate_id="cand_review",
            created_at="2026-08-31T09:00:00Z",
        )

    def _write_candidate(self, vault: Path) -> Path:
        candidate = self._candidate()
        path = candidate_placement(vault, candidate).path
        path.parent.mkdir(parents=True)
        path.write_text(candidate.render(), encoding="utf-8")
        return path

    def _write_conflict(self, vault: Path) -> Path:
        current = MemoryRecord(
            memory_id="mem_review",
            kind="decision",
            subject="Storage backend",
            scope="general",
            scope_id="general",
            status="current",
            source_updated_at="2026-08-31T08:00:00Z",
            created_at="2026-08-31T08:00:00Z",
            updated_at="2026-08-31T08:00:00Z",
            current="Use Markdown.",
        )
        conflict = start_conflict(
            current,
            ConflictProposal(
                "mem_review",
                "decision",
                "Storage backend",
                "general",
                "general",
                "SQLite",
                "Use SQLite.",
                "2026-08-31T08:30:00Z",
            ),
            updated_at="2026-08-31T08:31:00Z",
        )
        path = vault / record_relative_path(conflict)
        path.parent.mkdir(parents=True)
        path.write_text(conflict.render(), encoding="utf-8")
        return path

    def test_candidate_approval_is_noncanonical_and_receipted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_candidate(vault)

            receipt = OwnerReviewPublisher(vault, runtime).candidate_disposition(
                "cand_review",
                target_status="approved-for-manual-apply",
                operation_id="review_candidate",
                changed_at=NOW,
            )

            candidate = KnowledgeCandidate.parse(path.read_text(encoding="utf-8"))
            self.assertEqual(candidate.status, "approved-for-manual-apply")
            self.assertEqual(candidate.authority, "noncanonical")
            self.assertTrue(receipt.is_file())
            self.assertFalse((vault / "Canonical Memory").exists())
            self.assertEqual(OwnerReviewPublisher(vault, runtime).pending_intents(), ())

            repeated = OwnerReviewPublisher(vault, runtime).candidate_disposition(
                "cand_review",
                target_status="approved-for-manual-apply",
                operation_id="review_candidate_repeated",
                changed_at=NOW,
            )
            self.assertEqual(repeated, receipt)
            self.assertFalse((runtime / "owner-reviews/review_candidate_repeated").exists())

    def test_interrupted_candidate_review_recovers_same_fixed_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_candidate(vault)

            def stop(point: str) -> None:
                if point == "after-receipt":
                    raise RuntimeError("stop")

            with self.assertRaises(RuntimeError):
                OwnerReviewPublisher(vault, runtime, fault=stop).candidate_disposition(
                    "cand_review",
                    target_status="rejected",
                    operation_id="review_interrupted",
                    changed_at=NOW,
                )
            self.assertEqual(
                KnowledgeCandidate.parse(path.read_text(encoding="utf-8")).status,
                "pending",
            )

            receipt = OwnerReviewPublisher(vault, runtime).recover("review_interrupted")

            self.assertTrue(receipt.is_file())
            self.assertEqual(
                KnowledgeCandidate.parse(path.read_text(encoding="utf-8")).status,
                "rejected",
            )

    def test_target_mismatch_is_detected_before_durable_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_candidate(vault)
            candidate = self._candidate()
            disposition = plan_disposition(
                candidate,
                target_status="rejected",
                owner_confirmed=True,
                operation_id="review_preflight",
                changed_at=NOW,
            )
            before = disposition.before.render().encode()
            after = disposition.after.render().encode()
            review = OwnerReviewPlan(
                "review_preflight",
                "candidate-disposition",
                candidate.candidate_id,
                "System/Orca Memory/provenance/owner-reviews/review_preflight.json",
                disposition.receipt.render().encode(),
                (
                    ReviewOutput(
                        "knowledge-candidate",
                        candidate.candidate_id,
                        path.relative_to(vault).as_posix(),
                        hashlib.sha256(before).hexdigest(),
                        hashlib.sha256(after).hexdigest(),
                        after,
                    ),
                ),
            )
            path.write_text(path.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")

            with self.assertRaisesRegex(OwnerReviewRepairRequired, "source is not pending"):
                OwnerReviewPublisher(vault, runtime).publish(review)

            self.assertFalse(
                (vault / "System/Orca Memory/provenance/owner-reviews/review_preflight.json").exists()
            )
            self.assertFalse((runtime / "owner-reviews").exists())

    def test_public_plan_cannot_target_an_unrelated_vault_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            candidate = self._candidate()
            disposition = plan_disposition(
                candidate,
                target_status="rejected",
                owner_confirmed=True,
                operation_id="review_bad_path",
                changed_at=NOW,
            )
            after = disposition.after.render().encode()
            review = OwnerReviewPlan(
                "review_bad_path",
                "candidate-disposition",
                candidate.candidate_id,
                "System/Orca Memory/provenance/owner-reviews/review_bad_path.json",
                disposition.receipt.render().encode(),
                (
                    ReviewOutput(
                        "knowledge-candidate",
                        candidate.candidate_id,
                        "Canonical Memory/unrelated.md",
                        disposition.receipt.candidate_before_sha256,
                        hashlib.sha256(after).hexdigest(),
                        after,
                    ),
                ),
            )

            with self.assertRaisesRegex(OwnerReviewRepairRequired, "candidate review output"):
                OwnerReviewPublisher(vault, runtime).publish(review)
            self.assertFalse((runtime / "owner-reviews").exists())

    def test_candidate_scan_rejects_symlink_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            outside = root / "outside.md"
            outside.write_text(self._candidate().render(), encoding="utf-8")
            link = (
                vault
                / "System/Orca Memory/candidates/knowledge/general"
                / "linked.md"
            )
            link.parent.mkdir(parents=True)
            os.symlink(outside, link)

            with self.assertRaisesRegex(OwnerReviewRepairRequired, "symlink"):
                OwnerReviewPublisher(vault, runtime).candidate_disposition(
                    "cand_review",
                    target_status="rejected",
                    operation_id="review_symlink",
                    changed_at=NOW,
                )

    def test_candidate_receipt_status_must_match_post_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_candidate(vault)
            approved = plan_disposition(
                self._candidate(),
                target_status="approved-for-manual-apply",
                owner_confirmed=True,
                operation_id="review_status_mismatch",
                changed_at=NOW,
            )
            after = approved.after.render().encode()
            false_receipt = DispositionReceipt(
                "review_status_mismatch",
                "cand_review",
                "pending",
                "rejected",
                NOW,
                approved.receipt.candidate_before_sha256,
                hashlib.sha256(after).hexdigest(),
            )
            review = OwnerReviewPlan(
                "review_status_mismatch",
                "candidate-disposition",
                "cand_review",
                "System/Orca Memory/provenance/owner-reviews/review_status_mismatch.json",
                false_receipt.render().encode(),
                (
                    ReviewOutput(
                        "knowledge-candidate",
                        "cand_review",
                        path.relative_to(vault).as_posix(),
                        approved.receipt.candidate_before_sha256,
                        hashlib.sha256(after).hexdigest(),
                        after,
                    ),
                ),
            )

            with self.assertRaisesRegex(OwnerReviewRepairRequired, "post-image"):
                OwnerReviewPublisher(vault, runtime).publish(review)
            self.assertFalse((runtime / "owner-reviews").exists())

    def test_edit_after_receipt_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_candidate(vault)
            edited = path.read_text(encoding="utf-8") + "external edit\n"

            def edit_after_receipt(point: str) -> None:
                if point == "after-receipt":
                    path.write_text(edited, encoding="utf-8")

            with self.assertRaisesRegex(OwnerReviewRepairRequired, "target mismatch"):
                OwnerReviewPublisher(
                    vault, runtime, fault=edit_after_receipt
                ).candidate_disposition(
                    "cand_review",
                    target_status="rejected",
                    operation_id="review_race",
                    changed_at=NOW,
                )

            self.assertEqual(path.read_text(encoding="utf-8"), edited)
            self.assertTrue(
                (vault / "System/Orca Memory/provenance/owner-reviews/review_race.json").is_file()
            )
            self.assertTrue((runtime / "owner-reviews/review_race/intent.json").is_file())

    def test_recovery_rejects_symlinked_staged_post_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            self._write_candidate(vault)

            def stop(point: str) -> None:
                if point == "after-receipt":
                    raise RuntimeError("stop")

            with self.assertRaises(RuntimeError):
                OwnerReviewPublisher(vault, runtime, fault=stop).candidate_disposition(
                    "cand_review",
                    target_status="rejected",
                    operation_id="review_staged_symlink",
                    changed_at=NOW,
                )
            staged = runtime / "owner-reviews/review_staged_symlink/output-1.post"
            staged.unlink()
            outside = root / "outside.post"
            outside.write_text("outside", encoding="utf-8")
            os.chmod(outside, 0o600)
            os.symlink(outside, staged)

            with self.assertRaisesRegex(OwnerReviewRepairRequired, "staged output"):
                OwnerReviewPublisher(vault, runtime).recover("review_staged_symlink")

    def test_conflict_select_and_keep_are_explicit_receipted_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_conflict(vault)
            publisher = OwnerReviewPublisher(vault, runtime)

            publisher.conflict_review(
                "mem_review",
                operation_id="review_keep",
                changed_at=NOW,
                keep_unresolved=True,
            )
            kept = parse_conflict_record(path.read_text(encoding="utf-8"))
            self.assertEqual(kept.review_state, "acknowledged")

            publisher.conflict_review(
                "mem_review",
                operation_id="review_select",
                changed_at=datetime(2026, 8, 31, 11, 0, tzinfo=timezone.utc),
                select_variant_id="v2",
            )
            rendered = path.read_text(encoding="utf-8")
            self.assertIn("status: current", rendered)
            self.assertIn("Use SQLite.", rendered)
            self.assertTrue(
                (vault / "System" / "Orca Memory" / "provenance" / "owner-reviews" / "review_select.json").is_file()
            )

    def test_public_conflict_plan_cannot_select_a_nonexistent_variant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_conflict(vault)
            source = parse_conflict_record(path.read_text(encoding="utf-8"))
            arbitrary = MemoryRecord(
                memory_id=source.memory_id,
                kind=source.kind,
                subject=source.subject,
                scope=source.scope,
                scope_id=source.scope_id,
                status="current",
                source_updated_at="2026-08-31T09:30:00Z",
                created_at=source.created_at,
                updated_at="2026-08-31T10:00:00Z",
                current="Arbitrary unreviewed position.",
                lineage=("`v99` — Invented — selected — 2026-08-31T09:30:00Z",),
            )
            before_hash = hashlib.sha256(source.render().encode()).hexdigest()
            after = arbitrary.render().encode()
            after_hash = hashlib.sha256(after).hexdigest()
            output = ReviewOutput(
                "typed-memory-record",
                source.memory_id,
                path.relative_to(vault).as_posix(),
                before_hash,
                after_hash,
                after,
            )
            receipt = {
                "schema": "orca-conflict-review-receipt/0.1",
                "operation_id": "review_bad_selection",
                "memory_id": source.memory_id,
                "action": "select:v99",
                "recorded_at": "2026-08-31T10:00:00Z",
                "variant_dispositions": [
                    {"variant_id": "v99", "disposition": "selected"}
                ],
                "outputs": [
                    {
                        "artifact_kind": output.artifact_kind,
                        "artifact_id": output.artifact_id,
                        "before_sha256": output.before_sha256,
                        "after_sha256": output.after_sha256,
                    }
                ],
            }
            review = OwnerReviewPlan(
                "review_bad_selection",
                "conflict-review",
                source.memory_id,
                "System/Orca Memory/provenance/owner-reviews/review_bad_selection.json",
                (json.dumps(receipt, sort_keys=True) + "\n").encode(),
                (output,),
            )

            with self.assertRaisesRegex(ValueError, "does not exist"):
                OwnerReviewPublisher(vault, runtime).publish(review)
            self.assertFalse((runtime / "owner-reviews").exists())

    def test_new_review_refuses_pending_intent_and_mismatched_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_candidate(vault)

            def stop(point: str) -> None:
                if point == "after-receipt":
                    raise RuntimeError("stop")

            with self.assertRaises(RuntimeError):
                OwnerReviewPublisher(vault, runtime, fault=stop).candidate_disposition(
                    "cand_review",
                    target_status="rejected",
                    operation_id="review_pending",
                    changed_at=NOW,
                )
            path.write_text(path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
            with self.assertRaises(OwnerReviewRepairRequired):
                OwnerReviewPublisher(vault, runtime).recover("review_pending")

    def test_overflow_variant_can_be_selected_then_candidate_is_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime = root / "vault", root / "runtime"
            path = self._write_conflict(vault)
            two = parse_conflict_record(path.read_text(encoding="utf-8"))
            three, _, _ = apply_conflict(
                two,
                ConflictProposal(
                    "mem_review", "decision", "Storage backend", "general", "general",
                    "Both", "Use both.", "2026-08-31T09:00:00Z",
                ),
                updated_at="2026-08-31T09:01:00Z",
            )
            four, overflow, _ = apply_conflict(
                three,
                ConflictProposal(
                    "mem_review", "decision", "Storage backend", "general", "general",
                    "Remote", "Use remote storage.", "2026-08-31T09:30:00Z",
                ),
                updated_at="2026-08-31T09:31:00Z",
            )
            assert overflow is not None
            path.write_text(four.render(), encoding="utf-8")
            overflow_path = vault / overflow.relative_path()
            overflow_path.parent.mkdir(parents=True)
            overflow_path.write_text(overflow.render(), encoding="utf-8")

            OwnerReviewPublisher(vault, runtime).conflict_review(
                "mem_review",
                operation_id="review_overflow",
                changed_at=NOW,
                select_variant_id="v4",
            )

            self.assertFalse(overflow_path.exists())
            resolved = path.read_text(encoding="utf-8")
            self.assertIn("Use remote storage.", resolved)
            self.assertIn("`v4` — Remote — selected", resolved)
            receipt = json.loads(
                (
                    vault
                    / "System/Orca Memory/provenance/owner-reviews/review_overflow.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                receipt["variant_dispositions"],
                [
                    {"variant_id": "v1", "disposition": "not-selected"},
                    {"variant_id": "v2", "disposition": "not-selected"},
                    {"variant_id": "v3", "disposition": "not-selected"},
                    {"variant_id": "v4", "disposition": "selected"},
                ],
            )
            self.assertEqual(
                receipt["outputs"][1]["artifact_id"], "mem_review:v4"
            )


if __name__ == "__main__":
    unittest.main()
