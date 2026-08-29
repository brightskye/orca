---
type: memory-record-contract
status: phase-1-current
version: orca-memory-record/0.13
filename-policy: orca-memory-filename/0.1
layout-policy: orca-memory-layout/0.1
relationship-policy: orca-memory-relations/0.1
record-schema: orca-memory/0.2
status-policy: orca-memory-status/0.1
variant-policy: orca-memory-variant/0.4
review-policy: orca-memory-review/0.2
overflow-policy: orca-conflict-overflow/0.1
body-policy: orca-memory-body/0.1
updated: 2026-08-29
---

# Phase 1 Memory Record Contract

> [!WARNING]
> Archived compatibility source. Current behavior is owned by the
> [Memory Model Specification](../../03-specifications/memory-model.md).

> [!NOTE]
> This document is a compatibility mirror. The normative owner is the
> [Memory Model Specification](../../03-specifications/memory-model.md). Do not edit
> this mirror independently.

## Purpose

This contract makes Orca's living Markdown memory predictable to humans,
processors, and future implementations. It governs filenames, the physical
placement of Shallow Memory, and safe relationships between memory documents.
It also defines the core Typed Memory Record frontmatter and the separation
between current meaning and audit provenance, including conflict review state,
variant bodies, and compact resolution lineage.

The filename is a human discovery surface: before opening a file, a person must
be able to judge its subject and whether it is likely relevant. The filename is
not memory identity, authority, provenance, current status, or a substitute for
indexed retrieval.

## Responsibility

- Processor proposes a controlled `kind` and a concise, kind-appropriate
  `subject`. It never proposes a final path or publishes a file.
- Storage validates the subject, constructs the filename deterministically,
  resolves collisions, and publishes or renames the file.
- Recall resolves memory by scope, metadata, content, and permanent identity. It
  may display filenames but must not infer authority or truth from them.
- A future agent must not invent a filename or directory convention outside this
  contract.

The Storage interface accepts logical identity, scope, kind, and subject rather
than a caller-supplied path. Storage owns every mapping from those fields to a
physical locator. This keeps directory rules out of Processor and Recall.

## Structural summary contracts

Conversation Continuation Summary and Project Summary are structural derived
views, not Typed Memory Records. Neither receives a `memory_id`, participates in
Typed Memory Record matching, or carries source arrays. Run Manifests bind each
published revision to its sources and content hash.

### Conversation Continuation Summary

Each source conversation has one evolving Continuation Summary with this minimal
frontmatter:

```yaml
---
schema_version: orca-conversation-continuation/1
kind: conversation-continuation-summary
authority: noncanonical
conversation_id: <source-conversation-id>
project_id: <project-id-or-null>
---
```

Its body uses exactly these sections, omitting an optional section only when it
has no useful content:

```markdown
# <recognizable conversation purpose>

## Current state

## Important outcomes

## Open questions

## Next steps

## Relevant artifacts
```

It is current continuation context, not a transcript, evidence archive, detailed
decision history, preference profile, or canonical project record. It may be
updated from its prior revision plus newly processed turns. A branch has its own
`conversation_id` and therefore its own file. The configurable default maximum
is 2,000 tokens.

The filename is `<purpose-slug>--<short-conversation-id>.md`, where the purpose
is recognizable to a human and the suffix is the first 12 lowercase hexadecimal
characters of SHA-256 over the canonical conversation ID. Its recall reference
is `conv:<purpose-slug>--<short-conversation-id>`; identity remains the complete
`conversation_id` in frontmatter.

### Project Summary

Each project has at most one evolving `summary.md` with this minimal frontmatter:

```yaml
---
schema_version: orca-project-summary/1
kind: project-summary
authority: noncanonical
project_id: <permanent-project-id>
---
```

Its body is a bounded executive current-state view with purpose, current state,
active workstreams, important outcomes, open questions, next steps, and relevant
Typed Memory Record links when those sections apply. Supporting relationships
use validated `memory_id` values; Storage resolves their current paths when it
renders links. Unresolved conflicts are labelled without selecting a winner,
and superseded detail stays in the Typed Memory Records and Run Manifests.

Processor refreshes the Project Summary only after a material project-memory
change, using its previous revision, changed records, and bounded related current
records. It is rebuildable, carries no independent identity or authority, and
has a configurable default maximum of 2,000 tokens.

