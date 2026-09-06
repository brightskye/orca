---
id: SPEC-PROCESSING-PIPELINE
title: Orca Processing Pipeline Specification
document_type: specification
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
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
  [Capture Pipeline](capture.md);
- the immediately preceding turn overlap when needed;
- the current Conversation Continuation Summary;
- the current Project Summary when the run is project-scoped;
- a bounded same-scope set of relevant current Typed Memory Records;
- pending same-scope Knowledge Candidate targets within the shared related
  context budget;
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

Measure semantic output as compact UTF-8 JSON of the supplied proposal fields.
Exclude the Project Summary's locally rendered `body` and fixed `authority`:
the body repeats the supplied summary fields and must not count a second time.
All supplied semantic fields remain counted; genuinely oversized proposals are
still rejected against the unchanged output ceiling.

## Required behavior

### Chunking and selection

1. The Processor MUST process eligible new turns chronologically.
2. A backlog larger than one chunk MUST become sequential runs, each with its
   own Run Manifest and checkpoint advancement.
3. A chunk SHOULD split at a turn boundary. A single oversized turn MUST be
   segmented deterministically while preserving its conversation ID, turn ID,
   segment order, source timestamp, and provenance. Every selected turn,
   including an unsegmented turn, MUST receive the uniform source-segment
   identity defined by the [Provenance Ledger](provenance.md).
4. New evidence MUST NOT be silently truncated. The Processor MUST reduce the
   chunk or segment an oversized turn.
5. Related records MUST be same-scope and current. If the complete input still
   exceeds its ceiling, the Processor MUST remove the lowest-ranked related
   records first.
6. Project Summary input MUST be absent outside project scope.

The composed pipeline loads current records and pending candidates through
Storage before selection. Candidates share the existing related-context count
and token ceilings; they do not receive an additional budget. When a provider
exposes exact local request measurement, Processor fits that representation by
removing lowest-ranked candidates, related records, and optional preceding
overlap. It preserves new evidence and both continuation/project summaries.
If mandatory context still cannot fit, the run fails before a provider call and
leaves its evidence pending; it does not silently truncate or discard history.

### Semantic-provider Seam

The Codex adapter runs only the qualified static CLI version through a
bubblewrap filesystem and process boundary. The boundary exposes the executable,
the current disposable workspace, one file-backed authentication file, and
TLS/DNS support files. It supplies an explicit minimal environment and mounts
no vault, source store, checkout, user configuration, plugins, shell, or code-mode
host. Agent capabilities are disabled; advertised inert tool stubs must fail
when invoked. Missing isolation prerequisites or version drift MUST fail closed
without an unconfined fallback. The interface qualification and its real-CLI
sentinel test are recorded in Current and Test Strategy.

Each typed record, conflict, supersession, or candidate instruction MUST name
the supporting Owner input `segment_ref` values in a nonempty
`source_segment_refs` list. A locator is `<turn_id>#<segment_index>` within the
current conversation input. Missing, duplicate, unknown, or assistant-only
references are invalid. Processor derives semantic timestamps from the cited
source timestamps rather than trusting provider-supplied dates; support-only
operations preserve the target's semantic timestamp. Storage maps these exact
locators to the current Manifest's `src-*` identities. Structural cumulative
summaries may bind all relevant current input; this does not justify assigning
every Owner segment to every individual memory operation.

The primary continuity output is a cumulative Conversation Continuation Summary.
Use its previous revision and new evidence to preserve useful earlier outcomes,
reasons, tentative ideas, open questions, and next steps. A conversation need
not produce a Typed Memory Record or Knowledge Candidate to be worth continuing.

A provider should return no Project Summary proposal for support-only or
no-change runs. If it supplies one anyway, Storage leaves the existing Project
Summary untouched and continues publishing independently valid conversation
context and operations. It applies Project Summary refreshes only when a
material record change requires one.

The Codex adapter supplies selected Typed Memory Records as exact semantic
fields, including null sections, instead of a rendered Markdown body. A
`support` proposal must copy those fields unchanged; paraphrasing is rejected
by the existing deterministic meaning check.

