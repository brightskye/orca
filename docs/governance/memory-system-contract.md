---
type: governance-contract
status: phase-1-current
updated: 2026-08-29
---

# Phase 1 Memory System Contract

## Authority

- Owner is final authority.
- Canonical Memory is authoritative durable knowledge.
- Conversation Evidence is transient and noncanonical. Shallow Memory,
  Knowledge Candidates, Interaction Observations, Adaptive Interaction
  Profiles, Run Manifests, checkpoints, and retrieval indexes are
  noncanonical.
- A Confirmed Interaction Preference is canonical only after explicit Owner
  confirmation and governed human acceptance.
- Semantic output proposes meaning; it grants no canonical authority.
- An Interaction Observation Proposal is untrusted semantic output. Only
  deterministic validation can admit a controlled observation into a Run
  Manifest or change derived profile state.
- The retrieval backend is local, derived, rebuildable, and replaceable.
- Automatic canonical apply is disabled and unexposed.

## Capture

> [!NOTE]
> Exact Capture interface behavior is owned by the
> [Capture Pipeline Specification](../03-specifications/capture-pipeline.md).
> This section retains the accepted governance constraints as a compatibility
> source and must not be edited independently.

- The Codex Connector accepts only positively identified supported events.
- Injected envelopes, hidden reasoning, tool protocol, raw tool output, and
  subagent sessions remain outside Conversation Evidence.
- Private-session instructions publish no content.
- Orca cannot undo secrets already sent to Codex or stored in its rollout. The
  Owner remains responsible for the original disclosure; Orca enforces Secret
  Containment against further propagation.
- Conversation Evidence is normalized in memory from the agent-owned source; it
  is not published as a second raw archive.
- Before a `SessionEnd` hook returns, only its unprocessed normalized evidence
  may be written to a private local retry spool. The spool remains outside the
  vault and Git, uses fixed secure permissions, and is deleted after successful
  publication and checkpointing.
- A versioned deterministic privacy gate excludes explicitly private content
  before content enters a retry spool or semantic provider input. Private and
  other excluded turns retain only a content-free local receipt.
- Versioned credential patterns locally redact obvious credential values while
  permitting useful surrounding context to proceed. Retry spools and provider
  input contain only the redacted representation.
- Redaction-policy versions bind source hashes and manifests. A hash change under
  a new version is a policy revision, not a source-integrity error.
- Stable source identities and normalized content hashes are checked against
  durable Run Manifests before semantic processing. An in-memory manifest scan
  is sufficient; an optional local SQLite projection may accelerate lookup.
- Durable Run Manifests remain the deduplication authority after any local
  projection is missing, discarded, or rebuilt.
- A checkpoint advances only after validated outputs and their Run Manifest are
  published successfully.

## Processing

> [!NOTE]
> Exact Processing interface behavior is owned by the
> [Processing Pipeline Specification](../03-specifications/processing-pipeline.md).
> This section retains the accepted governance constraints as a compatibility
> source and must not be edited independently.

- The local WSL runtime is the only processor.
- One local OS lock protects each processing run.
- Lifecycle hooks queue work and trigger a one-shot background worker. A
  lightweight periodic catch-up submits missed work to the same worker.
- The processor receives transient normalized evidence and creates no raw or
  merged transcript archive.
- Provider input is minimized; local code binds provenance and hashes.
- Provider input contains only a minimal preceding-turn overlap, the current
  Conversation Continuation Summary, the current Project Summary when project-scoped, a
  bounded scope-filtered set of relevant current Typed Memory Records, and a
  capped chronological chunk of new Conversation Evidence. It never includes
  every prior conversation or every project record.
- Pending evidence larger than one chunk is processed as sequential runs, each
  with its own Run Manifest and checkpoint. Chunks split at turn boundaries when
  possible; deterministic segmentation of an oversized turn preserves its
  source conversation ID, turn ID, segment order, and provenance.
- Processor enforces the complete provider-input budget before the semantic
  call. The initial Phase 1 ceiling is 20,000 input tokens including fixed
  instructions: at most 8,000 new-evidence tokens, one preceding turn up to
  1,000 tokens, 2,000 Conversation Continuation Summary tokens, 2,000 Project Summary tokens,
  and five relevant Typed Memory Records totalling at most 5,000 tokens.
  Semantic output is capped at 4,000 tokens.
