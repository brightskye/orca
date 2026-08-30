"""Validate semantic proposals derived from normalized conversation turns."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Protocol

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.candidates import CandidateProposal
from orca_memory.conflicts import ConflictProposal, SupersedeProposal
from orca_memory.interaction import (
    InteractionObservation,
    ObservationAbstention,
    ObservationProposal,
    admit_observation,
)
from orca_memory.memory import ProjectSummary, RecordProposal
from orca_memory.privacy import contains_secret
from orca_memory.segmentation import (
    DEFAULT_BUDGETS,
    BudgetConfig,
    SourceSegment,
    measure_context,
    segment_turn_with_budget,
    select_related_records,
)


PROCESSOR_POLICY = "orca-processor/0.1"


@dataclass(frozen=True)
class ContinuationSummary:
    """Validated content for one structural Conversation Continuation Summary."""

    purpose: str
    current_state: str
    important_outcomes: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()
    relevant_artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessingInput:
    """Bounded input visible to one semantic-provider call."""

    owner_evidence: tuple[SourceSegment, ...]
    assistant_context: tuple[SourceSegment, ...]
    previous_continuation: str | None
    project_id: str | None
    preceding_turn: str | None = None
    project_summary: str | None = None
    related_records: tuple[object, ...] = ()


@dataclass(frozen=True)
class ProcessingProposal:
    """Untrusted semantic output; absence means a valid no-memory result."""

    continuation: ContinuationSummary | None
    record_proposals: tuple[RecordProposal, ...] = ()
    project_summary: ProjectSummary | None = None
    candidate_operations: tuple["CandidateInstruction", ...] = ()
    conflict_proposals: tuple[ConflictProposal, ...] = ()
    supersede_proposals: tuple[SupersedeProposal, ...] = ()
    abstentions: tuple["Abstention", ...] = ()
    observation_proposals: tuple[ObservationProposal, ...] = ()


@dataclass(frozen=True)
class CandidateInstruction:
    """Create or exactly support one ordinary Knowledge Candidate."""

    operation: str
    proposal: CandidateProposal
    target_candidate_id: str | None = None

    def __post_init__(self) -> None:
        if self.operation not in {"create", "support"}:
            raise ValueError("candidate operation must be create or support")
        if not isinstance(self.proposal, CandidateProposal):
            raise ValueError("candidate instruction requires CandidateProposal")
        if self.operation == "support" and not self.target_candidate_id:
            raise ValueError("candidate support requires target_candidate_id")
        if self.operation == "create" and self.target_candidate_id is not None:
            raise ValueError("candidate creation cannot target an identity")


@dataclass(frozen=True)
class Abstention:
    """One controlled semantic decline; it creates no operation receipt."""

    reason: str

    def __post_init__(self) -> None:
        if self.reason not in {
            "ambiguous",
            "hypothetical",
            "quoted",
            "private",
            "sensitive",
            "third-party",
            "task-or-reminder",
            "unsupported",
        }:
            raise ValueError("unsupported abstention reason")


class SemanticProvider(Protocol):
    """Replaceable semantic seam used by Processor."""

    name: str

    def distill(self, request: ProcessingInput) -> ProcessingProposal:
        """Return one proposal for the supplied bounded evidence."""


@dataclass(frozen=True)
class ProcessedConversation:
    """Validated Processor output ready for Storage."""

    conversation: ConversationBatch
    source_segments: tuple[SourceSegment, ...]
    continuation: ContinuationSummary | None
    record_proposals: tuple[RecordProposal, ...]
    project_summary: ProjectSummary | None
    candidate_operations: tuple[CandidateInstruction, ...]
    conflict_proposals: tuple[ConflictProposal, ...]
    supersede_proposals: tuple[SupersedeProposal, ...]
    abstentions: tuple[Abstention, ...]
    observations: tuple[InteractionObservation, ...]
    observation_abstentions: tuple[ObservationAbstention, ...]
    provider: str
    policy: str = PROCESSOR_POLICY


class Processor:
    """Hide semantic-provider invocation and deterministic output validation."""

    def __init__(self, provider: SemanticProvider) -> None:
        if not provider.name.strip():
            raise ValueError("semantic provider name is required")
        self._provider = provider

    def process(
        self,
        conversation: ConversationBatch,
        *,
        previous_continuation: str | None,
        project_id: str | None,
        scope_kind: str,
        scope_id: str,
        source_segments: tuple[SourceSegment, ...] | None = None,
        preceding_turn: str | None = None,
        project_summary: str | None = None,
        related_records: tuple[object, ...] = (),
        budgets: BudgetConfig = DEFAULT_BUDGETS,
    ) -> ProcessedConversation:
        if source_segments is None:
            source_segments = tuple(
                segment
                for turn in conversation.turns
                for segment in segment_turn_with_budget(turn, budgets)
            )
        valid_turn_ids = {turn.turn_id for turn in conversation.turns}
        if not source_segments or any(
            segment.turn_id not in valid_turn_ids for segment in source_segments
        ):
            raise ValueError("Processor source segments do not match the conversation")
        owner_evidence = tuple(
            segment for segment in source_segments if segment.source_role == "owner"
        )
        assistant_context = tuple(
            segment for segment in source_segments if segment.source_role == "assistant"
        )
        if len(owner_evidence) + len(assistant_context) != len(source_segments):
            raise ValueError("Processor received an unsupported source role")
        if not owner_evidence:
            raise ValueError("Processor requires at least one new Owner evidence turn")
        if scope_kind != "project" and project_summary is not None:
            raise ValueError("Project Summary input is forbidden outside project scope")
        selected_related = select_related_records(
            related_records, scope_kind, scope_id, budgets=budgets
        )
        preceding = preceding_turn or ""
        if preceding and len(preceding.encode("utf-8")) > budgets.preceding_turn_tokens:
            preceding = ""
        usage = measure_context(
            new_evidence=tuple(segment.text for segment in source_segments),
            preceding_turn=preceding,
            continuation_summary=previous_continuation or "",
            project_summary=project_summary or "",
            related_records=selected_related,
        )
        usage.validate(budgets)
        proposal = self._provider.distill(
            ProcessingInput(
                owner_evidence,
                assistant_context,
                previous_continuation,
                project_id,
                preceding or None,
                project_summary,
                selected_related,
            )
        )
        if not isinstance(proposal, ProcessingProposal):
            raise ValueError("semantic provider returned an invalid proposal")
        output_payload = json.dumps(asdict(proposal), sort_keys=True, default=str)
        measure_context(semantic_output=output_payload).validate(budgets)
        if proposal.continuation is not None:
            _validate_continuation(proposal.continuation)
        if not isinstance(proposal.record_proposals, tuple):
            raise ValueError("semantic provider record proposals must be a tuple")
        for record in proposal.record_proposals:
            if not isinstance(record, RecordProposal):
                raise ValueError("semantic provider returned an invalid record proposal")
            record.validate()
            if record.scope != scope_kind or record.scope_id != scope_id:
                raise ValueError("semantic provider proposal crosses resolved scope")
        for instruction in proposal.candidate_operations:
            if not isinstance(instruction, CandidateInstruction):
                raise ValueError("semantic provider returned an invalid candidate instruction")
            candidate = instruction.proposal
            if candidate.scope != scope_kind or candidate.scope_id != scope_id:
                raise ValueError("candidate instruction crosses resolved scope")
        for conflict in proposal.conflict_proposals:
            if not isinstance(conflict, ConflictProposal):
                raise ValueError("semantic provider returned an invalid conflict proposal")
            if conflict.scope != scope_kind or conflict.scope_id != scope_id:
                raise ValueError("conflict proposal crosses resolved scope")
        for replacement in proposal.supersede_proposals:
            if not isinstance(replacement, SupersedeProposal):
                raise ValueError("semantic provider returned an invalid supersede proposal")
            if replacement.scope != scope_kind or replacement.scope_id != scope_id:
                raise ValueError("supersede proposal crosses resolved scope")
        if not all(isinstance(item, Abstention) for item in proposal.abstentions):
            raise ValueError("semantic provider returned an invalid abstention")
        admitted_observations: list[InteractionObservation] = []
        observation_abstentions: list[ObservationAbstention] = []
        for observation_proposal in proposal.observation_proposals:
            result = admit_observation(observation_proposal, source_segments)
            if isinstance(result, InteractionObservation):
                observation_scope = result.scope
                unsupported_scope = (
                    observation_scope.agent_id not in {None, "codex"}
                    or observation_scope.project_id is not None
                    and observation_scope.project_id != project_id
                )
                if unsupported_scope:
                    observation_abstentions.append(
                        ObservationAbstention(result.observation_id, "unsupported-scope")
                    )
                else:
                    admitted_observations.append(result)
            else:
                observation_abstentions.append(result)
        if proposal.project_summary is not None:
            if scope_kind != "project" or project_id != scope_id:
                raise ValueError("Project Summary requires resolved project scope")
            proposal.project_summary.validate()
            if proposal.project_summary.project_id != project_id:
                raise ValueError("Project Summary crosses resolved project scope")
        return ProcessedConversation(
            conversation=conversation,
            source_segments=source_segments,
            continuation=proposal.continuation,
            record_proposals=proposal.record_proposals,
            project_summary=proposal.project_summary,
            candidate_operations=proposal.candidate_operations,
            conflict_proposals=proposal.conflict_proposals,
            supersede_proposals=proposal.supersede_proposals,
            abstentions=proposal.abstentions,
            observations=tuple(admitted_observations),
            observation_abstentions=tuple(observation_abstentions),
            provider=self._provider.name,
        )


def _validate_continuation(summary: ContinuationSummary) -> None:
    if not summary.purpose.strip():
        raise ValueError("continuation purpose is required")
    if not summary.current_state.strip():
        raise ValueError("continuation current state is required")
    values = (summary.purpose, summary.current_state) + tuple(
        item
        for group in (
            summary.important_outcomes,
            summary.open_questions,
            summary.next_steps,
            summary.relevant_artifacts,
        )
        for item in group
    )
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("continuation fields must contain nonempty strings")
    if any(contains_secret(value) for value in values):
        raise ValueError("continuation contains a credential-like value")
