from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def configured_vault_path() -> Path:
    environment_path = os.environ.get("ORCA_VAULT_PATH")
    if environment_path:
        return Path(environment_path)

    host_config = PROJECT_ROOT / "config" / "host.yaml"
    for line in host_config.read_text(encoding="utf-8").splitlines():
        if line.startswith("vault_path:"):
            return Path(line.split(":", 1)[1].strip())
    raise RuntimeError(f"vault_path is missing from {host_config}")


ORCA_VAULT = configured_vault_path()
TEST_ROOT = Path(__file__).resolve().parent
FIXTURE_ROOT = TEST_ROOT / "fixtures"
FIXTURE_VAULT = FIXTURE_ROOT / "vault"
SCENARIOS = json.loads((FIXTURE_ROOT / "scenarios.json").read_text(encoding="utf-8"))
SKILLS = {
    name: ORCA_VAULT / ".agents" / "skills" / name / "SKILL.md"
    for name in (
        "orca-capture",
        "orca-curator",
        "orca-source-ingestion",
        "orca-recall",
    )
}


def skill_text(name: str) -> str:
    return SKILLS[name].read_text(encoding="utf-8")


def fixture_text(relative_path: str) -> str:
    return (FIXTURE_VAULT / relative_path).read_text(encoding="utf-8")


