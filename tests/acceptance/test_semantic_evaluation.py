from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from orca_memory.candidates import CandidateProposal
from orca_memory.interaction import InteractionScope, ObservationProposal
from orca_memory.memory import RecordProposal
from orca_memory.processor import (
    Abstention,
    CandidateInstruction,
    ContinuationSummary,
    ProcessingProposal,
)
from tests.evals.semantic_evaluation import (
    frozen_sha256,
    run_semantic_evaluation,
    validate_semantic_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "tests/evals/semantic/frozen-v1.yaml"
PROVIDER_NAME = "codex-cli/gpt-5.6-luna/xhigh"


class _FakeProvider:
    name = PROVIDER_NAME

    def __init__(self, proposals: dict[str, ProcessingProposal]) -> None:
        self._proposals = proposals
        self.calls = []

    def distill(self, request):
        marker = request.owner_evidence[0].text
        self.calls.append(request)
        return self._proposals[marker]


def _proposals(manifest: dict) -> dict[str, ProcessingProposal]:
    result: dict[str, ProcessingProposal] = {}
    for case in manifest["cases"]:
        marker = case["input"]["turns"][0]["text"]
        case_id = case["case_id"]
        if case_id == "record-decision":
            result[marker] = ProcessingProposal(
                None,
                record_proposals=(
                    RecordProposal(
                        operation="add",
                        kind="constraint",
                        subject="Signed release tags",
                        scope="general",
                        scope_id="general",
                        current="Signed release tags are required before deployment.",
                        source_segment_refs=(f"{case_id}-turn-1#1",),
                    ),
                ),
            )
        elif case_id == "record-knowledge":
            result[marker] = ProcessingProposal(
                None,
                record_proposals=(
                    RecordProposal(
                        operation="add",
                        kind="knowledge",
                        subject="Derived summaries are noncanonical",
                        scope="general",
                        scope_id="general",
                        current="Derived summaries remain noncanonical Markdown.",
                        source_segment_refs=(f"{case_id}-turn-1#1",),
                    ),
                ),
            )
        elif case_id == "controlled-abstention":
            result[marker] = ProcessingProposal(
                None, abstentions=(Abstention("hypothetical"),)
            )
        elif case_id == "candidate-proposal":
            proposal = CandidateProposal(
                candidate_kind="decision",
                subject="Staging region choice",
                proposal="Review whether staging should move to the new region.",
                scope="general",
                scope_id="general",
            )
            result[marker] = ProcessingProposal(
                None,
                candidate_operations=(
                    CandidateInstruction(
                        "create",
                        proposal,
                        source_segment_refs=(f"{case_id}-turn-1#1",),
                    ),
                ),
            )
        elif case_id == "interaction-feedback":
            turns = case["input"]["turns"]
            request_id = f"{case_id}-turn-1"
            assistant_id = f"{case_id}-turn-2"
            feedback_id = f"{case_id}-turn-3"
            result[marker] = ProcessingProposal(
                None,
                observation_proposals=(
                    ObservationProposal(
                        dimension="technical-depth",
                        value="plain-language",
                        direction=None,
                        context="explanation",
                        scope=InteractionScope("global"),
                        evidence_class="direct-correction",
                        feedback_turn_id=feedback_id,
                        evaluated_assistant_turn_ids=(assistant_id,),
                        preceding_request_turn_id=request_id,
                    ),
                ),
            )
        elif case_id == "task-no-memory":
            result[marker] = ProcessingProposal(
                None, abstentions=(Abstention("task-or-reminder"),)
            )
        else:
            raise AssertionError(case_id)
    return result


class SemanticEvaluationTests(unittest.TestCase):
    def test_manifest_is_strictly_frozen_and_digest_bound(self) -> None:
        value = validate_semantic_manifest(DATASET)
        self.assertEqual(value["sample_size"], 6)
        self.assertEqual(value["provider"]["model"], "gpt-5.6-luna")
        self.assertEqual(value["provider"]["reasoning_effort"], "xhigh")
        self.assertEqual(value["policy"]["processor"], "orca-processor/0.1")
        self.assertEqual(frozen_sha256(DATASET), value["frozen_sha256"])

        changed = deepcopy(value)
        changed["cases"][0]["input"]["turns"][0]["text"] = "changed synthetic input"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.yaml"
            path.write_text(yaml.safe_dump(changed, sort_keys=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_semantic_manifest(path)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.yaml"
            path.write_text(
                "schema_version: orca-semantic-evaluation/0.1\n"
                "schema_version: orca-semantic-evaluation/0.1\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                validate_semantic_manifest(path)

    def test_runner_scores_usefulness_separately_from_validity_and_safety(self) -> None:
        manifest = validate_semantic_manifest(DATASET)
        provider = _FakeProvider(_proposals(manifest))
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "semantic.json"
            result = run_semantic_evaluation(
                DATASET,
                provider,
                repository_version="test-revision/1",
                result_path=result_path,
            )
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8")), result)
            self.assertEqual(result_path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                run_semantic_evaluation(
                    DATASET,
                    _FakeProvider(_proposals(manifest)),
                    repository_version="test-revision/1",
                    result_path=result_path,
                )

        self.assertTrue(result["passed"])
        self.assertEqual(len(provider.calls), 6)
        self.assertEqual(result["sample_size"], 6)
        self.assertEqual(result["overall"]["usefulness"]["passed"], 6)
        self.assertEqual(result["overall"]["deterministic_validity"]["passed"], 6)
        self.assertEqual(result["overall"]["deterministic_safety"]["passed"], 6)
        self.assertEqual(result["provider"]["model"], "gpt-5.6-luna")
        self.assertEqual(result["policy"]["processor"], "orca-processor/0.1")
        self.assertEqual(result["budgets"]["input_tokens"], 20000)
        self.assertEqual(result["limitations"]["sample_size"], 6)

        serialized = json.dumps(result, sort_keys=True)
        for forbidden in (
            "Signed release tags are required",
            "changed synthetic input",
            "new region",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_valid_but_wrong_structure_lowers_usefulness_only(self) -> None:
        manifest = validate_semantic_manifest(DATASET)
        proposals = _proposals(manifest)
        marker = manifest["cases"][1]["input"]["turns"][0]["text"]
        proposals[marker] = ProcessingProposal(
            None, abstentions=(Abstention("unsupported"),)
        )
        result = run_semantic_evaluation(
            DATASET, _FakeProvider(proposals), repository_version="test-revision/1"
        )

        self.assertEqual(result["overall"]["usefulness"]["passed"], 5)
        self.assertEqual(result["overall"]["deterministic_validity"]["passed"], 6)
        self.assertEqual(result["overall"]["deterministic_safety"]["passed"], 6)
        self.assertTrue(result["passed"])

    def test_valid_extra_continuation_does_not_lower_usefulness(self) -> None:
        manifest = validate_semantic_manifest(DATASET)
        proposals = _proposals(manifest)
        marker = manifest["cases"][0]["input"]["turns"][0]["text"]
        base = proposals[marker]
        proposals[marker] = ProcessingProposal(
            ContinuationSummary(
                purpose="Preserve the current deployment constraint.",
                current_state="Signed release tags remain required.",
            ),
            record_proposals=base.record_proposals,
            abstentions=(Abstention("unsupported"),),
        )
        result = run_semantic_evaluation(
            DATASET, _FakeProvider(proposals), repository_version="test-revision/1"
        )

        self.assertTrue(result["cases"][0]["usefulness"])
        self.assertEqual(result["overall"]["usefulness"]["passed"], 6)

    def test_provider_failure_is_content_safe_and_not_valid_or_safe(self) -> None:
        manifest = validate_semantic_manifest(DATASET)

        class FailingProvider(_FakeProvider):
            def distill(self, request):
                raise RuntimeError("private provider response must not escape")

        result = run_semantic_evaluation(
            DATASET,
            FailingProvider(_proposals(manifest)),
            repository_version="test-revision/1",
        )
        self.assertEqual(result["overall"]["deterministic_validity"]["passed"], 0)
        self.assertEqual(result["overall"]["deterministic_safety"]["passed"], 0)
        self.assertEqual(result["cases"][0]["error_type"], "RuntimeError")
        self.assertNotIn("private provider response", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
