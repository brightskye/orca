---
type: delivery-plan
status: accepted-baseline
created: 2026-08-25
updated: 2026-08-25
tags:
  - orca
  - agent-memory
  - delivery
  - architecture
---

# Orca Memory Delivery Plan

> [!WARNING]
> Archived all-phase delivery snapshot. Current phase direction is owned by the
> [Roadmap](../../project-record/roadmap.md).

## Purpose

Orca Memory is delivered in three usable phases. Each phase has one topology,
one operational flow, and explicit completion criteria. A later phase adds a
new sharing scope without changing the authority model established earlier.

```text
Phase 1: one local agent, one local vault
  -> Phase 2: multiple local agents, one local vault
  -> Phase 3: multiple agents and hosts, synchronized vault replicas
```

Canonical Orca remains authoritative in every phase. Conversation evidence,
shallow memory, candidates, and manifests remain noncanonical. Automatic
canonical apply is not required by any delivery phase and stays disabled until
it passes its separate governance gates.

## Common design

All phases use the same local-first processing path:

```text
authorized connector
  -> immutable conversation evidence
  -> one authorized processor
  -> shallow memory + knowledge candidates + run manifest
  -> rebuildable local retrieval index
  -> canonical-first recall
```

The implementation keeps five responsibilities behind small interfaces:

- **Capture module**: positively identify supported events, enforce privacy
  rules, normalize provenance, and publish immutable evidence.
- **Processor module**: select unprocessed evidence, invoke one semantic pass,
  validate proposals, and coordinate derived outputs and checkpoints.
- **Recall module**: retrieve canonical and permitted shallow memory, preserve
  authority labels, and enforce one result/token budget.
- **Governance module**: load configuration and decide applicable phase, host,
  connector, visibility, and privacy authority.
- **Storage module**: provide atomic publication, hashes, locks, checkpoints,
  manifests, and recovery; Phase 3 adds replica-conflict detection.

The selected retrieval implementation sits behind the recall/backend seam. Its
cache is local, rebuildable, and replaceable. Connector-specific parsing sits
behind the capture seam so adding agents does not change memory semantics.

## Phase 1 — Local Codex and local vault

### Outcome

Codex Desktop uses one Orca Memory runtime in WSL and reads and writes memory
artifacts through one locally configured Orca vault.

### Scope

Included:

- one Codex Desktop connector across its supported user sessions;
- one WSL Orca Memory runtime;
- one local vault path loaded from `config/host.yaml`;
- incremental Codex capture with file/offset checkpoints;
- positively identified owner messages and final user-visible Codex responses;
- private-session exclusion and hard-secret rejection;
- immutable conversation evidence and deterministic deduplication;
- local one-shot processing into agent shallow memory, knowledge candidates,
  and run manifests;
- canonical-first local recall through private MCP over stdio;
- local locks, checkpoints, recovery, and retrieval-index reconciliation;
- manual inspection of candidates; canonical apply remains disabled.

Excluded:

- additional agents or connector kinds;
- shared shallow memory between agents;
- Syncthing, VPS, remote processing, or processor transfer;
- native Windows runtime and public network interfaces;
- automatic canonical apply, source ingestion, interaction profiles, and
  retention automation.

### Architecture

```text
Codex Desktop
  -> WSL stdio MCP
  -> Codex connector / capture tick
  -> local vault/System/Orca Memory/conversations/codex/
  -> local processor tick
  -> local shallow/candidates/manifests
  -> rebuildable local retrieval index
  -> canonical-first recall to Codex
```

The WSL runtime is both the client-facing runtime and the sole authorized
processor. No host election, generation transfer, or synchronization logic is
needed.

### Operating flow

1. Codex completes an owner turn and a final user-visible response.
2. MCP startup or a local capture tick reads only new rollout bytes.
3. The connector positively identifies supported events and excludes protocol,
   hidden, injected, subagent, private-session, and secret-bearing content.
4. The capture module atomically publishes immutable JSONL evidence and advances
   its local checkpoint only after publication succeeds.
5. A local processor tick takes one OS lock and selects unprocessed evidence.
6. One minimized semantic pass proposes shallow memory and candidates.
7. Deterministic validation binds exact source IDs and hashes, commits all
   outputs for the chunk, and writes a run manifest and checkpoint.
8. The retrieval backend reconciles canonical Markdown and unexpired Codex
   shallow memory into its rebuildable local index.
9. Recall returns canonical results first, then Codex shallow results, with
   authority labels and a single context budget.

### Completion criteria

- Codex Desktop launches the WSL MCP runtime against the configured local vault.
- New, resumed, archived, partial-line, fork, and subagent rollout cases capture
  or fail closed as specified.
- Exact replay creates no duplicate evidence or semantic output.
- Private-session and hard-secret cases publish no content.
- A bounded real conversation is captured, processed, and recalled locally with
  correct provenance and no canonical mutation.
- Restart and cache rebuild preserve behavior from durable vault artifacts and
  checkpoints.

## Phase 2 — Multiple local agents and one local vault

### Outcome

Multiple authorized local agents share canonical and explicitly shared shallow
memory through one WSL runtime and one local vault while retaining agent-private
shallow isolation.

