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

> [!WARNING]
> Archived all-phase operations snapshot. Current executable procedures and
> unavailable interfaces are owned by the [Local Runbook](../../08-operations/runbook.md).

## Current status

The replacement service is not deployed. The existing manual implementation
and transitional Remote Agent nightly workflow remain operational authority
until a separately approved cutover. Delivery proceeds through the three stages
defined in [the delivery plan](delivery-plan.md): local Codex, multiple local
agents, then synchronized multi-host agents.

## Configuration model

The target uses two configuration surfaces:

- vault `orca-memory.yaml` for schema version, processing cadence, recall,
  connectors, provider selection, and privacy policy. It is local in
  Phases 1 and 2 and synchronized in Phase 3; Phase 3 adds processor authority;
- local project `config/host.yaml` for `host_id`, selected runtime, vault path, cache path, connector stores, and machine-local executable details. This file is excluded from Git.

Direct YAML editing is the initial settings interface. An explicitly invoked
agent skill may make the same validated edit. The service provides read-only
configuration validation and reloads applicable authority before each
operation. A general settings CLI is a future convenience, not an architectural
dependency.

## Installation model

Phase 1 installs one selected Git tag or exact commit as a standalone WSL Orca
project checkout. Phase 2 reuses that runtime for all configured local agents.
Phase 3 installs the same compatible release on the local and VPS hosts.
Launchers resolve the checked-out environment and preserve stdio and exit status
without implementing memory behavior.

- WSL uses a thin shell launcher.
- Codex Desktop may use a thin Windows command launcher only to enter WSL.
- Windows setup and Task Scheduler installation use PowerShell without
  implementing memory behavior.
- Phase 3 VPS jobs use the same Linux one-shot commands.

Production processing refuses a dirty service checkout. Development and fixture
commands may explicitly opt into development mode. Canonical apply remains
disabled throughout the three delivery phases.

## Scheduling

The runtime exposes one-shot commands for capture, processor tick, index
reconciliation, and configuration validation. Phase 3 adds synchronized
scheduled windows and processor-transfer checks. A permanent daemon is
unnecessary.

In Phases 1 and 2, Windows Task Scheduler invokes the WSL capture and processor
ticks. MCP startup also performs bounded capture and recall-cache catch-up. A
no-op processor tick performs no model call.

In Phase 3, the authorized processor uses cron to invoke a cheap processor tick
every 15 minutes. Synchronized configuration decides whether a semantic window
is due.

Missed windows run oldest-first, at most one per tick. Every window includes its
complete scheduled timestamp, timezone, cadence, configuration hash, and the
Phase 3 processor generation where applicable. Evidence checkpoints—not event
timestamps alone—decide what remains unprocessed.

## Capture scheduling

Phase 1 installs a separate deterministic incremental Codex capture tick. Phase
2 adds one checkpoint and namespace per configured local connector. Capture
does not violate the single semantic processor rule because connectors publish
only immutable evidence.

- Windows Task Scheduler invokes the WSL launcher.
- MCP startup also performs a bounded catch-up.

Phase 3 Remote Agent capture runs VPS-locally through a read-only Hermes
exporter once its schema and lifecycle contract are proven.

## Configuration changes

1. Edit vault or local YAML directly, or invoke an approved editing skill.
2. Parse and schema-validate without a model call.
3. Compute and report the resolved configuration hash.
4. Refuse affected operations on conflicts or incompatibility.
5. Reload applicable authority before the next operation.

Local host/runtime/path changes require restarting the affected MCP process or
scheduled job. Phase 3 synchronized policy changes do not require a permanent
service restart.

## Phase 3 processor transfer

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
5. reconcile or rebuild the local retrieval index;
6. restart MCP sessions or wait for the next scheduler tick.

Canonical apply stays disabled during processor upgrades. Executable rollback restores the previous compatible release and local rebuildable state; it never rolls synchronized Markdown backward automatically.

## Phase 3 conflict handling

Syncthing conflict copies are unresolved evidence. Automated writes stop for
the affected artifact and its dependents while unrelated namespaces may
continue. Configuration conflicts disable processing and any future canonical
apply. Human or Curator resolution preserves both variants and records the
selected disposition.

Temporary output is built and validated beneath the checkout's local `.runtime/`, then atomically published into the synchronized vault tree on the same filesystem. Readiness checks prove this filesystem condition and verify that project-local configuration and runtime state are not synchronized.

## Follow-on apply recovery

Automatic canonical apply is outside the three delivery phases. When separately
enabled, every apply records plan, policy, input, destination, before/after
hashes, result, and disposition. Content-addressed before-images remain
processor-local for 14 days. Rollback restores through a new governed
transaction and refuses automatic overwrite when the canonical destination has
changed since apply.

A VPS-local emergency switch may only reduce authority by disabling apply. It cannot enable apply when synchronized governance disables it. Suspended automation categories require Owner to resume.

## Delivery and cutover

### Phase 1

1. Implement and verify the local Codex capture-to-recall path in isolated
   fixtures.
2. Install the WSL runtime against the local vault with canonical apply
   disabled.
3. Run a bounded real-use canary and prove restart, replay, and cache rebuild.
4. Use the local path without disabling unrelated transitional Remote Agent
   operation.

### Phase 2

1. Add one local connector at a time behind the existing capture seam.
2. Verify agent identity, namespace isolation, shared visibility, and private
   shallow isolation.
3. Run a bounded local multi-agent canary before making shared recall routine.

### Phase 3

1. Install the same compatible release on the local and VPS hosts.
2. Create and verify Syncthing exclusions and synchronized governance.
3. Install the VPS processor scheduler with canonical apply disabled.
4. Verify capture, recall, conflict containment, cache reconciliation,
   provenance, missed windows, and processor transfer.
5. Run periodic processing in shadow mode and compare with the transitional
   workflow.
6. Explicitly disable the transitional workflow only after the synchronized
   multi-agent canary passes.
7. Archive the manual prototype only after verified cutover.

## Required canaries by phase

- Phase 1: Codex Desktop WSL, resume, fork, subagent, partial-line, archive,
  schema drift, final-visible response, compaction, replay, private-session,
  secret rejection, cache rebuild, and bounded canonical-first recall.
- Phase 2: every added local connector, agent identity, namespace isolation,
  shared/private visibility, cross-agent filter, connector failure, and bounded
  multi-agent recall.
- Phase 3: Remote Agent schema and lifecycle, source-class separation,
  Syncthing conflicts, immutable publication, duplicate processor detection,
  missed-window recovery, processor transfer, synchronized cache convergence,
  and equivalent recall after convergence.
- Follow-on automatic apply: policy reload, preconditions, atomic failure,
  before-image recovery, stale-plan refusal, and newer-human-edit protection.
- Follow-on retention: expiry, source tombstones, disposition preconditions,
  forced deletion, and physical-deletion safety.

## Deferred tuning

Provider selection, model, batching, chunk size, cadence, recall ranking, context budget, behavior weights, thresholds, and automation promotion metrics begin with conservative recommended defaults. Review them after real operating data exists rather than freezing speculative execution detail now.

A future CLI may include status, configuration inspection/editing, evidence
display, category suspension/resumption, and promotion recommendations. It
remains optional convenience over the file contracts and does not block the
three delivery phases.