- New evidence is never silently truncated to fit. Processor reduces the chunk
  or segments an oversized turn and removes the lowest-ranked related records
  first when the complete input exceeds its ceiling.
- A preference proposal requires the Owner feedback turn, the evaluated
  assistant response or passage, the preceding request, and applicable scope.
  Missing, ambiguous, private, or excluded context abstains. Accepted
  Interaction Observations are compact reference-based entries inside the Run
  Manifest; Orca creates no separate observation file and copies no conversation
  text into one.
- Shallow Memory uses controlled outputs: Conversation Continuation Summary, Project Summary,
  and typed records for workstream summary, decision, knowledge, entity,
  identity, goal, constraint, open question, lesson, and topic. Project Summary
  is a derived view without its own `memory_id`.
- Each conversation has its own evolving Conversation Continuation Summary. Related
  conversations contribute records to one Project Memory scope; workstream
  names are relationship labels and do not create additional authority or
  retrieval scopes.
- Each logical memory receives one permanent opaque `memory_id` that is
  independent of content hashes, source hashes, filenames, and revisions.
- Every Typed Memory Record uses the core `orca-memory/0.2` frontmatter defined
  by the Memory Record Contract: permanent identity, controlled kind and subject,
  explicit noncanonical authority, resolved scope and scope ID, lifecycle status,
  source-turn and Storage timestamps, and Workstream Labels.
- Processor proposes semantic fields, Governance resolves scope, and Storage
  assigns identity, schema, authority, and Storage timestamps. Filename, path,
  body text, and content hash are not duplicated in frontmatter.
- Typed Memory Records are living current-state documents. They retain compact
  supersession or conflict lineage but are not immutable event histories;
  durable Run Manifests provide the processing audit trail.
- Typed Memory Record status is exactly `current`, `conflict`, or `closed`.
  Status describes resolution, not authority. `current` has one usable state;
  `conflict` has no winner; `closed` is inactive retained history. Phase 1 uses
  no `proposed`, whole-file `superseded`, or `expired` status.
- Every current Typed Memory Record requires `## Current` with kind-appropriate
  applicable meaning. It may add bounded `## Context` and `## Implications` only
  when nonempty. Closed records use `## Final` and `## Closure`. Bodies contain
  no source lists, manifests, support counters, raw excerpts, or unrelated
  logical memories.
- Memory filenames follow the normative
  [Memory Model Specification](../03-specifications/memory-model.md). Processor proposes
  kind and subject; only Storage constructs or renames a filename. Filenames are
  human discovery labels and never memory identity or authority.
- Storage alone maps logical scope, kind, identity, and subject to the normative
  physical layout. Shallow Memory uses one living Markdown file per substantive
  logical record, human-readable kind directories, and no ID-prefix sharding or
  intermediate `records/` directory in Phase 1.
- Automatic matching is confined to one scope. Kind, normalized subject or
  entity, and provenance produce bounded possible matches; the Processor may
  propose `add`, `support`, `update`, `supersede`, `conflict`, or `abstain`.
- Exact support-only evidence writes a successful Run Manifest and advances the
  source checkpoint without rewriting the existing memory or advancing its
  `source_updated_at` or `updated_at`. Confirmed changed information revises the
  memory. Uncertain matches remain separate and cannot be merged merely because
  their text is similar.
- Typed Memory Records contain no provenance summary, source counter, manifest
  pointer, source hash list, or unbounded source array. `memory_id` joins a record
  to its complete immutable Run Manifest history through baseline filesystem
  lookup or an optional disposable SQLite projection rebuilt from manifests.
- Deterministic validation rejects a proposed target that does not exist, crosses
  scope, or attempts to change an existing memory's identity or scope.
- Each project has one permanent opaque `project_id` in the Orca Project
  Registry and one Owner-selected, human-readable, unique alias. Alias changes
  do not change project identity; aliases never grant authority by themselves.
- Each project's `project.md` holds its durable identity and current alias. These
  records collectively form the logical Project Registry; any local registry
  index is disposable and rebuildable, and Phase 1 has no separate `registry.md`.
- Machine-specific normalized project roots map locally to `project_id` and are
  never synchronized. Multiple roots may map to one project. Recognized Git
  worktrees may reuse an existing mapping through their common Git directory.
- Repository metadata may suggest a relink after a folder move or new clone, but
  only the Owner confirms it. Unknown or ambiguous roots remain separate or
  Unassigned and never silently inherit another project's memory.
