from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_ROOT = PROJECT_ROOT / "prototype" / "integration"
PHASE7_ROOT = INTEGRATION_ROOT / "phase7"
PHASE6_ROOT = INTEGRATION_ROOT / "phase6"
sys.path.insert(0, str(PHASE7_ROOT))
sys.path.insert(0, str(PHASE6_ROOT))

from cairn_delta_adapter import content_sha256, run_adapter  # noqa: E402
from curator_delta_intake import (  # noqa: E402
    AUTHORIZATION_SCHEMA,
    BatchValidationError,
    INTEGRATION_NAME,
    INTEGRATION_VERSION,
    PLAN_SCHEMA,
    PROPOSAL_SCHEMA,
    AuthorizationError,
    IntakeError,
    Phase7Error,
    PlanError,
    ProcessingStateError,
    _empty_state,
    _exclusive_state_lock,
    _new_event_state,
    _state_record_sha256,
    apply_plan,
    create_plan,
    derive_event_id,
    load_processing_state,
    process_batch,
    validate_phase6_batch,
)


FIXTURES = Path(__file__).parent / "fixtures" / "development"
TIME_1 = "2026-08-22T21:00:00+00:00"
TIME_2 = "2026-08-22T21:01:00+00:00"
TIME_3 = "2026-08-22T21:02:00+00:00"
STORE_ID = "phase7-development-store"
HARNESS = "phase7-development"


def note_text(permalink: str, content: str, *, source: str | None = None) -> str:
    return "\n".join(
        [
            "---",
            f"title: {permalink}",
            "type: memory",
            f"permalink: {permalink}",
            f"source: {source or 'memory://session/' + permalink}",
            f"harness: {HARNESS}",
            "project: Orca",
            "observed_project: Orca",
            "intent: implicit",
            "entry_mode: conversational",
            "authority: candidate",
            "---",
            "",
            f"- [context] {content} #orca-candidate",
            "",
        ]
    )


