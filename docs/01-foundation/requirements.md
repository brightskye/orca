---
id: REQ-ORCA
title: Orca Requirements
document_type: requirements
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-29
last_verified_against_code: 2026-08-29
---

# Orca requirements

## Purpose

This document defines the stable externally meaningful obligations for Orca
Phase 1. Exact schemas, state machines, budgets, and algorithms belong to the
linked contracts.

## This document owns

- Phase 1 functional, authority, privacy, reliability, data, interaction,
  retrieval, and operational requirements.

## This document does not own

- Component structure, exact formats, implementation tasks, or future phases.

## Authority and safety

### REQ-AUTH-001 — Owner authority

The Owner must remain the final authority for memory meaning, visibility,
automation scope, and canonical acceptance.

### REQ-AUTH-002 — Artifact classification

Orca must keep Canonical Memory, transient evidence, provisional memory,
candidates, interaction artifacts, operational records, and rebuildable indexes
visibly distinct. Synchronization or retrieval ranking must not change authority.

### REQ-AUTH-003 — No automatic canonical apply

Phase 1 must not expose or perform automatic canonical mutation.

### REQ-SAFE-001 — Fail closed

Unknown or ambiguous event identity, privacy, scope, provenance, target,
replacement intent, schema, or cross-scope relationship must be excluded,
rejected, or preserved as explicitly unresolved rather than guessed.

## Capture and privacy

### REQ-CAP-001 — Positive event identification

The Codex Connector must accept only supported positively identified Owner and
permitted assistant records and exclude system, tool, reasoning, injected,
subagent, private, and ambiguous content.

### REQ-CAP-002 — Secret containment

Before spooling or semantic processing, Orca must apply explicit privacy
controls and versioned local credential redaction. It must reject generated
artifacts that still contain credential-like values before storage, indexing,
synchronization, recall, or exposure to another agent.

### REQ-CAP-003 — Direct-source processing

Orca must normalize supported records from the agent-owned source without
creating a second raw or merged transcript archive. Any retry spool must contain
only permitted redacted unprocessed evidence, remain private and local, and be
removed after successful publication and checkpointing.

## Processing and provenance

### REQ-PROC-001 — Bounded semantic input

Processor input and output must be deterministically bounded. New evidence must
be split or segmented rather than silently truncated, and irrelevant context
must not be loaded merely because it is available.

### REQ-PROC-002 — Proposal and validation seam

Semantic providers may propose meaning only. Deterministic Orca modules must
validate permitted values, sources, identity, scope, authority, paths, safety,
and lifecycle transitions before publication.

### REQ-PROC-003 — Retry-safe progress

Processing must be idempotent by stable source identity and policy-bound content
hash. Outputs and their durable Run Manifest must be published before the source
checkpoint advances; failure must leave enough permitted state for safe retry.

### REQ-AUD-001 — Durable provenance

Every successful semantic outcome, including abstention, must have an immutable
Run Manifest that binds exact input identities, output identities, policy and
provider context, hashes, status, and failure information required by the
provenance contract.

## Memory and scope

### REQ-MEM-001 — Controlled provisional memory

Phase 1 must produce only the accepted structural summaries and controlled
Typed Memory Record kinds. Logical memories must retain stable identity across
content, filename, status, and revision changes.

### REQ-MEM-002 — Explicit scope

Project, General, and Unassigned memory must remain distinct. Project identity
must not be inferred across uncertain roots or clones, and one project's memory
must not silently enter another project or General Memory.

### REQ-MEM-003 — Conflict preservation

A later trusted Owner position may supersede an earlier one only when it clearly
states or confirms the applicable replacement. Chronology alone is insufficient;
otherwise all incompatible positions must remain visible as an unresolved
Memory Conflict until explicit Owner resolution.

### REQ-CAND-001 — Knowledge Candidate boundary

Ordinary Knowledge Candidates must remain atomic noncanonical proposals,
excluded from ordinary recall and canonical authority until a separately
governed human or Curator disposition. Their exact schema and lifecycle must be
defined by an active Phase 1 specification rather than inferred from legacy
Curator behavior.

## Interaction behavior

### REQ-INT-001 — Scoped presentation evidence

Interaction learning must use contextual evidence about presentation behavior
only. It must abstain when required context is missing or ambiguous and must not
infer personality, emotion, motives, mental health, sensitive traits, or hidden
intent.

### REQ-INT-002 — Controlled durable guidance

A one-turn or session-only instruction must not silently become a durable
preference. Only applicable active profile entries may compile through fixed
versioned guidance templates; conflicting or unknown entries must produce no
improvised guidance.

## Recall and retrieval

### REQ-REC-001 — Explicit bounded recall

Semantic memory recall must occur only after explicit invocation. It must apply
hard authority, visibility, project, and status filters before ranking, return a
bounded set selected for the explicit request, label authority and provenance,
and abstain or request refinement rather than guess.

### REQ-REC-002 — Replaceable retrieval

The retrieval backend and its indexes must remain local, derived, disposable,
rebuildable, and non-authoritative. Index failure must not damage memory
artifacts or bypass Orca filters.

## Operation and recovery

### REQ-OPS-001 — Local configuration boundary

Vault paths, host mappings, credentials, private memory, runtime state, and
generated caches must remain in local configuration or runtime locations and
outside tracked source. The vault path must come from `config/host.yaml` or
`ORCA_VAULT_PATH`.

### REQ-OPS-002 — Private local runtime

Phase 1 processing must run in the authorized local WSL runtime and expose no
public memory, administration, curation, ingestion, scheduling, or canonical
apply interface.

### REQ-OPS-003 — Recoverable derived state

Disposable indexes and projections must be rebuildable from durable permitted
artifacts. Restart, replay, missing-index, interrupted-publication, and stale
derived-view cases must not corrupt Canonical Memory or silently lose accepted
provisional state.

## Quality

### REQ-QUAL-001 — Direct verification

Phase 1 acceptance must verify deterministic boundaries, replay, recovery,
privacy exclusions, secret containment, bounded recall, interaction lifecycle,
and zero automatic canonical mutation. Probabilistic model interpretation may be
evaluated but must not be presented as deterministic proof.

## Specification routes

- **Specification registry and ownership:** [Specification Index](../03-specifications/README.md)
- **Authority, privacy policy, canonical behavior, and local-data constraints:** [Memory System Contract](../governance/memory-system-contract.md)
- **Capture and privacy handoff:** [Capture Pipeline](../03-specifications/capture-pipeline.md)
- **Bounded semantic processing:** [Processing Pipeline](../03-specifications/processing-pipeline.md)
- **Memory identities, records, conflicts, layout, and naming:** [Memory Model](../03-specifications/memory-model.md)
- **Ordinary Knowledge Candidates:** [Knowledge Candidates](../03-specifications/knowledge-candidates.md)
- **Run Manifests and checkpoints:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Explicit bounded recall:** [Retrieval Contract](../03-specifications/retrieval-contract.md)
- **Interaction observations and profiles:** [Interaction Preferences](../03-specifications/interaction-preferences.md)
- **Compiled interaction guidance:** [Interaction Guidance](../03-specifications/interaction-guidance.md)
- **Host and vault configuration:** [Configuration](../03-specifications/configuration.md)
- **Current implementation state:** [Current Status](../STATUS.md)
- **Documentation map:** [Documentation Index](../README.md)