- Each project has one evolving bounded Project Summary derived from current
  Typed Memory Records. It references supporting `memory_id` values and grants
  no independent identity, provenance, or authority.
- Processor refreshes the Project Summary only after a material change, using
  its previous version, changed records, and bounded related current records.
  It does not reread all project conversations or records.
- Superseded details remain in typed records rather than the main summary.
  Memory Conflicts are shown without selecting a winner. Optional Workstream
  Summaries remain labelled records in the same Project Memory scope.
- A no-change run does not rewrite the Project Summary; it is rebuildable from
  the project's typed records.
- Conflict resolution is a material change. The affected Project Summary and any
  Workstream Summary replace the conflict with the applicable current meaning and
  keep the same supporting `memory_id`; they do not copy resolution lineage.
  Merely acknowledging and keeping the conflict unresolved does not trigger a
  semantic summary rewrite.
- If bounded summary refresh cannot complete, the Owner's resolved Typed Memory
  Record remains valid. The Run Manifest marks the affected summary stale, Recall
  excludes it, and a later bounded rebuild replaces it; Orca does not roll back
  the Owner resolution.
- For otherwise matching records that conflict, a later trusted Owner turn makes
  its position current only when it clearly states or confirms the applicable
  replacement. The older position is retained as superseded with provenance.
  Conversation creation time and derived-record write time do not determine
  newness.
- Source-turn timestamps may establish chronology across conversations on the
  same trusted host. Turn IDs order records only within one conversation; copied
  branch-prefix turns retain their original identities, hashes, and timestamps.
- A later exploratory, hypothetical, quoted, or ambiguous branch turn does not
  automatically supersede an earlier position. Equal, missing, untrusted, or
  incomparable timestamps, or unclear replacement intent, preserve all distilled
  variants as a Memory Conflict until later trusted evidence resolves it.
- Each Conflict Variant has a stable identifier local to its `memory_id`, using
  monotonically assigned `v1`, `v2`, and later values. Storage assigns it;
  Processor may target an existing variant or propose a new alternative but may
  not choose the new identifier. Identifiers are never reused or renumbered and
  remain with compact lineage after resolution.
- Variant identity is independent of wording, content hash, source hash, and
  timestamp. Run Manifests bind every variant operation to its stable identifier
  and exact sources.
- Every active variant displays the actual trusted source-turn timestamp that
  introduced or materially changed its distinct position. Missing or untrusted
  time remains visibly unknown; conversation creation, processing, review, and
  file-write times cannot substitute for it. Support-only turns retain their own
  timestamps in Run Manifests without changing the variant's position timestamp.
- Each distinct qualifying Owner source turn supporting an existing variant adds
  one unit of derived Variant Support Weight; an exact replay adds none. Weight
  informs Owner review but cannot override a newer trusted Owner position.
- Every Memory Conflict is eligible for explicit Owner review. A third
  simultaneously unresolved variant makes review urgent, and the living record
  holds no more than three active unresolved variants.
- Pending Conflict Review is not automatically recalled, injected, or announced
  at session start. Review content is exposed only after explicit Owner
  invocation of the review skill. A dashboard or scheduled memory-health report
  remains optional later observability, not current Phase 1 behavior.
- Every later distinct position beginning with `v4` is preserved as a durable
  redacted overflow candidate with its stable variant ID and linked by the Run
  Manifest. Processing continues to record later overflow positions and support;
  it does not pause because overflow exists. Review exposes all active and
  overflow positions, paginating summaries when necessary.
- Each Conflict Overflow Candidate uses `orca-conflict-overflow/0.1`, is identified
  by `(memory_id, variant_id)`, contains only its redacted distilled position and
  minimum identity, scope, and timestamps, and remains under the target scope in
  `candidates/conflicts/`. It has no separate candidate identity or provenance
  arrays; Run Manifests retain exact source and support history.
- Conflict Overflow Candidates are excluded from summaries, Retrieval
  Projections, ordinary Recall, and automatic session context. Phase 1 applies no
  age-based retention. Explicit resolution commits current meaning and complete
  variant dispositions before idempotent candidate cleanup; interrupted cleanup
  cannot make a resolved candidate reviewable again.
- The living Typed Memory Record owns pending-review state; Phase 1 creates no
  duplicate review-queue record. The default review view shows only concise
  summaries sufficient to demonstrate the conflict, stable variant IDs,
  position timestamps, support weights, and overflow presence. Full distilled
  content and audit references require explicit Owner expansion; raw source text
  requires separate explicit inspection of the still-available agent source.
