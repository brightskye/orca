"""Local-only operator surface for Phase 1 configuration and derived state."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from orca_memory.attention import rebuild_status
from orca_memory.application import LocalOrcaApplication
from orca_memory.codex_provider import CODEX_CLI_ADAPTER, CodexCliSemanticProvider
from orca_memory.configuration import load_configuration
from orca_memory.conversation import normalize_codex_rollout
from orca_memory.interaction import rebuild_profiles, select_guidance
from orca_memory.retrieval import (
    AgentCairnRetrievalAdapter,
    RecallRequest,
    RecallService,
    discover_projection_sources,
    load_projection_index,
    rebuild_projection_index,
)
from orca_memory.runtime import LocalRuntime
from orca_memory.storage import MemoryScope


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="orca")
    parser.add_argument("--host-config", type=Path, default=Path("config/host.yaml"))
    parser.add_argument(
        "--registered-adapter",
        action="append",
        default=[],
        help="Locally installed semantic-provider adapter identity; validation only.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    commands.add_parser("health")
    commands.add_parser("status")
    commands.add_parser("rebuild")
    commands.add_parser("stop")
    start = commands.add_parser("start")
    start.add_argument("--session-id", required=True)
    start.add_argument("--context", default="general")
    start.add_argument("--project-id")
    start.add_argument("--project-alias")
    recall = commands.add_parser("recall")
    recall.add_argument("question")
    recall.add_argument("--project-id")
    recall.add_argument("--project-alias")
    recall.add_argument("--include-closed", action="store_true")
    queue = commands.add_parser("queue-pointer")
    queue.add_argument("--trigger", choices=("pre-compact", "explicit-save"), required=True)
    queue.add_argument("--connector-id", default="codex-local")
    queue.add_argument("--conversation-id", required=True)
    queue.add_argument("--source", type=Path, required=True)
    queue.add_argument("--start-offset", type=int, default=0)
    queue.add_argument("--scope", choices=("general", "unassigned"), default="unassigned")
    session_end = commands.add_parser("session-end")
    session_end.add_argument("--source", type=Path, required=True)
    session_end.add_argument("--connector-id", default="codex-local")
    session_end.add_argument("--scope", choices=("general", "unassigned"), default="unassigned")
    worker = commands.add_parser("worker")
    worker.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        required=True,
    )
    catch_up = commands.add_parser("catch-up")
    catch_up.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        required=True,
    )
    catch_up.add_argument("--max-sources", type=int, default=20)
    args = parser.parse_args(argv)
    registered_adapters = {CODEX_CLI_ADAPTER, *args.registered_adapter}
    configuration = load_configuration(
        args.host_config,
        registered_provider_adapters=registered_adapters,
    )
    vault = configuration.host.vault_path
    runtime = configuration.host.runtime_path
    if args.command == "validate":
        print("configuration: valid")
        return 0
    if args.command == "health":
        pending = len(LocalRuntime(runtime).pending())
        print(json.dumps({"configuration": "valid", "queue_pending": pending}, sort_keys=True))
        return 0
    if args.command == "status":
        print(rebuild_status(vault, runtime).render())
        return 0
    if args.command == "stop":
        print("Orca uses one-shot workers; no daemon is running.")
        return 0
    if args.command == "rebuild":
        aliases = {record.project_id: record.project_alias for record in configuration.project_registry.records}
        profiles = rebuild_profiles(
            vault,
            as_of=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            project_aliases=aliases,
        )
        index = rebuild_projection_index(
            discover_projection_sources(vault), runtime_root=runtime
        )
        status = rebuild_status(vault, runtime)
        print(
            json.dumps(
                {
                    "profiles": len(profiles),
                    "retrieval_projections": len(index.projections),
                    "attention_items": len(status.items),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "start":
        # Session start is deterministic: guidance plus a content-free status
        # reminder. It performs no semantic Recall or conversation processing.
        status = rebuild_status(vault, runtime)
        guidance = select_guidance(
            vault,
            context=args.context,
            agent_id="codex",
            project_id=args.project_id,
            project_alias=args.project_alias,
            token_budget=configuration.vault.budgets.interaction.auto_load_tokens,
        )
        from orca_memory.attention import session_reminder

        reminder = session_reminder(status, runtime_root=runtime, session_id=args.session_id)
        print(json.dumps({"guidance": guidance, "reminder": reminder}, sort_keys=True))
        return 0
    if args.command == "recall":
        index = load_projection_index(runtime, vault)

        def resolve(alias: str) -> str | None:
            record = configuration.project_registry.by_alias(alias)
            return record.project_id if record is not None else None

        recall_budgets = configuration.vault.budgets.recall
        response = RecallService(
            index,
            AgentCairnRetrievalAdapter.local(),
            project_alias_resolver=resolve,
            total_tokens=recall_budgets.total_tokens,
            per_document_tokens=recall_budgets.per_document_tokens,
            exact_continuation_tokens=recall_budgets.exact_continuation_tokens,
        ).recall(
            RecallRequest(
                args.question,
                project_id=args.project_id,
                project_alias=args.project_alias,
                include_closed=args.include_closed,
                max_results=configuration.vault.budgets.recall.max_results,
            )
        )
        print(json.dumps(asdict(response), sort_keys=True))
        return 0
    if args.command == "queue-pointer":
        source = _permitted_rollout_source(
            args.source, configuration.host.codex_rollout_store
        )
        item = LocalRuntime(runtime).enqueue_pointer(
            trigger=args.trigger,
            connector_id=args.connector_id,
            conversation_id=args.conversation_id,
            source_path=source,
            start_offset=args.start_offset,
            scope_kind=args.scope,
            scope_id=args.scope,
        )
        print(json.dumps({"work_id": item.work_id, "queued": True}, sort_keys=True))
        return 0
    if args.command == "session-end":
        source = _permitted_rollout_source(
            args.source, configuration.host.codex_rollout_store
        )
        batch = normalize_codex_rollout(source, connector_id=args.connector_id)
        if not batch.turns:
            print(json.dumps({"queued": False, "reason": "no-permitted-evidence"}, sort_keys=True))
            return 0
        item = LocalRuntime(runtime).enqueue_session_end(
            batch,
            now=datetime.now(timezone.utc),
            scope_kind=args.scope,
            scope_id=args.scope,
            retention_hours=configuration.vault.retry.retention_hours,
        )
        print(json.dumps({"work_id": item.work_id, "queued": True}, sort_keys=True))
        return 0
    if args.command == "catch-up":
        if args.max_sources <= 0:
            parser.error("catch-up --max-sources must be positive")
        local_runtime = LocalRuntime(
            runtime, max_attempts=configuration.vault.retry.max_attempts
        )
        queued = 0
        for source in sorted(configuration.host.codex_rollout_store.rglob("*.jsonl")):
            if queued >= args.max_sources:
                break
            batch = normalize_codex_rollout(source, connector_id="codex-local")
            if not batch.turns:
                continue
            local_runtime.enqueue_pointer(
                trigger="catch-up",
                connector_id=batch.connector_id,
                conversation_id=batch.conversation_id,
                source_path=source,
                start_offset=0,
                scope_kind="unassigned",
                scope_id="unassigned",
            )
            queued += 1
        result = _run_worker(configuration, args.reasoning_effort)
        print(
            json.dumps(
                {
                    "configured_interval_minutes": configuration.vault.cadence.catch_up_minutes,
                    "queued": queued,
                    "worker": result,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "worker":
        result = _run_worker(configuration, args.reasoning_effort)
        print(json.dumps({"worker": result}, sort_keys=True))
        return 0
    raise AssertionError("unreachable command")


def _permitted_rollout_source(source: Path, rollout_store: Path) -> Path:
    resolved = source.resolve()
    root = rollout_store.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(root):
        raise ValueError("Codex rollout source must be a file inside the configured store")
    return resolved


def _run_worker(configuration, reasoning_effort: str) -> str:
    if configuration.vault.provider.adapter != CODEX_CLI_ADAPTER:
        raise ValueError("worker supports only the configured codex-cli adapter")
    provider = CodexCliSemanticProvider(
        model=configuration.vault.provider.model,
        reasoning_effort=reasoning_effort,
    )
    application = LocalOrcaApplication(configuration, provider)
    local_runtime = LocalRuntime(
        configuration.host.runtime_path,
        max_attempts=configuration.vault.retry.max_attempts,
    )

    def process(item, retry_batch):
        batch = retry_batch
        if batch is None:
            source = _permitted_rollout_source(
                Path(item.source_locator), configuration.host.codex_rollout_store
            )
            batch = normalize_codex_rollout(
                source,
                connector_id=item.connector_id,
                start_offset=item.start_offset,
            )
        if batch.conversation_id != item.conversation_id:
            raise ValueError("runtime source conversation identity changed")
        if not any(turn.source_role == "owner" for turn in batch.turns):
            return
        application.process(
            batch,
            scope=MemoryScope(item.scope_kind, item.scope_id, item.project_alias),
        )
        application.recover_and_rebuild()

    return local_runtime.run_once(process)


if __name__ == "__main__":
    raise SystemExit(main())
