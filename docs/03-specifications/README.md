---
id: SPEC-INDEX
title: Orca Specification Index
document_type: documentation-index
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
---

# Orca specification index

## Purpose

This document registers the exact Phase 1 behavior owners and defines the seam
between specifications. It does not define behavior itself.

## This document owns

- Specification navigation, responsibility, migration status, and overlap rules.

## This document does not own

- Requirements, architecture, implementation progress, or exact behavior.

## Specification boundaries

Each specification defines one module interface: the invariants, ordering,
errors, configuration, and performance constraints callers or adapters must know.
Implementation complexity stays behind that interface. A specification must link
to another owner rather than copying its schemas or state machines.

| Subject | Specification | Migration state | Current exact owner |
|---|---|---|---|
| Capture and privacy pipeline | [Capture Pipeline](capture-pipeline.md) | Accepted extracted specification | [Capture Pipeline](capture-pipeline.md) |
| Bounded semantic processing | [Processing Pipeline](processing-pipeline.md) | Accepted extracted specification | [Processing Pipeline](processing-pipeline.md) |
| Memory records, summaries, conflicts, layout, and relationships | [Memory Model](memory-model.md) | Accepted direct migration | [Memory Model](memory-model.md) |
| Ordinary Knowledge Candidates | [Knowledge Candidates](knowledge-candidates.md) | Accepted new contract | [Knowledge Candidates](knowledge-candidates.md) |
| Run Manifests and checkpoints | [Provenance Ledger](provenance-ledger.md) | Accepted direct migration | [Provenance Ledger](provenance-ledger.md) |
| Recall and retrieval projections | [Retrieval Contract](retrieval-contract.md) | Accepted extracted specification | [Retrieval Contract](retrieval-contract.md) |
| Interaction observations and profiles | [Interaction Preferences](interaction-preferences.md) | Accepted direct migration | [Interaction Preferences](interaction-preferences.md) |
| Exact compiled interaction guidance | [Interaction Guidance](interaction-guidance.md) | Accepted direct migration | [Interaction Guidance](interaction-guidance.md) |
| Host and vault configuration | [Configuration](configuration.md) | Accepted new schemas | [Configuration](configuration.md) |

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

## Authority transition

The Owner accepted the four direct contract migrations and the extracted
Capture, Processing, and Retrieval specifications on 2026-08-29. Root-level
direct-contract sources remain as compatibility mirrors and must not be edited
independently. The Owner accepted Knowledge Candidates and Configuration on
2026-08-30. All Phase 1 specification subjects in this registry now have
normative owners.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Requirements:** [Requirements](../01-foundation/requirements.md)
- **Architecture:** [Architecture Overview](../02-architecture/overview.md)
- **Current implementation state:** [Current Status](../STATUS.md)
