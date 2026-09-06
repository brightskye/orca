from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from tests.evals.evaluation import (
    COMMON_CATEGORY_COUNTS,
    COMMON_RUBRIC,
    EDGE_ACCEPTED_OUTCOMES,
    frozen_sha256,
    run_common_use_evaluation,
    run_edge_safety_evaluation,
    score_quality_gate,
    validate_common_use_candidate,
    validate_edge_safety_candidate,
    write_evaluation_result,
)


ROOT = Path(__file__).resolve().parents[2]
VERSIONS = {
    "repository_version": "test-revision-1",
    "provider_version": "deterministic-unittest/1",
    "model_version": "none",
    "policy_version": "phase1-policy/1",
}


class ReadinessBoundaryTests(unittest.TestCase):
    def test_common_use_is_exactly_100_selector_backed_cases_and_frozen(self) -> None:
        path = ROOT / "tests/evals/common-use/candidate-v1.yaml"
        value = validate_common_use_candidate(path)
        cases = [
            case
            for category in value["categories"].values()
            for case in category["cases"]
        ]
        self.assertEqual(len(cases), 100)
        self.assertEqual(len({case["case_id"] for case in cases}), 100)
        self.assertEqual(len({case["selector"] for case in cases}), 100)
        self.assertEqual(value["rubric"], COMMON_RUBRIC)
        self.assertEqual(value["approval"]["owner"], "project-owner")
        self.assertEqual(value["approval"]["approved_at"], "2026-08-30")
        self.assertEqual(frozen_sha256(path), value["approval"]["frozen_sha256"])

    def test_edge_set_is_exactly_12_selector_backed_cases_and_frozen(self) -> None:
        path = ROOT / "tests/evals/edge-safety/candidate-v1.yaml"
        value = validate_edge_safety_candidate(path)
        self.assertEqual(len(value["cases"]), 12)
        self.assertEqual(
            [case["case_id"] for case in value["cases"]],
            [f"EDGE-{index:03d}" for index in range(1, 13)],
        )
        self.assertEqual(len({case["selector"] for case in value["cases"]}), 12)
        self.assertEqual(value["accepted_outcomes"], list(EDGE_ACCEPTED_OUTCOMES))
        self.assertEqual(value["approval"]["owner"], "project-owner")
        self.assertEqual(value["approval"]["approved_at"], "2026-08-30")
        self.assertEqual(frozen_sha256(path), value["approval"]["frozen_sha256"])

    def test_frozen_digest_omits_only_its_own_field(self) -> None:
        source = ROOT / "tests/evals/common-use/candidate-v1.yaml"
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
        changed_digest = deepcopy(value)
        changed_digest["approval"]["frozen_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed-digest.yaml"
            path.write_text(yaml.safe_dump(changed_digest, sort_keys=False), encoding="utf-8")
            self.assertEqual(frozen_sha256(source), frozen_sha256(path))
            with self.assertRaises(ValueError):
                validate_common_use_candidate(path)

    def test_manifest_mutation_and_schema_drift_fail_closed(self) -> None:
        source = ROOT / "tests/evals/edge-safety/candidate-v1.yaml"
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
        value["cases"][0]["scenario"] = "changed-scenario"
        value["unexpected"] = "not-accepted"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated.yaml"
            path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_edge_safety_candidate(path)

        common_source = ROOT / "tests/evals/common-use/candidate-v1.yaml"
        common = yaml.safe_load(common_source.read_text(encoding="utf-8"))
        common["rubric"]["overall_minimum"] = 0.90
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated-common.yaml"
            path.write_text(yaml.safe_dump(common, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_common_use_candidate(path)

    def test_quality_gate_requires_all_exact_categories_and_thresholds(self) -> None:
        passing = {name: (count, count) for name, count in COMMON_CATEGORY_COUNTS.items()}
        self.assertTrue(score_quality_gate(passing, critical_failures=0).passed)
        weak = dict(passing)
        weak["interaction-behavior"] = (8, 10)
        self.assertFalse(score_quality_gate(weak, critical_failures=0).passed)
        with self.assertRaises(ValueError):
            score_quality_gate({"a": (95, 100)}, critical_failures=0)
        self.assertFalse(score_quality_gate(passing, critical_failures=1).passed)

    def test_frozen_sets_run_separately_and_return_content_safe_results(self) -> None:
        common = run_common_use_evaluation(
            ROOT / "tests/evals/common-use/candidate-v1.yaml", **VERSIONS
        )
        edge = run_edge_safety_evaluation(
            ROOT / "tests/evals/edge-safety/candidate-v1.yaml", **VERSIONS
        )
        self.assertTrue(common["passed"])
        self.assertEqual(common["overall"]["total"], 100)
        self.assertEqual(common["overall"]["passed"], 100)
        self.assertEqual(common["critical_failures"], 0)
        self.assertEqual(common["versions"]["provider"], VERSIONS["provider_version"])
        self.assertEqual(common["manifest_sha256"], "0a7637288660dacc6c07072c9a838da86e8982c6afae4b13e0ae8ed20b656d1a")
        self.assertTrue(edge["passed"])
        self.assertEqual(edge["overall"]["total"], 12)
        self.assertEqual(edge["overall"]["passed"], 12)
        self.assertEqual(edge["critical_failures"], 0)
        self.assertEqual(edge["versions"]["policy"], VERSIONS["policy_version"])
        self.assertEqual(edge["manifest_sha256"], "ec5508954461045d5f5ee501eb48da94789313f808c2ea076cbe24c848adcaa2")
        self.assertEqual(set(common["categories"]), set(COMMON_CATEGORY_COUNTS))
        self.assertEqual(set(edge["categories"]), {"edge-safety"})
        serialized = json.dumps({"common": common, "edge": edge}, sort_keys=True)
        for forbidden in ("hunter2", "private stdout", "private error", "Traceback"):
            self.assertNotIn(forbidden, serialized)

        with tempfile.TemporaryDirectory() as directory:
            common_path = write_evaluation_result(Path(directory) / "common.json", common)
            edge_path = write_evaluation_result(Path(directory) / "edge.json", edge)
            self.assertEqual(json.loads(common_path.read_text(encoding="utf-8")), common)
            self.assertEqual(json.loads(edge_path.read_text(encoding="utf-8")), edge)
            self.assertEqual(common_path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_evaluation_result(common_path, common)

        unsafe = dict(common)
        unsafe["raw_output"] = "private fixture text"
        with tempfile.TemporaryDirectory() as directory:
            unsafe_path = Path(directory) / "unsafe.json"
            with self.assertRaises(ValueError):
                write_evaluation_result(unsafe_path, unsafe)
            self.assertFalse(unsafe_path.exists())

    def test_no_public_listener_or_canonical_apply_surface_is_present(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "src/orca_memory").glob("*.py"))
        )
        for forbidden in (
            "FastAPI(",
            "Flask(",
            "HTTPServer(",
            "socketserver",
            ".listen(",
            "canonical_apply",
        ):
            self.assertNotIn(forbidden, source)
        self.assertFalse((ROOT / "src/orca_memory/server.py").exists())


if __name__ == "__main__":
    unittest.main()
