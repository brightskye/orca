---
type: system-design
status: active
updated: 2026-08-29
---

# Orca Memory System Design

> [!WARNING]
> Archived migration source. Current architecture and exact behavior are owned
> by the [Documentation Index](../../README.md).

> [!NOTE]
> Architecture ownership moved to
> [`02-architecture/README.md`](../../architecture/README.md) and its child
> views on 2026-08-29. This file remains a migration source for embedded exact
> behavior and decision rationale until those subjects reach their PDS owners.
> Do not edit its architecture summaries independently.

## Purpose

Orca is a governed, local-first memory system for AI agents. It turns supported
agent conversations into traceable evidence, provisional working memory, and
reviewable knowledge proposals. It gives agents bounded recall without making
an agent, model, synchronization tool, or retrieval implementation authoritative.

Orca is delivered in three usable phases:

1. Codex Desktop uses one WSL runtime and one local vault.
2. Multiple local agents share the same local vault.
3. Local and remote agents use synchronized local and VPS vault replicas.

Phase 1 is current. Phases 2 and 3 are candidate directions that would extend
the deployment topology without changing the authority model or postponing core
memory behavior established here. Their exact future designs are not accepted by
this document.

## Design goals

- Preserve useful context from supported conversations.
- Keep every derived artifact traceable to its source evidence.
- Keep provisional memory visibly separate from accepted durable knowledge.
- Give agents small, relevant, authority-labelled recall results.
- Adapt presentation from inspectable, scoped interaction feedback without
  inferring personality or sensitive traits.
- Keep private memory and runtime state local to their permitted locations.
- Make source reading, processing, storage, and retrieval safe to retry.
- Allow retrieval and synchronization implementations to be replaced.

## Non-goals

- Orca does not treat model output as accepted knowledge.
- Orca does not automatically modify Canonical Memory.
- Orca is not a general document-ingestion system in the three delivery phases.
- Orca does not provide a public memory or administration interface.
- Orca does not infer personality, emotion, motives, mental health, or other
  sensitive traits from interaction behavior.
- Phase 1 does not implement multi-agent visibility or vault synchronization.

## Authority and artifacts

The Owner is the final authority. Artifacts have different roles and must not be
treated as interchangeable:

| Artifact | Purpose | Authority |
|---|---|---|
| Canonical Memory | Owner-accepted durable knowledge | Authoritative |
| Conversation Evidence | Transient normalized selection of supported source records supplied to processing | Noncanonical evidence |
| Shallow Memory | Compact provisional context for near-term recall | Noncanonical working memory |
| Conversation Continuation Summary | Evolving structural summary for continuing one source conversation ID | Noncanonical derived view |
| Typed Memory Record | Categorized project, General, or Unassigned current memory, traceable through Run Manifests | Noncanonical working memory |
| Project Summary | Bounded rebuildable overview referencing current project records | Noncanonical derived view |
| Knowledge Candidate | Proposed durable fact, decision, preference, lesson, or state | Noncanonical proposal |
| Conflict Overflow Candidate | Redacted provisional `v4+` position retained outside a bounded conflict record until Owner resolution | Noncanonical proposal |
| Interaction Observation | Scoped evidence about the Owner's response to presentation behavior | Noncanonical evidence |
| Adaptive Interaction Profile | Weighted and rebuildable presentation baseline derived from observations | Noncanonical working context |
| Confirmed Interaction Preference | Owner-confirmed durable presentation preference | Canonical after governed human acceptance |
| Run Manifest | Processing lineage, inputs, outputs, configuration, and status | Noncanonical operational record |
| Retrieval Index | Local projection used to find permitted Markdown | Derived and rebuildable |

Synchronization never changes an artifact's authority. A synchronized candidate
is still a candidate, and a retrieval result is never authoritative merely
because it ranked highly.

## System context

```text
supported agent conversation
          |
          v
  Conversation module
          |
          | presents transient Conversation Evidence
          v
     Processor module
          |
          | publishes Shallow Memory, candidates,
          | interaction artifacts, and manifests
          v
     Storage module --------------------------> configured Orca vault
                                                        |
Canonical Memory + permitted Shallow Memory ------------+
          |
          v
  retrieval adapter -> Recall module -> requesting agent
```

