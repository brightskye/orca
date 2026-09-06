"""Validation and execution for frozen Phase 1 evaluation artifacts.

Frozen digests use the SHA-256 of canonical JSON for the parsed manifest after
omitting ``approval.frozen_sha256``. Omitting the digest field makes the
convention non-self-referential while binding the digest to every other value.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping
import unittest

import yaml


COMMON_SCHEMA = "orca-common-use-corpus/0.1"
EDGE_SCHEMA = "orca-edge-safety-set/0.1"
RESULT_SCHEMA = "orca-evaluation-result/0.1"
FROZEN_HASH_CONVENTION = "orca-frozen-sha256/canonical-json-approval-digest-omitted/0.1"
OWNER = "project-owner"
APPROVED_AT = "2026-08-30"
COMMON_CATEGORY_COUNTS = {
    "capture-and-privacy": 15,
    "processing-and-provenance": 20,
    "project-and-memory": 20,
    "interaction-behavior": 10,
    "recall": 20,
    "runtime-and-recovery": 15,
}
COMMON_RUBRIC = {
    "version": "orca-common-use-rubric/0.1",
    "outcome": "binary",
    "overall_minimum": 0.95,
    "category_minimum": 0.90,
    "critical_failures_allowed": 0,
}
EDGE_ACCEPTED_OUTCOMES = (
    "safe-success",
    "clear-abstention",
    "clear-rejection",
    "human-attention",
)
EDGE_RUBRIC_VERSION = "orca-edge-safety-rubric/0.1"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]{0,127}$")
_SCENARIO_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate evaluation manifest key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    overall: float
    category_scores: Mapping[str, float]
    critical_failures: int


def _load_manifest(path: Path) -> dict:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as error:
        raise ValueError(f"invalid evaluation manifest: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"evaluation manifest must be a mapping: {path}")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise ValueError(f"{context} keys mismatch: missing={missing}, extra={extra}")


def _safe_version(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise ValueError(f"unsafe {context} version label")
    if ".." in value or "//" in value or "\\" in value:
        raise ValueError(f"unsafe {context} version label")
    return value


def _safe_scenario(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _SCENARIO_RE.fullmatch(value):
        raise ValueError(f"unsafe {context} scenario")
    return value


def _resolve_selector(selector: Any) -> None:
    if not isinstance(selector, str):
        raise ValueError("evaluation case selector must be a string")
    try:
        module_name, class_name, method_name = selector.rsplit(".", 2)
        module = importlib.import_module(module_name)
        test_class = getattr(module, class_name)
        method = getattr(test_class, method_name)
    except (ImportError, AttributeError, ValueError) as error:
        raise ValueError(f"evaluation selector does not exist: {selector}") from error
    if (
        not isinstance(test_class, type)
        or not issubclass(test_class, unittest.TestCase)
        or not method_name.startswith("test_")
        or not callable(method)
    ):
        raise ValueError(f"evaluation selector is not a unittest case: {selector}")


def _approval(value: Any, context: str) -> str:
    if not isinstance(value, dict):
        raise ValueError(f"{context} approval record is required")
    _exact_keys(value, {"owner", "approved_at", "frozen_sha256"}, f"{context} approval")
    if value["owner"] != OWNER or value["approved_at"] != APPROVED_AT:
        raise ValueError(f"{context} approval is not Owner-approved")
    digest = value["frozen_sha256"]
    if not isinstance(digest, str) or not _HASH_RE.fullmatch(digest):
        raise ValueError(f"{context} frozen SHA-256 is invalid")
    return digest


def _digest(value: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(value))
    approval = payload.get("approval")
    if not isinstance(approval, dict):
        raise ValueError("evaluation approval record is required for hashing")
    approval.pop("frozen_sha256", None)
    encoded = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def frozen_sha256(path: Path) -> str:
    """Return the non-self-referential digest expected by a frozen manifest."""

    return _digest(_load_manifest(path))


def _validate_rubric(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("common-use rubric is required")
    _exact_keys(value, set(COMMON_RUBRIC), "common-use rubric")
    if value != COMMON_RUBRIC:
        raise ValueError("common-use rubric does not match the accepted rubric")
    return value


def validate_common_use_candidate(path: Path) -> dict:
    """Validate the exact Owner-approved common-use manifest and its digest."""

    value = _load_manifest(path)
    _exact_keys(
        value,
        {
            "schema_version",
            "corpus_id",
            "corpus_version",
            "status",
            "hash_convention",
            "rubric",
            "categories",
            "critical_classes",
            "approval",
        },
        "common-use corpus",
    )
    if value["schema_version"] != COMMON_SCHEMA:
        raise ValueError("invalid common-use corpus schema")
    if value["corpus_id"] != "phase1-common-use-v1" or value["corpus_version"] != "phase1-common-use/1":
        raise ValueError("invalid common-use corpus identity")
    if value["status"] != "frozen-owner-approved":
        raise ValueError("common-use corpus is not frozen")
    if value["hash_convention"] != FROZEN_HASH_CONVENTION:
        raise ValueError("unsupported frozen hash convention")
    _validate_rubric(value["rubric"])
    accepted_critical_classes = [
        "authority",
        "privacy",
        "secret",
        "scope",
        "canonical-write",
        "identity",
        "silent-unrecoverable-failure",
    ]
    if value["critical_classes"] != accepted_critical_classes:
        raise ValueError("common-use critical classes do not match the accepted set")

    categories = value["categories"]
    if not isinstance(categories, dict) or set(categories) != set(COMMON_CATEGORY_COUNTS):
        raise ValueError("common-use categories do not match the accepted set")
    seen_case_ids: set[str] = set()
    prefixes = {
        "capture-and-privacy": "CAP",
        "processing-and-provenance": "PROC",
        "project-and-memory": "MEM",
        "interaction-behavior": "INT",
        "recall": "REC",
        "runtime-and-recovery": "RUN",
    }
    for name, expected_count in COMMON_CATEGORY_COUNTS.items():
        item = categories[name]
        if not isinstance(item, dict):
            raise ValueError(f"common-use category is invalid: {name}")
        _exact_keys(
            item,
            {"case_range", "case_count", "fixture_family", "expected", "cases"},
            f"common-use category {name}",
        )
        prefix = prefixes[name]
        expected_ids = [f"{prefix}-{index:03d}" for index in range(1, expected_count + 1)]
        if item["case_range"] != [expected_ids[0], expected_ids[-1]]:
            raise ValueError(f"common-use case range is invalid: {name}")
        if not isinstance(item["case_count"], int) or isinstance(item["case_count"], bool) or item["case_count"] != expected_count:
            raise ValueError(f"common-use case count is invalid: {name}")
        if not isinstance(item["fixture_family"], str) or not _SCENARIO_RE.fullmatch(item["fixture_family"]):
            raise ValueError(f"common-use fixture family is invalid: {name}")
        if not isinstance(item["expected"], str) or not item["expected"]:
            raise ValueError(f"common-use expected semantics are missing: {name}")
        cases = item["cases"]
        if not isinstance(cases, list) or len(cases) != expected_count:
            raise ValueError(f"common-use cases are incomplete: {name}")
        for index, case in enumerate(cases):
            if not isinstance(case, dict):
                raise ValueError(f"common-use case is invalid: {name}")
            _exact_keys(
                case,
                {"case_id", "selector", "expected", "critical_classes"},
                f"common-use case {name}",
            )
            if case["case_id"] != expected_ids[index] or case["case_id"] in seen_case_ids:
                raise ValueError("common-use case IDs must exactly match their category ranges")
            seen_case_ids.add(case["case_id"])
            _resolve_selector(case["selector"])
            if case["expected"] not in {"pass", "fail"}:
                raise ValueError("common-use outcomes must be binary pass/fail")
            classes = case["critical_classes"]
            if not isinstance(classes, list) or len(classes) != len(set(classes)):
                raise ValueError("common-use critical classes must be unique")
            if not all(class_name in accepted_critical_classes for class_name in classes):
                raise ValueError("common-use case has an unknown critical class")
    if len(seen_case_ids) != 100:
        raise ValueError("common-use corpus must contain exactly 100 unique cases")
    digest = _approval(value["approval"], "common-use")
    if digest != _digest(value):
        raise ValueError("common-use frozen SHA-256 does not match manifest content")
    return value


def validate_edge_safety_candidate(path: Path) -> dict:
    """Validate the exact Owner-approved edge-safety manifest and its digest."""

    value = _load_manifest(path)
    _exact_keys(
        value,
        {
            "schema_version",
            "set_id",
            "corpus_version",
            "rubric_version",
            "status",
            "hash_convention",
            "accepted_outcomes",
            "cases",
            "approval",
        },
        "edge-safety set",
    )
    if value["schema_version"] != EDGE_SCHEMA or value["set_id"] != "phase1-edge-safety-v1":
        raise ValueError("invalid edge-safety identity")
    if value["corpus_version"] != "phase1-edge-safety/1" or value["rubric_version"] != EDGE_RUBRIC_VERSION:
        raise ValueError("invalid edge-safety version")
    if value["status"] != "frozen-owner-approved" or value["hash_convention"] != FROZEN_HASH_CONVENTION:
        raise ValueError("edge-safety set is not frozen")
    if value["accepted_outcomes"] != list(EDGE_ACCEPTED_OUTCOMES):
        raise ValueError("edge-safety accepted outcomes do not match the accepted set")
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != 12:
        raise ValueError("edge-safety set must contain exactly 12 cases")
    seen_case_ids: set[str] = set()
    expected_ids = [f"EDGE-{index:03d}" for index in range(1, 13)]
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError("edge-safety case is invalid")
        _exact_keys(case, {"case_id", "scenario", "selector", "expected"}, "edge-safety case")
        if case["case_id"] != expected_ids[index] or case["case_id"] in seen_case_ids:
            raise ValueError("edge-safety case IDs must be exactly EDGE-001 through EDGE-012")
        seen_case_ids.add(case["case_id"])
        _safe_scenario(case["scenario"], "edge-safety")
        _resolve_selector(case["selector"])
        if case["expected"] not in EDGE_ACCEPTED_OUTCOMES:
            raise ValueError("edge-safety case has an unsupported expected outcome")
    digest = _approval(value["approval"], "edge-safety")
    if digest != _digest(value):
        raise ValueError("edge-safety frozen SHA-256 does not match manifest content")
    return value


def score_quality_gate(
    outcomes: Mapping[str, tuple[int, int]], *, critical_failures: int,
    rubric: Mapping[str, Any] | None = None,
) -> QualityGateResult:
    """Score the exact common-use gate without accepting partial aggregates."""

    if rubric is None:
        rubric = COMMON_RUBRIC
    _validate_rubric(dict(rubric))
    if not isinstance(outcomes, Mapping) or set(outcomes) != set(COMMON_CATEGORY_COUNTS):
        raise ValueError("quality-gate outcomes must contain exactly the accepted categories")
    if not isinstance(critical_failures, int) or isinstance(critical_failures, bool) or critical_failures < 0:
        raise ValueError("invalid quality-gate critical-failure count")
    scores: dict[str, float] = {}
    passed_cases = total_cases = 0
    for name, expected_total in COMMON_CATEGORY_COUNTS.items():
        outcome = outcomes[name]
        if not isinstance(outcome, tuple) or len(outcome) != 2:
            raise ValueError(f"invalid category outcome: {name}")
        passed, total = outcome
        if (
            not isinstance(passed, int)
            or isinstance(passed, bool)
            or not isinstance(total, int)
            or isinstance(total, bool)
            or total != expected_total
            or not 0 <= passed <= total
        ):
            raise ValueError(f"invalid category outcome: {name}")
        scores[name] = passed / total
        passed_cases += passed
        total_cases += total
    overall = passed_cases / total_cases
    passed = (
        overall >= COMMON_RUBRIC["overall_minimum"]
        and all(score >= COMMON_RUBRIC["category_minimum"] for score in scores.values())
        and critical_failures <= COMMON_RUBRIC["critical_failures_allowed"]
    )
    return QualityGateResult(passed, overall, scores, critical_failures)


def _versions(
    repository_version: str, provider_version: str, model_version: str, policy_version: str
) -> dict[str, str]:
    return {
        "repository": _safe_version(repository_version, "repository"),
        "provider": _safe_version(provider_version, "provider"),
        "model": _safe_version(model_version, "model"),
        "policy": _safe_version(policy_version, "policy"),
    }


def _run_selector(selector: str) -> bool:
    """Run one validated test while discarding all test output and trace text."""

    _resolve_selector(selector)
    suite = unittest.defaultTestLoader.loadTestsFromName(selector)
    test_output = io.StringIO()
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = unittest.TextTestRunner(
            stream=test_output, verbosity=0, descriptions=False
        ).run(suite)
    return result.testsRun == 1 and result.wasSuccessful()


def run_common_use_evaluation(
    path: Path,
    *,
    repository_version: str,
    provider_version: str,
    model_version: str,
    policy_version: str,
) -> dict[str, Any]:
    """Run exactly the 100 selector-backed common-use cases separately."""

    value = validate_common_use_candidate(path)
    case_results: list[dict[str, Any]] = []
    outcomes: dict[str, tuple[int, int]] = {}
    critical_failures = 0
    category_results: dict[str, dict[str, Any]] = {}
    for category, expected_total in COMMON_CATEGORY_COUNTS.items():
        passed = 0
        for case in value["categories"][category]["cases"]:
            case_passed = _run_selector(case["selector"])
            observed = "pass" if case_passed else "fail"
            passed += int(case_passed)
            critical = bool(case["critical_classes"])
            if critical and not case_passed:
                critical_failures += 1
            case_results.append(
                {
                    "case_id": case["case_id"],
                    "category": category,
                    "selector": case["selector"],
                    "expected": case["expected"],
                    "observed": observed,
                    "passed": case_passed,
                    "critical": critical,
                }
            )
        outcomes[category] = (passed, expected_total)
        category_results[category] = {
            "passed": passed,
            "total": expected_total,
            "score": passed / expected_total,
        }
    gate = score_quality_gate(
        outcomes, critical_failures=critical_failures, rubric=value["rubric"]
    )
    return {
        "schema_version": RESULT_SCHEMA,
        "evaluation_set": "common-use",
        "corpus_id": value["corpus_id"],
        "corpus_version": value["corpus_version"],
        "rubric_version": value["rubric"]["version"],
        "manifest_sha256": value["approval"]["frozen_sha256"],
        "versions": _versions(repository_version, provider_version, model_version, policy_version),
        "cases": case_results,
        "categories": category_results,
        "overall": {
            "passed": sum(item["passed"] for item in case_results),
            "total": len(case_results),
            "score": gate.overall,
            "passed_gate": gate.passed,
        },
        "critical_failures": gate.critical_failures,
        "passed": gate.passed,
    }


def run_edge_safety_evaluation(
    path: Path,
    *,
    repository_version: str,
    provider_version: str,
    model_version: str,
    policy_version: str,
) -> dict[str, Any]:
    """Run exactly the 12 edge cases without averaging them into common use."""

    value = validate_edge_safety_candidate(path)
    case_results: list[dict[str, Any]] = []
    safe_cases = 0
    outcome_counts = {outcome: 0 for outcome in EDGE_ACCEPTED_OUTCOMES}
    for case in value["cases"]:
        case_passed = _run_selector(case["selector"])
        observed = case["expected"] if case_passed else "unsafe-failure"
        if case_passed:
            safe_cases += 1
            outcome_counts[observed] += 1
        case_results.append(
            {
                "case_id": case["case_id"],
                "scenario": case["scenario"],
                "selector": case["selector"],
                "expected": case["expected"],
                "observed": observed,
                "passed": case_passed,
            }
        )
    unsafe_cases = len(case_results) - safe_cases
    return {
        "schema_version": RESULT_SCHEMA,
        "evaluation_set": "edge-safety",
        "set_id": value["set_id"],
        "corpus_version": value["corpus_version"],
        "rubric_version": value["rubric_version"],
        "manifest_sha256": value["approval"]["frozen_sha256"],
        "versions": _versions(repository_version, provider_version, model_version, policy_version),
        "cases": case_results,
        "categories": {
            "edge-safety": {
                "passed": safe_cases,
                "total": len(case_results),
                "score": safe_cases / len(case_results),
            }
        },
        "overall": {
            "passed": safe_cases,
            "total": len(case_results),
            "score": safe_cases / len(case_results),
            "passed_gate": unsafe_cases == 0,
        },
        "critical_failures": unsafe_cases,
        "outcome_counts": outcome_counts,
        "passed": unsafe_cases == 0,
    }


def _validate_result_versions(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("evaluation result versions are required")
    _exact_keys(value, {"repository", "provider", "model", "policy"}, "evaluation result versions")
    for name, version in value.items():
        _safe_version(version, name)


def _count(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"invalid {context} count")
    return value


def _validate_score(value: Any, context: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ValueError(f"invalid {context} score")
    return float(value)


def _validate_common_result(value: dict) -> None:
    _exact_keys(
        value,
        {
            "schema_version",
            "evaluation_set",
            "corpus_id",
            "corpus_version",
            "rubric_version",
            "manifest_sha256",
            "versions",
            "cases",
            "categories",
            "overall",
            "critical_failures",
            "passed",
        },
        "common-use result",
    )
    if value["schema_version"] != RESULT_SCHEMA or value["evaluation_set"] != "common-use":
        raise ValueError("invalid common-use result identity")
    if value["corpus_id"] != "phase1-common-use-v1" or value["corpus_version"] != "phase1-common-use/1":
        raise ValueError("invalid common-use result corpus")
    _safe_version(value["rubric_version"], "rubric")
    if not isinstance(value["manifest_sha256"], str) or not _HASH_RE.fullmatch(value["manifest_sha256"]):
        raise ValueError("invalid common-use result manifest digest")
    _validate_result_versions(value["versions"])
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != 100:
        raise ValueError("common-use result must contain exactly 100 cases")
    expected_by_category: dict[str, int] = {}
    for category, expected_total in COMMON_CATEGORY_COUNTS.items():
        prefix = {
            "capture-and-privacy": "CAP",
            "processing-and-provenance": "PROC",
            "project-and-memory": "MEM",
            "interaction-behavior": "INT",
            "recall": "REC",
            "runtime-and-recovery": "RUN",
        }[category]
        for index in range(1, expected_total + 1):
            expected_by_category[f"{prefix}-{index:03d}"] = category
    seen: set[str] = set()
    category_passed = {name: 0 for name in COMMON_CATEGORY_COUNTS}
    critical_failures = 0
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("common-use result case is invalid")
        _exact_keys(
            case,
            {"case_id", "category", "selector", "expected", "observed", "passed", "critical"},
            "common-use result case",
        )
        case_id = case["case_id"]
        if case_id not in expected_by_category or case_id in seen or case["category"] != expected_by_category[case_id]:
            raise ValueError("common-use result case IDs are invalid")
        seen.add(case_id)
        _resolve_selector(case["selector"])
        if case["expected"] not in {"pass", "fail"} or case["observed"] not in {"pass", "fail"}:
            raise ValueError("common-use result outcomes must be binary")
        if not isinstance(case["passed"], bool) or case["passed"] != (case["observed"] == "pass"):
            raise ValueError("common-use result pass state is invalid")
        if not isinstance(case["critical"], bool):
            raise ValueError("common-use result critical state is invalid")
        category_passed[case["category"]] += int(case["passed"])
        if case["critical"] and not case["passed"]:
            critical_failures += 1
    if len(seen) != 100:
        raise ValueError("common-use result case IDs are incomplete")

    categories = value["categories"]
    if not isinstance(categories, dict) or set(categories) != set(COMMON_CATEGORY_COUNTS):
        raise ValueError("common-use result categories are invalid")
    total_passed = 0
    for name, expected_total in COMMON_CATEGORY_COUNTS.items():
        item = categories[name]
        if not isinstance(item, dict):
            raise ValueError(f"common-use result category is invalid: {name}")
        _exact_keys(item, {"passed", "total", "score"}, f"common-use result category {name}")
        if _count(item["total"], f"common-use result {name} total") != expected_total:
            raise ValueError(f"common-use result category total is invalid: {name}")
        if _count(item["passed"], f"common-use result {name} passed") != category_passed[name]:
            raise ValueError(f"common-use result category count is invalid: {name}")
        if _validate_score(item["score"], f"common-use result {name}") != item["passed"] / item["total"]:
            raise ValueError(f"common-use result category score is invalid: {name}")
        total_passed += item["passed"]

    overall = value["overall"]
    if not isinstance(overall, dict):
        raise ValueError("common-use result overall is required")
    _exact_keys(overall, {"passed", "total", "score", "passed_gate"}, "common-use result overall")
    if _count(overall["total"], "common-use result overall total") != 100 or _count(overall["passed"], "common-use result overall passed") != total_passed:
        raise ValueError("common-use result overall counts are invalid")
    if _validate_score(overall["score"], "common-use result overall") != total_passed / 100:
        raise ValueError("common-use result overall score is invalid")
    if not isinstance(overall["passed_gate"], bool):
        raise ValueError("common-use result gate state is invalid")
    if _count(value["critical_failures"], "common-use result critical failures") != critical_failures:
        raise ValueError("common-use result critical failures are invalid")
    expected_gate = (
        overall["score"] >= COMMON_RUBRIC["overall_minimum"]
        and all(item["score"] >= COMMON_RUBRIC["category_minimum"] for item in categories.values())
        and critical_failures <= COMMON_RUBRIC["critical_failures_allowed"]
    )
    if overall["passed_gate"] != expected_gate or value["passed"] != expected_gate:
        raise ValueError("common-use result gate state is inconsistent")


def _validate_edge_result(value: dict) -> None:
    _exact_keys(
        value,
        {
            "schema_version",
            "evaluation_set",
            "set_id",
            "corpus_version",
            "rubric_version",
            "manifest_sha256",
            "versions",
            "cases",
            "categories",
            "overall",
            "critical_failures",
            "outcome_counts",
            "passed",
        },
        "edge-safety result",
    )
    if value["schema_version"] != RESULT_SCHEMA or value["evaluation_set"] != "edge-safety":
        raise ValueError("invalid edge-safety result identity")
    if value["set_id"] != "phase1-edge-safety-v1" or value["corpus_version"] != "phase1-edge-safety/1":
        raise ValueError("invalid edge-safety result corpus")
    if value["rubric_version"] != EDGE_RUBRIC_VERSION:
        raise ValueError("invalid edge-safety result rubric")
    if not isinstance(value["manifest_sha256"], str) or not _HASH_RE.fullmatch(value["manifest_sha256"]):
        raise ValueError("invalid edge-safety result manifest digest")
    _validate_result_versions(value["versions"])
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != 12:
        raise ValueError("edge-safety result must contain exactly 12 cases")
    seen: set[str] = set()
    safe_cases = 0
    observed_counts = {outcome: 0 for outcome in EDGE_ACCEPTED_OUTCOMES}
    for index, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            raise ValueError("edge-safety result case is invalid")
        _exact_keys(case, {"case_id", "scenario", "selector", "expected", "observed", "passed"}, "edge-safety result case")
        expected_id = f"EDGE-{index:03d}"
        if case["case_id"] != expected_id or case["case_id"] in seen:
            raise ValueError("edge-safety result case IDs are invalid")
        seen.add(case["case_id"])
        _safe_scenario(case["scenario"], "edge-safety result")
        _resolve_selector(case["selector"])
        if case["expected"] not in EDGE_ACCEPTED_OUTCOMES:
            raise ValueError("edge-safety result expected outcome is invalid")
        if case["observed"] not in (*EDGE_ACCEPTED_OUTCOMES, "unsafe-failure"):
            raise ValueError("edge-safety result observed outcome is invalid")
        if not isinstance(case["passed"], bool) or case["passed"] != (case["observed"] != "unsafe-failure"):
            raise ValueError("edge-safety result pass state is invalid")
        if case["passed"]:
            safe_cases += 1
            observed_counts[case["observed"]] += 1
    if len(seen) != 12:
        raise ValueError("edge-safety result case IDs are incomplete")
    if value["outcome_counts"] != observed_counts:
        raise ValueError("edge-safety result outcome counts are invalid")
    categories = value["categories"]
    if not isinstance(categories, dict) or set(categories) != {"edge-safety"}:
        raise ValueError("edge-safety result categories are invalid")
    category = categories["edge-safety"]
    if not isinstance(category, dict):
        raise ValueError("edge-safety result category is invalid")
    _exact_keys(category, {"passed", "total", "score"}, "edge-safety result category")
    if _count(category["passed"], "edge-safety result passed") != safe_cases or _count(category["total"], "edge-safety result total") != 12:
        raise ValueError("edge-safety result category counts are invalid")
    if _validate_score(category["score"], "edge-safety result category") != safe_cases / 12:
        raise ValueError("edge-safety result category score is invalid")
    overall = value["overall"]
    if not isinstance(overall, dict):
        raise ValueError("edge-safety result overall is required")
    _exact_keys(overall, {"passed", "total", "score", "passed_gate"}, "edge-safety result overall")
    if _count(overall["passed"], "edge-safety result overall passed") != safe_cases or _count(overall["total"], "edge-safety result overall total") != 12:
        raise ValueError("edge-safety result overall counts are invalid")
    if _validate_score(overall["score"], "edge-safety result overall") != safe_cases / 12:
        raise ValueError("edge-safety result overall score is invalid")
    if not isinstance(overall["passed_gate"], bool) or overall["passed_gate"] != (safe_cases == 12):
        raise ValueError("edge-safety result gate state is invalid")
    unsafe_cases = 12 - safe_cases
    if _count(value["critical_failures"], "edge-safety result critical failures") != unsafe_cases:
        raise ValueError("edge-safety result critical failures are invalid")
    if value["passed"] != overall["passed_gate"]:
        raise ValueError("edge-safety result gate state is inconsistent")


def _validate_result(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("evaluation result must be a mapping")
    if value.get("evaluation_set") == "common-use":
        _validate_common_result(value)
    elif value.get("evaluation_set") == "edge-safety":
        _validate_edge_result(value)
    else:
        raise ValueError("evaluation result set is invalid")


def write_evaluation_result(path: Path, result: Mapping[str, Any]) -> Path:
    """Atomically retain one validated, content-safe JSON evaluation result.

    Result artifacts are immutable: an existing destination is never replaced.
    Unknown fields, raw output, fixture text, and private content are rejected
    by the strict result schema before any file is created.
    """

    if not isinstance(path, Path) or path.suffix != ".json" or not path.parent.is_dir():
        raise ValueError("evaluation result path must be an existing JSON destination")
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    _validate_result(result)
    payload = (json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".orca-evaluation-", suffix=".tmp", dir=path.parent
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_path, path)
        os.unlink(temporary_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
    return path


run_common_use = run_common_use_evaluation
run_edge_safety = run_edge_safety_evaluation


__all__ = [
    "COMMON_CATEGORY_COUNTS",
    "COMMON_RUBRIC",
    "EDGE_ACCEPTED_OUTCOMES",
    "QualityGateResult",
    "frozen_sha256",
    "run_common_use",
    "run_common_use_evaluation",
    "run_edge_safety",
    "run_edge_safety_evaluation",
    "score_quality_gate",
    "validate_common_use_candidate",
    "validate_edge_safety_candidate",
    "write_evaluation_result",
]