## Core Typed Memory Record frontmatter

Every Typed Memory Record uses the following core schema. `project.md` and the
derived `summary.md` are structural artifacts and require separate schemas.

```yaml
---
schema: orca-memory/0.2
memory_id: mem_...
kind: decision
subject: Processed source index
authority: noncanonical
scope: project
scope_id: project_...
status: current
review_state: none
source_updated_at: 2026-08-27T10:15:00Z
created_at: 2026-08-27T10:20:00Z
updated_at: 2026-08-27T10:20:00Z
workstreams: []
---
```

The keys are required even when an allowed value is empty:

- `schema` is exactly `orca-memory/0.2` for this schema version.
- `memory_id` is the permanent opaque Memory Identity.
- `kind` is one controlled Typed Memory Record kind.
- `subject` is the stable human-readable Memory Subject, not its filename slug.
- `authority` is exactly `noncanonical` for Shallow Memory.
- `scope` is exactly `project`, `general`, or `unassigned`.
- `scope_id` is the permanent `project_id` for project scope and the literal
  `general` or `unassigned` for the corresponding fixed scope.
- `status` is the controlled memory-resolution state: `current`, `conflict`, or
  `closed`, as defined below.
- `review_state` is exactly `none`, `required`, `acknowledged`, or `overflow`, as
  defined by the conflict-review state table below.
- `source_updated_at` is the trusted source-turn timestamp that established the
  represented state. For a conflict it is the trusted turn time of the latest
  material change to the active variant set, when one exists, and does not by
  itself select a winner. It uses UTC RFC 3339 form and never derives from
  conversation creation or file-write time. Repeated support and a review-only
  acknowledgement do not advance it; a later turn advances it only when it
  changes or resolves content, status, or conflict lineage.
- `created_at` is the first successful Storage publication time in UTC RFC 3339
  form and does not change.
- `updated_at` is the latest successful material Storage publication time in UTC
  RFC 3339 form. A no-change run does not advance it.
- `workstreams` is a list of controlled Workstream Labels and is empty outside a
  project or when no label applies.

Processor proposes `kind`, `subject`, `status`, `source_updated_at`, and
Workstream Labels from validated evidence. Governance supplies the resolved
scope and `scope_id`. Storage assigns `schema`, `memory_id`, `authority`, derives
and validates `review_state` from validated conflict operations, and assigns
storage timestamps before publication.

Frontmatter does not duplicate the filename, physical path, Markdown body, or
content hash. Run Manifests bind the published path and content hash to the
record identity and schema version.

## Provenance boundary

A Typed Memory Record contains no provenance summary, source counter, manifest
pointer, source hash list, or unbounded source array. Its `memory_id` is the join
key for audit.

Immutable Run Manifests retain the complete supporting source history, including
conversation and turn identities, trusted turn timestamps, normalized source
hashes, processing policy, and published output hashes. Filesystem manifest
lookup is the Phase 1 correctness baseline. An optional local SQLite projection
may map `memory_id` to matching manifests for faster audit; it is disposable and
rebuildable by scanning the manifests.

An exact support-only result writes a successful Run Manifest and advances the
source checkpoint, but it does not rewrite the Typed Memory Record or advance
`source_updated_at` or `updated_at`. Evidence that changes current content,
status, or conflict lineage is a material record update rather than support-only.

## Status policy

`status` describes whether the memory has a usable current state. It does not
describe authority; every Shallow Memory record remains explicitly
`authority: noncanonical`.

- `current`: one clear current state exists and is eligible for ordinary Recall.
- `conflict`: incompatible variants exist and no winner is established. Recall
  may return the record only with an explicit unresolved-conflict label and must
  not synthesize a winner.
- `closed`: the subject is completed, resolved, abandoned, or otherwise inactive
  but remains useful history. Ordinary Recall excludes it unless the Recall
  Request explicitly asks for historical, completed, resolved, or closed memory.

Phase 1 does not use `proposed` because authority already expresses that Shallow
Memory is noncanonical. It does not use whole-file `superseded`; superseded
meaning remains compact lineage inside the living record. It does not use
`expired` because automated retention is outside Phase 1.