The configured vault owns memory artifacts. The project checkout owns source
code, tests, and technical documentation. Local runtime state supports
operation but carries no memory authority.

## Module responsibilities

Each module owns one responsibility behind a small interface.

### Semantic and deterministic responsibility seam

The semantic provider may propose meaning; it never grants authority or decides
whether an artifact is safe to publish. Orca's deterministic modules constrain,
validate, identify, place, and publish those proposals. The retrieval adapter is
a separate non-authoritative seam: it may rank already permitted projections but
cannot change their meaning, scope, status, or authority.

| Work | Responsible implementation | Contractual result |
|---|---|---|
| Identify eligible source events and exclude private, system, tool, reasoning, injected, subagent, and ambiguous content | Conversation module, deterministic | Only permitted normalized Conversation Evidence reaches processing |
| Redact obvious credentials and version the processed representation | Conversation module, deterministic | Redacted text and policy-bound source hashes |
| Select chronological chunks, enforce context budgets, and bind source references | Processor module, deterministic | Bounded provider input with exact provenance |
| Interpret conversational meaning; propose summary text, record kind and subject, add/support/update/supersede/conflict/abstain operations, and interaction observations | Semantic provider | Untrusted structured proposals only |
| Decide whether Owner wording expresses replacement, conflict, feedback, or another semantic relationship | Semantic provider | A proposal that remains subject to deterministic validation |
| Validate schemas, allowed values, source references, target existence, same-scope matching, trusted timestamps, lifecycle transitions, and conflict bounds | Processor and Governance modules, deterministic | Accepted controlled proposal or fail-closed rejection |
| Resolve project scope from accepted mappings and Owner-confirmed identity | Governance module, deterministic | `project`, `general`, or `unassigned` scope without semantic guessing |
| Assign `memory_id`, variant IDs, schemas, authority labels, timestamps, filenames, paths, and hashes | Storage module, deterministic | Stable identity and contract-compliant physical artifacts |
| Scan generated output for credential-like values, publish artifacts and Run Manifest, then advance checkpoint last | Storage module, deterministic | Recoverable publication or no committed checkpoint |
| Consolidate validated interaction observations and compile fixed guidance templates | Processor and Recall modules, deterministic | Rebuildable profile state and exact bounded guidance |
| Build Retrieval Projections and apply authority, visibility, scope, status, hash, and budget filters | Recall module, deterministic | Only eligible labelled projections reach ranking |
| Rank permitted Retrieval Projections for an explicit Recall Request | Replaceable retrieval adapter | Non-authoritative candidates returned to Recall for bounded presentation |

Natural-language interpretation and retrieval relevance are evaluated for
quality, not asserted as deterministic correctness. Deterministic tests stop at
source selection, policy enforcement, proposal validation, state transitions,
artifact construction, publication, projection, filtering, and bounded output.

### Conversation module

- Positively identifies supported events from an authorized connector.
- Uses genuine Owner prompts and steering as evidence and only final or directly
  referenced assistant messages as context.
- Excludes injected envelopes, hidden reasoning, system and tool protocol,
  private sessions, subagents, and ambiguous events through a versioned
  deterministic privacy gate.
- Locally redacts obvious credential values using versioned patterns before
  spooling or distillation while retaining permitted surrounding context.
- Normalizes source identity, ordering, provenance, and content hashes.
- Presents Conversation Evidence transiently to the Processor without creating
  a second raw conversation archive.

Conversation does not interpret events as durable knowledge or create Shallow
Memory.

### Processor module

- Receives eligible new Conversation Evidence after source deduplication.
- Processes eligible new turns chronologically in bounded chunks. Each semantic
  call receives only a minimal preceding-turn overlap, the current Conversation
  Continuation Summary, the current Project Summary when project-scoped, a bounded
  scope-filtered set of relevant current Typed Memory Records, and the capped
  new Conversation Evidence under the Phase 1 limits below.
- Never loads every prior conversation or every record in a Project Memory. When
  pending evidence exceeds one chunk, each chunk becomes a sequential processing
  run with its own Run Manifest and checkpoint.
