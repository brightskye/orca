from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import tempfile
import unittest

from orca_memory.candidates import (
    CANDIDATE_SCHEMA,
    CandidateProposal,
    DispositionReceipt,
    KnowledgeCandidate,
    candidate_filename,
    candidate_placement,
    candidate_short_id,
    materialize_candidate,
    plan_disposition,
    reconcile_disposition,
    support_candidate,
    validate_candidate,
)


NOW = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)


def _proposal(
    *,
    kind: str = "fact",
    scope: str = "project",
    scope_id: str = "proj_orca",
    context: str | None = "Bounded context.",
    source_updated_at: str | None = "2026-08-30T09:00:00Z",
) -> CandidateProposal:
    return CandidateProposal(
        candidate_kind=kind,
        subject="Deployment policy",
        proposal="The local runtime remains outside the configured vault.",
        context=context,
        scope=scope,
        scope_id=scope_id,
        source_updated_at=source_updated_at,
    )


def _candidate(**kwargs: object) -> KnowledgeCandidate:
    values = {
        "candidate_id": "cand_runtime",
        "candidate_kind": "fact",
        "subject": "Deployment policy",
        "authority": "noncanonical",
        "scope": "project",
        "scope_id": "proj_orca",
        "status": "pending",
        "source_updated_at": "2026-08-30T09:00:00Z",
        "created_at": NOW,
        "updated_at": NOW,
        "proposal": "The local runtime remains outside the configured vault.",
        "context": "Bounded context.",
        "schema_version": CANDIDATE_SCHEMA,
    }
    values.update(kwargs)
    return KnowledgeCandidate(**values)


class CandidateSchemaTests(unittest.TestCase):
    def test_materialization_always_starts_pending_and_round_trips_all_kinds(self) -> None:
        for kind in ("fact", "decision", "preference", "lesson", "project-state"):
            proposal = _proposal(kind=kind)
            candidate = materialize_candidate(
                proposal,
                candidate_id=f"cand_{kind}",
                created_at=NOW,
            )
            self.assertEqual(candidate.status, "pending")
            self.assertEqual(validate_candidate(candidate.render()), candidate)

    def test_round_trips_general_and_unassigned_scopes_and_terminal_states(self) -> None:
        for scope in ("general", "unassigned"):
            candidate = materialize_candidate(
                _proposal(scope=scope, scope_id=scope, context=None, source_updated_at=None),
                candidate_id=f"cand_{scope}",
                created_at=NOW,
            )
            for status in ("pending", "approved-for-manual-apply", "rejected"):
                current = KnowledgeCandidate(
                    **{
                        **candidate.__dict__,
                        "status": status,
                    }
                )
                self.assertEqual(validate_candidate(current.render()), current)

    def test_rejects_extra_provenance_target_and_secret_fields(self) -> None:
        rendered = _candidate().render()
        for extra in (
            "source_uri: codex://private",
            "canonical_target: canonical/file.md",
            "source_hash: abc",
        ):
            with self.assertRaises(ValueError):
                validate_candidate(rendered.replace("updated_at:", f"{extra}\nupdated_at:"))
        with self.assertRaises(ValueError):
            materialize_candidate(
                CandidateProposal(
                    candidate_kind="fact",
                    subject="Credential fact",
                    proposal="api_key=secret-value",
                    scope="general",
                    scope_id="general",
                ),
                candidate_id="cand_secret",
                created_at=NOW,
            )

    def test_rejects_unknown_sections_and_scope_inconsistency(self) -> None:
        with self.assertRaises(ValueError):
            validate_candidate(_candidate().render() + "\n## Sources\n\nnot permitted\n")
        with self.assertRaises(ValueError):
            _proposal(scope="general", scope_id="proj_orca")