Every status transition is a material record update recorded by a Run Manifest.
The exact `conflict` variant and `source_updated_at` representation is governed
by the conflict-lineage structure.

## Ordinary record body

Every `status: current` Typed Memory Record uses one predictable primary section:

```markdown
# <subject>

## Current

<concise applicable meaning>

## Context

<optional bounded context>

## Implications

<optional consequences or operational effect>
```

`## Current` is required. `## Context` and `## Implications` are optional and are
omitted when empty. No other generic section is introduced merely to hold
available text.

The required current meaning follows the controlled record kind:

| Kind | `## Current` meaning |
|---|---|
| Goal | Desired outcome and current direction |
| Decision | Selected choice and essential rationale |
| Knowledge | Supported current understanding |
| Entity | Relevant identifying facts about the entity |
| Identity | Current role, ownership, or relationship |
| Constraint | Operative limitation or rule |
| Open Question | Exact unresolved question and known boundary |
| Lesson | Reusable lesson and where it applies |
| Topic | Bounded current overview |
| Workstream Summary | Current workstream state and outcome |

The body must not embed source lists, manifests, support counters, raw excerpts,
or unrelated open questions. A separate substantive question, decision, goal, or
other logical memory receives its own Typed Memory Record.

A `status: closed` record uses `## Final` for its last applicable meaning and
`## Closure` for the reason it became completed, abandoned, resolved, or
inactive. Ordinary Recall excludes both; an explicit historical request may
retrieve them.

## Conflict variant identity

Every unresolved alternative within one Memory Conflict receives a stable
identifier local to that Typed Memory Record:

```text
v1
v2
v3
```

The full identity of a variant is the pair `(memory_id, variant_id)`. A variant
identifier is not globally unique and grants no separate memory identity,
authority, or scope.

- Storage assigns identifiers monotonically in first-publication order. When a
  current record first becomes conflicted, its existing state becomes `v1` and
  the new incompatible state becomes `v2`.
- An identifier is never reused, renumbered, or reassigned, including after the
  conflict is resolved and its variant moves into compact lineage.
- Processor may target an existing variant for support or resolution or propose
  a genuinely new alternative, but it cannot assign the new identifier.
- Variant identity is not derived from wording, content hashes, source hashes,
  or timestamps because those may change without changing the alternative's
  meaning.
- Run Manifests bind every variant creation, support, change, and resolution to
  its stable identifier and exact sources.
- Every active variant displays a `position_at` Variant Position Timestamp in
  UTC RFC 3339 form. It comes from the actual trusted conversation turn that
  introduced or materially changed that distinct position, never from
  conversation creation, processing, review, or file-write time. Missing or
  untrusted source time is displayed explicitly as unknown rather than inferred.
- Source-turn timestamps may establish chronology across conversations on the
  same trusted host, including a main conversation and its branch. Turn IDs order
  records only within their own conversation and are not cross-conversation
  clocks. Copied branch-prefix turns retain their original identities, hashes,
  and timestamps and do not become new evidence.
- Chronological newness alone does not establish supersession across branches.
  Only a later trusted Owner turn that clearly states or confirms the applicable
  replacement may win. Exploratory, hypothetical, quoted, or ambiguous later
  turns create or support variants without automatically replacing an earlier
  position.
- A support-only turn does not change `position_at`. Its actual timestamp remains
  in the Run Manifest and may be presented separately during Owner review.
- A distinct qualifying Owner source turn that supports an existing variant adds
  one unit of Variant Support Weight; exact replay of the same turn adds none.
  Weight is derived from Run Manifests rather than stored as a mutable counter in
  the record. It informs review but is neither authority nor a vote and cannot
  override the latest-trusted-turn rule or an explicit newer Owner resolution.
- A genuinely distinct third simultaneously unresolved variant is preserved and
  immediately crosses the Conflict Review Threshold, marking review as urgent.
- Crossing the threshold creates no automatic startup notice and injects no
  memory into an agent conversation. Conflict Review begins only when the Owner
  explicitly invokes the review skill. A future dashboard or scheduled
  memory-health report may expose aggregate pending-review state, but neither is
  required by the current Phase 1 flow.
