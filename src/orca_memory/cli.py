"""Local-only operator surface for Phase 1 configuration and derived state."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from orca_memory.attention import rebuild_status
from orca_memory.application import LocalOrcaApplication
from orca_memory.backup import create_backup, decrypt_backup_to_staging, verify_backup
from orca_memory.codex_provider import CODEX_CLI_ADAPTER, CodexCliSemanticProvider
from orca_memory.configuration import load_configuration
from orca_memory.conversation import codex_session_metadata, normalize_codex_rollout
from orca_memory.codex_hook import resolve_lifecycle_scope
from orca_memory.interaction import rebuild_profiles, select_guidance
from orca_memory.owner_review import OwnerReviewPublisher
from orca_memory.project_mapping import ProjectMappingPublisher
from orca_memory.projects import (
    allocate_project_id,
    prepare_registration,
    prepare_relink,
    resolve_project,
)
from orca_memory.retrieval import (
    AgentCairnRetrievalAdapter,
    RecallRequest,
    RecallService,
    discover_projection_sources,
    load_projection_index,
    rebuild_projection_index,
)
from orca_memory.runtime import LocalRuntime
from orca_memory.publication import RecoverablePublisher
from orca_memory.storage import MemoryScope


_SAFE_OPERATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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
    scope = commands.add_parser("scope")
    scope.add_argument("scope_kind", choices=("general", "unassigned"))
    scope.add_argument("--conversation-id", required=True)
    project = commands.add_parser("project")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    register = project_commands.add_parser("register")
    register.add_argument("--root", type=Path, required=True)
    register.add_argument("--alias", required=True)
    relink = project_commands.add_parser("relink")
    relink.add_argument("--root", type=Path, required=True)
    selection = relink.add_mutually_exclusive_group(required=True)
    selection.add_argument("--project-id")
    selection.add_argument("--project-alias")
    candidate = commands.add_parser("candidate")
    candidate_commands = candidate.add_subparsers(
        dest="candidate_command", required=True
    )
    for disposition in ("approve", "reject"):
        disposition_command = candidate_commands.add_parser(disposition)
        disposition_command.add_argument("candidate_id")
    conflict = commands.add_parser("conflict")
    conflict_commands = conflict.add_subparsers(dest="conflict_command", required=True)
    select = conflict_commands.add_parser("select")
    select.add_argument("memory_id")
    select.add_argument("--variant", required=True)
    resolve = conflict_commands.add_parser("resolve")
    resolve.add_argument("memory_id")
    resolve.add_argument("--resolution-file", type=Path, required=True)
    resolve.add_argument("--resolution-at", required=True)
    acknowledge = conflict_commands.add_parser("acknowledge")
    acknowledge.add_argument("memory_id")
    recovery = commands.add_parser("recovery")
    recovery_commands = recovery.add_subparsers(dest="recovery_command", required=True)
    for recovery_kind in ("publication", "project-mapping", "owner-review"):
        recovery_command = recovery_commands.add_parser(recovery_kind)
        recovery_command.add_argument("operation_id")
    backup = commands.add_parser("backup")
    backup_commands = backup.add_subparsers(dest="backup_command", required=True)
    backup_create = backup_commands.add_parser("create")
    backup_create.add_argument("--recipient", required=True)
    backup_create.add_argument("--output", type=Path, required=True)
    backup_verify = backup_commands.add_parser("verify")
    backup_verify.add_argument("--source", type=Path, required=True)
    backup_stage = backup_commands.add_parser("stage")
    backup_stage.add_argument("--source", type=Path, required=True)
    backup_stage.add_argument("--destination", type=Path, required=True)
    backup_stage.add_argument(
        "--standalone",
        action="store_true",
        help="Recover without host configuration; choose a new destination outside live data and checkouts.",
    )
    start = commands.add_parser("start")
    start.add_argument("--session-id", required=True)
    start.add_argument("--context", default="general")
    start.add_argument("--project-id")
    start.add_argument("--project-alias")
    recall = commands.add_parser("recall")
    recall.add_argument("question")
    recall.add_argument("--project-id")
    recall.add_argument("--project-alias")
    recall.add_argument("--scope", choices=("general", "unassigned"))
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
    worker.add_argument("--max-items", type=int, default=20)
    catch_up = commands.add_parser("catch-up")
    catch_up.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        required=True,
    )
    catch_up.add_argument("--max-sources", type=int, default=20)
    args = parser.parse_args(argv)
    # Recovery must remain available when the installation being recovered is lost.
    if args.command == "backup" and args.backup_command == "verify":
        verified = verify_backup(args.source)
        print(json.dumps({
            "backup": str(verified.backup_path),
            "manifest_sha256": verified.manifest_sha256,
            "member_count": verified.member_count,
            "total_bytes": verified.total_bytes,
            "verified": True,
        }, sort_keys=True))
        return 0
    if args.command == "backup" and args.backup_command == "stage" and args.standalone:
        staged = decrypt_backup_to_staging(args.source, staging_path=args.destination)
        print(json.dumps({"staged": str(staged), "live_state_changed": False}, sort_keys=True))
        return 0
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
    if args.command == "scope":
        path = LocalRuntime(runtime).set_scope_choice(
            args.conversation_id,
            args.scope_kind,
        )
        print(
            json.dumps(
                {
                    "conversation_id": args.conversation_id,
                    "scope": args.scope_kind,
                    "stored": path.is_file(),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "project":
        publisher = ProjectMappingPublisher(vault, runtime)
        project_root = args.root.resolve(strict=True)
        if not project_root.is_dir():
            raise ValueError("project root must be an existing directory")
        if args.project_command == "register":
            project_id = allocate_project_id(
                lambda: f"proj_{uuid4().hex}",
                existing_ids={
                    record.project_id for record in configuration.project_registry.records
                },
            )
            plan = prepare_registration(
                project_root,
                args.alias,
                configuration.project_registry,
                project_id=project_id,
                now=datetime.now(timezone.utc),
            )
        else:
            plan = prepare_relink(
                project_root,
                configuration.project_registry,
                project_id=args.project_id,
                project_alias=args.project_alias,
            )
        with _runtime_lock(runtime / "locks" / "processor.lock"):
            publisher.publish(
                plan,
                host_config_path=args.host_config,
                operation_id=f"map_{uuid4().hex}",
            )
        print(
            json.dumps(
                {
                    "action": plan.action,
                    "project_alias": plan.project_alias,
                    "project_id": plan.project_id,
                    "registered": True,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "candidate":
        operation_id = f"review_{uuid4().hex}"
        target = (
            "approved-for-manual-apply"
            if args.candidate_command == "approve"
            else "rejected"
        )
        with _runtime_lock(runtime / "locks" / "processor.lock"):
            receipt = OwnerReviewPublisher(vault, runtime).candidate_disposition(
                args.candidate_id,
                target_status=target,
                operation_id=operation_id,
                changed_at=datetime.now(timezone.utc),
            )
        operation_id = receipt.stem
        rebuild_status(vault, runtime)
        print(
            json.dumps(
                {
                    "candidate_id": args.candidate_id,
                    "operation_id": operation_id,
                    "status": target,
                    "receipt": receipt.relative_to(vault).as_posix(),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "conflict":
        operation_id = f"review_{uuid4().hex}"
        options: dict[str, object]
        if args.conflict_command == "select":
            options = {"select_variant_id": args.variant}
            outcome = f"selected:{args.variant}"
        elif args.conflict_command == "acknowledge":
            options = {"keep_unresolved": True}
            outcome = "acknowledged"
        else:
            if args.resolution_file.is_symlink():
                raise ValueError("conflict resolution file must not be a symlink")
            resolution_path = args.resolution_file.resolve(strict=True)
            if not resolution_path.is_file():
                raise ValueError("conflict resolution file must be a regular file")
            if resolution_path.stat().st_mode & 0o077:
                raise ValueError("conflict resolution file permissions must be private")
            options = {
                "owner_resolution": resolution_path.read_text(encoding="utf-8"),
                "resolution_at": args.resolution_at,
            }
            outcome = "owner-resolution"
        with _runtime_lock(runtime / "locks" / "processor.lock"):
            receipt = OwnerReviewPublisher(vault, runtime).conflict_review(
                args.memory_id,
                operation_id=operation_id,
                changed_at=datetime.now(timezone.utc),
                **options,
            )
        rebuild_status(vault, runtime)
        print(
            json.dumps(
                {
                    "memory_id": args.memory_id,
                    "operation_id": operation_id,
                    "outcome": outcome,
                    "receipt": receipt.relative_to(vault).as_posix(),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "recovery":
        if not _SAFE_OPERATION_ID.fullmatch(args.operation_id):
            raise ValueError("invalid recovery operation identity")
        with _runtime_lock(runtime / "locks" / "processor.lock"):
            if args.recovery_command == "publication":
                intent = runtime / "publications" / args.operation_id / "intent.json"
                result = RecoverablePublisher(vault, runtime).recover(intent)
            elif args.recovery_command == "project-mapping":
                intent = runtime / "project-mappings" / args.operation_id / "intent.json"
                result = ProjectMappingPublisher(vault, runtime).recover(
                    intent,
                    host_config_path=args.host_config,
                )
            else:
                result = OwnerReviewPublisher(vault, runtime).recover(
                    args.operation_id
                )
        rebuild_status(vault, runtime)
        print(
            json.dumps(
                {
                    "operation_id": args.operation_id,
                    "recovery": args.recovery_command,
                    "result": "reconciled",
                    "locator": (
                        result.relative_to(vault).as_posix()
                        if result.is_relative_to(vault)
                        else args.operation_id
                    ),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.command == "backup":
        if args.backup_command == "create":
            if configuration.vault.lifecycle.enabled:
                raise ValueError("disable lifecycle processing before creating a backup")
            with _runtime_lock(runtime / "locks" / "processor.lock"):
                summary = create_backup(
                    vault,
                    runtime,
                    recipient=args.recipient,
                    output_path=args.output,
                )
            result = {
                "backup": str(summary.output_path),
                "manifest_sha256": summary.manifest_sha256,
                "member_count": summary.member_count,
                "total_bytes": summary.total_bytes,
            }
        else:
            staged = decrypt_backup_to_staging(
                args.source,
                staging_path=args.destination,
                vault_root=vault,
                runtime_root=runtime,
                project_roots=tuple(mapping.normalized_root for mapping in configuration.host.project_root_mappings),
            )
            result = {"staged": str(staged), "live_state_changed": False}
        print(json.dumps(result, sort_keys=True))
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
        project_id = args.project_id
        if project_id is None and args.project_alias is None and args.scope is None:
            cwd = Path.cwd()
            workspace_root = next(
                (path for path in (cwd, *cwd.parents) if (path / ".git").exists()),
                cwd,
            )
            resolution = resolve_project(
                workspace_root,
                configuration.host.project_root_mappings,
                configuration.project_registry,
            )
            if resolution.status == "mapped":
                project_id = resolution.project_id
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
                project_id=project_id,
                project_alias=args.project_alias,
                scope=args.scope,
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
        if not configuration.vault.lifecycle.enabled:
            print(
                json.dumps(
                    {
                        "configured_interval_minutes": configuration.vault.cadence.catch_up_minutes,
                        "queued": 0,
                        "worker": "disabled",
                    },
                    sort_keys=True,
                )
            )
            return 0
        local_runtime = LocalRuntime(
            runtime, max_attempts=configuration.vault.retry.max_attempts
        )
        queued = 0
        for discovered_source in sorted(
            configuration.host.codex_rollout_store.rglob("*.jsonl")
        ):
            if queued >= args.max_sources:
                break
            try:
                source = _permitted_rollout_source(
                    discovered_source,
                    configuration.host.codex_rollout_store,
                )
                metadata = codex_session_metadata(source)
                conversation_id = metadata.get("id") or metadata.get("session_id")
                source_cwd = metadata.get("cwd")
                if (
                    not isinstance(conversation_id, str)
                    or not isinstance(source_cwd, str)
                    or not Path(source_cwd).is_absolute()
                ):
                    raise ValueError("invalid Codex session governance metadata")
                cwd = Path(source_cwd).resolve(strict=True)
                if not cwd.is_dir():
                    raise ValueError("Codex session cwd must be a directory")
                scope = resolve_lifecycle_scope(cwd, conversation_id, configuration)
                if scope.kind == "unassigned":
                    local_runtime.clear_discovery_failure(discovered_source)
                    continue
                start_offset = local_runtime.source_offset(
                    "codex-local", conversation_id, source
                )
                batch = normalize_codex_rollout(
                    source,
                    connector_id="codex-local",
                    start_offset=start_offset,
                )
                if batch.processed_through == start_offset:
                    local_runtime.clear_discovery_failure(discovered_source)
                    continue
                if not batch.turns:
                    local_runtime.advance_source_offset(
                        "codex-local",
                        conversation_id,
                        source,
                        batch.processed_through,
                    )
                    local_runtime.clear_discovery_failure(discovered_source)
                    continue
                local_runtime.enqueue_pointer(
                    trigger="catch-up",
                    connector_id=batch.connector_id,
                    conversation_id=batch.conversation_id,
                    source_path=source,
                    start_offset=start_offset,
                    scope_kind=scope.kind,
                    scope_id=scope.scope_id,
                    project_alias=scope.project_alias,
                )
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                local_runtime.record_discovery_failure(discovered_source)
                continue
            local_runtime.clear_discovery_failure(discovered_source)
            queued += 1
        result = _run_worker(
            configuration,
            args.reasoning_effort,
            max_items=args.max_sources,
            host_config_path=args.host_config,
        )
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
        result = _run_worker(
            configuration,
            args.reasoning_effort,
            max_items=args.max_items,
            host_config_path=args.host_config,
        )
        print(json.dumps({"worker": result}, sort_keys=True))
        return 0
    raise AssertionError("unreachable command")


def _permitted_rollout_source(source: Path, rollout_store: Path) -> Path:
    resolved = source.resolve()
    root = rollout_store.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(root):
        raise ValueError("Codex rollout source must be a file inside the configured store")
    return resolved


@contextmanager
def _runtime_lock(path: Path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _run_worker(
    configuration,
    reasoning_effort: str,
    *,
    max_items: int,
    host_config_path: Path,
) -> str:
    if max_items <= 0:
        raise ValueError("worker max_items must be positive")
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

    def should_process(item) -> bool:
        if item.trigger == "explicit-save":
            return True
        current = load_configuration(
            host_config_path,
            registered_provider_adapters={CODEX_CLI_ADAPTER},
        )
        return current.vault.lifecycle.enabled

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
            if item.source_kind == "rollout-pointer":
                local_runtime.advance_source_offset(
                    item.connector_id,
                    item.conversation_id,
                    Path(item.source_locator),
                    batch.processed_through,
                )
            return
        application.process(
            batch,
            scope=MemoryScope(item.scope_kind, item.scope_id, item.project_alias),
        )
        application.recover_and_rebuild()
        if item.source_kind == "rollout-pointer":
            local_runtime.advance_source_offset(
                item.connector_id,
                item.conversation_id,
                Path(item.source_locator),
                batch.processed_through,
            )

    retry_delay = 1.0
    while True:
        result = local_runtime.run_bounded(
            process,
            max_items=max_items,
            should_process=should_process,
        )
        if result != "retry":
            return result
        time.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 4.0)


if __name__ == "__main__":
    raise SystemExit(main())
