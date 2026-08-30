"""Validate semantic proposals derived from normalized conversation turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.memory import ProjectSummary, RecordProposal
from orca_memory.privacy import contains_secret


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

    owner_evidence: tuple[NormalizedTurn, ...]
    assistant_context: tuple[NormalizedTurn, ...]
    previous_continuation: str | None
    project_id: str | None


@dataclass(frozen=True)
class ProcessingProposal:
    """Untrusted semantic output; absence means a valid no-memory result."""

    continuation: ContinuationSummary | None
    record_proposals: tuple[RecordProposal, ...] = ()
    project_summary: ProjectSummary | None = None


class SemanticProvider(Protocol):
    """Replaceable semantic seam used by Processor."""

    name: str

    def distill(self, request: ProcessingInput) -> ProcessingProposal:
        """Return one proposal for the supplied bounded evidence."""


@dataclass(frozen=True)
class ProcessedConversation:
    """Validated Processor output ready for Storage."""

    conversation: ConversationBatch
    continuation: ContinuationSummary | None
    record_proposals: tuple[RecordProposal, ...]
    project_summary: ProjectSummary | None
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
    ) -> ProcessedConversation:
        owner_evidence = tuple(
            turn for turn in conversation.turns if turn.source_role == "owner"
        )
        assistant_context = tuple(
            turn for turn in conversation.turns if turn.source_role == "assistant"
        )
        if len(owner_evidence) + len(assistant_context) != len(conversation.turns):
            raise ValueError("Processor received an unsupported source role")
        if not owner_evidence:
            raise ValueError("Processor requires at least one new Owner evidence turn")
        proposal = self._provider.distill(
            ProcessingInput(
                owner_evidence,
                assistant_context,
                previous_continuation,
                project_id,
            )
        )
        if not isinstance(proposal, ProcessingProposal):
            raise ValueError("semantic provider returned an invalid proposal")
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
        if proposal.project_summary is not None:
            if scope_kind != "project" or project_id != scope_id:
                raise ValueError("Project Summary requires resolved project scope")
            proposal.project_summary.validate()
            if proposal.project_summary.project_id != project_id:
                raise ValueError("Project Summary crosses resolved project scope")
        return ProcessedConversation(
            conversation=conversation,
            continuation=proposal.continuation,
            record_proposals=proposal.record_proposals,
            project_summary=proposal.project_summary,
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
