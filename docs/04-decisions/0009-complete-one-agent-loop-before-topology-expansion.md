---
id: ADR-0009
title: Complete one-agent behavior before topology expansion
document_type: decision
status: accepted
authority: historical
implementation_status: partial
applies_to:
  - phase-1
  - phase-2-candidate
  - phase-3-candidate
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
---

# ADR-0009: Complete one-agent behavior before topology expansion

## Context

Adding agents or synchronized hosts before the complete memory loop works would
mix core semantic gaps with identity, visibility, coordination, and replica
failures. Deferring core capabilities would also make Phase 1 an incomplete
prototype rather than an independently useful delivery phase.

## Decision

Phase 1 delivers the complete governed memory, interaction, and explicit Recall
loop for Codex Desktop through one local WSL runtime and vault. Phase 2 changes
the number of local agents; Phase 3 changes the number and location of hosts.
Neither later phase is used to defer a Phase 1 core capability.

## Consequences

Topology work waits for a usable single-agent loop, reducing compounded failure
modes. Phase 1 carries more scope, while later phases can reuse established
artifact meanings and Interfaces instead of redefining them.

## Related documents

- **Roadmap:** [Roadmap](../ROADMAP.md)
- **Deployment:** [Deployment Architecture](../02-architecture/deployment.md)