- Splits chunks at turn boundaries when possible. An oversized single turn is
  segmented deterministically while preserving its source conversation ID, turn
  ID, segment order, and provenance. Processor enforces the complete input budget
  before invoking the semantic provider.
- Uses an initial hard ceiling of 20,000 input tokens per semantic call,
  including fixed processing instructions. Category ceilings are 8,000 tokens
  of new Conversation Evidence; one preceding turn up to 1,000 tokens; 2,000
  tokens for the current Conversation Continuation Summary; 2,000 tokens for the current
  Project Summary; and at most five relevant Typed Memory Records totalling
  5,000 tokens. Semantic output is capped at 4,000 tokens.
- Does not silently truncate new evidence to satisfy the ceiling. It reduces the
  chunk or segments an oversized turn; lowest-ranked related records are removed
  first when the complete input would otherwise exceed the ceiling.
- Validates the returned structure and binds it to exact source evidence.
- Rejects proposed outputs containing credential-like values before Storage can
  publish or index them.
- Proposes semantic content for Shallow Memory and Knowledge Candidates plus
  untrusted Interaction Observation Proposals. Storage constructs the immutable
  Run Manifest from validated sources, dispositions, and published outputs.
- May propose the controlled Shallow Memory content: Conversation Continuation
  Summary, Project Summary, and typed records for workstream summary, decision,
  knowledge, entity, identity, goal, constraint, open question, lesson, and
  topic. Project Summary remains a derived view without its own `memory_id`.
- Proposes the semantic core frontmatter fields `kind`, `subject`, `status`,
  `source_updated_at`, and Workstream Labels but does not assign identity,
  authority, scope, storage timestamps, paths, or hashes.
- Keeps one evolving Conversation Continuation Summary per conversation ID. Conversations in
  one project contribute typed records to the same Project Memory scope;
  workstreams are relationship labels within that scope, not nested scopes.
- Treats each logical memory as having one permanent opaque `memory_id`,
  independent of its content hash, source hashes, filename, and revisions.
  Storage assigns that identity for a validated new record; Processor may only
  target an existing identity supplied in its bounded same-scope candidates.
  Matching uses kind, normalized subject or entity, and provenance to find that
  bounded candidate set.
- Treats each Typed Memory Record as a living current-state document with compact
  supersession or conflict lineage, not as an immutable event history. Durable
  Run Manifests remain the processing audit trail.
- Uses only `current`, `conflict`, and `closed` as record status. Current records
  have one usable state; conflict records expose no winner; closed records remain
  history and are excluded from ordinary Recall unless explicitly requested.
- Proposes `add`, `support`, `update`, `supersede`, `conflict`, or `abstain`
  against that bounded set. Exact support-only evidence creates a successful Run
  Manifest without rewriting the memory; changed information about a confirmed
  match revises that memory; uncertain matches remain separate rather than being
  merged.
- When otherwise matching project records conflict, makes a later trusted Owner
  position current only when that turn clearly states or confirms the applicable
  replacement. It retains the older position as superseded while Run Manifests
  preserve both source chains.
- Uses trusted source-turn timestamps to establish chronology, not to establish
  supersession by themselves. It does not use conversation creation time or
  derived-record write time to decide which position is newer.
- If replacement intent is unclear, or the relevant source-turn timestamps are
  equal, missing, untrusted, or otherwise incomparable, preserves every
  distilled variant under one logical memory, marks it as a Memory Conflict, and
  selects no current variant.
- Addresses each Conflict Variant by a stable record-local identifier such as
  `v1`. Storage assigns identifiers monotonically and never reuses or renumbers
  them; Processor may target an existing identifier or propose a new alternative
  but cannot assign its identifier.
- Emits only controlled Memory Relationships established by scope, exact
  provenance, Workstream Label, validated summary support, or in-record lineage.
  It does not invent file paths or general semantic `related-to` edges.
- Treats semantic Interaction Observation Proposals as untrusted. Deterministic
  validation admits only controlled dimensions, contexts, scopes, evidence
  classes, source references, and dispositions before an observation enters a
  Run Manifest.
