---
id: SPEC-KNOWLEDGE-CANDIDATES
title: Orca Knowledge Candidate Specification
document_type: specification
status: accepted
authority: normative
implementation_status: implemented
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-30
supersedes: []
candidate-schema: orca-knowledge-candidate/0.1
---

# Orca Knowledge Candidate Specification

## Purpose

Define the Phase 1 contract for ordinary Knowledge Candidates: atomic,
inspectable, noncanonical proposals awaiting explicit human disposition.

This accepted design is not a migration of a legacy Curator contract.

## Scope

This specification owns ordinary candidate kinds, fields, bodies, placement,
review lifecycle, recall exclusion, retention, and disposition semantics.

It does not own Typed Memory Records or Conflict Overflow Candidates, which are
defined by the [Memory Model](memory-model.md). It does not authorize canonical
writes. Automatic canonical apply remains disabled and unexposed in Phase 1.

## Definitions

- **Knowledge Candidate:** one atomic proposed fact, decision, preference,
  lesson, or project state awaiting explicit human disposition.
- **Approval for manual apply:** an Owner disposition that the proposal is
  suitable for a separately governed manual canonicalization decision. It does
  not change the candidate's authority or perform that decision.
- **Rejection:** an Owner disposition that the proposal must not proceed from
  this candidate.

Candidate status and authority are independent: every candidate remains
`authority: noncanonical`, including a candidate marked
`approved-for-manual-apply`.

## Inputs

The Candidate interface accepts one deterministically validated Processor
proposal containing:

- exactly one controlled candidate kind;
- one concise subject;
- one atomic proposed meaning;
- optional bounded context needed to interpret that meaning;
- a Governance-resolved `project`, `general`, or `unassigned` scope; and
- exact source bindings retained in the Run Manifest.

Quoted, hypothetical, uncertain, third-party, task/reminder, private, sensitive,
or mixed proposals MUST abstain unless the applicable meaning and write intent
are explicit. Uncertain project ownership MUST use `unassigned`; it MUST NOT be
silently generalized or linked to a project.

## Outputs

Creation produces one pending candidate Markdown artifact and one Run Manifest
binding its `candidate_id` to exact sources. Review produces a deterministic
status update and a content-minimized disposition receipt. Neither output is
Canonical Memory or a canonical-write instruction.

## Data model

The schema identifier is `orca-knowledge-candidate/0.1`. A candidate
Markdown file contains exactly these frontmatter fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | Exactly `orca-knowledge-candidate/0.1` |
| `candidate_id` | string | Permanent opaque identity assigned by Storage |
| `candidate_kind` | enum | `fact`, `decision`, `preference`, `lesson`, or `project-state` |
| `subject` | string | Concise stable subject of this one proposal |
| `authority` | enum | Exactly `noncanonical` |
| `scope` | enum | `project`, `general`, or `unassigned` |
| `scope_id` | string | Permanent `project_id` for project scope; otherwise the fixed scope name |
| `status` | enum | `pending`, `approved-for-manual-apply`, or `rejected` |
| `source_updated_at` | timestamp or null | Trusted source-turn time when available; never processing time substituted for missing source time |
| `created_at` | timestamp | First Storage publication time |
| `updated_at` | timestamp | Last Storage-controlled disposition change time |

The body MUST contain `## Proposal` with only the atomic proposed meaning. It
MAY contain nonempty `## Context` when the proposal cannot be understood safely
without it. It MUST NOT contain raw excerpts, source lists, source hashes,
support counters, Run Manifest paths, multiple unrelated proposals, or a
canonical target chosen by the semantic provider.

## Placement and naming

Storage would place ordinary candidates under a distinct `knowledge/` subtree:

```text
System/Orca Memory/candidates/knowledge/
  projects/<project-alias-slug>/
  general/
  unassigned/
```

The filename is `<subject-slug>--<short-candidate-id>.md`. Storage alone
constructs and changes the path and filename. A project-alias change MAY move a
project candidate without changing `candidate_id`, scope identity, status, or
authority. Filename and path never grant identity or authority.

This subtree is part of the accepted Phase 1 data architecture.

## State transitions

```text
validated proposal
    -> pending
pending -> approved-for-manual-apply
pending -> rejected
```

| From | Trigger | Validation | To | Side effects |
|---|---|---|---|---|
| none | Validated Processor proposal | Schema, scope, atomicity, privacy, and secret scan pass | `pending` | Publish candidate, then bind it in the Run Manifest |
| `pending` | Explicit Owner approval during candidate review | Exact candidate identity and current status match | `approved-for-manual-apply` | Update only disposition metadata and record the disposition receipt |
| `pending` | Explicit Owner rejection during candidate review | Exact candidate identity and current status match | `rejected` | Update only disposition metadata and record the disposition receipt |

