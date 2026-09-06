---
id: SPEC-INTERACTION-PREFERENCES
title: Orca Interaction Preference Specification
document_type: specification
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
observation_policy: interaction-observation/1
aggregation_policy: interaction-aggregation/1
---

# Orca Interaction Preference Specification

## Purpose

This specification preserves the exact accepted behavior migrated from
`docs/archive/legacy-docs/interaction-preference-contract.md`.

## This document owns

- Interaction observation proposals, validated evidence, profile scope/state, consolidation, conflict, and expiry.

## This document does not own

- Semantic memory recall, personality inference, exact compiled guidance strings, or implementation progress.

> [!NOTE]
> This specification is the normative owner of interaction-preference behavior.

## Boundary

The semantic provider may propose an Interaction Observation Proposal. The
proposal is untrusted. Deterministic validation either admits one controlled
Interaction Observation into the current immutable Run Manifest or records a
content-free abstention for an evaluated plausible signal. Ordinary turns create
no preference receipt.

Run Manifests are the observation authority. Each admitted observation is the
`embedded_artifact` of one `observation` operation receipt; its `observation_id`
is the operation's `artifact_id`, and the operation cites the exact Manifest
source segments. Adaptive Interaction Profiles are living derived views. A
file-only Manifest scan is the baseline; an optional local SQLite projection may
accelerate lookup and aggregation but remains disposable and contains no
conversation text.

## Interaction Observation

An eligible observation uses this logical schema inside its Run Manifest:

```yaml
schema_version: orca-interaction-observation/1
observation_id: obs_<deterministic-id>
disposition: eligible
dimension: detail
value: null
direction: decrease
context: status-update
scope:
  type: agent
  agent_id: codex
evidence_class: direct-correction
source:
  conversation_id: <conversation-id>
  feedback_turn_id: <owner-turn-id>
  evaluated_assistant_turn_ids:
    - <assistant-turn-id>
  preceding_request_turn_id: <owner-turn-id>
  occurred_at: <feedback-turn-source-timestamp>
policy_version: interaction-observation/1
abstention_reason: null
```

Required validation rules:

- Exactly one of `value` or `direction` is non-null for an eligible observation.
- `dimension`, value or direction, context, scope, and evidence class must use
  controlled values.
- Every source reference must resolve to eligible normalized evidence in the
  same supported conversation context. The feedback must evaluate the referenced
  assistant response or passage and must have the preceding request needed to
  interpret it.
- `occurred_at` is the trusted feedback-turn timestamp, never processing or
  Storage time.
- `observation_id` is deterministic over source conversation, feedback turn,
  evaluated response, dimension, and policy version. Replay cannot add support.
- No raw feedback, assistant response, prompt, secret, personality description,
  inferred motive, or source array is copied into the observation.

The initial eligible evidence classes are `explicit-general`,
`natural-comparison`, `direct-correction`, and `dimension-specific-praise`.
Natural comparison is accepted only when the alternatives differ on one clearly
identified presentation dimension; Orca generates no automatic questionnaire.

An abstention contains no preference classification:

```yaml
schema_version: orca-interaction-observation/1
observation_id: obs_<deterministic-id>
disposition: abstained
policy_version: interaction-observation/1
abstention_reason: ambiguous-context
```

Controlled reasons include `missing-preceding-request`,
`missing-evaluated-response`, `ambiguous-target`, `ambiguous-context`,
`temporary-instruction`, `surface-signal-only`, `disallowed-inference`,
`unsupported-scope`, and `private-or-excluded`.

## Controlled dimensions and contexts

The initial dimensions are `detail`, `structure`, `question-frequency`,
`technical-depth`, `tone`, and `progress-updates`.

The initial contexts are `general`, `status-update`, `explanation`,
`design-discussion`, `implementation`, and `review`. Contexts are categorical
and are never scored. `general` requires explicit general applicability;
materially mixed or unclear context abstains.

## Adaptive Interaction Profile

Profiles are human-readable YAML under:

```text
System/Orca Memory/interaction/profiles/
  global.yaml
  agents/codex.yaml
  projects/<project-alias-slug>--<short-project-id>.yaml
  project-agents/<project-alias-slug>--<short-project-id>--codex.yaml
```

Structured scope, not the path, is identity. Scope type is `global`, `agent`,
`project`, or `project-agent`; project scope uses permanent `project_id`, and
agent scope uses stable adapter identity such as `codex`. Ambiguous project
identity loads no project-scoped profile.

A living profile has this shape:

```yaml
schema_version: orca-adaptive-profile/1
authority: noncanonical
scope:
  type: agent
  agent_id: codex
policy_version: interaction-aggregation/1
entries: []
```

Neutral is absence of an entry. One or two pending observations remain in Run
Manifests or a disposable projection and do not create a profile entry.

An active repeated entry is:

```yaml
- entry_id: detail--status-update
  dimension: detail
  context: status-update
  status: active
  value: concise
  direction: null
  basis: repeated-correction
  supporting_conversations: 3
  last_evidence_at: <source-turn-timestamp>
  expires_at: <180-days-after-last-evidence>
```

An explicit or Owner-resolved entry uses `basis: explicit`,
`basis: owner-resolution`, or `basis: owner-clarification`, has
`supporting_conversations: null`, and does not expire automatically.

A conflicting entry has no top-level value or direction:

```yaml
- entry_id: detail--status-update
  dimension: detail
  context: status-update
  status: conflicting
  candidates:
    - value: concise
      direction: null
      basis: repeated-correction
      supporting_conversations: 3
      last_evidence_at: <source-turn-timestamp>
    - value: detailed
      direction: null
      basis: repeated-correction
      supporting_conversations: 3
      last_evidence_at: <source-turn-timestamp>
```

Candidate support summaries are bounded derived inspection data, not evidence
authority. Run Manifests retain the complete observation history.

## Consolidation and runtime use

- One explicit lasting preference activates immediately.
- Otherwise aligned evidence requires three distinct conversations inside the
  preceding 180 days, using source-turn time. Repetition in one conversation
  counts once.
- Inferred active entries expire 180 days after their latest qualifying support.
  Explicit lasting or Owner-resolved entries do not expire automatically.
- A direction remains relative and never compounds into an extreme value.
  Concrete values require explicit support.
- Incompatible qualified evidence for the same scope, context, and dimension
  creates `conflicting` unless the Owner clearly replaces the earlier value or
  separates the contexts. Conflicting entries compile to no guidance.
- Current Owner instruction overrides current-session adjustment, which
  overrides confirmed preference, project-agent profile, project profile, agent
  profile, and global profile in that order.
- Active entries compile only through the
  [Interaction Guidance Specification](interaction-guidance.md). The
  configurable combined default is 500 tokens, and budget selection omits whole
  lower-precedence sentences rather than truncating them.
- Run Manifest scan and optional SQLite projection must produce the same current
  profile. Losing either projection loses no preference evidence.

Deterministic correctness ends at validated observation, consolidation, profile
state, exact guidance compilation, and delivery of the compiled payload. Natural
language interpretation and probabilistic agent compliance are evaluations, not
deterministic test claims.