- Consolidates validated observations deterministically by distinct source
  conversation, scope, context, dimension, direction or value, source-turn time,
  and policy version. Profiles contain only active or conflicting current state;
  they do not duplicate observation histories.
- Asks Storage to publish outputs and advance progress after successful writes.

Processor proposes meaning but cannot assign memory identity, choose physical
placement, or grant canonical authority.

### Project identity

- The logical Orca Project Registry gives each project one permanent opaque
  `project_id` and one Owner-selected, human-readable, unique alias. The alias is
  accepted in recall requests and may change without changing project identity.
- Host-local Project Root Mappings associate normalized Git or explicitly
  selected non-Git roots with a `project_id`. Multiple roots may map to one
  project; absolute host paths are never synchronized.
- Git worktrees sharing one recognized Git common directory resolve to the same
  project automatically. Repository metadata may suggest a match after a move or
  new clone, but only the Owner can confirm the relink.
- Unknown or ambiguous roots never silently inherit an existing project's
  memory. They receive a separate identity or remain Unassigned.
- Orca does not require a marker file inside participating project repositories.

### Project consolidation

- Each project has one evolving bounded Project Summary containing its purpose,
  goals, current status, important current decisions and knowledge, constraints,
  active workstreams, open questions, and unresolved conflicts.
- Typed Memory Records remain the detailed project memory. The Project Summary
  references their `memory_id` values and carries no independent memory identity,
  provenance, or authority.
- After a successful run materially changes current project records, Processor
  refreshes the summary from its previous version, the changed records, and a
  bounded set of closely related current records. It does not reread every
  conversation or every project record.
- Superseded content leaves the main overview but remains preserved in its typed
  records. Memory Conflicts are shown explicitly and the summary cannot choose a
  winner.
- A no-change run does not rewrite the Project Summary. The summary can be
  rebuilt from typed records if it is missing or damaged.
- Large workstreams may have optional Workstream Summary records. They retain
  their Workstream Labels and remain within the same Project Memory scope.

### Storage module

- Maps each permitted artifact kind to an approved location.
- Assigns a permanent opaque `memory_id` to a newly accepted logical memory and
  rejects attempts to silently change an existing memory's identity or scope.
- Assigns the record schema, explicit noncanonical authority, and storage
  timestamps; combines them with Governance-resolved scope and Processor-proposed
  semantic fields; and validates the complete `orca-memory/0.2` frontmatter.
- Constructs and renames human-readable filenames under the normative
  [Memory Model Specification](../../specifications/memory.md). Processor proposes kind
  and subject but never a final path.
- Maps logical scope, kind, identity, and subject to the contract's physical
  layout. No caller supplies or infers a record path.
- Validates the required structure and encoding before publication.
- Creates directories, hashes content, and publishes files safely.
- Resolves stable supporting `memory_id` values to current paths when rendering
  human-readable links in Project Summary or Workstream Summary. It regenerates
  those derived links after an applicable rename; ordinary Typed Memory Records
  receive no speculative cross-file links.
- Prevents accidental overwrite and detects duplicate or conflicting content.
- Maintains locks, checkpoints, recovery records, and a local rebuildable
  processed-source index derived from durable Run Manifests.
- Keeps complete provenance in immutable Run Manifests and maintains the local
  rebuildable `memory_id`-to-manifest audit mapping. It adds no provenance block,
  source counter, manifest pointer, or source list to a Typed Memory Record.
- Publishes `v4+` Conflict Overflow Candidates under the applicable
  `candidates/conflicts/` scope using `(memory_id, variant_id)` identity, keeps
  them outside ordinary retrieval, and performs idempotent cleanup only after an
  Owner resolution manifest commits their dispositions.

Storage does not parse agent conversations or decide what an artifact means.
Conversation and Processor create meaningful artifacts; Storage validates and
safely places them.

### Recall module

- Builds a deterministic Retrieval Projection from each governed Markdown file
  before handing content to a replaceable retrieval adapter. A current record
  contributes only `## Current`; an unresolved record contributes its
  labelled variants; `## Resolution lineage` is excluded from ordinary search.