The Codex provider serialization MUST contain only selected segment text and
required metadata, never the complete parent turn through a nested object.
Its fixed prompt and output schema are included in the local conservative input
estimate; overflow fails before invocation. This does not establish isolation
from the Codex agent's own tools or context; Current owns that readiness gap.

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
- that every cited source segment belongs to the current processing input;
- that Governance resolved the scope without semantic guessing;
- that a proposed target exists and remains in the same scope;
- that an existing record's identity and scope do not change;
- lifecycle and conflict transitions owned by the
  [Memory Model](memory.md);
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
segment bindings for zero or more contract-owned artifacts. Each instruction
identifies its accepted operation and source support; Storage assigns run-local
operation references, stable artifact identity where required, physical
representation, and output references according to:

- [Memory Model](memory.md) for structural summaries, Typed Memory
  Records, conflicts, and Conflict Overflow Candidates;
- [Knowledge Candidates](knowledge-candidates.md) for ordinary candidates;
- [Interaction Preferences](interaction-preferences.md) for admitted
  observations and affected derived profiles; and
- [Provenance Ledger](provenance.md) for the Run Manifest and checkpoint.

A valid output-free result MUST become a successful `no_memory` Run Manifest.

## Invariants

- Exactly one authorized local WSL Processor handles a run under one local OS
  lock.
- Semantic output proposes meaning but grants no identity, placement, safety, or
  authority.
- Source references in validated output are a subset of the current bounded
  input.
- Every accepted operation retains its exact current-run source-segment
  bindings through the Run Manifest.
- Provider or deterministic-validation failure creates no publication intent or
  derived artifact. Interrupted publication may leave only the fixed
  intent-bound before/after state; it advances no checkpoint until recovery
  publishes the Run Manifest.
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
| Interrupted artifact or Manifest publication | Recover from the fixed local publication intent without another provider call, or fail closed for human repair |

When proposed artifacts are prepared together, publication is recoverable but
not described as transactionally atomic. Storage first publishes the complete
private local publication intent, then artifacts, the immutable Run Manifest,
and the checkpoint in the order defined by the Provenance Ledger.

## Idempotency

Durable Run Manifests are the processed-source authority. Exact successful
segment replay MUST make no semantic call and create no duplicate artifact. A
known segment identity with a different whole-turn hash, segment range, segment
hash, count, or same-policy representation MUST fail closed. A redaction or
segmentation-policy change requires governed reprocessing rather than being
treated as an unrelated new segment.

## Security and privacy

Provider input MUST be the minimum bounded, permitted, redacted context needed
for the current run. The Processor MUST NOT receive excluded or unredacted
capture content. Every generated durable output MUST pass deterministic secret
scanning before publication, indexing, synchronization, recall, or exposure to
another agent.

## Implementation status

[Current](../project-record/current.md) owns implementation status, including
pending findings on provider serialization, budgets, and context composition.
The required behavior above remains the contract against which those findings
are assessed.

## Acceptance criteria

- Budget tests cover every category ceiling and complete input/output ceilings.
- Backlog and oversized-turn fixtures preserve chronological segment identity
  without truncation and create separate replay-safe run receipts.
- Provider proposals cannot assign deterministic Storage or authority fields.
- Every controlled operation passes valid cases and rejects missing-target,
  cross-scope, identity-change, unsupported-transition, and secret-output cases.
- Every accepted operation cites exact current-run source segments and its
  logical artifact identity.
- Exact replay performs no semantic call; a valid abstention publishes
  `no_memory`; failed validation leaves the checkpoint unchanged.
- Published outputs validate against their owning specifications without
  duplicating those schemas here.

## Related documents

- **Requirements:** [Processing and provenance](requirements.md#processing-and-provenance)
- **Previous interface:** [Capture Pipeline](capture.md)
- **Runtime:** [Runtime Architecture](../architecture/README.md#runtime)
- **Configuration:** [Configuration](configuration.md)
- **Current state:** [Current Status](../project-record/current.md)
