---
id: GOVERNANCE-MEMORY-SYSTEM
title: Orca Memory System Governance Contract
document_type: specification
status: accepted
authority: normative
implementation_status: implemented
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-31
last_verified_against_code: 2026-08-31
related:
  - REQ-ORCA
  - ARCH-OVERVIEW
  - ADR-0011
---

# Orca memory system governance contract

## Purpose

Define the Phase 1 authority, privacy, trust, and canonical-mutation invariants
that apply across every Orca module and interface.

## This document owns

- Memory authority classification and Owner control.
- Cross-module privacy and trust invariants.
- The Phase 1 prohibition on automatic or agent-initiated Canonical Memory
  mutation.

## This document does not own

- Event eligibility, schemas, budgets, lifecycles, filenames, publication
  mechanics, retrieval ranking, configuration fields, or operator procedures.
- Implementation progress or future-phase behavior.

## Authority model

- The Owner is the final authority for memory meaning, visibility, automation
  scope, and canonical acceptance.
- Canonical Memory is Owner-accepted durable knowledge in the configured
  canonical vault folders.
- Conversation Evidence, Shallow Memory, Knowledge Candidates, Interaction
  Observations, Adaptive Interaction Profiles, Run Manifests, checkpoints, and
  retrieval indexes are noncanonical.
- A Confirmed Interaction Preference becomes canonical only through explicit
  Owner confirmation and the separately governed human acceptance path.
- Semantic-provider output proposes meaning only. A provider, agent, retrieval
  adapter, synchronization tool, path, filename, score, or arrival order cannot
  grant authority.
- Every recalled result remains visibly authority-labelled.

## Canonical mutation boundary

- Phase 1 exposes and performs no automatic or agent-initiated Canonical Memory
  mutation.
- Candidate creation, review, or `approved-for-manual-apply` disposition does
  not change authority and does not write a canonical target.
- Canonical changes require a separate governed human action outside the Phase
  1 automatic processing and recall loop.
- Any future canonical-apply interface requires an accepted design change with
  explicit authorization, validation, audit, recovery, and quality obligations.

## Privacy and trust invariants

- Agent-owned conversation history remains an external source; Orca creates no
  second raw or merged transcript archive.
- Explicitly private or ineligible content reaches no semantic provider and
  publishes no memory content.
- Secret Containment reduces further propagation of credential values already
  disclosed to an agent-owned source; it does not claim to undo the original
  disclosure.
- Semantic output and retrieval ranking are untrusted until the owning
  deterministic Orca interface validates their permitted fields and effects.
- Unknown or ambiguous source identity, privacy, scope, provenance, target,
  replacement intent, schema, or cross-scope relationship fails closed or
  remains explicitly unresolved.
- Generated content containing credential-like material is rejected before
  storage, indexing, synchronization, recall, or exposure to another agent.

## Local operation boundary

- Phase 1 runs in one authorized local WSL runtime and exposes no public memory,
  administration, ingestion, scheduling, or canonical-apply service.
- The project checkout, configured vault, agent-owned source, and local runtime
  are separate locations with separate ownership and publication rules.
- Host configuration, credentials, raw sessions, retry material, checkpoints,
  locks, queues, caches, and disposable indexes remain local, private, and
  outside tracked source. Host-local runtime state also remains outside the
  configured vault.
- Retrieval and other disposable projections remain rebuildable and carry no
  memory authority.

## Exact behavior owners

| Subject | Canonical owner |
|---|---|
| Stable project obligations | [Requirements](../01-foundation/requirements.md) |
| Component and trust structure | [Architecture Overview](../02-architecture/overview.md) and [Security and Trust](../02-architecture/security-and-trust.md) |
| Capture, privacy filtering, redaction, and retry handoff | [Capture Pipeline](../03-specifications/capture-pipeline.md) |
| Bounded processing and proposal validation | [Processing Pipeline](../03-specifications/processing-pipeline.md) |
| Memory records, summaries, conflicts, identity, and placement | [Memory Model](../03-specifications/memory-model.md) |
| Ordinary candidate lifecycle and disposition | [Knowledge Candidates](../03-specifications/knowledge-candidates.md) |
| Run Manifests, deduplication, and checkpoints | [Provenance Ledger](../03-specifications/provenance-ledger.md) |
| Interaction observations, profiles, and guidance | [Interaction Preferences](../03-specifications/interaction-preferences.md) and [Interaction Guidance](../03-specifications/interaction-guidance.md) |
| Explicit Recall and retrieval projections | [Retrieval Contract](../03-specifications/retrieval-contract.md) |
| Host and vault configuration | [Configuration](../03-specifications/configuration.md) |
| Executable local procedures | [Phase 1 Local Runbook](../08-operations/runbook.md) |

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Project scope:** [Project Charter](../01-foundation/project-charter.md)
- **Required behavior:** [Requirements](../01-foundation/requirements.md)
- **Current architecture:** [Architecture Overview](../02-architecture/overview.md)
- **Current implementation state:** [Current Status](../STATUS.md)
- **Canonical-apply rationale:** [ADR-0011](../04-decisions/0011-keep-automatic-canonical-apply-disabled.md)
