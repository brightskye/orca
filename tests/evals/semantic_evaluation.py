"""Small frozen semantic evaluation over the deterministic Processor seam.

The fixture is intentionally synthetic and its result is deliberately
content-free.  The semantic provider is exercised once per case, while the
Processor remains responsible for deterministic validation and safety.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

import yaml

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.interaction import ABSTENTION_REASONS, CONTEXTS, DIMENSIONS, EVIDENCE_CLASSES
from orca_memory.memory import MEMORY_KINDS
from orca_memory.privacy import REDACTION_POLICY, contains_secret
from orca_memory.processor import PROCESSOR_POLICY, Processor, SemanticProvider
from orca_memory.segmentation import BudgetConfig, SEGMENTATION_POLICY


SEMANTIC_MANIFEST_SCHEMA = "orca-semantic-evaluation/0.1"
SEMANTIC_RESULT_SCHEMA = "orca-semantic-evaluation-result/0.1"
DATASET_ID = "phase1-semantic-v1"
DATASET_VERSION = "phase1-semantic/1"
HASH_CONVENTION = "orca-semantic-sha256/canonical-json-digest-omitted/0.1"
PROVIDER_ADAPTER = "codex-cli"
PROVIDER_MODEL = "gpt-5.6-luna"
PROVIDER_REASONING = "xhigh"
PROVIDER_VERSION = "orca-semantic-provider/0.1"
SAMPLE_SIZE = 6
RUBRIC = {
    "version": "orca-semantic-rubric/0.1",
    "usefulness_minimum": 0.8,
    "deterministic_validity_required": True,
    "deterministic_safety_required": True,
}
LIMITATIONS = {
    "dataset": "synthetic-nonprivate",
    "sample_size": SAMPLE_SIZE,
    "semantic_quality": "not-deterministic-proof",
    "provider_sensitivity": "provider-model-policy-sensitive",
    "routine_use": "owner-review-required",
}
_BUDGETS = {
    "model_window_tokens": 32768,
    "input_tokens": 20000,
    "output_tokens": 4000,
    "new_evidence_tokens": 8000,
    "preceding_overlap_tokens": 1000,
    "continuation_summary_tokens": 2000,
    "project_summary_tokens": 2000,
    "related_records_tokens": 5000,
    "max_related_records": 5,
}
_POLICY = {
    "processor": PROCESSOR_POLICY,
    "redaction": REDACTION_POLICY,
    "segmentation": SEGMENTATION_POLICY,
}
_PROVIDER = {
    "adapter": PROVIDER_ADAPTER,
    "model": PROVIDER_MODEL,
    "reasoning_effort": PROVIDER_REASONING,
    "version": PROVIDER_VERSION,
}
_RECORD_OPERATIONS = {"add", "support", "update"}
_CANDIDATE_OPERATIONS = {"create", "support"}
_CANDIDATE_KINDS = {"fact", "decision", "preference", "lesson", "project-state"}
_ABSTENTION_REASONS = {
    "ambiguous",
    "hypothetical",
    "quoted",
    "private",
    "sensitive",
    "third-party",
    "task-or-reminder",
    "unsupported",
}
_CASE_ORDER = (
    "record-decision",
    "record-knowledge",
    "controlled-abstention",
    "candidate-proposal",
    "interaction-feedback",
    "task-no-memory",
)
_CASE_IDS = set(_CASE_ORDER)
_EXPECTED_OUTCOME_BY_EVIDENCE = {
    "durable-record": "durable-record",
    "controlled-abstention": "controlled-abstention",
    "candidate-proposal": "candidate",
    "interaction-feedback": "interaction-observation",
}
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+/-]{0,127}$")
_CASE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
_ERROR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate semantic evaluation key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True)
class _CaseResult:
    case_id: str
    evidence_class: str
    expected_outcome: str
    expected_usefulness: bool
    usefulness: bool
    deterministic_validity: bool
    deterministic_safety: bool
    expected_structure: dict[str, Any]
    observed_structure: dict[str, Any] | None
    error_type: str | None

    def value(self) -> dict[str, Any]:
        passed = self.usefulness and self.deterministic_validity and self.deterministic_safety
        return {
            "case_id": self.case_id,
            "evidence_class": self.evidence_class,
            "expected_outcome": self.expected_outcome,
            "expected_usefulness": self.expected_usefulness,
            "usefulness": self.usefulness,
            "deterministic_validity": self.deterministic_validity,
            "deterministic_safety": self.deterministic_safety,
            "expected_structure": self.expected_structure,
            "observed_structure": self.observed_structure,
            "error_type": self.error_type,
            "passed": passed,
        }


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid semantic evaluation manifest: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("semantic evaluation manifest must be a mapping")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise ValueError(f"{context} keys mismatch: missing={missing}, extra={extra}")


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError(f"{context} contains a control character")
    if contains_secret(value):
        raise ValueError(f"{context} contains a credential-like value")
    return value


def _version(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise ValueError(f"unsafe {context} version")
    if ".." in value or "//" in value or "\\" in value:
        raise ValueError(f"unsafe {context} version")
    return value


def _digest(value: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(value))
    digest = payload.pop("frozen_sha256", None)
    if digest is None:
        raise ValueError("semantic evaluation frozen_sha256 is required")
    encoded = json.dumps(
        payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def frozen_sha256(path: Path) -> str:
    """Return the non-self-referential digest of a semantic manifest."""

    return _digest(_load_manifest(path))


def _validate_budgets(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("semantic evaluation budgets are required")
    _exact_keys(value, set(_BUDGETS), "semantic evaluation budgets")
    for name, expected in _BUDGETS.items():
        actual = value[name]
        if not isinstance(actual, int) or isinstance(actual, bool) or actual != expected:
            raise ValueError(f"semantic evaluation budget is not frozen: {name}")
    if value["input_tokens"] + value["output_tokens"] > value["model_window_tokens"]:
        raise ValueError("semantic evaluation budgets exceed model window")
    return dict(value)


def _validate_structure(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} structure is required")
    _exact_keys(
        value,
        {
            "continuation",
            "records",
            "candidates",
            "observations",
            "observation_abstentions",
            "abstentions",
            "conflicts",
            "supersessions",
            "project_summary",
        },
        f"{context} structure",
    )
    for key in ("continuation", "project_summary"):
        if value[key] not in {"required", "allowed", "forbidden"}:
            raise ValueError(f"{context} {key} presence expectation is invalid")
    _validate_expected_items(
        value["records"],
        context,
        "record",
        lambda item: (
            isinstance(item, dict)
            and set(item) == {"operation", "kind"}
            and item["operation"] in _RECORD_OPERATIONS
            and item["kind"] in MEMORY_KINDS
        ),
    )
    _validate_expected_items(
        value["candidates"],
        context,
        "candidate",
        lambda item: (
            isinstance(item, dict)
            and set(item) == {"operation", "kind"}
            and item["operation"] in _CANDIDATE_OPERATIONS
            and item["kind"] in _CANDIDATE_KINDS
        ),
    )
    _validate_expected_items(
        value["observations"],
        context,
        "observation",
        lambda item: (
            isinstance(item, dict)
            and set(item) == {"dimension", "context", "evidence_class"}
            and item["dimension"] in DIMENSIONS
            and item["context"] in CONTEXTS
            and item["evidence_class"] in EVIDENCE_CLASSES
        ),
    )
    _validate_expected_items(
        value["observation_abstentions"],
        context,
        "observation abstention",
        lambda item: item in ABSTENTION_REASONS,
    )
    _validate_expected_items(
        value["abstentions"],
        context,
        "abstention",
        lambda item: item in _ABSTENTION_REASONS,
    )
    for key in ("conflicts", "supersessions"):
        bounds = value[key]
        if not isinstance(bounds, dict) or set(bounds) != {"minimum", "maximum"}:
            raise ValueError(f"{context} {key} bounds are invalid")
        if any(
            not isinstance(bounds[name], int)
            or isinstance(bounds[name], bool)
            or bounds[name] < 0
            for name in ("minimum", "maximum")
        ) or bounds["minimum"] > bounds["maximum"]:
            raise ValueError(f"{context} {key} bounds are invalid")
    return deepcopy(value)


def _validate_expected_items(
    value: Any,
    context: str,
    item_name: str,
    validator: Any,
) -> None:
    if not isinstance(value, dict) or set(value) != {"required", "forbidden"}:
        raise ValueError(f"{context} {item_name} expectations are invalid")
    if not isinstance(value["required"], list) or not isinstance(value["forbidden"], bool):
        raise ValueError(f"{context} {item_name} expectations are invalid")
    for index, item in enumerate(value["required"]):
        if not validator(item):
            raise ValueError(f"{context} {item_name} {index} is invalid")


def _validate_case(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"semantic case {index} is invalid")
    _exact_keys(value, {"case_id", "evidence_class", "input", "expected"}, f"semantic case {index}")
    case_id = value["case_id"]
    if not isinstance(case_id, str) or not _CASE_RE.fullmatch(case_id) or case_id not in _CASE_IDS:
        raise ValueError(f"semantic case {index} has an invalid case_id")
    if value["evidence_class"] not in _EXPECTED_OUTCOME_BY_EVIDENCE:
        raise ValueError(f"semantic case {case_id} has an invalid evidence class")
    input_value = value["input"]
    if not isinstance(input_value, dict):
        raise ValueError(f"semantic case {case_id} input is required")
    _exact_keys(input_value, {"turns"}, f"semantic case {case_id} input")
    turns = input_value["turns"]
    if not isinstance(turns, list) or not 2 <= len(turns) <= 8:
        raise ValueError(f"semantic case {case_id} must contain two to eight turns")
    owner_count = 0
    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            raise ValueError(f"semantic case {case_id} turn {turn_index} is invalid")
        _exact_keys(turn, {"role", "text"}, f"semantic case {case_id} turn")
        if turn["role"] not in {"owner", "assistant"}:
            raise ValueError(f"semantic case {case_id} has an unsupported role")
        if turn["role"] == "owner":
            owner_count += 1
        _text(turn["text"], f"semantic case {case_id} turn text")
    if turns[0]["role"] != "owner" or owner_count == 0:
        raise ValueError(f"semantic case {case_id} must start with Owner evidence")
    expected = value["expected"]
    if not isinstance(expected, dict):
        raise ValueError(f"semantic case {case_id} expected result is required")
    _exact_keys(expected, {"outcome", "usefulness", "structure"}, f"semantic case {case_id} expected")
    if (
        expected["outcome"] != _EXPECTED_OUTCOME_BY_EVIDENCE[value["evidence_class"]]
        or expected["usefulness"] is not True
    ):
        raise ValueError(f"semantic case {case_id} expected result is invalid")
    _validate_structure(expected["structure"], f"semantic case {case_id}")
    return deepcopy(value)


def validate_semantic_manifest(path: Path) -> dict[str, Any]:
    """Validate the exact synthetic dataset and its non-self-referential digest."""

    value = _load_manifest(path)
    _exact_keys(
        value,
        {
            "schema_version",
            "evaluation_id",
            "dataset_version",
            "status",
            "hash_convention",
            "provider",
            "policy",
            "budgets",
            "sample_size",
            "rubric",
            "limitations",
            "cases",
            "frozen_sha256",
        },
        "semantic evaluation manifest",
    )
    if value["schema_version"] != SEMANTIC_MANIFEST_SCHEMA or value["evaluation_id"] != DATASET_ID:
        raise ValueError("semantic evaluation identity is invalid")
    if value["dataset_version"] != DATASET_VERSION or value["status"] != "frozen-synthetic":
        raise ValueError("semantic evaluation dataset is not frozen")
    if value["hash_convention"] != HASH_CONVENTION:
        raise ValueError("semantic evaluation hash convention is unsupported")
    if value["provider"] != _PROVIDER or value["policy"] != _POLICY:
        raise ValueError("semantic evaluation provider or policy is not frozen")
    budgets = _validate_budgets(value["budgets"])
    if value["sample_size"] != SAMPLE_SIZE:
        raise ValueError("semantic evaluation sample size is not frozen")
    if value["rubric"] != RUBRIC or value["limitations"] != LIMITATIONS:
        raise ValueError("semantic evaluation rubric or limitations are not frozen")
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != SAMPLE_SIZE:
        raise ValueError("semantic evaluation case count is not frozen")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        validated = _validate_case(case, index)
        if validated["case_id"] != _CASE_ORDER[index]:
            raise ValueError("semantic evaluation case order is not frozen")
        if validated["case_id"] in seen:
            raise ValueError("semantic evaluation case IDs must be unique")
        seen.add(validated["case_id"])
    if seen != _CASE_IDS:
        raise ValueError("semantic evaluation cases are incomplete")
    digest = value["frozen_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("semantic evaluation frozen SHA-256 is invalid")
    if digest != _digest(value):
        raise ValueError("semantic evaluation frozen SHA-256 does not match manifest")
    return value


def _processor_budgets(value: Mapping[str, int]) -> BudgetConfig:
    return BudgetConfig(
        new_evidence_tokens=value["new_evidence_tokens"],
        preceding_turn_tokens=value["preceding_overlap_tokens"],
        continuation_summary_tokens=value["continuation_summary_tokens"],
        project_summary_tokens=value["project_summary_tokens"],
        related_records_tokens=value["related_records_tokens"],
        related_record_count=value["max_related_records"],
        total_input_tokens=value["input_tokens"],
        semantic_output_tokens=value["output_tokens"],
    )


def _conversation(case: Mapping[str, Any]) -> ConversationBatch:
    case_id = case["case_id"]
    conversation_id = f"semantic-{case_id}"
    turns: list[NormalizedTurn] = []
    for index, item in enumerate(case["input"]["turns"], 1):
        text = item["text"]
        turns.append(
            NormalizedTurn(
                connector_id="semantic-evaluation",
                conversation_id=conversation_id,
                turn_id=f"{case_id}-turn-{index}",
                occurred_at=f"2026-08-30T00:{index:02d}:00Z",
                source_uri=f"synthetic://semantic-evaluation/{case_id}/{index}",
                text=text,
                content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                source_role=item["role"],
            )
        )
    return ConversationBatch("semantic-evaluation", conversation_id, tuple(turns))


def _structure(processed: Any) -> dict[str, Any]:
    return {
        "continuation": processed.continuation is not None,
        "records": sorted(
            ({"operation": item.operation, "kind": item.kind} for item in processed.record_proposals),
            key=lambda item: (item["operation"], item["kind"]),
        ),
        "candidates": sorted(
            (
                {"operation": item.operation, "kind": item.proposal.candidate_kind}
                for item in processed.candidate_operations
            ),
            key=lambda item: (item["operation"], item["kind"]),
        ),
        "observations": sorted(
            (
                {
                    "dimension": item.dimension,
                    "context": item.context,
                    "evidence_class": item.evidence_class,
                }
                for item in processed.observations
            ),
            key=lambda item: (item["dimension"], item["context"], item["evidence_class"]),
        ),
        "observation_abstentions": sorted(
            item.abstention_reason for item in processed.observation_abstentions
        ),
        "abstentions": sorted(item.reason for item in processed.abstentions),
        "conflicts": len(processed.conflict_proposals),
        "supersessions": len(processed.supersede_proposals),
        "project_summary": processed.project_summary is not None,
    }


def _presence_matches(actual: bool, expectation: str) -> bool:
    return expectation == "allowed" or (
        expectation == "required" and actual
    ) or (expectation == "forbidden" and not actual)


def _items_match(actual: list[Any], expectation: Mapping[str, Any]) -> bool:
    required = expectation["required"]
    if not all(item in actual for item in required):
        return False
    if expectation["forbidden"] and any(item not in required for item in actual):
        return False
    return True


def _bounded_count_matches(actual: int, expectation: Mapping[str, int]) -> bool:
    return expectation["minimum"] <= actual <= expectation["maximum"]


def _structure_matches(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return (
        _presence_matches(actual["continuation"], expected["continuation"])
        and _presence_matches(actual["project_summary"], expected["project_summary"])
        and all(
            _items_match(actual[key], expected[key])
            for key in (
                "records",
                "candidates",
                "observations",
                "observation_abstentions",
                "abstentions",
            )
        )
        and _bounded_count_matches(actual["conflicts"], expected["conflicts"])
        and _bounded_count_matches(actual["supersessions"], expected["supersessions"])
    )


def _score(passed: int, total: int, *, minimum: float | None = None) -> dict[str, Any]:
    score = passed / total
    return {
        "passed": passed,
        "total": total,
        "score": score,
        "passed_gate": minimum is None or score >= minimum,
    }


def run_semantic_evaluation(
    path: Path,
    provider: SemanticProvider,
    *,
    repository_version: str,
    result_path: Path | None = None,
) -> dict[str, Any]:
    """Run exactly the frozen synthetic cases through one Processor boundary.

    The returned record contains structural outcomes only.  It never includes
    the fixture input, provider proposal text, or exception messages.
    """

    if result_path is not None:
        _validate_result_path(result_path)
    manifest = validate_semantic_manifest(path)
    provider_name = getattr(provider, "name", None)
    expected_name = f"{PROVIDER_ADAPTER}/{PROVIDER_MODEL}/{PROVIDER_REASONING}"
    if provider_name != expected_name:
        raise ValueError("semantic provider identity does not match frozen manifest")
    repository_version = _version(repository_version, "repository")
    budgets = _processor_budgets(manifest["budgets"])
    processor = Processor(provider)
    case_results: list[_CaseResult] = []
    for case in manifest["cases"]:
        expected = case["expected"]
        observed_structure = None
        valid = safe = False
        error_type = None
        try:
            processed = processor.process(
                _conversation(case),
                previous_continuation=None,
                project_id=None,
                scope_kind="general",
                scope_id="general",
                budgets=budgets,
            )
            observed_structure = _structure(processed)
            valid = True
            safe = processed.provider == provider_name and not contains_secret(processed.provider)
        except Exception as error:
            error_type = type(error).__name__
            if not _ERROR_RE.fullmatch(error_type):
                error_type = "ProviderOrProcessorError"
        useful = valid and observed_structure is not None and _structure_matches(
            observed_structure, expected["structure"]
        )
        case_results.append(
            _CaseResult(
                case["case_id"],
                case["evidence_class"],
                expected["outcome"],
                expected["usefulness"],
                useful,
                valid,
                safe,
                deepcopy(expected["structure"]),
                observed_structure,
                error_type,
            )
        )
    values = [item.value() for item in case_results]
    usefulness_passed = sum(item.usefulness for item in case_results)
    validity_passed = sum(item.deterministic_validity for item in case_results)
    safety_passed = sum(item.deterministic_safety for item in case_results)
    usefulness = _score(
        usefulness_passed,
        len(values),
        minimum=manifest["rubric"]["usefulness_minimum"],
    )
    validity = _score(validity_passed, len(values))
    safety = _score(safety_passed, len(values))
    passed = (
        usefulness["passed_gate"]
        and (validity["passed"] == validity["total"])
        and (safety["passed"] == safety["total"])
    )
    result = {
        "schema_version": SEMANTIC_RESULT_SCHEMA,
        "evaluation_id": manifest["evaluation_id"],
        "dataset_version": manifest["dataset_version"],
        "manifest_sha256": manifest["frozen_sha256"],
        "repository_version": repository_version,
        "provider": deepcopy(manifest["provider"]),
        "policy": deepcopy(manifest["policy"]),
        "budgets": deepcopy(manifest["budgets"]),
        "sample_size": manifest["sample_size"],
        "rubric": deepcopy(manifest["rubric"]),
        "limitations": deepcopy(manifest["limitations"]),
        "cases": values,
        "overall": {
            "usefulness": usefulness,
            "deterministic_validity": validity,
            "deterministic_safety": safety,
        },
        "passed": passed,
    }
    if result_path is not None:
        _publish_result(result_path, result)
    return result


def _publish_result(path: Path, result: Mapping[str, Any]) -> None:
    """Retain one content-safe immutable result produced by this runner."""

    _validate_result_path(path)
    payload_text = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if contains_secret(payload_text):
        raise ValueError("semantic result failed secret containment")
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".orca-semantic-evaluation-", suffix=".tmp", dir=path.parent
        )
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload_text.encode("utf-8"))
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


def _validate_result_path(path: Path) -> None:
    if path.suffix != ".json" or not path.parent.is_dir():
        raise ValueError("semantic result path must be an existing JSON destination")
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
