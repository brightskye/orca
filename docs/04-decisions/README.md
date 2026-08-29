---
id: DECISION-INDEX
title: Orca Decision Registry
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

# Orca decision registry

## Purpose

Register significant architectural decisions, preserve numbering and
supersession history, and distinguish accepted current rationale from proposed
or future-only material. Exact behavior remains owned by architecture and
specifications, not by ADRs.

## Numbering

ADR numbers are never reused. Accepted, proposed, and superseded ADR records all
remain in this registry; lifecycle status determines authority, not placement.

## Registry

| ADR | Status | Applicability | Location |
|---|---|---|---|
| [ADR-0001](0001-separate-local-and-synchronized-system-state.md) | Superseded by ADR-0004 | Historical only | Decision registry |
| [ADR-0002](0002-authorize-one-processor-by-host-identity.md) | Proposed; future-only evidence | Phase 3 candidate; not accepted current design | Decision registry |
| [ADR-0003](0003-graduate-canonical-apply-by-category.md) | Proposed; future-only evidence | Separately governed follow-on; not an accepted roadmap commitment | Decision registry |
| [ADR-0004](0004-separate-project-workspace-from-vault.md) | Accepted | Current Phase 1 and later topology | Active registry |
| [ADR-0005](0005-read-agent-history-without-raw-archive.md) | Accepted | Current architecture rationale | Active registry |
| [ADR-0006](0006-separate-memory-authority-classes.md) | Accepted | Current architecture rationale | Active registry |
| [ADR-0007](0007-separate-conversation-processor-and-storage.md) | Accepted | Current architecture rationale | Active registry |
| [ADR-0008](0008-keep-retrieval-replaceable-and-non-authoritative.md) | Accepted | Current architecture rationale | Active registry |
| [ADR-0009](0009-complete-one-agent-loop-before-topology-expansion.md) | Accepted | Current roadmap rationale | Active registry |
| [ADR-0010](0010-keep-interaction-preferences-inspectable-and-noncanonical.md) | Accepted | Current specification rationale | Active registry |
| [ADR-0011](0011-keep-automatic-canonical-apply-disabled.md) | Accepted | Current governance rationale | Active registry |
| [ADR-0012](0012-use-agentcairn-behind-retrieval-interface.md) | Accepted | Current integration rationale | Active registry |

## Lifecycle rules

- `proposed` ADRs are working rationale and do not change accepted design.
- `accepted` ADRs record why an accepted architecture or specification choice
  exists; they do not become the sole behavior owner.
- A replacement receives a new number and names the ADR it supersedes.
- Superseded and future-only records preserve their original text and source
  status where it differs from their current PDS lifecycle classification.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture:** [Architecture Overview](../02-architecture/overview.md)
- **Specifications:** [Specification Index](../03-specifications/README.md)
- **Roadmap:** [Roadmap](../ROADMAP.md)
- **Template:** [Decision template](template.md)
