"""Validate semantic proposals derived from normalized conversation turns."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
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
_DEFAULT_INPUT_TOKENS = DEFAULT_BUDGETS.total_input_tokens


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
    related_candidates: tuple[object, ...] = ()
    scope_kind: str | None = None
    scope_id: str | None = None
    input_tokens: int = _DEFAULT_INPUT_TOKENS


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
    # Deterministic current-run segment locators supplied by the provider.
    source_segment_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.operation not in {"create", "support"}:
            raise ValueError("candidate operation must be create or support")
        if not isinstance(self.proposal, CandidateProposal):
            raise ValueError("candidate instruction requires CandidateProposal")
        if self.operation == "support" and not self.target_candidate_id:
            raise ValueError("candidate support requires target_candidate_id")
        if self.operation == "create" and self.target_candidate_id is not None:
            raise ValueError("candidate creation cannot target an identity")
        if not isinstance(self.source_segment_refs, (tuple, list)):
            raise ValueError("source_segment_refs must be a sequence")
        refs = tuple(self.source_segment_refs)
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ValueError("source_segment_refs must contain non-empty strings")
        if len(set(refs)) != len(refs):
            raise ValueError("source_segment_refs must be unique")
        object.__setattr__(self, "source_segment_refs", refs)


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
        related_candidates: tuple[object, ...] = (),
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
        related_record_tokens = sum(_context_tokens(record) for record in selected_related)
        selected_candidates = _select_related_candidates(
            related_candidates,
            scope_kind,
            scope_id,
            budgets=budgets,
            token_budget=max(0, budgets.related_records_tokens - related_record_tokens),
            count_budget=max(0, budgets.related_record_count - len(selected_related)),
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
            related_candidates=selected_candidates,
        )
        usage.validate(budgets)
        provider_input = _fit_provider_input(
            self._provider,
            owner_evidence=owner_evidence,
            assistant_context=assistant_context,
            previous_continuation=previous_continuation,
            project_id=project_id,
            preceding=preceding,
            project_summary=project_summary,
            related_records=selected_related,
            related_candidates=selected_candidates,
            scope_kind=scope_kind,
            scope_id=scope_id,
            budgets=budgets,
        )
        proposal = self._provider.distill(provider_input)
        if not isinstance(proposal, ProcessingProposal):
            raise ValueError("semantic provider returned an invalid proposal")
        output_fields = asdict(proposal)
        if isinstance(proposal.project_summary, ProjectSummary):
            # Rendering duplicates the supplied summary fields; authority is
            # fixed locally. Neither is additional semantic-provider output.
            output_fields["project_summary"].pop("body")
            output_fields["project_summary"].pop("authority")
        output_payload = json.dumps(
            output_fields, sort_keys=True, default=str, ensure_ascii=False,
            separators=(",", ":"),
        )
        measure_context(semantic_output=output_payload).validate(budgets)
        if proposal.continuation is not None:
            _validate_continuation(proposal.continuation)
        if not isinstance(proposal.record_proposals, tuple):
            raise ValueError("semantic provider record proposals must be a tuple")
        if not all(isinstance(item, RecordProposal) for item in proposal.record_proposals):
            raise ValueError("semantic provider returned an invalid record proposal")
        if not isinstance(proposal.candidate_operations, tuple) or not all(
            isinstance(item, CandidateInstruction) for item in proposal.candidate_operations
        ):
            raise ValueError("semantic provider returned an invalid candidate instruction")
        if not isinstance(proposal.conflict_proposals, tuple) or not all(
            isinstance(item, ConflictProposal) for item in proposal.conflict_proposals
        ):
            raise ValueError("semantic provider returned an invalid conflict proposal")
        if not isinstance(proposal.supersede_proposals, tuple) or not all(
            isinstance(item, SupersedeProposal) for item in proposal.supersede_proposals
        ):
            raise ValueError("semantic provider returned an invalid supersede proposal")
        owner_by_ref = {
            source_segment_ref(segment): segment for segment in owner_evidence
        }
        if len(owner_by_ref) != len(owner_evidence):
            raise ValueError("Processor source segment locators are not unique")
        known_records = {
            getattr(record, "memory_id", None): record
            for record in selected_related
            if getattr(record, "memory_id", None) is not None
        }
        record_proposals = tuple(
            _bind_record_proposal(item, owner_by_ref, known_records)
            for item in proposal.record_proposals
        )
        conflict_proposals = tuple(
            _bind_conflict_proposal(item, owner_by_ref) for item in proposal.conflict_proposals
        )
        supersede_proposals = tuple(
            _bind_supersede_proposal(item, owner_by_ref) for item in proposal.supersede_proposals
        )
        candidate_operations = tuple(
            _bind_candidate_instruction(item, owner_by_ref, selected_candidates)
            for item in proposal.candidate_operations
        )
        if not isinstance(record_proposals, tuple):
            raise ValueError("semantic provider record proposals must be a tuple")
        for record in record_proposals:
            if not isinstance(record, RecordProposal):
                raise ValueError("semantic provider returned an invalid record proposal")
            record.validate()
            if record.scope != scope_kind or record.scope_id != scope_id:
                raise ValueError("semantic provider proposal crosses resolved scope")
        for instruction in candidate_operations:
            if not isinstance(instruction, CandidateInstruction):
                raise ValueError("semantic provider returned an invalid candidate instruction")
            candidate = instruction.proposal
            if candidate.scope != scope_kind or candidate.scope_id != scope_id:
                raise ValueError("candidate instruction crosses resolved scope")
        for conflict in conflict_proposals:
            if not isinstance(conflict, ConflictProposal):
                raise ValueError("semantic provider returned an invalid conflict proposal")
            if conflict.scope != scope_kind or conflict.scope_id != scope_id:
                raise ValueError("conflict proposal crosses resolved scope")
        for replacement in supersede_proposals:
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
            record_proposals=record_proposals,
            project_summary=proposal.project_summary,
            candidate_operations=candidate_operations,
            conflict_proposals=conflict_proposals,
            supersede_proposals=supersede_proposals,
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


def source_segment_ref(segment: SourceSegment) -> str:
    """Return the provider-visible identity of one current source segment.

    Captured turn IDs are portable identifiers and cannot contain ``#``.  The
    pair therefore cannot collide across the selected source segments.
    """

    if not isinstance(segment, SourceSegment):
        raise TypeError("source segment reference requires a SourceSegment")
    return f"{segment.turn_id}#{segment.index}"


def _fit_provider_input(
    provider: SemanticProvider,
    *,
    owner_evidence: tuple[SourceSegment, ...],
    assistant_context: tuple[SourceSegment, ...],
    previous_continuation: str | None,
    project_id: str | None,
    preceding: str,
    project_summary: str | None,
    related_records: tuple[object, ...],
    related_candidates: tuple[object, ...],
    scope_kind: str,
    scope_id: str,
    budgets: BudgetConfig,
) -> ProcessingInput:
    """Fit optional context to a provider's complete local input ceiling.

    The Codex adapter exposes ``input_size`` for the fixed prompt and output
    schema it actually sends.  Only related context and the preceding overlap
    are dropped; current evidence, the continuation summary, and a project
    summary remain intact.  Providers without that optional measurement keep
    the category-level budget check performed by :class:`Processor`.
    """

    input_size = getattr(provider, "input_size", None)
    records = list(related_records)
    candidates = list(related_candidates)
    preceding_value = preceding or None

    def make_input() -> ProcessingInput:
        return ProcessingInput(
            owner_evidence=owner_evidence,
            assistant_context=assistant_context,
            previous_continuation=previous_continuation,
            project_id=project_id,
            preceding_turn=preceding_value,
            project_summary=project_summary,
            related_records=tuple(records),
            related_candidates=tuple(candidates),
            scope_kind=scope_kind,
            scope_id=scope_id,
            input_tokens=budgets.total_input_tokens,
        )

    if not callable(input_size):
        return make_input()
    while True:
        current = make_input()
        if input_size(current) <= budgets.total_input_tokens:
            # Keep the category ceilings honest after optional context is
            # removed.  No evidence or continuation content is truncated.
            measure_context(
                new_evidence=tuple(segment.text for segment in owner_evidence + assistant_context),
                preceding_turn=preceding_value or "",
                continuation_summary=previous_continuation or "",
                project_summary=project_summary or "",
                related_records=tuple(records),
                related_candidates=tuple(candidates),
            ).validate(budgets)
            return current
        if candidates:
            candidates.pop()
        elif records:
            records.pop()
        elif preceding_value is not None:
            preceding_value = None
        else:
            raise ValueError(
                "complete provider input exceeds total_input_tokens after optional context removal"
            )


def _validated_source_segments(
    refs: tuple[str, ...],
    owner_by_ref: dict[str, SourceSegment],
    *,
    label: str,
) -> tuple[tuple[str, ...], tuple[SourceSegment, ...]]:
    if not refs:
        raise ValueError(f"{label} must cite at least one source segment")
    if len(set(refs)) != len(refs):
        raise ValueError(f"{label} source_segment_refs must be unique")
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError(f"{label} source_segment_refs must contain non-empty strings")
    missing = [ref for ref in refs if ref not in owner_by_ref]
    if missing:
        raise ValueError(f"{label} cites a missing or non-Owner source segment")
    return refs, tuple(owner_by_ref[ref] for ref in refs)


def _source_timestamp(segments: tuple[SourceSegment, ...]) -> str | None:
    parsed: list[datetime] = []
    for segment in segments:
        value = segment.occurred_at
        if value is None:
            continue
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("source segment occurred_at is not a valid UTC timestamp") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("source segment occurred_at must include a timezone")
        parsed.append(timestamp.astimezone(timezone.utc))
    if not parsed:
        return None
    return max(parsed).isoformat().replace("+00:00", "Z")


def _bind_record_proposal(
    proposal: RecordProposal,
    owner_by_ref: dict[str, SourceSegment],
    known_records: dict[str, object],
) -> RecordProposal:
    refs, segments = _validated_source_segments(
        proposal.source_segment_refs, owner_by_ref, label="record proposal"
    )
    source_updated_at = _source_timestamp(segments)
    if proposal.operation == "support":
        target = known_records.get(proposal.target_memory_id)
        source_updated_at = getattr(target, "source_updated_at", source_updated_at)
    return replace(
        proposal,
        source_updated_at=source_updated_at,
        source_segment_refs=refs,
    )


def _bind_conflict_proposal(
    proposal: ConflictProposal,
    owner_by_ref: dict[str, SourceSegment],
) -> ConflictProposal:
    refs, segments = _validated_source_segments(
        proposal.source_segment_refs, owner_by_ref, label="conflict proposal"
    )
    # Supporting an existing variant must preserve that variant's original
    # trusted position timestamp. Storage validates the exact target value;
    # the new support turn remains recorded by its Manifest sources.
    position_at = (
        proposal.position_at
        if proposal.target_variant_id is not None
        else _source_timestamp(segments)
    )
    return replace(
        proposal,
        position_at=position_at,
        source_segment_refs=refs,
    )


def _bind_supersede_proposal(
    proposal: SupersedeProposal,
    owner_by_ref: dict[str, SourceSegment],
) -> SupersedeProposal:
    refs, segments = _validated_source_segments(
        proposal.source_segment_refs, owner_by_ref, label="supersede proposal"
    )
    return replace(
        proposal,
        source_updated_at=_source_timestamp(segments),
        source_segment_refs=refs,
    )


def _bind_candidate_instruction(
    instruction: CandidateInstruction,
    owner_by_ref: dict[str, SourceSegment],
    selected_candidates: tuple[object, ...],
) -> CandidateInstruction:
    refs, segments = _validated_source_segments(
        instruction.source_segment_refs, owner_by_ref, label="candidate instruction"
    )
    source_updated_at = _source_timestamp(segments)
    if instruction.operation == "support":
        target = next(
            (
                candidate
                for candidate in selected_candidates
                if getattr(candidate, "candidate_id", None)
                == instruction.target_candidate_id
            ),
            None,
        )
        source_updated_at = getattr(target, "source_updated_at", source_updated_at)
    return replace(
        instruction,
        proposal=replace(instruction.proposal, source_updated_at=source_updated_at),
        source_segment_refs=refs,
    )


def _context_tokens(record: object) -> int:
    if isinstance(record, dict):
        value = record.get("body") or record.get("current") or record.get("final")
    else:
        value = (
            getattr(record, "body", None)
            or getattr(record, "current", None)
            or getattr(record, "final", None)
        )
    if not isinstance(value, str):
        value = getattr(record, "proposal", None)
    if not isinstance(value, str):
        raise ValueError("related context has no bounded text representation")
    return len(value.encode("utf-8"))


def _select_related_candidates(
    candidates: tuple[object, ...] | list[object],
    scope_kind: str,
    scope_id: str,
    *,
    budgets: BudgetConfig,
    token_budget: int,
    count_budget: int,
) -> tuple[object, ...]:
    """Select pending same-scope candidates for exact support targeting."""

    selected: list[object] = []
    used_tokens = 0
    if token_budget <= 0 or count_budget <= 0:
        return ()
    for candidate in candidates:
        if isinstance(candidate, dict):
            scope = candidate.get("scope")
            identity = candidate.get("scope_id")
            status = candidate.get("status")
        else:
            scope = getattr(candidate, "scope", None)
            identity = getattr(candidate, "scope_id", None)
            status = getattr(candidate, "status", None)
        if (scope, identity) != (scope_kind, scope_id) or status != "pending":
            continue
        if len(selected) >= count_budget:
            break
        tokens = _context_tokens(candidate)
        if tokens > token_budget or used_tokens + tokens > token_budget:
            break
        selected.append(candidate)
        used_tokens += tokens
    return tuple(selected)