- Accepts a Recall Request containing the explicit memory question, optional
  project, kind, topic, or time filters, and only the immediately relevant
  conversation context needed to resolve a direct reference. It does not use an
  inferred hidden motive or the Adaptive Interaction Profile.
- Applies authority, visibility, project, and status filters before retrieval,
  then ranks permitted memory documents against the explicit requested meaning,
  such as rationale, procedure, current state, or history.
- Returns at most six Recall Results and may return fewer when fewer documents
  pass the relevance threshold. Ambiguity causes an explicit refinement request
  rather than guessed results.
- Collapses duplicate identities and strongly overlapping results. Relevance
  determines eligibility and selection: weakly relevant Canonical Memory cannot
  displace strongly relevant Shallow Memory merely because it is canonical.
  Among comparably relevant selected results, Canonical Memory is presented
  before Shallow Memory and every result remains authority-labelled.
- Supplies the applicable Adaptive Interaction Profile automatically at startup,
  resume, and post-compaction continuation through a separate, bounded
  presentation-context path.
- Compiles active entries by exact lookup under the
  [Interaction Guidance Specification](../../specifications/interaction-guidance.md). It does not
  paraphrase templates, and a conflicting or unknown entry produces no
  guidance.
- Preserves authority and provenance labels.
- Enforces a 4,000-token ceiling across the complete Recall Result set, including
  authority labels and provenance, with no more than 1,500 tokens from one memory
  document. Higher-ranked results receive space first.
- Selects passages that answer the Recall Request rather than returning the start
  of each file. Omission is visibly marked, and each result includes its path and
  permanent `memory_id` when one exists so the caller can request more detail.
- Uses deterministic excerpts and makes no additional LLM call merely to
  summarize retrieval results.
- Applies requester visibility without silently broadening the search scope.
- Resolves a supplied Project Alias through the Project Registry, then searches
  by permanent `project_id`; the alias itself grants no scope or authority.
- Requires each indexed projection to retain `memory_id`, authority, scope,
  status, source-file content hash, and projection-policy version. A hash mismatch
  excludes the stale result until reconciliation replaces it.

Recall does not search Conversation Evidence, Knowledge Candidates, or Run
Manifests during ordinary agent use.
Memory Relationships and rendered links never bypass Recall's authority,
visibility, project, status, or relevance rules.

### Governance module

- Loads and validates host and vault configuration.
- Enforces applicable authority, privacy, connector, and visibility rules.
- Fails closed when required identity or policy is missing or ambiguous.

Governance decides what an operation is permitted to do. It does not perform
semantic analysis or make retrieval results authoritative.

### Replaceable adapters

Connector adapters translate supported agent formats into the Conversation
interface. A retrieval adapter indexes deterministic Retrieval Projections and
returns bounded matches through the Recall interface; it never decides which
Markdown sections are current or historically ineligible. These adapters may
change without changing Orca's artifact meanings or authority rules.

## Data locations

```text
project checkout/
  src/orca_memory/             runtime implementation
  tests/                       verification code
  config/host.yaml             local configuration; ignored by Git
  .runtime/                    optional indexes, processed-source index, locks, queue,
                               retry spool, receipts, checkpoints, recovery

configured Orca vault/
  canonical folders/          accepted durable knowledge
  System/Orca Memory/         explicitly noncanonical artifacts
    shallow/
      projects/
        <project-alias-slug>/  project.md, summary.md, and kind directories
      general/                 fixed projectless scope and kind directories
      unassigned/              fixed ambiguous-ownership scope and kind directories
    candidates/
      conflicts/
        projects/<project-alias-slug>/
        general/
        unassigned/
    interaction/
      profiles/
        global.yaml
        agents/codex.yaml
        projects/<project-alias-slug>--<short-project-id>.yaml
        project-agents/<project-alias-slug>--<short-project-id>--codex.yaml
    manifests/
```

Credentials, raw agent session files, caches, indexes, locks, and recovery data
remain outside the vault. Private memory data remains outside the project and
public Git history.

Machine-specific Project Root Mappings remain local with host configuration or
runtime state and are never synchronized.

