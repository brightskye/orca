"""Validate semantic proposals derived from normalized conversation turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from orca_memory.conversation import ConversationBatch
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

    conversation: ConversationBatch
    previous_continuation: str | None
    project_id: str | None


@dataclass(frozen=True)
class ProcessingProposal:
    """Untrusted semantic output; absence means a valid no-memory result."""

    continuation: ContinuationSummary | None


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
    ) -> ProcessedConversation:
        if not conversation.turns:
            raise ValueError("Processor requires at least one new turn")
        proposal = self._provider.distill(
            ProcessingInput(conversation, previous_continuation, project_id)
        )
        if not isinstance(proposal, ProcessingProposal):
            raise ValueError("semantic provider returned an invalid proposal")
        if proposal.continuation is not None:
            _validate_continuation(proposal.continuation)
        return ProcessedConversation(
            conversation=conversation,
            continuation=proposal.continuation,
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
