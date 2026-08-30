"""Run the minimal recoverable Step 3 processing flow."""

from __future__ import annotations

from orca_memory.conversation import ConversationBatch
from orca_memory.processor import Processor
from orca_memory.segmentation import DEFAULT_BUDGETS, BudgetConfig, chunk_turns
from orca_memory.storage import MemoryScope, PublicationResult, Storage


class Step3Pipeline:
    """Coordinate deduplication, Processor, Storage, and checkpoint-last publication."""

    def __init__(self, processor: Processor, storage: Storage) -> None:
        self._processor = processor
        self._storage = storage

    def run(
        self,
        conversation: ConversationBatch,
        *,
        scope: MemoryScope,
        preceding_turn: str | None = None,
    ) -> PublicationResult:
        """Process every bounded chunk and return the final chunk result."""

        return self.run_all(
            conversation, scope=scope, preceding_turn=preceding_turn
        )[-1]

    def run_all(
        self,
        conversation: ConversationBatch,
        *,
        scope: MemoryScope,
        budgets: BudgetConfig = DEFAULT_BUDGETS,
        preceding_turn: str | None = None,
    ) -> tuple[PublicationResult, ...]:
        """Process a backlog as sequential replay-safe Manifest chunks."""

        if not conversation.turns:
            raise ValueError("Step 3 requires at least one normalized turn")
        self._storage.recover_pending_publications()
        results: list[PublicationResult] = []
        preceding_context = preceding_turn
        for chunk in chunk_turns(conversation.turns, budgets):
            new_segments = self._storage.select_unprocessed_segments(chunk.segments)
            if not new_segments:
                results.append(self._storage.record_segment_replay(chunk.segments))
                preceding_context = chunk.segments[-1].text
                continue
            chunk_conversation = ConversationBatch(
                conversation.connector_id,
                conversation.conversation_id,
                chunk.turns,
                conversation.processed_through,
                conversation.has_partial_tail,
            )
            previous = self._storage.load_continuation(
                conversation.conversation_id, scope=scope
            )
            processed = self._processor.process(
                chunk_conversation,
                previous_continuation=previous,
                project_id=scope.scope_id if scope.kind == "project" else None,
                scope_kind=scope.kind,
                scope_id=scope.scope_id,
                source_segments=new_segments,
                preceding_turn=preceding_context,
                project_summary=self._storage.load_project_summary(scope),
                budgets=budgets,
            )
            results.append(self._storage.publish(processed, scope=scope))
            preceding_context = chunk.segments[-1].text
        return tuple(results)