- One living memory record may contain at most three active unresolved variants.
  Every later genuinely distinct position, beginning with `v4`, is stored as a
  durable redacted overflow candidate with its stable record-local variant ID and
  linked by the Run Manifest. Processing continues to record `v5`, `v6`, and
  later overflow positions and support evidence; it does not pause merely because
  overflow exists. Review presents the three active variants and every overflow
  candidate, with pagination when needed, so the bound never discards a position.
- Human-readable conflict headings show the stable identifier, concise variant
  label, and `position_at`.

## Conflict review and resolution

The living Typed Memory Record owns its pending-review state. Phase 1 creates no
duplicate review-queue record. A durable redacted overflow candidate remains a
separate provisional artifact when the three-active-variant bound is exceeded.

`status` and `review_state` are independent axes:

| `status` | `review_state` | Meaning |
|---|---|---|
| `current` | `none` | One usable current position exists. |
| `conflict` | `none` | Two variants are reviewable but have not crossed the urgency threshold. |
| `conflict` | `required` | Three active variants make review urgent. |
| `conflict` | `acknowledged` | The Owner reviewed the conflict and chose to keep it unresolved. |
| `conflict` | `overflow` | One or more `v4+` positions exist as overflow candidates and urgent review remains visible. |
| `closed` | `none` | The memory is inactive retained history. |

Every record with `status: conflict` is eligible for the review skill regardless
of `review_state`. The default review order is `overflow`, `required`, `none`,
then `acknowledged`. Selecting a variant or supplying an Owner resolution produces
`current` plus `none`. Keeping a conflict unresolved produces `acknowledged` when
no overflow exists and otherwise remains `overflow`. A third distinct active
position changes `none` or `acknowledged` to `required`; `v4` changes it to
`overflow`. `current` or `closed` with any non-`none` review state fails
validation.

The review skill uses progressive disclosure. Its default view contains only the
minimum information needed to demonstrate the conflict:

- memory subject and scope;
- a one-line summary for every active variant and overflow position;
- each active variant's stable ID, `position_at`, and derived support weight; and
- a visible count of any additional audit details available.

Only an explicit Owner request expands full distilled variant text, source
conversation and turn references, support history, or manifest details. Raw
conversation text is not stored by Orca and is inspected from the agent-owned
source only when explicitly requested, still available, and permitted.

Conflict Review permits exactly three Owner outcomes:

1. select one existing variant as current;
2. resolve the conflict using an applicable position supplied by the Owner,
   including an Owner-directed merge or replacement; or
3. keep the conflict unresolved.

Selecting a variant or supplying a resolution changes the record to `current`,
places the resulting current meaning in the main body, clears pending review,
and retains compact lineage identifying every prior variant and its disposition.
The resolution turn and complete evidence remain in the Run Manifest. Full
source histories, support lists, and repeated evidence are not copied into the
living record. Keeping the conflict unresolved preserves its variants and review
state as `acknowledged`; it does not synthesize a winner. That review-state-only
change advances Storage `updated_at` but not semantic `source_updated_at`.

### Conflict body

An unresolved record uses one stable section per active variant:

```markdown
# <subject>

## Conflict

### v1 — <concise label>

Position at: <UTC RFC 3339 timestamp or unknown>

<distilled position>
```

Sections remain in monotonically assigned variant order. Support weights and
source lists are derived during review rather than copied into the body.

### Resolved body and compact lineage

A resolved record places only the applicable meaning in `## Current`.
It retains a bounded `## Resolution lineage` list containing each former stable
variant ID, its concise label, its `position_at`, and disposition: `selected`,
`not selected`, or `replaced by Owner resolution`. The current position has no
new variant ID; its identity is the record's permanent `memory_id`.

```markdown
# <subject>

## Current

<applicable current meaning>

## Resolution lineage

- `v1` — <label> — not selected — <position_at>
- `v2` — <label> — selected — <position_at>
```

When the Owner supplies a new resolution, every prior variant disposition is
`replaced by Owner resolution`. The resolving Owner turn establishes
`source_updated_at`; the Run Manifest retains the exact resolution operation and
complete evidence.

## Conflict Overflow Candidate contract

Each distinct `v4+` position is one redacted, noncanonical Conflict Overflow
Candidate. Its full identity remains `(memory_id, variant_id)`; it receives no
separate candidate identity.