class Phase7Fixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = root / "cairn"
        self.canonical = root / "canonical"
        self.artifacts = root / "curator"
        self.state = root / "state" / "processing.json"
        self.checkpoint = root / "phase6" / "checkpoint.json"
        self.batch_index = 0
        shutil.copytree(FIXTURES / "cairn", self.store)
        shutil.copytree(FIXTURES / "canonical", self.canonical)

    def write_note(self, permalink: str, content: str, filename: str | None = None) -> Path:
        path = self.store / (filename or f"{permalink}.md")
        path.write_text(note_text(permalink, content), encoding="utf-8")
        return path

    def emit(self, at: str) -> tuple[Path, dict]:
        self.batch_index += 1
        path = self.root / "phase6" / f"batch-{self.batch_index}.json"
        result = run_adapter(
            source_root=self.store,
            checkpoint_path=self.checkpoint,
            output_path=path,
            store_id=STORE_ID,
            harness=HARNESS,
            default_intent="implicit",
            generated_at=at,
        )
        return path, result

    def intake(self, batch_path: Path, batch: dict, at: str = TIME_2) -> dict:
        return process_batch(
            batch_path=batch_path,
            source_root=self.store,
            state_path=self.state,
            artifact_root=self.artifacts,
            store_id=STORE_ID,
            harness=HARNESS,
            default_intent="implicit",
            expected_previous_checkpoint_id=batch["checkpoint"]["previous_id"],
            checked_at=at,
        )

    def intake_path(self, result: dict, index: int = 0) -> Path:
        return self.artifacts / result["results"][index]["reference"]

    def proposal(
        self,
        intake_path: Path,
        *,
        comparison: str = "new distinct knowledge",
        disposition: str = "promoted",
        action: str = "write_markdown",
        target: str | None = "Knowledge/phase7.md",
        content: str = "# Phase 7 fixture\n\nOne governed canonical effect.\n",
        authority: str = "curator",
    ) -> Path:
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        proposed_action = {"kind": "none"} if action == "none" else {"kind": "write_markdown", "content": content}
        proposal = {
            "schema": PROPOSAL_SCHEMA,
            "schema_version": 1,
            "event_id": intake["event_id"],
            "comparison_class": comparison,
            "proposed_disposition": disposition,
            "canonical_target": target,
            "proposed_action": proposed_action,
            "evidence_references": [intake_path.relative_to(self.artifacts).as_posix()],
            "rationale": "Fixture Curator judgment supplied outside deterministic code.",
            "authority_requirement": authority,
        }
        path = self.root / "proposals" / f"proposal-{len(list((self.root / 'proposals').glob('*.json'))) if (self.root / 'proposals').exists() else 0}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
        return path

    def plan(self, intake_path: Path, proposal_path: Path, at: str = TIME_2) -> dict:
        return create_plan(
            intake_path=intake_path,
            proposal_path=proposal_path,
            source_root=self.store,
            canonical_root=self.canonical,
            state_path=self.state,
            artifact_root=self.artifacts,
            generated_at=at,
        )

    def plan_path(self, plan: dict) -> Path:
        return self.artifacts / "plans" / (plan["plan_id"].split(":", 1)[1] + ".json")

    def authorization(self, plan: dict, *, approved: bool = True, authority: str = "curator") -> Path:
        value = {
            "schema": AUTHORIZATION_SCHEMA,
            "schema_version": 1,
            "plan_id": plan["plan_id"],
            "approved": approved,
            "actor": "human:fixture-owner" if authority == "human" else "agent:fixture-curator",
            "authority": authority,
            "scope": "phase7-fixture-or-explicit-local-plan",
        }
        path = self.root / "authorization" / (plan["plan_id"].split(":", 1)[1] + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def apply(self, plan: dict, authorization: Path, **kwargs) -> dict:
        return apply_plan(
            plan_path=self.plan_path(plan),
            authorization_path=authorization,
            source_root=self.store,
            canonical_root=self.canonical,
            state_path=self.state,
            artifact_root=self.artifacts,
            applied_at=TIME_3,
            **kwargs,
        )


class Phase7Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fx = Phase7Fixture(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def initial_intake(self) -> tuple[Path, dict, Path]:
        batch_path, batch = self.fx.emit(TIME_1)
        result = self.fx.intake(batch_path, batch)
        return batch_path, batch, self.fx.intake_path(result)

    def planned(self, **proposal_kwargs) -> tuple[dict, Path]:
        _, _, intake_path = self.initial_intake()
        proposal = self.fx.proposal(intake_path, **proposal_kwargs)
        plan = self.fx.plan(intake_path, proposal)
        return plan, intake_path

    # I1-I10 deterministic intake
    def test_I1_valid_added_batch(self) -> None:
        _, batch, intake_path = self.initial_intake()
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        self.assertEqual(batch["summary"]["added"], 1)
        self.assertEqual(intake["candidate"]["change"], "added")
        self.assertEqual(intake["freshness"]["status"], "fresh")

    def test_I2_valid_changed_batch_preserves_revisions(self) -> None:
        self.fx.emit(TIME_1)
        path = self.fx.store / "alpha.md"
        old = content_sha256("Alpha is a durable Phase 7 fixture candidate.")
        path.write_text(note_text("phase7-alpha", "Alpha is revised."), encoding="utf-8")
        batch_path, batch = self.fx.emit(TIME_2)
        result = self.fx.intake(batch_path, batch, TIME_3)
        intake = json.loads(self.fx.intake_path(result).read_text(encoding="utf-8"))
        self.assertEqual(intake["candidate"]["change"], "changed")
        self.assertEqual(intake["candidate"]["previous_revision"], old)
        self.assertEqual(intake["candidate"]["current_revision"], content_sha256("Alpha is revised."))

    def test_I3_valid_deleted_batch_preserves_prior_evidence(self) -> None:
        self.fx.emit(TIME_1)
        (self.fx.store / "alpha.md").unlink()
        batch_path, batch = self.fx.emit(TIME_2)
        result = self.fx.intake(batch_path, batch)
        intake = json.loads(self.fx.intake_path(result).read_text(encoding="utf-8"))
        self.assertEqual(intake["candidate"]["change"], "deleted")
        self.assertIsNone(intake["candidate"]["current_revision"])
        self.assertTrue(intake["candidate"]["previous_revision"])
        self.assertFalse(intake["curator_contract"]["canonical_deletion_from_source_removal"])

    def test_I4_unchanged_only_batch_creates_no_intake(self) -> None:
        self.fx.emit(TIME_1)
        batch_path, batch = self.fx.emit(TIME_2)
        result = self.fx.intake(batch_path, batch)
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["unchanged_suppressed"], 1)
        self.assertFalse((self.fx.artifacts / "intakes").exists())

    def test_I5_duplicate_batch_retry_has_no_duplicate_intake(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        first = self.fx.intake(batch_path, batch)
        second = self.fx.intake(batch_path, batch, TIME_3)
        self.assertEqual(second["results"][0]["status"], "already_processed")
        self.assertEqual(len(list((self.fx.artifacts / "intakes").glob("*.json"))), 1)
        self.assertEqual(first["results"][0]["event_id"], second["results"][0]["event_id"])

    def test_I6_duplicate_event_inside_batch_fails_whole_batch(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        bad = copy.deepcopy(batch)
        bad["deltas"].append(copy.deepcopy(bad["deltas"][0]))
        bad["summary"]["added"] += 1
        batch_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(BatchValidationError, "duplicate"):
            self.fx.intake(batch_path, bad)
        self.assertFalse(self.fx.state.exists())

    def test_I7_unsupported_schema_or_adapter_fails_closed(self) -> None:
        _, batch = self.fx.emit(TIME_1)
        for mutation in (("schema_version", 99), ("adapter", {"name": "orca-cairn-delta", "version": "9"})):
            bad = copy.deepcopy(batch)
            bad[mutation[0]] = mutation[1]
            with self.subTest(mutation=mutation), self.assertRaises(BatchValidationError):
                validate_phase6_batch(bad, expected_store_id=STORE_ID, expected_harness=HARNESS, expected_default_intent="implicit", expected_previous_checkpoint_id=None)

    def test_I8_source_store_mismatch_fails_closed(self) -> None:
        _, batch = self.fx.emit(TIME_1)
        with self.assertRaisesRegex(BatchValidationError, "source-store mismatch"):
            validate_phase6_batch(batch, expected_store_id="wrong", expected_harness=HARNESS, expected_default_intent="implicit", expected_previous_checkpoint_id=None)

    def test_I9_checkpoint_lineage_mismatch_fails_closed(self) -> None:
        _, batch = self.fx.emit(TIME_1)
        with self.assertRaisesRegex(BatchValidationError, "checkpoint-lineage mismatch"):
            validate_phase6_batch(batch, expected_store_id=STORE_ID, expected_harness=HARNESS, expected_default_intent="implicit", expected_previous_checkpoint_id="phase6:" + "0" * 64)

    def test_I10_malformed_delta_fails_without_state(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        bad = copy.deepcopy(batch)
        del bad["deltas"][0]["sources"]
        batch_path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaisesRegex(BatchValidationError, "malformed"):
            self.fx.intake(batch_path, bad)
        self.assertFalse(self.fx.state.exists())

    # F1-F5 freshness
    def test_F1_added_revision_remains_current(self) -> None:
        _, _, intake_path = self.initial_intake()
        self.assertEqual(json.loads(intake_path.read_text(encoding="utf-8"))["freshness"]["status"], "fresh")

    def test_F2_changed_revision_changed_again_is_stale(self) -> None:
        self.fx.emit(TIME_1)
        (self.fx.store / "alpha.md").write_text(note_text("phase7-alpha", "Revision two."), encoding="utf-8")
        batch_path, batch = self.fx.emit(TIME_2)
        (self.fx.store / "alpha.md").write_text(note_text("phase7-alpha", "Revision three."), encoding="utf-8")
        result = self.fx.intake(batch_path, batch, TIME_3)
        self.assertEqual(result["results"][0]["status"], "stale")
        self.assertFalse((self.fx.artifacts / "intakes").exists())

    def test_F3_deleted_permalink_remains_absent(self) -> None:
        self.fx.emit(TIME_1)
        (self.fx.store / "alpha.md").unlink()
        batch_path, batch = self.fx.emit(TIME_2)
        self.assertEqual(self.fx.intake(batch_path, batch)["results"][0]["status"], "fresh")

    def test_F4_deleted_permalink_reappears_is_stale(self) -> None:
        self.fx.emit(TIME_1)
        original = (self.fx.store / "alpha.md").read_text(encoding="utf-8")
        (self.fx.store / "alpha.md").unlink()
        batch_path, batch = self.fx.emit(TIME_2)
        (self.fx.store / "alpha.md").write_text(original, encoding="utf-8")
        result = self.fx.intake(batch_path, batch, TIME_3)
        self.assertEqual(result["results"][0]["status"], "stale")

    def test_F5_move_same_permalink_revision_has_no_actionable_event(self) -> None:
        self.fx.emit(TIME_1)
        (self.fx.store / "alpha.md").rename(self.fx.store / "renamed.md")
        batch_path, batch = self.fx.emit(TIME_2)
        self.assertEqual(batch["summary"], {"added": 0, "changed": 0, "deleted": 0, "unchanged": 1})
        self.assertEqual(self.fx.intake(batch_path, batch)["event_count"], 0)

    # D1-D5 idempotency
    def test_D1_same_event_planned_twice_has_one_plan_identity(self) -> None:
        _, _, intake_path = self.initial_intake()
        proposal = self.fx.proposal(intake_path)
        first = self.fx.plan(intake_path, proposal, TIME_2)
        second = self.fx.plan(intake_path, proposal, TIME_3)
        self.assertEqual(first["plan_id"], second["plan_id"])
        self.assertEqual(len(list((self.fx.artifacts / "plans").glob("*.json"))), 1)

    def test_D2_same_event_applied_twice_has_one_effect(self) -> None:
        plan, _ = self.planned()
        auth = self.fx.authorization(plan)
        first = self.fx.apply(plan, auth)
        second = self.fx.apply(plan, auth)
        self.assertEqual(first["canonical_effect"]["after_sha256"], file_hash(self.fx.canonical / "Knowledge/phase7.md"))
        self.assertEqual(second["status"], "already_applied")
        self.assertEqual(len(list((self.fx.artifacts / "dispositions").glob("*.md"))), 1)

    def test_D2_retry_revalidates_authorization_before_already_applied(self) -> None:
        plan, _ = self.planned()
        valid = self.fx.authorization(plan)
        self.fx.apply(plan, valid)
        denied = self.fx.authorization(plan, approved=False)
        with self.assertRaisesRegex(AuthorizationError, "approve this exact plan"):
            self.fx.apply(plan, denied)
        self.assertEqual(len(list((self.fx.artifacts / "dispositions").glob("*.md"))), 1)

    def test_D3_process_restart_uses_persisted_state(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        self.fx.intake(batch_path, batch)
        reloaded = load_processing_state(self.fx.state, batch["source_store"])
        self.assertEqual(len(reloaded["events"]), 1)
        self.assertEqual(self.fx.intake(batch_path, batch)["results"][0]["status"], "already_processed")

    def test_D4_same_permalink_newer_revision_is_new_event(self) -> None:
        batch1_path, batch1 = self.fx.emit(TIME_1)
        first = self.fx.intake(batch1_path, batch1)
        (self.fx.store / "alpha.md").write_text(note_text("phase7-alpha", "A later revision."), encoding="utf-8")
        batch2_path, batch2 = self.fx.emit(TIME_2)
        second = self.fx.intake(batch2_path, batch2, TIME_3)
        self.assertNotEqual(first["results"][0]["event_id"], second["results"][0]["event_id"])
        self.assertEqual(len(list((self.fx.artifacts / "intakes").glob("*.json"))), 2)

    def test_D5_similar_content_independent_permalink_is_not_retry(self) -> None:
        content = "Same words, independent evidence."
        self.fx.store.joinpath("alpha.md").write_text(note_text("phase7-alpha", content), encoding="utf-8")
        self.fx.write_note("phase7-beta", content, "beta.md")
        batch_path, batch = self.fx.emit(TIME_1)
        result = self.fx.intake(batch_path, batch)
        self.assertEqual(len({item["event_id"] for item in result["results"]}), 2)

    # A1-A5 apply safety
    def test_A1_source_changes_after_plan_aborts_apply(self) -> None:
        plan, _ = self.planned()
        auth = self.fx.authorization(plan)
        (self.fx.store / "alpha.md").write_text(note_text("phase7-alpha", "Changed after plan."), encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "source precondition"):
            self.fx.apply(plan, auth)
        self.assertFalse((self.fx.canonical / "Knowledge/phase7.md").exists())

    def test_A2_canonical_target_changes_after_plan_aborts(self) -> None:
        plan, _ = self.planned(target="Knowledge/existing.md")
        auth = self.fx.authorization(plan)
        (self.fx.canonical / "Knowledge/existing.md").write_text("human edit\n", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "canonical precondition"):
            self.fx.apply(plan, auth)
        self.assertEqual((self.fx.canonical / "Knowledge/existing.md").read_text(encoding="utf-8"), "human edit\n")

    def test_A3_missing_or_insufficient_authority_never_applies(self) -> None:
        plan, _ = self.planned(authority="human")
        denied = self.fx.authorization(plan, approved=False, authority="human")
        with self.assertRaises(AuthorizationError):
            self.fx.apply(plan, denied)
        curator_only = self.fx.authorization(plan, authority="curator")
        with self.assertRaisesRegex(AuthorizationError, "human"):
            self.fx.apply(plan, curator_only)
        self.assertFalse((self.fx.canonical / "Knowledge/phase7.md").exists())

    def test_A4_successful_authorized_fixture_apply_links_disposition(self) -> None:
        plan, _ = self.planned()
        result = self.fx.apply(plan, self.fx.authorization(plan))
        disposition = (self.fx.artifacts / result["disposition_reference"]).read_text(encoding="utf-8")
        self.assertIn(plan["event_id"], disposition)
        self.assertIn(plan["plan_id"], disposition)
        self.assertIn("Knowledge/phase7.md", disposition)

    def test_A5_failure_after_canonical_write_recovers_without_duplicate_effect(self) -> None:
        plan, _ = self.planned()
        auth = self.fx.authorization(plan)
        calls = []

        def fail_once(path: Path) -> None:
            calls.append(path)
            raise RuntimeError("controlled crash")

        with self.assertRaisesRegex(RuntimeError, "controlled crash"):
            self.fx.apply(plan, auth, after_canonical_write=fail_once)
        target = self.fx.canonical / "Knowledge/phase7.md"
        first_bytes = target.read_bytes()
        result = self.fx.apply(plan, auth)
        self.assertEqual(target.read_bytes(), first_bytes)
        self.assertEqual(result["canonical_effect"]["status"], "already_present")
        self.assertEqual(len(calls), 1)

    def test_apply_recovers_after_disposition_before_state_persistence(self) -> None:
        plan, _ = self.planned()
        auth = self.fx.authorization(plan)

        def fail_once(path: Path) -> None:
            raise RuntimeError(f"controlled state-persistence crash after {path.name}")

        with self.assertRaisesRegex(RuntimeError, "state-persistence crash"):
            self.fx.apply(plan, auth, after_disposition_write=fail_once)
        result = self.fx.apply(plan, auth)
        self.assertEqual(result["status"], "applied")
        self.assertEqual(len(list((self.fx.artifacts / "dispositions").glob("*.md"))), 1)

    # X1-X4 deletion safety
    def deletion_intake(self) -> Path:
        self.fx.emit(TIME_1)
        (self.fx.store / "alpha.md").unlink()
        batch_path, batch = self.fx.emit(TIME_2)
        return self.fx.intake_path(self.fx.intake(batch_path, batch, TIME_3))

    def test_X1_deleted_unreviewed_candidate_has_no_canonical_deletion(self) -> None:
        intake = self.deletion_intake()
        proposal = self.fx.proposal(intake, comparison="source candidate removed", disposition="consumed", action="none", target=None)
        plan = self.fx.plan(intake, proposal)
        result = self.fx.apply(plan, self.fx.authorization(plan))
        self.assertEqual(result["canonical_effect"]["kind"], "none")

    def test_X2_deleted_rejected_candidate_preserves_history(self) -> None:
        _, _, intake = self.initial_intake()
        proposal = self.fx.proposal(intake, comparison="unsupported", disposition="rejected", action="none", target=None)
        plan = self.fx.plan(intake, proposal)
        first = self.fx.apply(plan, self.fx.authorization(plan))
        (self.fx.store / "alpha.md").unlink()
        batch_path, batch = self.fx.emit(TIME_2)
        deletion = json.loads(self.fx.intake_path(self.fx.intake(batch_path, batch, TIME_3)).read_text(encoding="utf-8"))
        self.assertEqual(deletion["prior_dispositions"][0]["disposition_id"], first["disposition_id"])
        self.assertTrue((self.fx.artifacts / first["disposition_reference"]).exists())

    def test_X3_deleted_promoted_candidate_leaves_canonical_note(self) -> None:
        plan, _ = self.planned()
        self.fx.apply(plan, self.fx.authorization(plan))
        target = self.fx.canonical / "Knowledge/phase7.md"
        before = target.read_bytes()
        (self.fx.store / "alpha.md").unlink()
        batch_path, batch = self.fx.emit(TIME_2)
        deletion_path = self.fx.intake_path(self.fx.intake(batch_path, batch, TIME_3))
        proposal = self.fx.proposal(deletion_path, comparison="source candidate removed", disposition="consumed", action="none", target="Knowledge/phase7.md")
        deletion_plan = self.fx.plan(deletion_path, proposal)
        self.fx.apply(deletion_plan, self.fx.authorization(deletion_plan))
        self.assertEqual(target.read_bytes(), before)

    def test_X4_deleted_source_reappears_as_new_event_with_history(self) -> None:
        deleted_path = self.deletion_intake()
        proposal = self.fx.proposal(deleted_path, comparison="source candidate removed", disposition="consumed", action="none", target=None)
        deleted_plan = self.fx.plan(deleted_path, proposal)
        deleted_result = self.fx.apply(deleted_plan, self.fx.authorization(deleted_plan))
        self.fx.write_note("phase7-alpha", "Alpha is a durable Phase 7 fixture candidate.", "alpha-returned.md")
        batch_path, batch = self.fx.emit("2026-08-22T21:03:00+00:00")
        returned = json.loads(self.fx.intake_path(self.fx.intake(batch_path, batch, "2026-08-22T21:04:00+00:00")).read_text(encoding="utf-8"))
        self.assertEqual(returned["candidate"]["change"], "added")
        self.assertEqual(returned["prior_dispositions"][0]["disposition_id"], deleted_result["disposition_id"])

    def test_processing_state_corruption_fails_closed(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        self.fx.state.parent.mkdir(parents=True, exist_ok=True)
        self.fx.state.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ProcessingStateError):
            self.fx.intake(batch_path, batch)
        self.assertEqual(self.fx.state.read_text(encoding="utf-8"), "{broken")

    def test_partial_batch_reports_fresh_stale_and_already_processed(self) -> None:
        self.fx.write_note("phase7-beta", "Beta current.", "beta.md")
        self.fx.write_note("phase7-gamma", "Gamma current.", "gamma.md")
        batch_path, batch = self.fx.emit(TIME_1)
        validated = validate_phase6_batch(batch, expected_store_id=STORE_ID, expected_harness=HARNESS, expected_default_intent="implicit", expected_previous_checkpoint_id=None)
        state = _empty_state(batch["source_store"])
        gamma_event = next(event for event in validated.events if event.delta["permalink"] == "phase7-gamma")
        gamma = _new_event_state(gamma_event, validated.batch_id)
        gamma["status"] = "applied"
        gamma["intake_reference"] = "intakes/preexisting.json"
        gamma["plan_id"] = "phase7-plan:" + "2" * 64
        gamma["plan_reference"] = "plans/preexisting.json"
        gamma["disposition_id"] = "phase7-disposition:" + "1" * 64
        gamma["disposition_reference"] = "dispositions/preexisting.md"
        gamma["canonical_effect"] = {"kind": "none"}
        state["events"][gamma_event.event_id] = gamma
        self.fx.state.parent.mkdir(parents=True, exist_ok=True)
        self.fx.state.write_text(json.dumps(state), encoding="utf-8")
        (self.fx.store / "beta.md").write_text(note_text("phase7-beta", "Beta changed again."), encoding="utf-8")
        result = self.fx.intake(batch_path, batch, TIME_2)
        statuses = {item["permalink"]: item["status"] for item in result["results"]}
        self.assertEqual(statuses, {"phase7-alpha": "fresh", "phase7-beta": "stale", "phase7-gamma": "already_processed"})

    def test_event_identity_is_deterministic_and_revision_specific(self) -> None:
        _, batch = self.fx.emit(TIME_1)
        event = batch["deltas"][0]
        first = derive_event_id(batch, event)
        self.assertEqual(first, derive_event_id(copy.deepcopy(batch), copy.deepcopy(event)))
        changed = copy.deepcopy(event)
        changed["change"] = "changed"
        changed["previous_sha256"] = event["current_sha256"]
        changed["current_sha256"] = "f" * 64
        self.assertNotEqual(first, derive_event_id(batch, changed))

    def test_plan_schema_records_source_and_canonical_preconditions(self) -> None:
        plan, _ = self.planned(target="Knowledge/existing.md")
        self.assertEqual(plan["schema"], PLAN_SCHEMA)
        self.assertEqual(plan["source_precondition"]["permalink"], "phase7-alpha")
        self.assertEqual(plan["canonical_precondition"]["expected_sha256"], file_hash(self.fx.canonical / "Knowledge/existing.md"))
        self.assertTrue(plan["disposition_id"].startswith("phase7-disposition:"))

    def test_governance_cases_are_external_and_preserved_in_plans(self) -> None:
        cases = json.loads((FIXTURES / "governance-cases.json").read_text(encoding="utf-8"))
        self.assertEqual(set(cases), {"distinct", "exact_duplicate", "semantic_duplicate", "rejection", "merge", "promotion_plan", "correction_plan", "supersession_plan", "source_removal"})
        for name, case in cases.items():
            with self.subTest(case=name):
                self.assertIsInstance(case["comparison"], str)
                self.assertIn(case["disposition"], {"consumed", "rejected", "merged", "promoted", "superseded"})
                self.assertIn(case["action"], {"none", "write_markdown"})
        self.assertEqual(cases["supersession_plan"]["disposition"], "promoted")
        self.assertEqual(cases["supersession_plan"]["prior_disposition"], "superseded")
        module_text = (PHASE7_ROOT / "curator_delta_intake.py").read_text(encoding="utf-8")
        self.assertNotIn("semantic_duplicate =", module_text)
        self.assertNotIn("if comparison_class", module_text)

    def test_lineage_reconstructs_delta_intake_plan_disposition_effect(self) -> None:
        plan, intake_path = self.planned()
        result = self.fx.apply(plan, self.fx.authorization(plan))
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        disposition = (self.fx.artifacts / result["disposition_reference"]).read_text(encoding="utf-8")
        self.assertEqual(intake["event_id"], plan["event_id"])
        self.assertIn(plan["event_id"], disposition)
        self.assertIn(plan["plan_id"], disposition)
        self.assertEqual(result["canonical_effect"]["target"], plan["canonical_target"])

    def test_no_delete_action_exists(self) -> None:
        _, _, intake_path = self.initial_intake()
        proposal = self.fx.proposal(intake_path)
        value = json.loads(proposal.read_text(encoding="utf-8"))
        value["proposed_action"] = {"kind": "delete"}
        proposal.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "none or write_markdown"):
            self.fx.plan(intake_path, proposal)

    def test_tampered_intake_candidate_is_rejected_before_plan(self) -> None:
        _, _, intake_path = self.initial_intake()
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        intake["candidate"]["content"] = "tampered content"
        intake_path.write_text(json.dumps(intake), encoding="utf-8")
        proposal = self.fx.proposal(intake_path)
        with self.assertRaisesRegex(IntakeError, "change-kind semantics"):
            self.fx.plan(intake_path, proposal)

    def test_unrecorded_duplicate_intake_path_is_rejected(self) -> None:
        _, _, intake_path = self.initial_intake()
        duplicate = self.fx.artifacts / "intakes" / "duplicate.json"
        duplicate.write_bytes(intake_path.read_bytes())
        proposal = self.fx.proposal(duplicate)
        with self.assertRaisesRegex(PlanError, "matching received intake"):
            self.fx.plan(duplicate, proposal)

    def test_incoherent_schema_shaped_state_fails_closed(self) -> None:
        _, batch, _ = self.initial_intake()
        state = json.loads(self.fx.state.read_text(encoding="utf-8"))
        event = next(iter(state["events"].values()))
        event["plan_id"] = "phase7-plan:" + "3" * 64
        self.fx.state.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ProcessingStateError, "plan lineage is incoherent"):
            load_processing_state(self.fx.state, batch["source_store"])

    def test_state_identity_fields_are_hash_bound(self) -> None:
        _, batch, _ = self.initial_intake()
        state = json.loads(self.fx.state.read_text(encoding="utf-8"))
        next(iter(state["events"].values()))["permalink"] = "tampered-permalink"
        self.fx.state.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ProcessingStateError, "identity binding"):
            load_processing_state(self.fx.state, batch["source_store"])

    def test_retry_rejects_state_metadata_conflicting_with_batch(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        self.fx.intake(batch_path, batch)
        state = json.loads(self.fx.state.read_text(encoding="utf-8"))
        event = next(iter(state["events"].values()))
        event["batch_id"] = "phase7-batch:" + "4" * 64
        event["record_sha256"] = _state_record_sha256(event)
        self.fx.state.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ProcessingStateError, "conflicts with batch evidence"):
            self.fx.intake(batch_path, batch)

    def test_replanning_applied_event_preserves_applied_state(self) -> None:
        plan, intake_path = self.planned()
        self.fx.apply(plan, self.fx.authorization(plan))
        proposal = self.fx.proposal(intake_path)
        repeated = self.fx.plan(intake_path, proposal, "2026-08-23T00:10:00+00:00")
        state = json.loads(self.fx.state.read_text(encoding="utf-8"))
        record = state["events"][plan["event_id"]]
        self.assertEqual(repeated["plan_id"], plan["plan_id"])
        self.assertEqual(record["status"], "applied")
        self.assertEqual(record["disposition_id"], plan["disposition_id"])

    def test_replanning_applied_event_after_source_change_preserves_applied_state(self) -> None:
        plan, intake_path = self.planned()
        self.fx.apply(plan, self.fx.authorization(plan))
        (self.fx.store / "alpha.md").write_text(
            note_text("phase7-alpha", "Changed after the completed disposition."), encoding="utf-8"
        )
        repeated = self.fx.plan(intake_path, self.fx.proposal(intake_path), TIME_3)
        record = json.loads(self.fx.state.read_text(encoding="utf-8"))["events"][plan["event_id"]]
        self.assertEqual(repeated["plan_id"], plan["plan_id"])
        self.assertEqual(record["status"], "applied")

    def test_concurrent_state_lock_fails_closed_without_advancement(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        with _exclusive_state_lock(self.fx.state):
            with self.assertRaisesRegex(ProcessingStateError, "locked"):
                self.fx.intake(batch_path, batch)
        self.assertFalse(self.fx.state.exists())

    def test_cross_process_state_lock_fails_closed_without_advancement(self) -> None:
        batch_path, batch = self.fx.emit(TIME_1)
        script = "\n".join(
            [
                "import sys",
                "from pathlib import Path",
                "sys.path.insert(0, sys.argv[1])",
                "from curator_delta_intake import _exclusive_state_lock",
                "with _exclusive_state_lock(Path(sys.argv[2])):",
                "    print('locked', flush=True)",
                "    sys.stdin.readline()",
            ]
        )
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", script, str(PHASE7_ROOT), str(self.fx.state)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            with self.assertRaisesRegex(ProcessingStateError, "locked"):
                self.fx.intake(batch_path, batch)
            self.assertFalse(self.fx.state.exists())
        finally:
            if process.stdin is not None:
                process.stdin.write("\n")
                process.stdin.flush()
            process.wait(timeout=10)
        stderr = process.stderr.read() if process.stderr is not None else ""
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()
        self.assertEqual(process.returncode, 0, stderr)

    def test_unsafe_attempt_reference_fails_closed(self) -> None:
        _, batch, _ = self.initial_intake()
        baseline = json.loads(self.fx.state.read_text(encoding="utf-8"))
        for reference in (
            "../outside.json",
            "/rooted.json",
            "\\rooted.json",
            "C:/rooted.json",
            "C:drive-relative.json",
            "attempts\\backslash.json",
            "attempts/./dot.json",
        ):
            with self.subTest(reference=reference):
                state = copy.deepcopy(baseline)
                next(iter(state["events"].values()))["attempt_references"] = [reference]
                self.fx.state.write_text(json.dumps(state), encoding="utf-8")
                with self.assertRaisesRegex(ProcessingStateError, "attempts are invalid"):
                    load_processing_state(self.fx.state, batch["source_store"])

    def test_stale_planned_event_replay_remains_coherent_and_requires_replan(self) -> None:
        batch_path, batch, intake_path = self.initial_intake()
        original = (self.fx.store / "alpha.md").read_text(encoding="utf-8")
        proposal_path = self.fx.proposal(intake_path)
        plan = self.fx.plan(intake_path, proposal_path)
        authorization = self.fx.authorization(plan)
        (self.fx.store / "alpha.md").write_text(
            note_text("phase7-alpha", "Changed before the first apply."), encoding="utf-8"
        )
        with self.assertRaisesRegex(PlanError, "plan is stale"):
            self.fx.apply(plan, authorization)
        (self.fx.store / "alpha.md").write_text(original, encoding="utf-8")
        replay = self.fx.intake(batch_path, batch, TIME_3)
        self.assertEqual(replay["results"][0]["status"], "stale_plan_ready_for_replan")
        state = load_processing_state(self.fx.state, batch["source_store"])
        record = state["events"][plan["event_id"]]
        self.assertEqual(record["status"], "stale")
        self.assertEqual(record["plan_id"], plan["plan_id"])
        replanned = self.fx.plan(intake_path, proposal_path, "2026-08-23T00:20:00+00:00")
        self.assertEqual(replanned["plan_id"], plan["plan_id"])
        final = load_processing_state(self.fx.state, batch["source_store"])
        self.assertEqual(final["events"][plan["event_id"]]["status"], "planned")

    def test_failed_event_is_blocked_from_replan_and_apply(self) -> None:
        plan, intake_path = self.planned()
        state = json.loads(self.fx.state.read_text(encoding="utf-8"))
        state["events"][plan["event_id"]]["status"] = "failed"
        self.fx.state.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "failed operational outcome"):
            self.fx.plan(intake_path, self.fx.proposal(intake_path))
        with self.assertRaisesRegex(PlanError, "failed operational outcome"):
            self.fx.apply(plan, self.fx.authorization(plan))

    def test_applied_retry_requires_disposition_evidence(self) -> None:
        plan, _ = self.planned()
        authorization = self.fx.authorization(plan)
        result = self.fx.apply(plan, authorization)
        (self.fx.artifacts / result["disposition_reference"]).unlink()
        with self.assertRaisesRegex(Phase7Error, "disposition evidence is missing"):
            self.fx.apply(plan, authorization)

    def test_applied_retry_detects_later_canonical_edit_without_overwrite(self) -> None:
        plan, _ = self.planned()
        authorization = self.fx.authorization(plan)
        self.fx.apply(plan, authorization)
        target = self.fx.canonical / "Knowledge/phase7.md"
        target.write_text("human later edit\n", encoding="utf-8")
        repeated = self.fx.apply(plan, authorization)
        self.assertEqual(repeated["status"], "already_applied")
        self.assertFalse(repeated["canonical_effect_current"])
        self.assertEqual(target.read_text(encoding="utf-8"), "human later edit\n")

    def test_indeterminate_batch_retry_remains_visible_and_does_not_regress(self) -> None:
        batch_path, batch, intake_path = self.initial_intake()
        proposal = self.fx.proposal(intake_path)
        plan = self.fx.plan(intake_path, proposal)
        state = json.loads(self.fx.state.read_text(encoding="utf-8"))
        state["events"][plan["event_id"]]["status"] = "indeterminate"
        self.fx.state.write_text(json.dumps(state), encoding="utf-8")
        result = self.fx.intake(batch_path, batch, TIME_3)
        after = json.loads(self.fx.state.read_text(encoding="utf-8"))["events"][plan["event_id"]]
        self.assertEqual(result["results"][0]["status"], "indeterminate")
        self.assertEqual(after["status"], "indeterminate")
        self.assertEqual(after["plan_id"], plan["plan_id"])

    def test_apply_rejects_plan_path_not_bound_to_state(self) -> None:
        plan, _ = self.planned()
        copied_plan = self.fx.artifacts / "plans" / "copied-plan.json"
        copied_plan.write_bytes(self.fx.plan_path(plan).read_bytes())
        authorization = self.fx.authorization(plan)
        with self.assertRaisesRegex(PlanError, "does not contain this exact plan"):
            apply_plan(
                plan_path=copied_plan,
                authorization_path=authorization,
                source_root=self.fx.store,
                canonical_root=self.fx.canonical,
                state_path=self.fx.state,
                artifact_root=self.fx.artifacts,
                applied_at=TIME_3,
            )

    def test_versioned_schema_files_are_valid_json(self) -> None:
        schemas = PHASE7_ROOT / "schemas"
        for name in ("processing-state.schema.json", "intake.schema.json", "plan.schema.json", "authorization.schema.json"):
            with self.subTest(schema=name):
                value = json.loads((schemas / name).read_text(encoding="utf-8"))
                self.assertEqual(value["$schema"], "https://json-schema.org/draft/2020-12/schema")


def file_hash(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main(verbosity=2)
