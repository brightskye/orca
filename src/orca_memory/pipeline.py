"""Run the minimal recoverable Step 3 processing flow."""

from __future__ import annotations

from orca_memory.conversation import ConversationBatch
from orca_memory.processor import Processor
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
    ) -> PublicationResult:
        if not conversation.turns:
            raise ValueError("Step 3 requires at least one normalized turn")
        self._storage.recover_pending_publications()
        new_conversation = self._storage.select_unprocessed(conversation)
        if not new_conversation.turns:
            return self._storage.record_replay(conversation)
        previous = self._storage.load_continuation(
            conversation.conversation_id, scope=scope
        )
        processed = self._processor.process(
            new_conversation,
            previous_continuation=previous,
            project_id=scope.scope_id if scope.kind == "project" else None,
            scope_kind=scope.kind,
            scope_id=scope.scope_id,
        )
        return self._storage.publish(processed, scope=scope)