```yaml
---
schema: orca-conflict-overflow/0.1
memory_id: mem_...
variant_id: v4
subject: Processed source index
authority: noncanonical
scope: project
scope_id: project_...
position_at: 2026-08-28T09:30:00Z
created_at: 2026-08-28T09:35:00Z
updated_at: 2026-08-28T09:35:00Z
---
```

The body contains only a human-readable heading and `## Position` with the
redacted distilled position. It contains no raw conversation text, source array,
support counter, manifest pointer, or embedded processing history. Run Manifests
bind sources, hashes, support, and every lifecycle operation to the stable pair.

Storage places candidates by scope:

```text
System/Orca Memory/candidates/conflicts/
  projects/<project-alias-slug>/
  general/
  unassigned/
```

The filename is
`<subject-slug>--<short-memory-id>--<variant-id>.md`, for example
`processed-source-index--a81f3c--v4.md`. Storage alone constructs and relocates
the path. A project-alias change moves matching candidates without changing
their identity.

Support-only evidence writes a Run Manifest without rewriting the candidate or
its timestamps. A material change to the same position may update its distilled
body and `position_at`; a genuinely different position receives the next stable
variant ID and another candidate file. Privacy redaction and deterministic secret
scanning run before every publication.

Conflict Overflow Candidates are excluded from Project and Workstream Summaries,
Retrieval Projections, ordinary Recall, and automatic session context. Only the
explicit review skill reads them, together with the target record's active
variants. Phase 1 applies no age-based retention: candidates persist until
explicit Owner resolution.

Resolution first publishes the resolved living record and a Run Manifest that
records every active and overflow disposition. Candidate cleanup occurs only
after that commit. If cleanup is interrupted, the latest resolved lineage and
manifest make the leftover candidate ineligible for review, and later idempotent
cleanup may delete it. Keeping the conflict unresolved preserves every candidate.

## Physical Shallow Memory layout

Phase 1 uses one human-readable directory per scope and one directory per
record kind. It does not use opaque ID-only paths, ID-prefix shard directories,
or an intermediate `records/` directory.

```text
System/Orca Memory/
  shallow/
    projects/
      <project-alias-slug>/
        project.md
        summary.md
        conversation-summaries/
        workstreams/
        goals/
        decisions/
        knowledge/
        entities/
        identities/
        constraints/
        open-questions/
        lessons/
        topics/
    general/
      conversation-summaries/
      goals/
      decisions/
      knowledge/
      entities/
      identities/
      constraints/
      open-questions/
      lessons/
      topics/
    unassigned/
      conversation-summaries/
      goals/
      decisions/
      knowledge/
      entities/
      identities/
      constraints/
      open-questions/
      lessons/
      topics/
```

Storage creates a kind directory only when its first record is published. Empty
directories shown above are conceptual and need not exist.

### Project directories and registry

- Storage derives `<project-alias-slug>` from the Owner-accepted Project Alias
  using the portable slug rules in this contract. It must be unique under
  case-insensitive comparison.
- `project.md` stores the permanent `project_id`, current Project Alias, and
  project identity metadata. The directory name remains a locator, not project
  identity.
- The collection of project identity records is the durable logical Orca
  Project Registry. A local registry index is disposable and rebuildable from
  those files; Phase 1 has no separate `registry.md`.
- Changing a Project Alias preserves `project_id`. Storage performs the governed
  directory move, records the old and new locators in the Run Manifest, and
  reconciles the local indexes.
- `summary.md` is the one current Project Summary for that Project Memory. It is
  a rebuildable view and has no independent `memory_id`.

### Record placement

| Record kind | Directory inside its scope |
|---|---|
| Workstream Summary | `workstreams/` inside a project only |
| Goal | `goals/` |
| Decision | `decisions/` |
| Knowledge | `knowledge/` |
| Entity | `entities/` |
| Identity | `identities/` |
| Constraint | `constraints/` |
| Open Question | `open-questions/` |
| Lesson | `lessons/` |
| Topic | `topics/` |

Each substantive logical memory has one living Markdown file. New evidence
updates that file only when current content, status, or conflict lineage changes;
support-only evidence remains in Run Manifests rather than creating evidence
files or rewriting the memory.
Conflicting variants and compact supersession lineage remain in that same
logical record. Full processing history belongs in immutable Run Manifests.

