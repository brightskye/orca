---
id: SPEC-INDEX
title: Orca Specifications
document_type: documentation-index
status: accepted
authority: informative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
---

# Orca specifications

## Purpose

This document registers the exact Phase 1 behavior owners and defines the seam
between specifications. It does not define behavior itself.

## This document owns

- Specification navigation, responsibility, and overlap rules.

## This document does not own

- Requirements, architecture, implementation progress, or exact behavior.

## Specification boundaries

Each specification defines one module interface: the invariants, ordering,
errors, configuration, and performance constraints callers or adapters must know.
Implementation complexity stays behind that interface. A specification must link
to another owner rather than copying its schemas or state machines.

| Subject | Canonical specification |
|---|---|
| Capture and privacy pipeline | [Capture Pipeline](capture.md) |
| Bounded semantic processing | [Processing Pipeline](processing.md) |
| Memory records, summaries, conflicts, layout, and relationships | [Memory Model](memory.md) |
| Ordinary Knowledge Candidates | [Knowledge Candidates](knowledge-candidates.md) |
| Run Manifests and checkpoints | [Provenance Ledger](provenance.md) |
| Recall and retrieval projections | [Retrieval Contract](retrieval.md) |
| Interaction observations and profiles | [Interaction Preferences](interaction-preferences.md) |
| Exact compiled interaction guidance | [Interaction Guidance](interaction-guidance.md) |
| Host and vault configuration | [Configuration](configuration.md) |
| Lifecycle coordination, worker, catch-up, attention, and reminders | [Runtime](runtime.md) |
| Backup membership, verification, and staging | [Backup](backup.md) |

## Overlap rules

- Capture owns source eligibility, privacy filtering, redaction, normalized
  source identity, and retry handoff; processing consumes its permitted output.
- Processing owns bounded context assembly and proposal validation; memory,
  candidate, provenance, and interaction specifications own output formats and
  lifecycle.
- Memory Model owns Typed Memory Records, structural summaries, conflicts,
  filename/layout policy, and validated relationships.
- Knowledge Candidates owns only ordinary candidates; Conflict Overflow
  Candidates remain part of the Memory Model.
- Provenance Ledger owns Run Manifest and checkpoint fields, deduplication
  meaning, receipt ordering, and repair semantics.
- Retrieval owns requests, hard filters, projections, ranking, budgets, and
  result shape; a retrieval adapter is replaceable and non-authoritative.
- Interaction Preferences owns evidence and profile state; Interaction Guidance
  owns only deterministic compiled strings and selection.
- Configuration owns sources, fields, validation, and precedence. Each
  behavioral specification owns its applicable default values; the runbook owns
  executable operational procedures.
- Runtime owns coordination and attention; it delegates source admission to
  Capture and publication semantics to Provenance.
- Backup owns the recovery-copy interface; Operations owns how to invoke it.

## Authority state

Every specification in this registry is accepted and normative. Historical
source contracts under `docs/archive/` retain migration evidence only and do
not define current behavior.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Requirements:** [Requirements](requirements.md)
- **Architecture:** [Architecture Overview](../architecture/README.md)
- **Current implementation state:** [Current Status](../project-record/current.md)