Each `project.md` durably relates one permanent project ID to its current alias;
those records collectively form the logical Project Registry. Local registry and
retrieval indexes are rebuildable projections. Shallow Memory uses one living
Markdown file per substantive logical record and no `registry.md`, `records/`
intermediary, or ID-prefix filesystem sharding in Phase 1. The normative path
mapping is defined by the [Memory Model Specification](../../specifications/memory.md).

## Normal operating flow

1. `PreCompact` and `SessionEnd` hooks queue work and trigger a one-shot local
   background worker. Periodic catch-up submits missed work to the same worker.
2. The worker reads new records directly from the agent-owned source or an
   eligible local retry spool after the checkpoint.
3. Conversation identifies, filters, and normalizes the records into transient
   Conversation Evidence with stable identities and content hashes.
4. Storage checks those identities and hashes against its local processed-source
   index, which is rebuildable from durable Run Manifests.
5. Processor receives only evidence that has not been processed successfully.
6. One minimized semantic pass proposes a Conversation Continuation Summary, controlled
   typed Shallow Memory records, Knowledge Candidates, and untrusted Interaction
   Observation Proposals. Project records may carry workstream relationship
   labels but remain in one Project Memory scope.
7. When current project records materially change, Processor refreshes the
   bounded Project Summary from its previous version, the changed records, and
   bounded related current records. No-change runs leave it untouched.
8. Processor validates the proposals, embeds only accepted compact Interaction
   Observations in the Run Manifest, and deterministically updates any affected
   Adaptive Interaction Profile. A file-only Manifest scan is the baseline;
   optional local SQLite may accelerate the same consolidation without becoming
   authoritative.
9. Storage safely publishes the derived artifacts and Run Manifest; the source
   checkpoint advances last.
10. The retrieval adapter reconciles Canonical Memory and permitted Shallow
   Memory into a local rebuildable index.
11. Startup, resume, and post-compaction continuation load at most the configured
   interaction-guidance budget, initially 500 tokens, from applicable active
   profile entries. Memory recall remains dormant until an
   explicit Recall Request selects at most six permitted documents by explicit
   intent relevance. Among comparably relevant selected results, Canonical Memory
   appears before Shallow Memory and every result remains authority-labelled.

Exact replay is a no-op. Failed processing leaves the agent-owned source and
local checkpoint unchanged for retry. A missing retrieval index affects recall
but does not damage memory artifacts.

## Delivery topology

| Phase | Topology | Capability added |
|---|---|---|
| **1 — Current** | Codex Desktop -> one WSL runtime -> one local vault | Complete single-agent memory and interaction-preference loop |
| **2 — Candidate** | Multiple local agents -> one local runtime -> one local vault | Agent identity, private/shared visibility, and coordinated local writes |
| **3 — Candidate** | Local and remote agents -> local/VPS runtimes -> synchronized vault replicas | Host authorization, replica conflict containment, and synchronized memory artifacts |

The phases vary by participating agents and hosts. Phase 2 reuses the complete
Phase 1 artifact model and modules for more local agents. Phase 3 synchronizes
completed vault artifacts but keeps indexes, locks, checkpoints, credentials,
and host configuration local. Synchronization is transport, not authority or a
semantic merge mechanism.

The detailed scope, interfaces, and completion criteria for the current phase
are defined in [Phase 1 Architecture](architecture.md).

## Key design decisions

| Decision | Rationale |
|---|---|
| Keep the project checkout separate from the vault. | Source code and private memory have different ownership, backup, and publication rules. |
| Read agent-owned history directly without a second raw archive. | Source identities, hashes, manifests, and checkpoint-last publication preserve retry and traceability while avoiding duplicate private transcripts. |
| Separate canonical, provisional, and operational artifacts. | A model proposal or operational record must never silently become accepted knowledge. |
| Separate Conversation, Processor, and Storage responsibilities. | Event recognition, semantic interpretation, and safe publication change for different reasons and can be verified independently. |
| Keep retrieval replaceable and non-authoritative. | Search quality can evolve without changing memory ownership or artifact semantics. |
| Establish the complete behavior with Codex in Phase 1. | Later phases add agents and hosts without redefining what Orca memory does. |
| Keep adaptive interaction preferences inspectable and noncanonical. | Orca can improve presentation without turning inferred behavior into asserted truth. |
| Keep automatic canonical apply disabled. | Durable knowledge changes require separate governance and evidence beyond memory capture and recall. |

