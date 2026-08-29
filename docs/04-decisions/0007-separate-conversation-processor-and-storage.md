---
id: ADR-0007
title: Separate Conversation, Processor, and Storage responsibilities
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

# ADR-0007: Separate Conversation, Processor, and Storage responsibilities

## Context

Source-format recognition, semantic interpretation, and recoverable filesystem
publication change for different reasons and have different deterministic test
surfaces. Combining them would spread privacy, authority, and recovery logic
across callers.

## Decision

Conversation owns the source-format Seam and permitted evidence Interface.
Processor owns bounded semantic input and validated proposal output. Storage
owns identity, physical representation, publication ordering, and checkpoint
advancement. A semantic-provider Adapter may propose meaning but cannot cross
these Interfaces to assign authority or placement.

## Consequences

Each Module has a focused Interface shared by callers and tests. Coordination
requires explicit source and proposal records, but changes retain locality and
semantic-provider replacement cannot bypass deterministic controls.

## Related documents

- **Architecture:** [Architecture Overview](../02-architecture/overview.md)
- **Capture:** [Capture Pipeline](../03-specifications/capture-pipeline.md)
- **Processing:** [Processing Pipeline](../03-specifications/processing-pipeline.md)