- Conflict Review permits only three Owner outcomes: select one variant as
  current, resolve using an applicable Owner-supplied position, or keep the
  conflict unresolved. Resolution restores `current` status and retains compact
  variant dispositions in the living record while complete evidence remains in
  Run Manifests. Keeping the conflict unresolved selects no winner.
- `review_state` is exactly `none`, `required`, `acknowledged`, or `overflow` and
  expresses urgency or acknowledgement, not review eligibility, and remains
  independent of `status`. Two variants with `none` remain reviewable; three
  active variants produce `required`; `v4+` produces `overflow`; keeping a
  reviewed conflict unresolved produces `acknowledged` only when no overflow
  exists; resolution produces `current` plus `none`. `current` and `closed`
  require `none`.
- Unresolved bodies contain monotonically ordered stable variant sections with a
  concise label, `position_at`, and distilled position. Resolved bodies contain
  the applicable current meaning plus bounded lineage recording each former
  variant ID, label, timestamp, and disposition. Support lists and complete
  evidence remain in Run Manifests.
- Phase 1 stores only controlled Memory Relationships established by scope,
  exact provenance, Workstream Label, validated summary support, or in-record
  conflict and supersession lineage. Similarity alone cannot create a generic
  `related-to` relationship.
- Stable IDs and labels represent relationships. Only Project Summary and
  Workstream Summary may render Storage-generated clickable links for their
  already validated supporting `memory_id` values. A link is a locator and never
  grants identity, scope, authority, or provenance.
- Missing or impermissibly cross-scope targets fail closed. Phase 1 adds no
  general link graph, graph database, model-generated ontology, or entity
  resolution pipeline.
- Invalid or failed semantic output commits no derived artifacts and leaves the
  source checkpoint unchanged for retry. Any required `SessionEnd` retry spool
  remains available while the agent-owned source may disappear.
- Successful runs publish outputs, a manifest, and a durable checkpoint.
- Manifest and checkpoint fields, deduplication meaning, date sharding, and
  checkpoint-last recovery follow the normative
  [Provenance Ledger Specification](../03-specifications/provenance-ledger.md).
- A valid semantic abstention publishes a successful `no_memory` Run Manifest.
- Every proposed output is scanned deterministically before publication. Any
  affected output containing a credential-like value is rejected before storage,
  embedding, indexing, synchronization, recall, or exposure to another agent.
- Retry spools receive at most three automatic attempts. Their configurable
  retention defaults to 72 hours; terminal expiry deletes content and retains
  only a content-free local failure receipt.

## Interaction preferences

- Observation, profile, scope, and consolidation schemas follow the normative
  [Interaction Preference Specification](../03-specifications/interaction-preferences.md).
- Phase 1 learns presentation behavior for Codex from supported Conversation
  Evidence.
- Interaction Observations are restricted to presentation dimensions such as
  detail, structure, question frequency, technical depth, tone formality, and
  progress-update frequency.
- The only Phase 1 Interaction Contexts are `general`, `status-update`,
  `explanation`, `design-discussion`, `implementation`, and `review`. `general`
  requires explicit general applicability; unclear or materially mixed context
  abstains instead of receiving a score or guessed label.
- Personality, emotion, motives, mental health, sensitive traits, and unsupported
  intent are never inferred.
- Message length, vocabulary, punctuation, question count, and other surface
  linguistic behavior cannot establish a preference by themselves.
- Adaptive Interaction Profiles are living, scoped, inspectable, correctable,
  conflict-aware, and rebuildable. They contain only `active` or `conflicting`
  current entries; complete observation evidence remains in Run Manifests.
- One explicit lasting preference activates the applicable entry immediately.
  Otherwise aligned corrections require three distinct source conversations
  inside a 180-day source-turn window. Repetition within one conversation counts
  once. An inferred active entry expires after 180 days without reinforcement;
  an explicit lasting preference does not expire automatically.
- Incompatible qualified evidence for the same scope, context, and dimension
  creates a conflicting entry unless the Owner clearly replaces the earlier
  preference or separates the contexts. Conflicting entries supply no automatic
  guidance.
- Relative evidence remains `increase`, `decrease`, `more-formal`, or
  `more-conversational` as applicable; repetition does not compound it into an
  extreme value. Only explicit evidence establishes a concrete categorical
  value.