## Interaction preference lifecycle

Interaction preference handling is part of Phase 1:

1. A turn directive affects the current response and requires no stored profile.
2. A session adjustment affects the current Codex task without becoming a
   durable preference.
3. A semantic pass may propose a scoped Interaction Observation only when it has
   the feedback turn, evaluated assistant response or passage, preceding request,
   and applicable scope. Missing or ambiguous context requires abstention.
4. Deterministic validation restricts observations to presentation behavior and
   the controlled Interaction Contexts `general`, `status-update`, `explanation`,
   `design-discussion`, `implementation`, and `review`. General applicability
   must be explicit; mixed or ambiguous context abstains.
5. Individual observations live only inside their supporting immutable Run
   Manifests. A profile is a living derived view containing only `active` or
   `conflicting` entries.
6. An explicit lasting preference becomes active immediately. Otherwise aligned
   corrections must occur in three distinct conversations inside a 180-day
   source-time window. An inferred active entry expires after 180 days without
   reinforcement; explicit lasting preferences do not expire automatically.
7. Incompatible qualified evidence for the same scope, context, and dimension
   produces a conflicting entry unless the Owner clearly replaces the earlier
   preference. Conflicting entries generate no automatic guidance.
8. Active values and directions compile through fixed versioned natural-language
   templates. A direction remains relative and never compounds into an extreme
   value; only explicit evidence establishes a concrete value.
9. Applicable guidance is supplied to Codex as bounded, noncanonical
   presentation context. The configurable combined default is 500 tokens.
10. A preference becomes a Confirmed Interaction Preference only when the Owner
   confirms it and it is accepted through canonical governance. Until then, it
   may be a Knowledge Candidate but is not Canonical Memory.

Observations retain provenance and scope in Run Manifests. Profiles are
inspectable, correctable, conflict-aware, and rebuildable. Orca does not infer a
preference from message length, vocabulary, punctuation, question count, or
other surface linguistic behavior; generalize a project-specific preference;
infer sensitive traits or hidden intent; automatically generate pairwise
questionnaires; or test probabilistic response quality as deterministic
correctness.

## Selected Phase 1 retrieval implementation

The design requires a local, bounded, replaceable retrieval adapter; it does
not require a particular product. [AgentCairn](https://github.com/ccf/agentcairn)
is selected for Phase 1 because it provides Markdown-vault indexing, hybrid
retrieval, a disposable DuckDB index, and private local Codex/MCP integration.

Orca still owns indexed roots, authority labels, source classification,
semantic derivation, candidate disposition, privacy, canonical writes, and
synchronization policy. Replacing AgentCairn must not change those decisions.

## Document responsibilities

- [README](../README.md): project goal, phase status, and entry points.
- **This document**: stable project-wide design and decision rationale.
- [Phase 1 Architecture](architecture.md): current topology, interfaces, and
  completion criteria.
- [Operations](operations.md): installation, scheduling, normal flow, and
  recovery behavior.
- [Memory System Contract](../../specifications/memory-system-contract.md): authority,
  privacy, lifecycle, and fail-closed requirements.
- [Memory Model Specification](../../specifications/memory.md): structural summaries,
  Typed Memory Record schemas, conflicts, filenames, and physical placement.
- [Provenance Ledger Specification](../../specifications/provenance.md): operational
  receipts, deduplication, date sharding, and checkpoint-last recovery.
- [Interaction Guidance Specification](../../specifications/interaction-guidance.md): exact
  profile-to-agent template keys, wording, and compilation rules.
- [Interaction Preference Specification](../../specifications/interaction-preferences.md):
  observation and profile schemas, consolidation, scope, and deterministic
  validation boundary.
- [Domain Language](../../specifications/glossary.md): canonical meanings of Orca terms.
