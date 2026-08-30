---
id: SPEC-INTERACTION-GUIDANCE
title: Orca Interaction Guidance Specification
document_type: specification
status: accepted
authority: normative
implementation_status: implemented
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-29
last_verified_against_code: 2026-08-30
supersedes: []
policy_version: interaction-guidance/1
---

# Orca Interaction Guidance Specification

## Purpose

This specification preserves the exact accepted behavior migrated from
`docs/_archive/legacy-docs/interaction-guidance-contract.md`.

## This document owns

- Versioned deterministic guidance templates, applicable-entry selection, ordering, and budget behavior.

## This document does not own

- Observation interpretation, profile lifecycle, semantic recall, or implementation progress.

> [!NOTE]
> This specification is the normative owner of interaction-guidance behavior.

## Contract purpose

This contract defines the exact natural-language guidance compiled from active
Adaptive Interaction Profile entries. Compilation is deterministic: an agent or
model must not invent, paraphrase, or expand these templates at runtime.

## Context prefixes

```yaml
general: "Generally, "
status-update: "For status updates, "
explanation: "For explanations, "
design-discussion: "For design discussions, "
implementation: "During implementation work, "
review: "For reviews, "
```

## Guidance clauses

```yaml
detail:
  concise: "keep the response concise and omit nonessential background."
  balanced: "provide enough detail to support the answer without unnecessary expansion."
  detailed: "provide thorough context, rationale, and supporting detail."
  decrease: "reduce unnecessary detail and prioritize the information needed to proceed."
  increase: "provide more context, rationale, and supporting detail."

structure:
  minimal: "use minimal formatting and only necessary headings."
  moderate: "use short sections or lists when they materially improve clarity."
  highly-structured: "organize the response into clear sections and actionable lists."
  decrease: "reduce headings, lists, and structural overhead."
  increase: "add clearer organization and section boundaries."

question-frequency:
  blocking-only: "ask questions only when proceeding would create meaningful risk."
  selective: "ask when the answer would materially change the outcome."
  proactive: "surface important ambiguities and alternatives before proceeding."
  decrease: "ask fewer questions and make reasonable low-risk assumptions."
  increase: "check important assumptions more explicitly before proceeding."

technical-depth:
  plain-language: "explain technical concepts in accessible language and define necessary terms."
  mixed: "use technical detail where useful and explain unfamiliar terms."
  expert: "use precise technical language without explaining standard concepts."
  decrease: "reduce specialist detail and explain concepts more plainly."
  increase: "include more technical mechanisms and implementation detail."

tone:
  formal: "use a professional and formal tone."
  neutral: "use a direct, neutral, and professional tone."
  conversational: "use a natural and conversational tone while remaining precise."
  more-formal: "use a more formal and restrained tone."
  more-conversational: "use a warmer and more conversational tone."

progress-updates:
  milestones-only: "report only meaningful milestones, blockers, and completion."
  periodic: "provide concise updates at useful intervals during ongoing work."
  frequent: "provide regular progress updates during ongoing work."
  decrease: "reduce routine progress narration and report only material changes."
  increase: "provide more frequent visibility into progress, blockers, and next steps."
```

## Compilation

One active entry compiles as exact concatenation:

```text
context_prefixes[context] + guidance[dimension][value_or_direction]
```

For example, `implementation`, `progress-updates`, and `milestones-only`
compile exactly to:

> During implementation work, report only meaningful milestones, blockers, and completion.

Compilation follows these rules:

- Only `active` entries compile. A `conflicting` entry produces no guidance.
- Current Owner instructions and current-session adjustments override compiled
  guidance.
- More-specific scope replaces broader guidance for the same context and
  dimension.
- Identical compiled sentences appear once.
- An unknown or missing template key is omitted and recorded as a validation
  failure; the compiler never improvises replacement wording.
- The complete automatically loaded interaction guidance uses the configured
  token budget, initially 500 tokens.
- Budget selection keeps higher-precedence complete sentences and omits lower-
  precedence complete sentences. It never truncates a sentence.
- Evidence, support counts, timestamps, and profile lifecycle details are not
  included in compiled guidance.

Any change to a context prefix, guidance clause, allowed key, or compilation
rule requires a new policy version and updated exact-output tests.