class Phase4SkillContractTests(unittest.TestCase):
    def test_00_all_four_skill_definitions_exist_and_are_discoverable(self) -> None:
        for name, path in SKILLS.items():
            with self.subTest(skill=name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"))
                self.assertIn(f"name: {name}\n", text)
                self.assertIn("description:", text)

    def test_C1_explicit_project_fact(self) -> None:
        result = SCENARIOS["capture"]["C1"]["result"]
        self.assertEqual(result["authority"], "candidate")
        self.assertEqual(result["orca_state"], "new")
        self.assertEqual(result["intent"], "explicit")
        self.assertEqual(result["applicability"], {"scope": "project-specific", "project": "Example"})
        self.assertTrue(result["sources"][0]["resource"])

    def test_C2_explicit_preference_actor_attribution(self) -> None:
        result = SCENARIOS["capture"]["C2"]["result"]
        self.assertEqual(result["attribution"]["holder"], "Owner")
        self.assertEqual(result["attribution"]["speaker"], "Owner")
        self.assertEqual(result["sources"][0]["author"], "human:owner")
        self.assertEqual(result["authority"], "candidate")

    def test_C3_temporary_project_context_keeps_independent_dimensions(self) -> None:
        result = SCENARIOS["capture"]["C3"]["result"]
        self.assertEqual(result["applicability"]["scope"], "project-specific")
        self.assertEqual(result["applicability"]["project"], "Example")
        self.assertEqual(result["retention"]["class"], "temporary")
        self.assertTrue(result["retention"].get("valid_until") or result["retention"].get("valid_while"))

    def test_C4_ambiguous_capture_preserves_uncertainty_without_invention(self) -> None:
        result = SCENARIOS["capture"]["C4"]["result"]
        self.assertEqual(result["intent"], "explicit")
        self.assertIsNone(result["candidate_type"])
        self.assertIsNone(result["applicability"])
        self.assertIn("meaning", result["uncertainty"])
        self.assertEqual(result["authority"], "candidate")

    def test_K1_distinct_candidate_plans_promotion(self) -> None:
        case = SCENARIOS["curator"]["K1"]
        self.assertEqual(case["comparison"], "new distinct knowledge")
        self.assertEqual(case["disposition"], "promoted")
        self.assertTrue(case["canonical_target"])
        self.assertTrue(case["source_preserved"])

    def test_K2_exact_duplicate_is_consumed_without_canonical_mutation(self) -> None:
        case = SCENARIOS["curator"]["K2"]
        self.assertEqual(case["comparison"], "exact duplicate")
        self.assertEqual(case["disposition"], "consumed")
        self.assertFalse(case["canonical_changed"])
        self.assertFalse(case["routine_log_written"])

    def test_K3_semantic_duplicate_remains_governed(self) -> None:
        case = SCENARIOS["curator"]["K3"]
        self.assertEqual(case["comparison"], "semantic duplicate")
        self.assertEqual(case["semantic_judgment"], "governed")
        self.assertIn(case["disposition"], {"consumed", "merged"})

    def test_K4_correction_preserves_old_and_new_evidence(self) -> None:
        case = SCENARIOS["curator"]["K4"]
        self.assertEqual(case["comparison"], "correction")
        self.assertTrue(case["old_evidence"])
        self.assertTrue(case["new_evidence"])
        self.assertEqual(case["relation"]["type"], "revises")
        self.assertTrue(case["history_preserved"])

    def test_K5_supersession_preserves_history_and_marks_current(self) -> None:
        case = SCENARIOS["curator"]["K5"]
        self.assertEqual(case["comparison"], "supersession")
        self.assertEqual(case["old_status"], "deprecated")
        self.assertEqual(case["relation"]["type"], "supersedes")
        self.assertTrue(case["current_target"])
        self.assertTrue(case["history_preserved"])

    def test_K6_rejection_keeps_source_and_excludes_authoritative_recall(self) -> None:
        case = SCENARIOS["curator"]["K6"]
        self.assertEqual(case["disposition"], "rejected")
        self.assertTrue(case["reason"])
        self.assertTrue(case["source_preserved"])
        self.assertFalse(case["authoritative_recall"])

    def test_K7_human_correction_is_strong_traceable_evidence(self) -> None:
        case = SCENARIOS["curator"]["K7"]
        correction = case["human_correction"]
        self.assertTrue(correction["explicit"])
        self.assertEqual(correction["actor"], "human:owner")
        self.assertEqual(correction["evidence_weight"], "strong")
        self.assertTrue(case["old_evidence"])
        self.assertTrue(case["current_interpretation"])
        self.assertIn(case["relation"]["type"], {"revises", "supersedes"})

    def test_K8_raw_source_path_does_not_require_cairn(self) -> None:
        case = SCENARIOS["curator"]["K8"]
        self.assertEqual(case["input_kind"], "raw-source-candidate")
        self.assertFalse(case["cairn_required"])
        self.assertTrue((FIXTURE_VAULT / case["source"]).is_file())

    def test_S1_original_source_is_preserved(self) -> None:
        case = SCENARIOS["source_ingestion"]["S1"]
        self.assertTrue(case["original_preserved"])
        self.assertTrue((FIXTURE_VAULT / case["original"]).is_file())

    def test_S2_derived_material_links_to_original_source(self) -> None:
        case = SCENARIOS["source_ingestion"]["S2"]
        derived = fixture_text(case["derived_candidate"])
        self.assertIn(case["derived_from"], derived)

    def test_S3_source_candidate_hands_off_to_curator_without_cairn(self) -> None:
        case = SCENARIOS["source_ingestion"]["S3"]
        self.assertFalse(case["cairn_required"])
        self.assertTrue((FIXTURE_VAULT / case["curator_handoff"]).is_file())

    def test_S4_ingestion_does_not_grant_canonical_authority(self) -> None:
        case = SCENARIOS["source_ingestion"]["S4"]
        self.assertEqual(case["ingested_authority"], "candidate")
        self.assertEqual(case["orca_state_before_curator"], "new")
        self.assertFalse(case["automatic_canonical_write"])

    def test_R1_canonical_result_is_labelled_current(self) -> None:
        case = SCENARIOS["recall"]["R1"]
        self.assertEqual(case["authority"], "CANONICAL")
        self.assertTrue(case["current"])
        self.assertTrue((FIXTURE_VAULT / case["path"]).is_file())

    def test_R2_cairn_or_explicit_candidate_is_not_canonical(self) -> None:
        case = SCENARIOS["recall"]["R2"]
        self.assertEqual(case["authority"], "CANDIDATE")
        self.assertEqual(case["orca_state"], "new")
        self.assertFalse(case["canonical"])

    def test_R3_canonical_candidate_conflict_preserves_authority(self) -> None:
        case = SCENARIOS["recall"]["R3"]
        self.assertEqual(case["canonical_authority"], "CANONICAL")
        self.assertEqual(case["candidate_authority"], "CANDIDATE")
        self.assertTrue(case["canonical_preferred"])
        self.assertTrue(case["conflict_surfaced"])
        self.assertTrue(case["curator_review_recommended"])

    def test_R4_current_is_preferred_and_history_is_labelled(self) -> None:
        case = SCENARIOS["recall"]["R4"]
        self.assertTrue((FIXTURE_VAULT / case["current"]).is_file())
        self.assertTrue((FIXTURE_VAULT / case["historical"]).is_file())
        self.assertEqual(case["historical_authority"], "HISTORICAL / SUPERSEDED")
        self.assertTrue(case["current_preferred"])

    def test_R5_recall_exposes_source_provenance(self) -> None:
        case = SCENARIOS["recall"]["R5"]
        self.assertTrue(case["provenance_visible"])
        self.assertIn(case["source"], fixture_text(case["result"]))

    def test_replayability_chain_is_reconstructable(self) -> None:
        chain = SCENARIOS["replayability"]
        for key in ("source", "candidate", "disposition", "canonical_target", "prior_canonical"):
            self.assertTrue((FIXTURE_VAULT / chain[key]).is_file(), key)

        candidate = fixture_text(chain["candidate"])
        disposition = fixture_text(chain["disposition"])
        current = fixture_text(chain["canonical_target"])
        historical = fixture_text(chain["prior_canonical"])
        self.assertIn(chain["source"], candidate)
        self.assertIn(chain["candidate"], disposition)
        self.assertIn(chain["canonical_target"], disposition)
        self.assertIn(f"type: {chain['relation']}", disposition)
        self.assertIn(chain["human_correction_source"], disposition)
        self.assertIn(chain["human_correction_source"], current)
        self.assertIn("status: deprecated", historical)

    def test_skills_are_agent_independent(self) -> None:
        combined = "\n".join(skill_text(name).lower() for name in SKILLS)
        for actor in ("codex", "hermes"):
            self.assertNotIn(actor, combined)
        self.assertIn("agent-independent", skill_text("orca-curator").lower())

    def test_phase_boundaries_are_explicit(self) -> None:
        for name in SKILLS:
            with self.subTest(skill=name):
                text = skill_text(name).lower()
                self.assertIn("phase 5", text)
                self.assertIn("phase 6", text)
                self.assertIn("not implement", text)
                self.assertIn("production", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
