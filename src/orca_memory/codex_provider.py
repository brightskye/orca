"""Bounded Codex CLI Semantic Provider Adapter for the private local runtime."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable, Mapping

from orca_memory.candidates import CandidateProposal
from orca_memory.conflicts import ConflictProposal, SupersedeProposal
from orca_memory.interaction import InteractionScope, ObservationProposal
from orca_memory.memory import ProjectSummary, RecordProposal
from orca_memory.privacy import contains_secret
from orca_memory.processor import (
    Abstention,
    CandidateInstruction,
    ContinuationSummary,
    ProcessingInput,
    ProcessingProposal,
)


CODEX_CLI_ADAPTER = "codex-cli"
_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})
_MAX_RESPONSE_BYTES = 1_000_000


class CodexProviderError(RuntimeError):
    """The provider failed without exposing private request or response text."""


class CodexCliSemanticProvider:
    """Invoke one isolated ephemeral Codex turn and parse an untrusted proposal.

    The caller supplies the exact configured model and reasoning effort. The
    adapter inherits only the local Codex authentication mechanism; it does not
    copy credentials into Orca configuration, prompts, or runtime artifacts.
    """

    def __init__(
        self,
        *,
        model: str,
        reasoning_effort: str,
        codex_binary: str = "codex",
        timeout_seconds: int = 300,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Codex provider model is required")
        if reasoning_effort not in _REASONING_EFFORTS:
            raise ValueError("unsupported Codex reasoning effort")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ValueError("Codex provider timeout must be positive")
        self.model = model.strip()
        self.reasoning_effort = reasoning_effort
        self.codex_binary = codex_binary
        self.timeout_seconds = timeout_seconds
        self._command_runner = command_runner
        self.name = f"{CODEX_CLI_ADAPTER}/{self.model}/{self.reasoning_effort}"

    def distill(self, request: ProcessingInput) -> ProcessingProposal:
        if not isinstance(request, ProcessingInput):
            raise TypeError("Codex provider requires ProcessingInput")
        request_json = json.dumps(asdict(request), ensure_ascii=False, sort_keys=True)
        if contains_secret(request_json):
            raise CodexProviderError("semantic provider input failed secret containment")
        prompt = _prompt(request_json)
        try:
            with tempfile.TemporaryDirectory(prefix="orca-codex-provider-") as directory:
                root = Path(directory)
                schema_path = root / "proposal.schema.json"
                output_path = root / "proposal.json"
                schema_path.write_text(
                    json.dumps(_output_schema(), sort_keys=True), encoding="utf-8"
                )
                command = [
                    self.codex_binary,
                    "exec",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--model",
                    self.model,
                    "--config",
                    f'model_reasoning_effort="{self.reasoning_effort}"',
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(output_path),
                    "-",
                ]
                completed = self._command_runner(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    cwd=root,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                if completed.returncode != 0:
                    raise CodexProviderError(
                        f"Codex semantic provider failed with exit status {completed.returncode}"
                    )
                if not output_path.is_file() or output_path.stat().st_size > _MAX_RESPONSE_BYTES:
                    raise CodexProviderError("Codex semantic provider returned no bounded proposal")
                value = json.loads(output_path.read_text(encoding="utf-8"))
        except CodexProviderError:
            raise
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise CodexProviderError("Codex semantic provider invocation failed safely") from exc
        try:
            return _proposal_from_mapping(value)
        except (KeyError, TypeError, ValueError) as exc:
            raise CodexProviderError("Codex semantic provider returned an invalid proposal") from exc


def _prompt(request_json: str) -> str:
    return (
        "You are the semantic proposal component of Orca Phase 1. "
        "Use only the supplied JSON. Do not call tools, inspect files, browse, or infer authority. "
        "Propose meaning only; deterministic Orca code validates scope, identity, safety, and storage. "
        "Every scoped proposal must use exactly scope_kind and scope_id from the supplied input. "
        "For every interaction observation, set exactly one of value or direction to a "
        "non-null controlled value and set the other field to null. "
        "Treat quoted, hypothetical, third-party, task/reminder, private, sensitive, or ambiguous text "
        "conservatively and abstain when required. Never invent IDs or cross the supplied scope. "
        "Return exactly the requested JSON schema.\n\n"
        f"Processing input:\n{request_json}"
    )


def _proposal_from_mapping(value: Any) -> ProcessingProposal:
    if not isinstance(value, Mapping):
        raise TypeError("proposal must be a mapping")
    expected = {
        "continuation",
        "record_proposals",
        "project_summary",
        "candidate_operations",
        "conflict_proposals",
        "supersede_proposals",
        "abstentions",
        "observation_proposals",
    }
    if set(value) != expected:
        raise ValueError("proposal fields do not match the provider contract")
    continuation_value = value["continuation"]
    continuation = None
    if continuation_value is not None:
        continuation = ContinuationSummary(
            continuation_value["purpose"],
            continuation_value["current_state"],
            tuple(continuation_value["important_outcomes"]),
            tuple(continuation_value["open_questions"]),
            tuple(continuation_value["next_steps"]),
            tuple(continuation_value["relevant_artifacts"]),
        )
    records = tuple(
        RecordProposal.from_mapping(
            {**item, "workstreams": tuple(item["workstreams"])}
        )
        for item in value["record_proposals"]
    )
    summary_value = value["project_summary"]
    project_summary = None
    if summary_value is not None:
        project_summary = ProjectSummary(
            project_id=summary_value["project_id"],
            purpose=summary_value["purpose"],
            current_state=summary_value["current_state"],
            active_workstreams=tuple(summary_value["active_workstreams"]),
            important_outcomes=tuple(summary_value["important_outcomes"]),
            open_questions=tuple(summary_value["open_questions"]),
            next_steps=tuple(summary_value["next_steps"]),
            relevant_memory_ids=tuple(summary_value["relevant_memory_ids"]),
        )
    candidate_operations = tuple(
        CandidateInstruction(
            item["operation"],
            CandidateProposal(**item["proposal"]),
            item["target_candidate_id"],
        )
        for item in value["candidate_operations"]
    )
    conflicts = tuple(ConflictProposal(**item) for item in value["conflict_proposals"])
    supersessions = tuple(
        SupersedeProposal(**item) for item in value["supersede_proposals"]
    )
    abstentions = tuple(Abstention(item["reason"]) for item in value["abstentions"])
    observations = tuple(
        ObservationProposal(
            dimension=item["dimension"],
            context=item["context"],
            scope=InteractionScope(**item["scope"]),
            evidence_class=item["evidence_class"],
            feedback_turn_id=item["feedback_turn_id"],
            evaluated_assistant_turn_ids=tuple(item["evaluated_assistant_turn_ids"]),
            preceding_request_turn_id=item["preceding_request_turn_id"],
            value=item["value"],
            direction=item["direction"],
            lasting=item["lasting"],
            replaces_prior=item["replaces_prior"],
        )
        for item in value["observation_proposals"]
    )
    return ProcessingProposal(
        continuation,
        records,
        project_summary,
        candidate_operations,
        conflicts,
        supersessions,
        abstentions,
        observations,
    )


def _nullable(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"type": "null"}]}


def _string_array() -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _array(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item}


def _output_schema() -> dict[str, Any]:
    text = {"type": "string"}
    nullable_text = _nullable(text)
    continuation = _object(
        {
            "purpose": text,
            "current_state": text,
            "important_outcomes": _string_array(),
            "open_questions": _string_array(),
            "next_steps": _string_array(),
            "relevant_artifacts": _string_array(),
        }
    )
    record = _object(
        {
            "operation": {"enum": ["add", "support", "update"]},
            "target_memory_id": nullable_text,
            "kind": {"enum": ["workstream-summary", "decision", "knowledge", "entity", "identity", "goal", "constraint", "open-question", "lesson", "topic"]},
            "subject": text,
            "scope": {"enum": ["project", "general", "unassigned"]},
            "scope_id": text,
            "status": {"enum": ["current", "closed"]},
            "source_updated_at": nullable_text,
            "workstreams": _string_array(),
            "current": nullable_text,
            "context": nullable_text,
            "implications": nullable_text,
            "final": nullable_text,
            "closure": nullable_text,
        }
    )
    project_summary = _object(
        {
            "project_id": text,
            "purpose": text,
            "current_state": text,
            "active_workstreams": _string_array(),
            "important_outcomes": _string_array(),
            "open_questions": _string_array(),
            "next_steps": _string_array(),
            "relevant_memory_ids": _string_array(),
        }
    )
    candidate = _object(
        {
            "candidate_kind": {"enum": ["fact", "decision", "preference", "lesson", "project-state"]},
            "subject": text,
            "proposal": text,
            "scope": {"enum": ["project", "general", "unassigned"]},
            "scope_id": text,
            "context": nullable_text,
            "source_updated_at": nullable_text,
        }
    )
    candidate_instruction = _object(
        {
            "operation": {"enum": ["create", "support"]},
            "proposal": candidate,
            "target_candidate_id": nullable_text,
        }
    )
    conflict = _object(
        {
            "target_memory_id": text,
            "kind": text,
            "subject": text,
            "scope": text,
            "scope_id": text,
            "label": text,
            "position": text,
            "position_at": nullable_text,
            "target_variant_id": nullable_text,
        }
    )
    supersede = _object(
        {
            "target_memory_id": text,
            "kind": text,
            "subject": text,
            "scope": text,
            "scope_id": text,
            "current": text,
            "source_updated_at": nullable_text,
            "context": nullable_text,
            "implications": nullable_text,
            "explicit_replacement": {"type": "boolean"},
        }
    )
    scope = _object(
        {
            "type": {"enum": ["global", "agent", "project", "project-agent"]},
            "agent_id": nullable_text,
            "project_id": nullable_text,
        }
    )
    observation = _object(
        {
            "dimension": {"enum": ["detail", "structure", "question-frequency", "technical-depth", "tone", "progress-updates"]},
            "context": {"enum": ["general", "status-update", "explanation", "design-discussion", "implementation", "review"]},
            "scope": scope,
            "evidence_class": {"enum": ["explicit-general", "natural-comparison", "direct-correction", "dimension-specific-praise"]},
            "feedback_turn_id": text,
            "evaluated_assistant_turn_ids": _string_array(),
            "preceding_request_turn_id": text,
            "value": nullable_text,
            "direction": nullable_text,
            "lasting": {"type": "boolean"},
            "replaces_prior": {"type": "boolean"},
        }
    )
    return _object(
        {
            "continuation": _nullable(continuation),
            "record_proposals": _array(record),
            "project_summary": _nullable(project_summary),
            "candidate_operations": _array(candidate_instruction),
            "conflict_proposals": _array(conflict),
            "supersede_proposals": _array(supersede),
            "abstentions": _array(
                _object(
                    {
                        "reason": {
                            "enum": [
                                "ambiguous",
                                "hypothetical",
                                "quoted",
                                "private",
                                "sensitive",
                                "third-party",
                                "task-or-reminder",
                                "unsupported",
                            ]
                        }
                    }
                )
            ),
            "observation_proposals": _array(observation),
        }
    )


__all__ = [
    "CODEX_CLI_ADAPTER",
    "CodexCliSemanticProvider",
    "CodexProviderError",
]
