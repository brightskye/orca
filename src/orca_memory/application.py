"""Composition root for the private local Phase 1 Orca runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from orca_memory.attention import OrcaStatus, rebuild_status, session_reminder
from orca_memory.configuration import ValidatedConfiguration
from orca_memory.conversation import ConversationBatch
from orca_memory.interaction import rebuild_profiles, select_guidance
from orca_memory.pipeline import Step3Pipeline
from orca_memory.processor import Processor, SemanticProvider
from orca_memory.retrieval import (
    AgentCairnRetrievalAdapter,
    RecallRequest,
    RecallResponse,
    RecallService,
    discover_projection_sources,
    load_projection_index,
    rebuild_projection_index,
)
from orca_memory.storage import MemoryScope, PublicationResult, Storage


@dataclass(frozen=True)
class StartupContext:
    guidance: str
    reminder: str | None
    status: OrcaStatus


class LocalOrcaApplication:
    """Wire validated configuration to processing, recovery, guidance, and Recall."""

    def __init__(
        self,
        configuration: ValidatedConfiguration,
        semantic_provider: SemanticProvider,
        *,
        clock=None,
        id_factory=None,
        recall_adapter=None,
    ) -> None:
        self.configuration = configuration
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._storage = Storage(
            configuration.host.vault_path,
            configuration.host.runtime_path,
            clock=self._clock,
            id_factory=id_factory,
        )
        self._pipeline = Step3Pipeline(Processor(semantic_provider), self._storage)
        self._recall_adapter = recall_adapter or AgentCairnRetrievalAdapter.local()

    def process(self, conversation: ConversationBatch, *, scope: MemoryScope) -> PublicationResult:
        return self._pipeline.run(
            conversation,
            scope=scope,
            budgets=self.configuration.vault.budgets.processor.as_processing_budget(),
        )

    def startup(
        self,
        *,
        session_id: str,
        context: str,
        agent_id: str = "codex",
        project_id: str | None = None,
        project_alias: str | None = None,
        owner_instruction_keys=frozenset(),
        session_adjustment_keys=frozenset(),
    ) -> StartupContext:
        status = rebuild_status(
            self.configuration.host.vault_path,
            self.configuration.host.runtime_path,
        )
        guidance = select_guidance(
            self.configuration.host.vault_path,
            context=context,
            agent_id=agent_id,
            project_id=project_id,
            project_alias=project_alias,
            owner_instruction_keys=owner_instruction_keys,
            session_adjustment_keys=session_adjustment_keys,
            token_budget=self.configuration.vault.budgets.interaction.auto_load_tokens,
        )
        reminder = session_reminder(
            status,
            runtime_root=self.configuration.host.runtime_path,
            session_id=session_id,
        )
        return StartupContext(guidance, reminder, status)

    def recover_and_rebuild(self) -> tuple[Path, ...]:
        recovered = list(self._storage.recover_pending_publications())
        aliases = {
            record.project_id: record.project_alias
            for record in self.configuration.project_registry.records
        }
        recovered.extend(
            rebuild_profiles(
                self.configuration.host.vault_path,
                as_of=self._clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                project_aliases=aliases,
            )
        )
        rebuild_projection_index(
            discover_projection_sources(self.configuration.host.vault_path),
            runtime_root=self.configuration.host.runtime_path,
        )
        rebuild_status(
            self.configuration.host.vault_path,
            self.configuration.host.runtime_path,
        )
        return tuple(recovered)

    def recall(self, request: RecallRequest) -> RecallResponse:
        index = load_projection_index(
            self.configuration.host.runtime_path,
            self.configuration.host.vault_path,
        )

        def resolve(alias: str) -> str | None:
            matches = self.configuration.project_registry.by_alias(alias)
            return matches.project_id if matches is not None else None

        budgets = self.configuration.vault.budgets.recall
        return RecallService(
            index,
            self._recall_adapter,
            project_alias_resolver=resolve,
            total_tokens=budgets.total_tokens,
            per_document_tokens=budgets.per_document_tokens,
            exact_continuation_tokens=budgets.exact_continuation_tokens,
        ).recall(request)


__all__ = ["LocalOrcaApplication", "StartupContext"]
