---
type: operations
status: accepted-baseline
created: 2026-08-25
updated: 2026-08-25
tags:
  - orca
  - agent-memory
  - operations
---

# Orca Memory Operations

## Current status

The replacement service is not deployed. The existing manual implementation and transitional Remote Agent nightly workflow remain operational authority until a separately approved cutover. This document defines the intended operating model and readiness evidence.

## Configuration model

The target uses two configuration surfaces:

- synchronized `orca-memory.yaml` for schema version, processor authority, processing cadence, recall, retention, automation, connectors, provider selection, and privacy policy;
- local project `config/host.yaml` for `host_id`, selected runtime, vault path, cache path, connector stores, and machine-local executable details. This file is excluded from Git.

Direct YAML editing is the initial settings interface. An explicitly invoked agent skill may make the same validated edit. The service provides read-only configuration validation and reloads synchronized authority before each operation or apply batch. A general settings CLI is documented as a future convenience, not an architectural dependency.

## Installation model

Every directly connected host installs the same selected Git tag or exact commit as a standalone Orca project checkout. Launchers resolve the checked-out environment and preserve stdio and exit status without implementing memory behavior.

- Linux/WSL uses a thin shell launcher.
- Windows MCP uses a thin CMD launcher.
- Windows setup, updates, and Task Scheduler installation use PowerShell.

Production processing and apply refuse a dirty service checkout. Development and fixture commands may explicitly opt into development mode.

## Scheduling

The processor exposes one-shot commands for capture, processor tick, nightly processing, retention, index reconciliation, and configuration validation. A permanent daemon is unnecessary until a future ChatGPT adapter requires one.

The initial VPS scheduler is cron. It invokes a cheap processor tick every 15 minutes. The synchronized semantic schedule decides whether work is due; a no-op tick performs no model call. A Windows processor uses Task Scheduler and may invoke either native Windows or WSL execution.

Missed windows run oldest-first, at most one per tick. Every window includes its complete scheduled timestamp, timezone, cadence, configuration hash, and processor generation. Evidence checkpoints—not event timestamps alone—decide what remains unprocessed.

## Capture scheduling

The selected local runtime installs a separate capture tick. It performs deterministic incremental Codex capture only and does not violate the single semantic processor rule.

- WSL selection: Windows Task Scheduler invokes the WSL launcher.
- Native Windows selection: Task Scheduler invokes the native launcher.
- MCP startup also performs a bounded catch-up.

Remote Agent capture runs VPS-locally through a read-only Hermes exporter once its schema and lifecycle contract are proven.

## Configuration changes

1. Edit synchronized or local YAML directly, or invoke an approved editing skill.
2. Parse and schema-validate without a model call.
3. Compute and report the resolved configuration hash.
4. Refuse affected operations on conflicts or incompatibility.
5. Reload synchronized authority before the next operation.

Local host/runtime/path changes require restarting the affected MCP process or scheduled job. Synchronized policy changes do not require a permanent service restart.

## Processor transfer

1. Install and validate the same compatible service release on the new host.
2. Install its scheduler disabled.
3. Change synchronized `processor.host_id` and increment processor generation.
4. Synchronize and validate both replicas.
5. Run a dry-run and duplicate-processor check on the new host.
6. Enable the new scheduler and retire the old scheduler.

The old host refuses processor-only commands after it receives the new authority. Run manifests from earlier processor generations remain history and do not block the new generation.

## Release update and rollback

1. Allow active MCP work to finish.
2. Fetch and check out the explicitly selected release.
3. Update the local environment.
4. validate configuration and isolated fixtures;
5. reconcile or rebuild the local Cairn cache;
6. restart MCP sessions or wait for the next scheduler tick.

Canonical apply stays disabled during processor upgrades. Executable rollback restores the previous compatible release and local rebuildable state; it never rolls synchronized Markdown backward automatically.

## Conflict handling

Syncthing conflict copies are unresolved evidence. Automated writes stop for the affected artifact and its dependents while unrelated namespaces may continue. Configuration conflicts disable all canonical apply. Human or Curator resolution preserves both variants and records the selected disposition.

Temporary output is built and validated beneath the checkout's local `.runtime/`, then atomically published into the synchronized vault tree on the same filesystem. Readiness checks prove this filesystem condition and verify that project-local configuration and runtime state are not synchronized.

## Apply recovery

Every apply records plan, policy, input, destination, before/after hashes, result, and disposition. Content-addressed before-images remain processor-local for 14 days. Rollback restores through a new governed transaction and refuses automatic overwrite when the canonical destination has changed since apply.

A VPS-local emergency switch may only reduce authority by disabling apply. It cannot enable apply when synchronized governance disables it. Suspended automation categories require Owner to resume.

## Initial cutover

1. Create structural service modules and synchronized schemas without changing production flows.
2. Install and verify the selected local client runtime.
3. Install the VPS processor with canonical apply disabled.
4. Verify Syncthing exclusions, capture, recall, cache reconciliation, and provenance.
5. Run periodic processing in shadow mode against bounded evidence.
6. Compare with the transitional workflow and resolve material gaps.
7. Explicitly disable the transitional workflow.
8. Enable the new processor as the sole periodic path.
9. Keep canonical apply disabled until its independent graduation gates pass.
10. Archive the old manual source tree only after verified cutover.

## Required canaries

- Codex Desktop Windows, Desktop WSL, CLI WSL, resume, fork, subagent, partial-line, archive, and schema-drift capture.
- Final-visible-agent-response classification and compaction behavior.
- Remote Agent/Hermes schema snapshot, turn lifecycle, assistant visibility, profile isolation, source-class separation, replay, mutation, failure, and atomic publication.
- Syncthing conflict containment, immutable publication, duplicate processor detection, missed-window recovery, and processor transfer.
- Canonical-first recall, shared/private visibility, stale-cache behavior, and bounded context.
- Apply preconditions, policy reload, atomic failure, before-image recovery, stale-plan refusal, and newer-human-edit protection.

## Deferred tuning

Provider selection, model, batching, chunk size, cadence, recall ranking, context budget, behavior weights, thresholds, and automation promotion metrics begin with conservative recommended defaults. Review them after real operating data exists rather than freezing speculative execution detail now.

The future CLI proposal may include status, configuration inspection/editing, evidence display, category suspension/resumption, and promotion recommendations. It remains optional convenience over the file contracts.
