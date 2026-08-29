---
id: PLAN-INDEX
title: Orca Plan Registry
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

# Orca plan registry

## Purpose

Register active and completed execution plans without turning plans into a
second source of requirements, design, or current status.

## This document owns

- Plan navigation, lifecycle, and active/completed placement.

## This document does not own

- Accepted behavior, phase direction, architectural rationale, or current
  implementation truth.

## Active plans

| Plan | Status | Roadmap phase | Execution authority |
|---|---|---|---|
| [Phase 1 Implementation Plan](active/phase-1-implementation.md) | Accepted | [Phase 1](../ROADMAP.md#phase-1) | Active execution plan |

## Completed plans

No plan has completed under the PDS plan lifecycle.

## Lifecycle

- Active plans remain under `active/` while accepted work is in progress.
- A proposed plan is review material and does not authorize its sequence.
- Current progress is reported in [Current Status](../STATUS.md), not inferred
  from checklist state alone.
- When every completion criterion is verified, the plan becomes historical and
  moves to `completed/`; the path is never reused for a different plan.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Current state:** [Current Status](../STATUS.md)
- **Phase direction:** [Roadmap](../ROADMAP.md)
- **Unaccepted substantial changes:** [Proposal Registry](../05-proposals/README.md)
