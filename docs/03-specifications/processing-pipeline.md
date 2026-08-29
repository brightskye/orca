---
id: SPEC-PROCESSING-PIPELINE
title: Orca Processing Pipeline Specification
document_type: specification
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-29
last_verified_against_code: 2026-08-29
supersedes: []
processor-policy: orca-processor/0.1
---

# Orca Processing Pipeline Specification

## Purpose

Define the Processor module interface that turns eligible new Conversation
Evidence into bounded, validated publication instructions. The Module hides
context assembly, replaceable semantic-provider invocation, and deterministic
proposal validation behind one controlled Seam.

## Scope

This specification owns chronological chunking, context selection and budgets,
provider input, provider output operations, deterministic validation,
abstention, and failure behavior.

It does not own capture eligibility, artifact schemas, identity or path
assignment, publication ordering, recall ranking, or candidate disposition.
Those interfaces belong to the linked specifications.

## Inputs

One processing run receives:

- an ordered nonempty batch of eligible new Conversation Evidence from the
  [Capture Pipeline](capture-pipeline.md);
- the immediately preceding turn overlap when needed;
- the current Conversation Continuation Summary;
- the current Project Summary when the run is project-scoped;
- a bounded same-scope set of relevant current Typed Memory Records;
- a Governance-resolved `project`, `general`, or `unassigned` scope; and
- active processor, privacy, and output-contract versions.

The Processor MUST NOT receive every prior conversation or every project record.

## Context budget

The complete provider input, including fixed instructions, MUST NOT exceed
20,000 tokens. These are independent category ceilings, not reservations:

| Category | Ceiling |
|---|---:|
| New Conversation Evidence | 8,000 tokens |
| One preceding turn | 1,000 tokens |
| Conversation Continuation Summary | 2,000 tokens |
| Project Summary | 2,000 tokens |
| Up to five related current Typed Memory Records | 5,000 tokens total |
| Complete semantic output | 4,000 tokens |

A configuration MAY lower these limits. A larger model window MUST NOT silently
increase them. Configuration validation MUST reject category ceilings that
cannot fit within the complete input or output ceiling.

## Required behavior

### Chunking and selection

1. The Processor MUST process eligible new turns chronologically.
2. A backlog larger than one chunk MUST become sequential runs, each with its
   own Run Manifest and checkpoint advancement.
3. A chunk SHOULD split at a turn boundary. A single oversized turn MUST be
   segmented deterministically while preserving its conversation ID, turn ID,
   segment order, source timestamp, and provenance.
4. New evidence MUST NOT be silently truncated. The Processor MUST reduce the
   chunk or segment an oversized turn.
5. Related records MUST be same-scope and current. If the complete input still
   exceeds its ceiling, the Processor MUST remove the lowest-ranked related
   records first.
6. Project Summary input MUST be absent outside project scope.

### Semantic-provider Seam

The semantic provider is a replaceable Adapter. It MAY interpret conversational
meaning and propose:

- Conversation Continuation Summary content;
- Project Summary refresh content after a material record change;
- Typed Memory Record kind, subject, body, and one of `add`, `support`, `update`,
  `supersede`, `conflict`, or `abstain`;
- one atomic Knowledge Candidate;
- an Interaction Observation Proposal; or
- `no_memory` when no durable output is justified.

The provider MUST NOT assign schema versions, `memory_id`, candidate identity,
variant IDs, authority, scope, Storage timestamps, filenames, paths, hashes, or
publication order. Its entire response is untrusted until deterministic
validation succeeds.

### Deterministic validation

Before any output reaches Storage, Processor and Governance MUST validate:

- the response schema and controlled values;
- that every cited source belongs to the current processing input;
- that Governance resolved the scope without semantic guessing;
- that a proposed target exists and remains in the same scope;
- that an existing record's identity and scope do not change;
- lifecycle and conflict transitions owned by the
  [Memory Model](memory-model.md);
- Knowledge Candidate structure and lifecycle owned by
  [Knowledge Candidates](knowledge-candidates.md);
- Interaction Observation admission owned by
  [Interaction Preferences](interaction-preferences.md); and
- absence of credential-like values in every proposed durable output.

For a preference proposal, the validated input MUST contain the Owner feedback
turn, the evaluated assistant response or passage, the preceding request, and
an applicable controlled scope and context. Missing, ambiguous, private, or
excluded context MUST abstain.

### Operation semantics

- `add` proposes a new logical record when no safe same-scope target exists.
- `support` records exact qualifying support without rewriting the logical
  memory or advancing its source or Storage timestamps.
