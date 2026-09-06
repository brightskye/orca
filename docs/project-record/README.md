---
id: PROJECT-RECORD
title: Orca Project Record
document_type: project-record
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - all-phases
owners:
  - project-owner
last_reviewed: 2026-09-04
---

# Orca project record

## Purpose

This is the normal entry point for Orca information across time. It links to
the document that owns each detail rather than duplicating those details here.

## Current

- [Current](current.md) owns the implemented capability, limitation, and
  verification snapshot.
- Orca follows the PLS 0.3 working model. The [documentation map](../README.md)
  owns the detailed project map and subject ownership routes.

## Next

- The [Roadmap](roadmap.md) owns candidate Phase 2 and Phase 3 outcomes and
  intentionally deferred capabilities.
- [Plans](plans/README.md) records whether an execution plan is
  active and links completed plans.

## Proposals

- [Proposals](proposals/README.md) owns unaccepted substantial
  changes and records whether any RFC is active.

## Decisions

- [Decisions](decisions/README.md) owns architectural rationale,
  lifecycle, numbering, and supersession history.
- Current design belongs to the mapped Architecture and Specifications owners,
  not to old decision records.

## History

- The completed [Phase 1 Implementation Plan](plans/completed/phase-1-implementation.md)
  records the accepted delivery sequence and outcomes.
- The [Archive](../archive/README.md) contains inactive project
  documents and the completed PDS migration record.
- [`PDS-0.2.md`](../archive/standards/PDS-0.2.md) preserves Orca's former
  layout-standard baseline; it no longer governs current placement.
- Orca's 2026-09-04 PLS adoption replaced obsolete PDS-era structure while
  preserving useful project material and historical records.
- On 2026-09-05, the Owner directed full PLS 0.3 content ownership without
  unconfirmed placement exceptions. Architecture was reduced to system views;
  exact runtime and backup behavior moved into Specifications, and stale
  implementation claims were replaced by routes to Current.
