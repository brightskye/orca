---
id: ARCH-OVERVIEW
title: Orca Architecture
document_type: architecture
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-09-05
related:
  - CHARTER-ORCA
  - REQ-ORCA
---

# Orca architecture

## Purpose

This document is the accepted primary system-design entry point for Orca Phase
1. It describes boundaries, components, responsibilities, dependencies, and
high-level flows without owning exact contracts or implementation status.

## This document owns

- Phase 1 system boundaries, architectural principles, and component roles.
- The high-level relationship between runtime, data, security, deployment, and
  integration views.

## This document does not own

- Exact schemas, budgets, lifecycle transitions, implementation progress, or
  future-phase commitment.

## Scope and boundaries

Phase 1 provides continuity across sessions within one harness, Codex. It
connects Codex Desktop to one local WSL runtime and one configured Orca vault.
Distilled conversation history remains in the existing designated vault area;
the LLM wiki's broader workflows are a separate later review. The project checkout owns code, tests, and technical
documentation. The vault owns memory artifacts. Agent-owned conversation
history remains outside Orca ownership, and local runtime state carries no
memory authority.

Canonical Memory remains Owner-accepted durable knowledge. Orca may derive
noncanonical evidence, working memory, candidates, interaction context,
provenance records, and disposable indexes, but it cannot silently promote any
of them to canonical authority.

## Architecture principles

- The Owner is final authority.
- Semantic providers propose meaning; deterministic Orca modules validate,
  identify, scope, place, and publish permitted results.
- Source reading, semantic processing, storage, governance, and retrieval have
  separate responsibilities.
- The configured vault is authoritative for memory artifacts; indexes and local
  projections are rebuildable.
- Processing is bounded, provenance-preserving, fail-closed, and safe to retry.
- Retrieval and synchronization products remain replaceable and non-authoritative.
- Automatic canonical apply is disabled and unexposed.

## System context

The [system-context diagram](diagrams/system-context.mmd) shows the Phase 1
design boundary. It represents accepted intended architecture, not a claim that
every component is implemented; see [Current Status](../project-record/current.md).

```text
Codex-owned conversation
  -> Connector and privacy boundary
  -> local Processor and Governance
  -> Storage
  -> configured Orca vault
  -> rebuildable retrieval adapter
  -> scoped Recall (Owner- or agent-initiated)
  -> Codex
```

## Major components

| Component | Responsibility | Must not do |
|---|---|---|
| Codex Connector | Positively identify, filter, redact, and normalize permitted source records | Infer memory meaning or accept ambiguous events |
| Processor | Build bounded provider input and validate controlled semantic proposals | Assign authority, identity, paths, or final storage timestamps |
| Semantic provider | Propose summaries, records, candidates, and interaction observations | Grant authority or publish artifacts |
| Governance | Resolve permitted scope, privacy, visibility, configuration, and policy constraints | Guess uncertain ownership or replacement intent |
| Storage | Assign controlled identities and locations, validate complete artifacts, publish recoverably, and advance progress last | Interpret conversational meaning |
| Retrieval adapter | Index and rank already permitted projections | Establish authority, scope, status, or provenance |
| Recall | Return bounded continuation context for Owner- or agent-initiated scoped requests | Broaden scope or infer hidden motives |
| AgentCairn adapter | Supply a replaceable prevalidated distillation/retrieval seam where permitted | Become Orca's authority or enable its native canonical pipeline |

## Allowed dependencies

- Connector output enters Processor only after deterministic privacy and source
  validation.
- Processor may call one replaceable semantic provider, then passes only
  validated logical proposals to Governance and Storage.
- Storage owns physical placement and publication; callers supply logical
  identity, scope, kind, and subject rather than arbitrary paths.
- Retrieval indexes deterministic permitted projections from current Markdown;
  Recall treats adapter results as candidates subject to Orca filters.
- No adapter or model may bypass Governance or write Canonical Memory.

## Data ownership summary

- The Owner and configured canonical folders own Canonical Memory.
- Agent-owned systems own source conversations; Orca receives only permitted
  transient selections.
- The configured vault owns noncanonical memory records, candidates, interaction
  profiles, and Run Manifests.
- The local runtime owns checkpoints, locks, queues, retry spools, publication
  intents and staged post-images, receipts, host mappings, and disposable
  indexes.

See [Data Architecture](data.md) for lifecycle and storage classes.

## Runtime

Phase 1 has one authorized local processor. Hooks perform bounded handoff;
semantic work runs in a one-shot worker under a local lock. Catch-up discovers
eligible missed work and reuses that worker. Scheduling belongs to the
[Runbook](../operations/runbook.md); no permanent daemon is required.

### Execution paths

| Context | Responsibility |
|---|---|
| Project setup | Establish a confirmed identity and recoverable local mapping |
| Session start | Supply scoped guidance, an attention reminder, and a scoped recall command |
| Explicit Recall | Return permitted memory for a specific request |
| Lifecycle hook or explicit save | Hand eligible source work to the private runtime |
| Worker and catch-up | Process queued work and discover eligible missed work |
| Owner review | Apply an explicit candidate or conflict disposition |
| Recovery | Complete a fixed interrupted operation when recorded state matches |
| Backup | Create and verify an encrypted copy and expose separate staging |
| Reconciliation | Rebuild disposable projections from their owning artifacts |

Startup uses interaction profiles and supplies a scoped recall command without
reading conversation memory. The Owner may ask for recall, or Codex may invoke
it when earlier context is useful to the discussion. Attention projects unresolved source states and routes the
Owner to the responsible workflow. Viewing status does not repair source state.
Exact coordination belongs to [Runtime](../specifications/runtime.md), guidance
to [Interaction Guidance](../specifications/interaction-guidance.md), and recall
to [Retrieval](../specifications/retrieval.md).

