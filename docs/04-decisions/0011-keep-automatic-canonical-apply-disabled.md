---
id: ADR-0011
title: Keep automatic canonical apply disabled
document_type: decision
status: accepted
authority: historical
implementation_status: verified
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
---

# ADR-0011: Keep automatic canonical apply disabled

## Context

Conversation-derived proposals are probabilistic, may conflict, and may contain
privacy or attribution mistakes. Automatically promoting them would let a model
change Owner-authoritative knowledge through a capture path designed for
provisional memory.

## Decision

Phase 1 exposes no automatic canonical-apply Interface. Knowledge Candidates
remain noncanonical even when `approved-for-manual-apply`; canonical changes
require a separate future governance decision and implementation.

## Consequences

Phase 1 cannot provide hands-off canonical maintenance, but model output cannot
silently alter accepted knowledge. Future automation must be proposed and
governed separately rather than added behind an existing capture operation.

## Related documents

- **Governance:** [Memory System Contract](../governance/memory-system-contract.md)
- **Candidates:** [Knowledge Candidates](../03-specifications/knowledge-candidates.md)