A Conversation Continuation Summary remains one evolving structural file per
conversation ID under `conversation-summaries/`. A Workstream Summary is an
optional Typed Memory Record under `workstreams/`; the folder does not make a
workstream a scope, and detailed workstream-labelled records remain in their
normal kind directories.

General and Unassigned are fixed scope roots. They have no `project.md`, Project
Summary, or Workstream Summary because they are not Project Memory scopes.

The following never creates a Shallow Memory file:

- an individual source turn or raw conversation excerpt;
- a provenance item that merely supports an existing logical memory;
- a valid `no_memory` result; or
- a Run Manifest, Knowledge Candidate, Interaction Observation, or other
  artifact governed outside Shallow Memory.

### Human and machine retrieval

Every substantive Markdown file must be useful when opened directly; a Project
Summary is an overview, not the only readable project memory. Human-readable
directories and filenames help manual discovery and audit.

Machine retrieval still filters and searches indexed scope, identity, metadata,
and content. It does not infer memory identity, authority, or project membership
from a path. Before indexing, Recall deterministically builds a Retrieval
Projection: current records expose `## Current`, unresolved conflicts
expose clearly labelled active variants, and resolved `## Resolution lineage` is
excluded from ordinary semantic search. Historical requests may inspect lineage
explicitly. Each projection binds the source-file content hash so a stale indexed
version fails closed until reconciliation. The local retrieval and project-
registry indexes are rebuildable from the Markdown records.

Phase 1 adds no filesystem sharding below these kind directories. If measured
file counts later require sharding, it must be introduced as a versioned Storage
policy migration without changing logical identity or the interfaces used by
Processor and Recall.

## Relationship policy

Phase 1 does not create a general graph of `related-to` links. A relationship is
stored only when it follows from a verified Orca fact already required by the
record model:

- scope membership through `project_id` or a fixed General or Unassigned scope;
- exact source conversation and turn provenance;
- Workstream Labels within one Project Memory scope;
- supporting `memory_id` references used by a Project Summary or Workstream
  Summary; or
- compact conflict and supersession lineage inside one living record.

Stable IDs and controlled labels carry the relationship. A filename or path is
only a current locator and must not be stored as the relationship identity.
Processor must not propose arbitrary file paths or a generic semantic
`related-to` edge merely because two records appear similar.

Ordinary Typed Memory Records contain no speculative cross-file Markdown links.
Project Summary and Workstream Summary may render human-readable clickable links
for supporting `memory_id` values already validated as part of that summary.
Storage resolves each ID to its current path and regenerates those derived links
after an applicable rename. The link grants no scope, authority, or provenance.

Relationship validation fails closed when a referenced identity is missing,
crosses an impermissible scope, or conflicts with structured provenance. Recall
and retrieval must still apply their normal hard filters and cannot use a link to
bypass them. Phase 1 requires no graph database, model-generated ontology, or
general entity-resolution pipeline.

## Filename form

Typed Memory Records use:

```text
<semantic-slug>--<short-id>.md
```

For example:

```text
build-business-knowledge-system--a1b2c3d4e5f6.md
processed-source-index--7f18c29a04de.md
codex-rollout-storage--42d783a6bc10.md
```

The leading semantic slug must carry enough meaning for a human to decide
whether to open the file. The suffix prevents collisions and binds the locator
to the permanent identity without exposing the full ID.

Reserved structural files do not use a suffix:

- `project.md` identifies one project and its alias.
- `summary.md` is the one current Project Summary in that project.

## Kind-specific subjects

The subject identifies the stable concern appropriate to the record kind. It is
not a summary of the source conversation.