- Active entries compile only through the exact versioned templates in the
  [Interaction Guidance Specification](../03-specifications/interaction-guidance.md). Runtime
  compilation makes no model call, performs no paraphrasing, deduplicates exact
  sentences, and omits complete lower-precedence sentences rather than
  truncating them.
- A turn directive or session adjustment does not silently become a durable
  preference.
- Orca does not automatically generate pairwise preference questionnaires. A
  clear natural comparison may produce one contextual observation, and explicit
  conflict inspection may let the Owner select a stored candidate.
- An inferred preference remains noncanonical. Owner confirmation may qualify
  a Knowledge Candidate for manual acceptance; it becomes a Confirmed
  Interaction Preference only after that governed acceptance. Automatic
  canonical apply remains disabled.

## Recall

> [!NOTE]
> Exact Recall interface behavior is owned by the
> [Retrieval Contract](../03-specifications/retrieval-contract.md). This section
> retains the accepted governance constraints as a compatibility source and
> must not be edited independently.

- Memory recall runs only through explicit recall-skill invocation in Phase 1.
- A Recall Request consists of the explicit memory question, optional project,
  kind, topic, or time filters, and only the immediately relevant conversation
  context needed to resolve a direct reference. Recall does not use a guessed
  hidden motive or the Adaptive Interaction Profile as semantic search intent.
- Recall may accept a Project Alias for convenience but resolves and enforces
  scope using the permanent `project_id`.
- Authority, visibility, project, and status are hard filters. Recall then ranks
  permitted memory documents by relevance to the explicit requested meaning and
  returns at most six. It may return fewer or request refinement rather than fill
  unused positions with weak or ambiguous matches.
- Ordinary Recall includes `current`, may include clearly labelled `conflict`
  without selecting a winner, and excludes `closed` unless the Recall Request
  explicitly asks for historical, completed, resolved, or closed memory.
- Recall builds deterministic Retrieval Projections before using a replaceable
  retrieval adapter. Current records contribute current meaning, unresolved
  records contribute labelled variants, and resolved lineage is excluded from
  ordinary search but remains available to explicit historical requests.
- Every indexed projection carries the source `memory_id`, authority, scope,
  status, source-file content hash, and projection-policy version. Recall rejects
  a mismatched hash or a summary marked stale until reconciliation replaces it.
- Relevance determines result eligibility and selection. Weakly relevant
  Canonical Memory cannot displace strongly relevant Shallow Memory solely due
  to authority; among comparably relevant selected results, Canonical Memory is
  presented first and every result is authority-labelled.
- Duplicate identities and strongly overlapping results do not consume separate
  result positions.
- The applicable bounded Adaptive Interaction Profile loads automatically at
  startup, resume, and post-compaction continuation through a separate path.
- Interaction precedence is current Owner instruction, current-session
  adjustment, confirmed applicable preference, project-and-agent profile,
  project profile, agent profile, then global profile.
- The interaction profile remains separately labelled presentation context; it
  is not blended into Canonical Memory or semantic search results.
- Candidates, manifests, `Raw/`, `Inbox/`, and `Archive/` remain outside ordinary
  recall. Transient Conversation Evidence is never indexed.
- One 4,000-token ceiling bounds the complete result of each Recall Request,
  including labels and provenance. No memory document contributes more than
  1,500 tokens, and higher-ranked results receive space first.
- An explicit exact-conversation recall by stable `conv:<purpose>--<short-id>`
  reference returns up to 2,000 tokens from that Conversation Continuation
  Summary, up to 1,000 tokens from its Project Summary when applicable, and
  relevant Typed Memory Record excerpts within the remaining 4,000-token total.
  This exact Continuation Summary is the sole Phase 1 exception to the ordinary
  1,500-token per-document ceiling.
- Recall selects directly responsive passages, visibly marks omitted content,
  and returns each source path plus permanent `memory_id` when one exists. It
  does not make another LLM call merely to summarize retrieval results.
- A separately configurable budget bounds automatically loaded interaction
  guidance, initially 500 tokens. Only whole compiled sentences are selected.
- A missing or corrupt index makes semantic recall unavailable until rebuild;
  broad vault scanning is not a silent fallback.

## Local data

- The vault path comes from `config/host.yaml` or `ORCA_VAULT_PATH`.
- `config/host.yaml`, `.runtime/`, credentials, caches, locks, raw sessions, and
  recovery material remain outside Git and outside the vault.
- No Phase 1 interface is publicly network-accessible.