### Processing flow

1. A hook or explicit invocation identifies eligible source work.
2. Connector filtering and local handoff preserve permitted evidence.
3. The worker checks durable provenance and builds bounded provider input.
4. The provider proposes meaning; Processor and Governance validate it.
5. Storage prepares a fixed publication intent and publishes artifacts.
6. A Run Manifest records the run before the checkpoint advances.
7. Derived projections reconcile for later explicit Recall.

The [processing diagram](diagrams/processing-flow.mmd) shows these relationships.
[Capture](../specifications/capture.md), [Processing](../specifications/processing.md),
and [Provenance](../specifications/provenance.md) own the exact rules.

### Recovery and failure containment

Publication is recoverable rather than one atomic transaction. Storage records
a fixed plan before final mutation. Matching state can complete without another
semantic call; conflicting state requires human repair.

Project registration and Owner review use separate intents because their
identities and outcomes differ. Their contracts belong to
[Configuration](../specifications/configuration.md),
[Memory](../specifications/memory.md), and
[Knowledge Candidates](../specifications/knowledge-candidates.md).

Invalid source stops at capture; invalid proposals stop before publication.
Stale indexes and summaries remain excluded until rebuilt, while valid source
records remain intact. Optional caches remain disposable.

Backup is a separate maintenance path. A recovery copy gains no memory
authority, and decrypted staging stays separate from live state.
[Backup](../specifications/backup.md) owns the interface; the
[Runbook](../operations/runbook.md) owns operating and recovery procedures.

## Security and trust

Orca protects personal memory, agent conversation content and references,
credentials, private-session content, host paths, identity mappings, and the
integrity of provenance, recovery, scope, and authority.

The Owner has final authority. Codex supplies source and consumes context;
semantic providers propose meaning; retrieval adapters rank candidates.
None can grant durable memory authority. Connector, Governance, and Storage
enforce their assigned boundaries. The local operator and host protect files,
credentials, configuration, and process access.

### Trust boundaries

1. Agent-owned source crosses into Connector-controlled normalization.
2. Locally filtered evidence crosses into the semantic-provider request.
3. Untrusted provider output crosses into deterministic validation.
4. Storage publishes governed artifacts into approved vault locations.
5. Permitted vault projections cross into disposable retrieval indexes.
6. Public checkout, private vault, and host-local runtime occupy separate stores.

[Memory System Contract](../specifications/memory-system-contract.md) owns exact
privacy and authority invariants. Capture owns admission and redaction;
Processing owns provider input and output validation. These are intended
boundaries; [Current](../project-record/current.md) owns known enforcement gaps.

### Threats and mitigation responsibilities

| Threat | Architectural response |
|---|---|
| Injected content masquerades as Owner evidence | Connector controls event classification |
| Private content propagates beyond permitted use | Local privacy gate before provider handoff; output validation before publication |
| Model output assigns authority, scope, or paths | Governance and Storage retain those responsibilities |
| Cross-project retrieval leaks | Orca owns filtering around the replaceable adapter |
| Replay or interrupted writes corrupt memory | Durable provenance and fixed recovery plans |
| Runtime or cache content enters public storage | Separate checkout, vault, and host-local boundaries |
| A future replica gains authority by arrival order | Synchronization cannot establish authority or merge meaning |

Phase 1 relies on the local Owner and host boundary and exposes no public
service. Future remote hosts or MCP surfaces require an explicit transport,
authorization, and threat model.

Run Manifests support reference-based audit without a second raw conversation
archive. [Provenance](../specifications/provenance.md) owns receipt semantics.
Vulnerability reporting belongs to the root [Security policy](../../SECURITY.md).

Residual risks include source-format drift, incomplete credential detection,
disclosures already present in agent history, operator misconfiguration,
filesystem weaknesses, and semantic errors that structural validation cannot
eliminate. [Current](../project-record/current.md) records findings and disposition.

## Deployment summary

The intended Phase 1 deployment is local: Codex Desktop invokes a WSL runtime
that reads its supported local source and uses a configured vault. No public
service is part of this topology. [Current](../project-record/current.md) owns
deployment status and readiness limitations; [Setup](../operations/setup.md)
owns installation and activation.

Phases 2 and 3 are candidate directions only. See [Deployment
Architecture](deployment.md) and the [Roadmap](../project-record/roadmap.md).

## Design boundaries

- Canonical automatic apply remains disabled and unexposed.
- Codex's rollout format is not a stable public contract; unsupported format
  changes fail closed pending isolated verification.
- Scheduling the supported periodic catch-up command is an external operator
  concern; the architecture requires no daemon or OS scheduler.
- Superseded architecture sources are preserved under `docs/archive/` and do
  not define current behavior.

## Detailed design map

- [Deployment Architecture](deployment.md)
- [Data Architecture](data.md)
- [Integration Architecture](integrations.md)
- [Specification Index](../specifications/README.md)
- [Runtime coordination](../specifications/runtime.md)
- [Backup](../specifications/backup.md)
- [Memory System Contract](../specifications/memory-system-contract.md)
- [Capture Pipeline](../specifications/capture.md)
- [Processing Pipeline](../specifications/processing.md)
- [Memory Model](../specifications/memory.md)
- [Provenance Ledger](../specifications/provenance.md)
- [Retrieval Contract](../specifications/retrieval.md)
- [Interaction Preferences](../specifications/interaction-preferences.md)
- [Interaction Guidance](../specifications/interaction-guidance.md)
- [Decision Registry](../project-record/decisions/README.md)

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Required by:** [Requirements](../specifications/requirements.md)
- **Roadmap phase:** [Phase 1](../project-record/roadmap.md#phase-1)
- **Implementation state:** [Current Status](../project-record/current.md)