| Kind | Filename subject | Good example | Avoid |
|---|---|---|---|
| Workstream Summary | Workstream purpose or outcome | `phase-1-codex-memory--...md` | `workstream-b1--...md` |
| Goal | Independently manageable desired outcome, normally expressed with a verb | `build-business-knowledge-system--...md` | `knowledge-system--...md` |
| Decision | Stable issue or question decided, not the selected answer | `processed-source-index--...md` | `use-sqlite--...md` |
| Knowledge | Stable subject of the knowledge | `codex-rollout-storage--...md` | `important-codex-fact--...md` |
| Entity | Recognizable entity name, qualified only when required to disambiguate | `agentcairn--...md` | `retrieval-tool--...md` |
| Identity | Recognizable identity and role | `orca-owner--...md` | `user-1--...md` |
| Constraint | Stable constrained area, not the current limit or value | `canonical-write-authority--...md` | `one-writer-only--...md` |
| Open Question | Stable unresolved question subject without status words or punctuation | `shallow-memory-size-limits--...md` | `unresolved-question-3--...md` |
| Lesson | Stable situation or practice learned | `safe-publication-order--...md` | `important-lesson--...md` |
| Topic | Recognizable topic name | `secret-containment--...md` | `miscellaneous--...md` |

A Goal filename follows the desired outcome. A Decision filename follows the
decision subject so a later change in the answer does not make the filename
false. Entity and Topic filenames follow the entity or topic because those kinds
do not express an outcome.

## Semantic slug construction

Storage applies these rules in order:

1. Normalize the proposed subject to Unicode NFC and lowercase it.
2. Replace whitespace, underscores, path separators, and punctuation with a
   single hyphen. Retain Unicode letters and decimal digits.
3. Collapse repeated hyphens and remove leading or trailing hyphens.
4. Limit the semantic slug to 72 characters. Truncate at the last complete word
   when practical, then remove any trailing hyphen.
5. Reject an empty or non-descriptive slug rather than falling back to an
   ID-only filename.
6. Reject Windows reserved names, control characters, trailing dots or spaces,
   and any filename that is not portable between the Phase 1 Windows/WSL
   filesystems.

Generic slugs are invalid unless the word is part of a more descriptive subject:

```text
memory
record
note
item
misc
untitled
goal-1
decision-final
current-goal
latest-decision
```

## Short ID construction

Storage derives `short-id` from the permanent full identity:

```text
short-id = first 12 lowercase hexadecimal characters of
           SHA-256(canonical UTF-8 full ID)
```

If that suffix collides with a different full ID in the same destination,
Storage extends both the comparison and proposed suffix by four hexadecimal
characters until it is unique. The full `memory_id` remains in frontmatter and
is the identity used for matching, manifests, and retrieval.

## Stability and renaming

- Changes to content, status, workstream labels, sources, the current decision,
  or the current goal wording do not by themselves rename a file.
- Storage may rename a file when the Memory Subject was corrected or evolved so
  materially that the old filename would mislead a human.
- A rename preserves the full `memory_id`. It is a locator change, not a new
  memory or source revision.
- Storage records the old path, new path, filename-policy version, and resulting
  content hash in the Run Manifest and reconciles the retrieval index.
- Direct model output and ad hoc agent code must not rename memory files.

For example, the same evolving Goal may be renamed without changing identity:

```text
build-owner-llm-wiki--a1b2c3d4e5f6.md
build-business-knowledge-system--a1b2c3d4e5f6.md
```

## Safety

- Filenames must not contain credentials, secret values, private-conversation
  content, raw prompt excerpts, or other content excluded by Orca governance.
- A filename must not claim canonical authority or certainty through words such
  as `approved`, `verified`, or `final` unless those words are part of the stable
  subject itself and the governing artifact permits that claim.
- A valid `no_memory` result creates no memory filename.

## Policy versioning

Every Run Manifest that creates, renames, relocates, or changes structured
relationships records the applicable filename-policy, layout-policy, and
relationship-policy versions. A future policy revision does not silently rename
existing files or turn a valid historical locator or relationship into an
integrity failure. Migration requires a separate governed operation.

## Acceptance examples

These examples are normative:

| Input meaning | Required result |
|---|---|
| Goal: build a business knowledge system | `build-business-knowledge-system--<short-id>.md` |
| Same Goal expands from Owner support to business support | Same `memory_id`; rename only if the previous subject is now misleading |
| Decision changes from JSONL to SQLite | Keep a subject filename such as `processed-source-index--<short-id>.md`; update the living document |
| Two independent goals mention the same entity | Two files named by their separate outcomes, each with its own `memory_id` |
| New evidence exactly supports an existing memory without changing its state | Do not rewrite the memory; publish the successful Run Manifest and checkpoint |
| Processor cannot produce a descriptive safe subject | Reject or abstain; never publish an ID-only or generic filename |
