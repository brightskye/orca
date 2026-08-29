---
type: architecture
status: phase-1-current
updated: 2026-08-29
---

# Phase 1 Architecture

> [!WARNING]
> Archived migration source. Current architecture is owned by
> [`docs/02-architecture/`](../../02-architecture/overview.md).

> [!NOTE]
> Current architecture is owned by
> [`02-architecture/overview.md`](../../02-architecture/overview.md) and its child
> views. This file remains a definition-complete migration source until later
> archive approval and must not be edited independently.

This document applies the project-wide [Orca Memory System Design](system-design.md)
to the current delivery phase.

## Goal

Codex Desktop uses a private WSL runtime connected to one local Orca vault. A
supported conversation can be read directly from its Codex rollout, processed
into provisional memory, and recalled locally while Codex receives an
inspectable adaptive presentation profile, without automatic canonical writes.

## Non-goals

Phase 1 does not implement multiple agents, Syncthing, a VPS, remote processing,
automated retention, general source ingestion, public network interfaces, or
automatic canonical apply.

## System shape

```text
Codex Desktop
  -> private stdio MCP in WSL
  -> lifecycle hook queues work and triggers one-shot worker
  -> Codex Connector reads new agent-owned rollout records
  -> transient normalized conversation evidence
  -> one local processor
  -> shallow memory + knowledge candidates + run manifest with observations
  -> scoped adaptive interaction profiles
  -> rebuildable local retrieval index
  -> explicit recall skill -> relevance-qualified, authority-labelled memory

SessionStart -> applicable bounded interaction profile -> Codex
```

The vault is authoritative for memory. The project checkout contains code and
local runtime state but no private memory data.

## Modules

- **Conversation module**: reads new Codex records after the local checkpoint,
  positively identifies supported events, excludes unsafe or ambiguous content,
  applies the versioned deterministic privacy gate, and presents transient
  normalized evidence to the Processor.
- **Processor module**: receives normalized evidence, runs one minimized
  semantic pass, and treats every proposed interaction classification as
  untrusted. Deterministic validation admits only controlled, source-bound
  observations into the Run Manifest; deterministic consolidation then derives
  the applicable adaptive profiles under the
  [Interaction Preference Specification](../../03-specifications/interaction-preferences.md).
- **Recall module**: deterministically projects eligible sections of canonical
  and permitted shallow Markdown, retrieves those projections, verifies indexed
  content hashes against current files, preserves authority labels, and enforces
  bounded context when explicitly invoked. Resolved lineage remains available
  for explicit history but outside ordinary retrieval. The applicable interaction
  profile is loaded automatically through a separate session-start path.
- **Governance module**: loads local configuration and enforces Phase 1
  authority, privacy, and visibility rules.
- **Storage module**: validates artifact locations and formats, then provides
  hashes, safe publication, locks, checkpoints, duplicate/conflict detection,
  and recovery. It maintains a local rebuildable processed-source index from
  durable Run Manifests. Its interface accepts logical identity, scope, kind,
  and subject rather than caller-supplied paths. It alone maps records to the
  physical layout and constructs or renames filenames under the
  [Memory Model Specification](../../03-specifications/memory-model.md). It also publishes `v4+`
  Conflict Overflow Candidates and cleans them only after a committed Owner
  resolution records their dispositions. Run receipts and local progress follow
  the [Provenance Ledger Specification](../../03-specifications/provenance-ledger.md).

Tests exercise these behaviors through the public MCP or one-shot job
interface. Internal seams exist only for fail-closed parsing, storage, and
provider substitution.

## Storage

```text
project checkout/
  config/host.yaml             local, ignored
  .runtime/                    index, processed-source index, locks,
                               queue, retry spool, receipts, checkpoints,
                               recovery

configured Orca vault/
  canonical folders/          accepted durable knowledge
  System/Orca Memory/         explicitly noncanonical
    orca-memory.yaml
    shallow/
      projects/
        <project-alias-slug>/
          project.md
          summary.md
          conversation-summaries/
          workstreams/
          goals/ decisions/ knowledge/ entities/ identities/
          constraints/ open-questions/ lessons/ topics/
      general/
        conversation-summaries/
        goals/ decisions/ knowledge/ entities/ identities/
        constraints/ open-questions/ lessons/ topics/
      unassigned/
        conversation-summaries/
        goals/ decisions/ knowledge/ entities/ identities/
        constraints/ open-questions/ lessons/ topics/
    candidates/
      conflicts/
        projects/<project-alias-slug>/
        general/
        unassigned/
    interaction/profiles/
      global.yaml
      agents/codex.yaml
      projects/<project-alias-slug>--<short-project-id>.yaml
      project-agents/<project-alias-slug>--<short-project-id>--codex.yaml
    manifests/
```

