---
id: ADR-0012
title: Use AgentCairn behind the retrieval interface
document_type: decision
status: accepted
authority: historical
implementation_status: implemented
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-31
supersedes: []
---

# ADR-0012: Use AgentCairn behind the retrieval interface

## Context

Phase 1 needs private local Markdown retrieval, hybrid search, a rebuildable
index, and Codex integration. Building all retrieval machinery would delay the
memory system, while granting a retrieval product authority would couple Orca's
semantics to that product.

## Decision

Use AgentCairn as the initial retrieval Adapter behind Orca's Retrieval
Interface. Orca retains ownership of indexed roots, projections, filters,
authority labels, source classification, candidate disposition, and canonical
governance. Another Adapter may replace AgentCairn without changing those
contracts.

## Consequences

Orca can reuse an existing local Markdown retrieval implementation while
retaining its own semantics. The integration must constrain AgentCairn to
prevalidated projections and preserve a replacement path; current wiring remains
partial.

## Related documents

- **Integration:** [Integration Architecture](../02-architecture/integration-architecture.md)
- **Retrieval behavior:** [Retrieval Contract](../03-specifications/retrieval-contract.md)
- **Current implementation:** [Current Status](../STATUS.md)
