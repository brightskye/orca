---
id: PROPOSAL-INDEX
title: Orca Proposal Registry
document_type: documentation-index
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - all-phases
owners:
  - project-owner
last_reviewed: 2026-08-30
---

# Orca proposal registry

## Purpose

Register substantial changes that are being considered but are not accepted
current design. A proposal supports review; it does not authorize
implementation or change architecture, specifications, governance, or roadmap
commitment.

## This document owns

- Proposal numbering, status, navigation, and relationship to roadmap phases.
- The distinction between an active proposal and noncurrent proposal input.

## This document does not own

- Accepted requirements, architecture, specifications, decisions, or plans.
- Exact future design that has not passed proposal review.

## Active proposals

No numbered RFC has been created or accepted.

## Undrafted proposal inputs

These topics may justify future proposals. Their retained sources are evidence
only; the source files' internal `accepted-baseline` wording does not make the
design current or accepted.

| Candidate topic | Roadmap context | Retained input | Current state |
|---|---|---|---|
| Multiple local agents sharing one local vault | [Phase 2](../ROADMAP.md#phase-2) | [Archived all-phase design](../_archive/legacy-design/system-overview.md) | Candidate topic; no RFC |
| Synchronized local and remote vault replicas | [Phase 3](../ROADMAP.md#phase-3) | [Archived all-phase design](../_archive/legacy-design/system-overview.md) | Candidate topic; no RFC |
| Automatic or agent-initiated canonical apply | [Intentionally deferred](../ROADMAP.md#intentionally-deferred) | [Proposed ADR-0003](../04-decisions/0003-graduate-canonical-apply-by-category.md) | Deferred topic; no RFC |
| Automated retention beyond accepted recovery rules | [Intentionally deferred](../ROADMAP.md#intentionally-deferred) | [Archived governance snapshot](../_archive/legacy-design/memory-system-contract.md) | Deferred topic; no RFC |

## Numbering and lifecycle

- Allocate the next `RFC-NNNN` number only when a concrete proposal is created;
  never reuse an allocated number.
- `draft` and `under-review` proposals are unaccepted and have informative
  authority only.
- `accepted` records a successful proposal review but does not itself rewrite
  current design. Accepted conclusions must be promoted into their canonical
  requirements, architecture, specifications, ADRs, roadmap, or plans.
- `rejected`, `withdrawn`, and `superseded` proposals remain available as
  historical evidence or move to the archive with a replacement link.
- Implementation must not begin from a proposal with unclear acceptance unless
  the work is explicitly scoped as exploratory.

## Promotion boundary

Creating an RFC from deferred material requires separate Owner approval. The
RFC must reconcile the retained source with current Phase 1 authority instead
of copying old exact design or internal status labels. Current architecture
must remain understandable without reading a proposal or archived source.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Future direction:** [Roadmap](../ROADMAP.md)
- **Accepted rationale:** [Decision Registry](../04-decisions/README.md)
- **Proposal template:** [Proposal template](template.md)
- **Archived proposal inputs:** [Documentation Archive](../_archive/README.md)