`config/host.yaml`, `.runtime/`, credentials, caches, raw rollout files, and
copied raw conversations never enter the vault. The vault path is configured
rather than hard-coded.

Each substantive Shallow Memory record is one living Markdown file. Project
identity records collectively form the logical Project Registry; the local
registry and retrieval indexes are disposable and rebuildable. Phase 1 uses no
`registry.md`, `records/` intermediary, or ID-prefix filesystem sharding.

Hooks perform bounded deterministic handoff only. A one-shot background worker
performs semantic processing, and periodic catch-up reuses that worker for missed
jobs. Retry-spool content is private, short-lived, and never synchronized.

## Interfaces

Private MCP exposes the minimum agent-facing interface:

- `orca.recall` for bounded, intent-relevant, authority-labelled recall.

An explicit recall skill invokes `orca.recall`; session startup does not invoke
semantic memory recall automatically.

The explicit `$orca-save` workflow queues the active conversation for the same
one-shot processing path and returns its stable `conv:<purpose>--<short-id>`
reference, complete conversation ID, status, and processed-through turn. The
workflow invocation itself is excluded from semantic evidence. It does not
create a second transcript archive.

One-shot jobs provide:

- incremental direct-source processing;
- processor tick;
- retrieval-index reconciliation;
- configuration validation.

## Retrieval implementation

The architecture requires a replaceable local retrieval backend, not a specific
product. The backend must index configured Markdown, return bounded relevant
results, keep its cache disposable, and run without a public service.

[AgentCairn](https://github.com/ccf/agentcairn) is the selected Phase 1
implementation because it provides Markdown-vault indexing, hybrid retrieval,
a rebuildable local DuckDB index, and private Codex/MCP integration. Orca still
owns authority, indexed roots, source classification, semantic derivation,
candidate disposition, and canonical writes.

The active AgentCairn adapter preserves the proven custom-Distiller seam: Orca
supplies an already validated noncanonical note, and an unknown or canonical
distillation fails closed. The initial Processor/Storage slice now publishes
Conversation Continuation Summaries, immutable Run Manifests, and checkpoints.
AgentCairn provider wiring, Typed Memory Records, Project Summary refresh,
interaction consolidation, Recall, and Codex Desktop runtime integration remain
to be implemented.

Phase 1 does not enable a general semantic link graph. Structured IDs and labels
carry verified relationships; Storage may render links only in rebuildable
Project and Workstream Summaries. The retrieval adapter cannot use a link to
bypass Orca scope, authority, status, or relevance filters.

## Completion criteria

- Codex Desktop launches the WSL MCP runtime against the configured local vault.
- Supported owner messages and visible assistant responses are selected with
  exact provenance; ambiguous, subagent, and private-session cases fail closed.
  Obvious credential values are redacted before distillation, and generated
  outputs containing credential-like values are rejected before publication.
- Replay creates no duplicate semantic output.
- One bounded conversation range is read, processed, and recalled locally
  through explicit skill invocation.
- Recall returns at most six results selected by the explicit Recall Request.
  Weakly relevant Canonical Memory cannot displace strongly relevant Shallow
  Memory; among comparably relevant results, Canonical Memory is presented first
  and every result retains its authority label.
- The complete Recall Result set is capped at 4,000 tokens and one document may
  contribute at most 1,500 tokens. Excerpts are directly responsive, visibly
  incomplete when shortened, and require no additional LLM summarization call.
- Validated presentation feedback is stored only as compact references and
  controlled observations inside immutable Run Manifests. No observation file
  or copied conversation text is created.
- Deterministic consolidation produces an inspectable scoped Adaptive
  Interaction Profile; only active entries compile through the exact
  [Interaction Guidance Specification](../../03-specifications/interaction-guidance.md), conflicting
  entries compile to nothing, and the combined configurable default is 500
  tokens.
- A one-turn or session-only instruction does not silently become a Confirmed
  Interaction Preference or Canonical Memory.
- Tests stop at the deterministic boundary: proposal validation, replay,
  consolidation, conflict and expiry state, scope precedence, exact guidance
  compilation, bounded selection, and Manifest rebuild. Model interpretation
  and response quality are non-blocking evaluations rather than correctness
  claims.
- Restart and index rebuild recover from durable vault artifacts and checkpoints.
- No operation mutates canonical memory automatically.
