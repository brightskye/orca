---
id: ADR-0006
title: Separate canonical, provisional, and operational memory classes
document_type: decision
status: accepted
authority: historical
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
---

# ADR-0006: Separate canonical, provisional, and operational memory classes

## Context

Model output, working context, accepted knowledge, and processing receipts have
different owners and failure modes. Treating them as one memory class would let
confidence, ranking, placement, or automation masquerade as human authority.

## Decision

Orca keeps Canonical Memory, noncanonical Shallow Memory and Knowledge
Candidates, transient Conversation Evidence, and operational or derived state
as distinct data classes. Movement between classes requires the governing
Interface; storage location or retrieval rank never grants authority.

## Consequences

Callers must preserve visible authority labels and use separate lifecycle rules.
The additional classes cost schema and validation work but prevent semantic
proposals and operational receipts from silently becoming accepted knowledge.

## Related documents

- **Authority:** [Memory System Contract](../governance/memory-system-contract.md)
- **Data classes:** [Data Architecture](../02-architecture/data-architecture.md)
