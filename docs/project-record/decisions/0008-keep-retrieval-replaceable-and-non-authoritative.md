---
id: ADR-0008
title: Keep retrieval replaceable and non-authoritative
document_type: decision
status: accepted
authority: historical
implementation_status: planned
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
---

# ADR-0008: Keep retrieval replaceable and non-authoritative

## Context

Search quality and indexing technology will evolve, while memory authority,
scope, status, and current meaning must remain stable and reviewable outside any
one retrieval product.

## Decision

Recall builds permitted deterministic Retrieval Projections before a retrieval
Adapter ranks them. The Adapter sits at a replaceable Seam and cannot broaden
filters, change meaning, select a conflict winner, or grant authority. Indexes
remain local, disposable, and rebuildable from governed Markdown.

## Consequences

Retrieval technology may change without migrating memory authority or artifact
semantics. Orca must maintain projection and reconciliation logic and treats a
missing index as unavailable recall rather than silently scanning the vault.

## Related documents

- **Retrieval behavior:** [Retrieval Contract](../../specifications/retrieval.md)
- **Integration:** [Integration Architecture](../../architecture/integrations.md)