`approved-for-manual-apply` and `rejected` are terminal Phase 1 candidate
states. Reconsidered or corrected meaning requires a new candidate rather than
silently rewriting the reviewed proposal. No semantic provider or automatic job
may perform a disposition transition.

## Required behavior

1. One candidate MUST contain one proposal of one controlled kind.
2. Storage MUST assign `candidate_id`, schema, authority, timestamps, filename,
   and path; the Processor MAY propose only semantic fields.
3. Exact source history and candidate disposition receipts MUST remain in the
   [Provenance Ledger](provenance-ledger.md), not in unbounded candidate arrays.
4. Support-only evidence MAY add a Run Manifest association but MUST NOT rewrite
   the candidate body or advance its source or Storage timestamps.
5. A materially different proposal MUST receive a distinct candidate identity.
   Similarity alone MUST NOT merge candidates.
6. Candidate review MUST be explicitly invoked by the Owner. Candidate content
   MUST NOT be injected or announced automatically at startup. A pending
   candidate contributes only a content-free review count and safe ID to Orca
   Status and its once-per-session counts-only reminder.
7. All candidate states MUST remain outside ordinary Recall, structural
   summaries, interaction profiles, and automatic agent context.
8. A candidate marked `approved-for-manual-apply` remains noncanonical. It MAY
   inform a later separately governed manual canonicalization action, but this
   specification does not define or expose that action and records no canonical
   target receipt.
9. Phase 1 applies no age-based retention and exposes no candidate-cleanup
   interface. Candidates persist until a later accepted retention specification
   defines an Owner-authorized cleanup workflow.
10. Orca Status derives candidate Attention Items from current candidate state;
    status cannot approve, reject, clean up, recall, or apply a candidate.

## Invariants

- Candidate content never becomes canonical by status change, filename, path,
  indexing, or model confidence.
- Candidate review never silently changes Canonical Memory.
- Candidate scope is deterministic and never crosses projects automatically.
- Ordinary candidates and Conflict Overflow Candidates remain distinct schemas,
  identities, paths, and review flows.
- An interrupted disposition cannot leave a candidate eligible for both
  approved and rejected outcomes; the latest durable disposition receipt and
  current candidate status must agree before review proceeds.

## Error behavior and idempotency

| Condition | Required result |
|---|---|
| Unsupported kind, mixed proposal, missing subject, or missing body | Reject before publication |
| Missing or ambiguous scope | Use `unassigned` only when publication remains safe; otherwise abstain |
| Credential-like generated value | Reject before storage, indexing, or synchronization |
| Duplicate exact proposal from already processed sources | No new candidate and no semantic replay |
| Disposition for missing, stale, or non-pending identity | Fail closed; change nothing |
| Interrupted candidate publication | Recover from the fixed publication intent; do not advance the checkpoint before its Run Manifest |
| Interrupted disposition update | Reconcile candidate status against its durable disposition receipt before retry |

Repeating the same validated creation or disposition operation MUST converge on
one candidate identity and one terminal state without duplicate artifacts.
After interrupted publication, Storage MUST reuse the `candidate_id` and fixed
output recorded by the publication intent. If that intent is missing or invalid,
Storage MUST expose the orphan for human repair rather than assign another
identity, overwrite it, or delete it.

## Security and privacy

Candidate text MUST already be permitted and redacted by capture policy and MUST
pass generated-output secret scanning before publication. Candidate files live
in the configured private vault and MUST NOT be copied into the public project.
Raw conversation text requires separate explicit inspection of the still
available agent-owned source.

## Compatibility

This proposal satisfies the accepted authority and recall boundary in
[REQ-CAND-001](../01-foundation/requirements.md#req-cand-001--knowledge-candidate-boundary)
without adopting legacy Curator behavior. Existing AgentCairn candidate tests
and `legacy/manual-prototype/` artifacts are historical implementation evidence only; they do
not define this contract.

## Acceptance criteria

- Schema fixtures validate every controlled kind, scope, and state and reject
  extra authority or provenance fields.
- Creation, approval, rejection, stale-disposition, replay, and interrupted
  publication cases satisfy the state table.
- Ordinary Recall and automatic context never return any candidate state.
- Candidates approved for manual apply remain visibly noncanonical and cause
  zero automatic canonical mutations.
- Candidate placement remains distinct from Conflict Overflow Candidates.
- The schema, `knowledge/` placement, terminal lifecycle, and retention rule
  remain consistent with the accepted Data Architecture.

## Open questions

None.

## Related documents

- **Requirements:** [REQ-CAND-001](../01-foundation/requirements.md#req-cand-001--knowledge-candidate-boundary)
- **Authority:** [Memory System Contract](../governance/memory-system-contract.md)
- **Processing:** [Processing Pipeline](processing-pipeline.md)
- **Data ownership:** [Data Architecture](../02-architecture/data-architecture.md)
- **Security:** [Security and Trust](../02-architecture/security-and-trust.md)
