---
id: ADR-0010
title: Keep interaction preferences inspectable and noncanonical
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

# ADR-0010: Keep interaction preferences inspectable and noncanonical

## Context

Presentation adaptation can reduce repeated corrections, but inferred behavior
is uncertain and can easily be mistaken for a claim about the Owner's identity,
intent, or stable personality.

## Decision

Orca learns only scoped presentation behavior through validated observations,
inspectable derived profiles, controlled lifecycle rules, and fixed guidance
templates. Inferred profiles remain noncanonical; only separately governed
Owner confirmation can create a Confirmed Interaction Preference.

## Consequences

Adaptation remains correctable, conflict-aware, and quiet by default without
classifying the human. The controlled evidence and compilation model is more
constrained than free-form personalization and must abstain on missing context.

## Related documents

- **Preference lifecycle:** [Interaction Preferences](../../specifications/interaction-preferences.md)
- **Compiled guidance:** [Interaction Guidance](../../specifications/interaction-guidance.md)