class CandidatePlacementTests(unittest.TestCase):
    def test_placement_uses_knowledge_subtree_and_deterministic_short_id(self) -> None:
        candidate = _candidate()
        expected_short = hashlib.sha256(candidate.candidate_id.encode()).hexdigest()[:12]
        self.assertEqual(candidate_short_id(candidate.candidate_id), expected_short)
        self.assertEqual(candidate_filename(candidate), f"deployment-policy--{expected_short}.md")
        with tempfile.TemporaryDirectory() as directory:
            placement = candidate_placement(directory, candidate, project_alias="Orca")
            self.assertEqual(
                placement.relative_path,
                f"System/Orca Memory/candidates/knowledge/projects/orca/{candidate_filename(candidate)}",
            )
            self.assertEqual(placement.path, Path(directory) / placement.relative_path)
            self.assertFalse(placement.path.exists())

    def test_general_and_unassigned_placement_has_no_project_alias(self) -> None:
        for scope in ("general", "unassigned"):
            candidate = _candidate(scope=scope, scope_id=scope, context=None, source_updated_at=None)
            placement = candidate_placement("/vault", candidate)
            self.assertIn(f"knowledge/{scope}/", placement.relative_path)
            with self.assertRaises(ValueError):
                candidate_placement("/vault", candidate, project_alias="Orca")


class CandidateLifecycleTests(unittest.TestCase):
    def test_exact_support_returns_same_candidate_without_rewrite_or_timestamp_change(self) -> None:
        candidate = _candidate()
        result = support_candidate(candidate, candidate.to_proposal(), candidate_id=candidate.candidate_id)
        self.assertIs(result.candidate, candidate)
        self.assertFalse(result.changed)
        self.assertEqual(result.operation, "support")

        supporting_source = CandidateProposal(
            **{
                **candidate.to_proposal().__dict__,
                "source_updated_at": "2026-08-30T11:00:00Z",
            }
        )
        self.assertIs(support_candidate(candidate, supporting_source).candidate, candidate)
        with self.assertRaises(ValueError):
            support_candidate(
                candidate,
                CandidateProposal(
                    candidate_kind="fact",
                    subject="Different subject",
                    proposal=candidate.proposal,
                    scope="project",
                    scope_id="proj_orca",
                ),
            )

    def test_disposition_requires_owner_and_pending_identity(self) -> None:
        candidate = _candidate()
        with self.assertRaises(PermissionError):
            plan_disposition(
                candidate,
                target_status="approved-for-manual-apply",
                owner_confirmed=False,
                operation_id="op_1",
                changed_at=NOW,
            )
        with self.assertRaises(ValueError):
            plan_disposition(
                candidate,
                target_status="rejected",
                owner_confirmed=True,
                operation_id="op_1",
                changed_at=NOW,
                expected_candidate_id="cand_other",
            )
        approved = plan_disposition(
            candidate,
            target_status="approved-for-manual-apply",
            owner_confirmed=True,
            operation_id="op_1",
            changed_at="2026-08-30T11:00:00Z",
            expected_candidate_id=candidate.candidate_id,
        )
        self.assertEqual(approved.after.status, "approved-for-manual-apply")
        self.assertEqual(approved.after.authority, "noncanonical")
        self.assertEqual(approved.before.status, "pending")
        self.assertEqual(approved.receipt.candidate_id, candidate.candidate_id)
        self.assertNotIn("Deployment policy", approved.receipt.render())

        with self.assertRaises(ValueError):
            plan_disposition(
                approved.after,
                target_status="rejected",
                owner_confirmed=True,
                operation_id="op_2",
                changed_at="2026-08-30T12:00:00Z",
            )

    def test_disposition_receipt_reconciles_before_after_or_repair(self) -> None:
        candidate = _candidate()
        plan = plan_disposition(
            candidate,
            target_status="rejected",
            owner_confirmed=True,
            operation_id="op_reject",
            changed_at="2026-08-30T11:00:00Z",
        )
        self.assertEqual(reconcile_disposition(candidate, plan.receipt).status, "pending")
        self.assertEqual(reconcile_disposition(plan.after, plan.receipt).status, "applied")
        changed = KnowledgeCandidate(
            **{**plan.after.__dict__, "context": "Changed after receipt."}
        )
        self.assertEqual(reconcile_disposition(changed, plan.receipt).status, "repair-required")
        self.assertEqual(
            DispositionReceipt.parse(plan.receipt.render()),
            plan.receipt,
        )


if __name__ == "__main__":
    unittest.main()