- `update` proposes changed applicable meaning for an existing target.
- `supersede` proposes explicit replacement with retained compact lineage.
- `conflict` preserves incompatible applicable positions without selecting a
  winner.
- `abstain` declines one proposed semantic operation.
- `no_memory` means the complete run is valid but publishes no derived memory.

Matching MUST remain within one scope. Kind, normalized subject or entity, and
provenance MAY produce a bounded set of possible targets. Textual similarity
alone MUST NOT merge uncertain records.

## Outputs

On success, the Processor returns validated instructions and exact source
bindings for zero or more contract-owned artifacts. Storage then assigns
identity and physical representation according to:

- [Memory Model](memory-model.md) for structural summaries, Typed Memory
  Records, conflicts, and Conflict Overflow Candidates;
- [Knowledge Candidates](knowledge-candidates.md) for ordinary candidates;
- [Interaction Preferences](interaction-preferences.md) for admitted
  observations and affected derived profiles; and
- [Provenance Ledger](provenance-ledger.md) for the Run Manifest and checkpoint.

A valid output-free result MUST become a successful `no_memory` Run Manifest.

## Invariants

- Exactly one authorized local WSL Processor handles a run under one local OS
  lock.
- Semantic output proposes meaning but grants no identity, placement, safety, or
  authority.
- Source references in validated output are a subset of the current bounded
  input.
- One failed run commits no derived artifact and advances no checkpoint.
- Complete audit provenance remains in Run Manifests, not duplicated into Typed
  Memory Record bodies or frontmatter.
- Project scope, general scope, and unassigned scope never match automatically
  across one another.

## Error behavior and recovery

| Condition | Required result |
|---|---|
| Empty new-evidence batch | Do not call the provider |
| Lock contention | Exit without processing or checkpoint advancement |
| Budget overflow before provider call | Rechunk, segment, or drop lowest-ranked related records; never truncate new evidence |
| Provider timeout or malformed output | Publish nothing; preserve source or retry spool |
| Invalid source reference, target, scope, transition, or controlled value | Reject the run; publish nothing |
| Credential-like generated value | Reject every affected output before storage or indexing |
| Valid `no_memory` | Publish a successful Run Manifest and advance checkpoint last |
| Summary refresh failure after an independently valid Owner resolution | Preserve the resolved record; mark the derived summary stale in the Run Manifest for bounded rebuild |

When proposed artifacts are prepared together, publication is recoverable but
not described as transactionally atomic. Artifact files publish first, the Run
Manifest publishes after the complete output set is durable, and the local
checkpoint advances last as defined by the Provenance Ledger.

## Idempotency

Durable Run Manifests are the processed-source authority. Exact successful
replay MUST make no semantic call and create no duplicate artifact. A known
source identity with a different hash under the same redaction policy MUST fail
closed as a source revision. A redaction-policy change requires governed
reprocessing rather than being treated as an exact replay.

## Security and privacy

Provider input MUST be the minimum bounded, permitted, redacted context needed
for the current run. The Processor MUST NOT receive excluded or unredacted
capture content. Every generated durable output MUST pass deterministic secret
scanning before publication, indexing, synchronization, recall, or exposure to
another agent.

## Compatibility and current divergence

The interface preserves the accepted Phase 1 rules from the
[Memory System Contract](../governance/memory-system-contract.md),
[Architecture Overview](../02-architecture/overview.md), and
[Runtime Architecture](../02-architecture/runtime.md).

Current code supports one replaceable provider call for a Conversation
Continuation Summary, validates its required text and secret exclusion, and
publishes `success` or `no_memory`. It does not yet implement full context
budgets, chunking, related-record selection, the complete proposal set,
interaction processing, or the candidate and record lifecycles. See
[Current Status](../STATUS.md).

## Acceptance criteria

- Budget tests cover every category ceiling and complete input/output ceilings.
- Backlog and oversized-turn fixtures preserve chronological identity without
  truncation and create separate run receipts.
- Provider proposals cannot assign deterministic Storage or authority fields.
- Every controlled operation passes valid cases and rejects missing-target,
  cross-scope, identity-change, unsupported-transition, and secret-output cases.
- Exact replay performs no semantic call; a valid abstention publishes
  `no_memory`; failed validation leaves the checkpoint unchanged.
- Published outputs validate against their owning specifications without
  duplicating those schemas here.

## Related documents

- **Requirements:** [Processing and provenance](../01-foundation/requirements.md#processing-and-provenance)
- **Previous interface:** [Capture Pipeline](capture-pipeline.md)
- **Runtime:** [Runtime Architecture](../02-architecture/runtime.md)
- **Configuration:** [Configuration](configuration.md)
- **Current state:** [Current Status](../STATUS.md)