### Entry condition

Phase 1 is operational and its completion criteria pass without relying on
manual file repair.

### Scope

Included:

- multiple configured logical agents and connector identities on one machine;
- versioned connector adapters with separate evidence namespaces;
- one local processor and one rebuildable local retrieval index;
- agent-private and explicitly shared shallow memory;
- requester-aware recall and explicit cross-agent filters;
- per-agent capture checkpoints, provenance, replay protection, and failures;
- local candidate inspection across all configured agents.

Excluded:

- synchronized replicas, VPS processing, and remote-host agents;
- public MCP or administrative network surfaces;
- duplicate-processor coordination across hosts;
- automatic canonical apply and production retention deletion.

### Architecture

```text
Codex Desktop ----\
Codex CLI ---------+-> one WSL Orca Memory runtime -> one local vault
other local agent -/          |
                              +-> one local processor
                              +-> one local retrieval index
```

Each connector owns only its configured evidence namespace. The processor is
the sole writer of derived shared data. Agent identity and visibility are
configured facts, never inferred from paths or message prose.

### Operating flow

1. Each agent's connector captures supported events into its own namespace.
2. The local processor consumes all eligible namespaces under one lock.
3. Semantic proposals retain originating agent, project, topic, and visibility.
4. Deterministic policy routes shallow memory to the originating agent or to an
   explicitly justified shared scope.
5. The retrieval backend indexes canonical, shared shallow, and agent-private
   shallow data while preserving visibility metadata.
6. Recall returns canonical, matching shared, then requesting-agent shallow
   memory. Other-agent shallow memory requires an explicit filter.

### Completion criteria

- At least two local logical agents capture and recall through the same runtime
  and vault.
- Shared memory is visible to the intended agents and project/topic scopes.
- Agent-private shallow memory is hidden from other agents by default.
- Connector replay, failure, or malformed input cannot corrupt another
  namespace or duplicate processing.
- A bounded multi-agent canary shows correct identity, provenance, authority,
  and visibility with no canonical mutation.

## Phase 3 — Multiple agents and synchronized vault replicas

### Outcome

Local and remote agents share governed memory through synchronized Orca vault
replicas while exactly one authorized host performs semantic processing.

### Entry condition

Phase 2 is operational and agent identity, namespace isolation, visibility, and
replay behavior are proven locally.

### Scope

Included:

- one local and one VPS Orca replica synchronized through Syncthing;
- local and remote connector namespaces;
- host identity, processor generation, and one authorized processor;
- VPS-local Remote Agent export after its schema is proven read-only;
- synchronized noncanonical evidence, shallow memory, candidates, governance,
  and manifests;
- one rebuildable local retrieval index per host;
- Syncthing conflict containment, missed-window recovery, processor transfer,
  and deployment canaries;
- private host-local recall/capture interfaces for remote agents where
  explicitly authorized.

Excluded:

- treating Syncthing as a transaction manager or semantic merger;
- a public administrative memory interface;
- synchronization of credentials, local runtime state, caches, or before-images;
- unrestricted ChatGPT administration or automatic canonical apply;
- automated retention or physical deletion.

### Architecture

```text
local agents -> local runtime -> local Orca replica
                                   <-> Syncthing <-> VPS Orca replica
remote agents -> VPS runtime ---------------------/       |
                                                        authorized processor

each host: local retrieval index <- canonical + permitted shallow Markdown
```

Synchronized governance names one `processor.host_id` and generation. The
authorized processor performs semantic derivation and derived writes; every
connector may publish immutable evidence only to its own namespace.

### Operating flow

1. Local and remote connectors publish immutable evidence on their own host.
2. Syncthing replicates completed artifacts between replicas.
3. Each operation checks for conflict copies and compatible governance.
4. The host whose local `host_id` matches processor authority takes a local OS
   lock and processes the oldest due window.
5. It publishes derived artifacts, manifests, and checkpoints atomically.
6. Syncthing returns those artifacts to the other replica.
7. Each host reconciles its local retrieval index and serves local recall.

### Completion criteria

- Both replicas converge without synchronizing local configuration or runtime
  state.
- Duplicate-processor and stale-generation attempts fail closed.
- Conflict copies block only the affected artifact and its dependents.
- Remote Agent capture is proven against the deployed source schema.
- Missed windows, restart, replay, and processor transfer recover without
  duplicate semantic output.
- Local and remote recall return equivalent authority-labelled memory after
  synchronization converges.
- A bounded synchronized multi-agent canary passes before transitional workflow
  cutover.

## Work outside the three delivery phases

The following capabilities require their own later scope and evidence. They do
not block the three memory-sharing phases:

- automatic canonical apply by disposition category;
- general source ingestion beyond conversation capture;
- adaptive interaction profiles and confirmed-preference workflows;
- automated retention and physical deletion;
- a constrained ChatGPT adapter;
- a general settings or administration CLI;
- tuning providers, cadence, ranking, budgets, thresholds, and retention from
  real operating evidence.

## Change rule

Implementation proceeds one vertical slice at a time. A slice is complete only
when its public MCP or one-shot job behavior passes through an isolated vault,
its authority and failure behavior are explicit, and it does not depend on a
later phase's topology.
