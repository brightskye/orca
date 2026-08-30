---
id: ARCH-OVERVIEW
title: Orca Architecture Overview
document_type: architecture
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-29
related:
  - CHARTER-ORCA
  - REQ-ORCA
---

# Orca architecture overview

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

Phase 1 connects one Codex Desktop agent to one local WSL runtime and one
configured Orca vault. The project checkout owns code, tests, and technical
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
every component is implemented; see [Current Status](../STATUS.md).

```text
Codex-owned conversation
  -> Connector and privacy boundary
  -> local Processor and Governance
  -> Storage
  -> configured Orca vault
  -> rebuildable retrieval adapter
  -> explicit Recall
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
| Recall | Apply hard filters, relevance selection, budgets, and authority labels for explicit requests | Perform automatic semantic recall or infer hidden intent |
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

See [Data Architecture](data-architecture.md) for lifecycle and storage classes.

## Primary runtime flows

- Session start loads only applicable bounded interaction guidance.
- Explicit recall retrieves permitted authority-labelled memory.
- `PreCompact`, `SessionEnd`, or explicit save queues bounded local processing.
- The worker deduplicates source evidence, validates semantic proposals,
  prepares one fixed local publication intent, publishes outputs and a Run
  Manifest, then advances the checkpoint last.
- Retrieval reconciliation projects and indexes current permitted Markdown.

See [Runtime Architecture](runtime.md) and the
[processing-flow diagram](diagrams/processing-flow.mmd).

## Failure boundaries

- Ambiguous, private, malformed, cross-scope, unsafe, or invalid input fails
  closed before publication.
- Semantic or validation failure leaves the checkpoint unchanged for retry.
- Publication is recoverable rather than transactionally atomic: a complete
  private local intent is durable before artifact mutation, then artifacts, the
  Run Manifest, and the checkpoint publish in order. Safe matching state
  completes without another semantic call; mismatch fails closed for human
  repair.
- Index or derived-summary failure cannot roll back authoritative source records;
  stale projections are excluded until rebuilt.

## Trust boundaries

The Owner is trusted for authority and explicit disposition. Agent events,
semantic-provider output, retrieval ranking, synchronized copies, and external
tools are not trusted to establish memory truth. The local project checkout,
runtime, vault, provider boundary, and any future synchronized host are distinct
security zones.

See [Security and Trust](security-and-trust.md).

## Deployment summary

The intended Phase 1 deployment is local: Codex Desktop invokes a WSL runtime
that reads its supported local source and uses a configured vault. No public
service is exposed. The runtime is not yet deployed for routine use.

Phases 2 and 3 are candidate directions only. See [Deployment
Architecture](deployment.md) and the [Roadmap](../ROADMAP.md).

## Known limitations

- Current code implements only the initial Owner-turn,
  Continuation-Summary/Manifest/checkpoint slice.
- Assistant context, complete typed memory, candidates, interaction behavior,
  recall, lifecycle wiring, configuration, and deployment remain incomplete.
- Ordinary Knowledge Candidate behavior has an accepted specification; its
  schema and lifecycle remain unimplemented.
- Superseded architecture sources are preserved under `docs/_archive/` and do
  not define current behavior.

## Architectural risks

- Agent source formats may drift without a stable public contract.
- Privacy mistakes can propagate personal conversation content or secrets.
- Model output can appear authoritative unless deterministic boundaries remain
  explicit.
- Partial filesystem publication and stale indexes require careful recovery.
- Later synchronization could create authority or consistency confusion if host
  state and vault artifacts are not separated.

## Detailed design map

- [Runtime Architecture](runtime.md)
- [Deployment Architecture](deployment.md)
- [Data Architecture](data-architecture.md)
- [Security and Trust](security-and-trust.md)
- [Integration Architecture](integration-architecture.md)
- [Specification Index](../03-specifications/README.md)
- [Memory System Contract](../governance/memory-system-contract.md)
- [Capture Pipeline](../03-specifications/capture-pipeline.md)
- [Processing Pipeline](../03-specifications/processing-pipeline.md)
- [Memory Model](../03-specifications/memory-model.md)
- [Provenance Ledger](../03-specifications/provenance-ledger.md)
- [Retrieval Contract](../03-specifications/retrieval-contract.md)
- [Interaction Preferences](../03-specifications/interaction-preferences.md)
- [Interaction Guidance](../03-specifications/interaction-guidance.md)
- [Decision Registry](../04-decisions/README.md)

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Required by:** [Requirements](../01-foundation/requirements.md)
- **Roadmap phase:** [Phase 1](../ROADMAP.md#phase-1)
- **Implementation state:** [Current Status](../STATUS.md)
