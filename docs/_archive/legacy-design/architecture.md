---
type: architecture
status: accepted-baseline
created: 2026-08-25
updated: 2026-08-25
tags:
  - orca
  - agent-memory
  - architecture
---

# Orca Memory Architecture

> [!WARNING]
> Archived all-phase design snapshot. Current architecture is owned by the
> [Architecture Overview](../../02-architecture/overview.md).

## Purpose

Orca Memory begins as a local Codex memory system and expands deliberately to
local multi-agent sharing and then synchronized multi-host sharing. It
separates capture, provisional recall, semantic derivation, Curator judgment,
and canonical apply so each responsibility has clear authority without forcing
distributed-system concerns into the local implementation.

The architecture replaces planning-phase names with structural responsibilities. Phase 6 and Phase 7 remain historical evidence, not target modules.

The canonical delivery scope, operating flows, and completion criteria are in
[the delivery plan](delivery-plan.md). Its three phases are delivery stages;
they do not restore the old phase-shaped implementation.

## System shape

```text
authorized connectors
  -> immutable conversation evidence
  -> one authorized processor
       -> agent/shared shallow memory
       -> knowledge candidates
       -> run manifest

canonical Markdown + bounded shallow Markdown
  -> rebuildable local retrieval index per machine
  -> canonical-first recall

Phase 3 adds Syncthing between two replicas around the same path.

follow-on capabilities
  -> interaction observations and profiles
  -> dated summaries and retention
  -> Curator planning and policy-gated canonical apply
```

Orca is the governed system. Orca Memory Service is its executable layer. The
retrieval implementation is replaceable and never becomes a gateway or source
of truth. The same local-first processing path is retained through all three
delivery phases:

```text
Phase 1: one local Codex agent + one local vault
Phase 2: multiple local agents + one local vault
Phase 3: multiple agents + synchronized local/VPS vault replicas
```

## Storage topology

Phases 1 and 2 use one local Orca vault. Phase 3 adds a VPS replica and
Syncthing eventual replication; it does not change artifact authority or turn
the filesystem into a transaction manager.

```text
/workspace/projects/orca/      standalone project checkout
  config/host.yaml             local only; ignored by Git and Syncthing
  .runtime/                    local index, locks, recovery, checkpoints

System/Orca Memory/            noncanonical system area in the configured vault
  orca-memory.yaml             local in Phases 1/2; synchronized in Phase 3
  governance/
  conversations/
  shallow/agents/
  shallow/shared/
  candidates/
  manifests/

  # Created only by separately scoped follow-on capabilities
  interaction/observations/
  interaction/profiles/
  curator/intakes/
  curator/plans/
  curator/dispositions/
```

In Phases 1 and 2 this system area is local because the vault itself is local.
In Phase 3 it is synchronized. Project-local `config/host.yaml`, `.runtime/`,
caches, credentials, and recovery material never enter it.

External sources continue to enter `Raw/`. Accepted durable outputs continue
to enter canonical Orca folders. `System/Orca Memory/` never becomes a shortcut
around that promotion rule.

Artifact formats follow their use: sealed conversation segments use JSONL; shallow memory and knowledge candidates use Markdown with validated frontmatter; observations, Curator records, and manifests use structured JSON; adaptive profiles and configuration use YAML; contracts and human summaries use Markdown.

## Deployment topology

Deployment expands by delivery phase:

- Phase 1: one WSL runtime serves Codex Desktop and the local vault. It is also
  the only processor.
- Phase 2: the same WSL runtime serves multiple configured local agents and
  remains the only processor.
- Phase 3: local and VPS hosts install the same pinned Orca Memory Service code.
  Synchronized governance authorizes exactly one processor host.

Only Phase 3 needs role derivation across hosts:

```text
local host_id == synchronized processor.host_id
  -> processor deployment
otherwise
  -> client deployment
```

WSL is the selected runtime for Phases 1 and 2. Native Windows runtime support
is outside these delivery phases. A future constrained ChatGPT adapter is also
outside the three-phase delivery scope and is never a public administrative
interface.

## Interfaces

Phase 1 launches private MCP over local stdio for Codex Desktop. Its required
interface is intentionally small:

- `orca.recall`;
- `orca.capture`;
- candidate inspection through a local one-shot job.

Phase 2 reuses the same interface for additional configured local agents and
adds requester-aware visibility. Phase 3 reuses it on each host after adding
host authorization and synchronization checks.

Conversation recording, processor tick, reconciliation, and configuration
validation are internal one-shot jobs. Phase 3 adds scheduled windows,
retention, and processor-transfer jobs. Canonical apply remains internal and
unexposed until its independent readiness gates pass.

## Capture

Connectors are configured identities, not inferences from paths or prose. Each connector writes immutable JSONL segments into its own namespace. Segments contain normalized owner messages, final user-visible agent responses once positively classifiable, stable turn ordering, and supported compaction evidence. Tool protocol, hidden reasoning, system envelopes, and raw tool output remain outside conversation evidence.

Phase 1 Codex capture uses incremental rollout-file scanning with file/offset
checkpoints, positive event identification, event-level hashes, and periodic
local capture ticks. No terminal-session marker is assumed. Phase 2 gives each
local connector its own configured identity, namespace, and checkpoint. Phase 3
adds Remote Agent capture through a VPS-local, read-only exporter proven against
the deployed Hermes schema. Historical backfill is always explicit.

## Periodic processing

Only the authorized processor performs semantic derivation. In Phases 1 and 2,
the single WSL runtime is authorized by topology and a local scheduler wakes a
one-shot processor tick. In Phase 3, synchronized configuration authorizes one
host and determines whether a processing window is due. Deterministic window
IDs, processor generation in Phase 3, local OS locking, checkpoints, and
immutable manifests make retries safe.

The processor reads unprocessed evidence directly. It does not create a
persistent merged transcript. In the three delivery phases, one semantic
extraction per bounded chunk may propose:

1. shallow memory;
2. knowledge candidates.

The same run produces a run manifest. Separately scoped retention may later add
a dated reference summary under `Raw/Memory Summaries/YYYY/`; reviewed
summaries move to `Archive/sources/Memory Summaries/`. Shared shallow
eligibility is expressed by project, topic, visibility, and source-agent
metadata; it does not require a separate aggregation copy.

Execution details such as provider, model, chunk sizes, cadence, and thresholds remain configurable and are tuned from operating evidence.

## Lineage

Full connector provenance is normalized once on source evidence and the relevant run manifest. Derived memory stores its own ID, run ID, compact evidence references, authority, scope, and content rather than copying paths and hashes repeatedly. Canonical promotion references the Curator disposition, which resolves back through candidate, run, and source records.

When separately scoped retention is enabled, expired processed conversation
text leaves a compact source tombstone containing identity, hash,
connector/session provenance, processing disposition, deletion time, and the
archived-summary reference without retaining the full conversation.

## Follow-on interaction memory

Interaction profiles are outside the three delivery phases. When separately
implemented, interaction behavior has four runtime levels:

1. turn directive;
2. session adjustment;
3. adaptive interaction profile;
4. confirmed canonical preference.

Automatic adaptation is limited to presentation dimensions such as detail, structure, question frequency, technical depth, tone formality, and progress-update frequency. It does not infer personality, emotion, mental health, motives, or sensitive traits.

Connectors publish immutable preference feedback. The processor alone derives profiles using deterministic weighting, recency, contradiction, decay, and hysteresis. A confirmed durable preference becomes a Curator-ready candidate for `System/Assistant/`.

## Recall

The retrieval backend indexes canonical Markdown and bounded agent/shared
shallow Markdown. Conversation evidence, observations, candidates, Curator
plans, manifests, `Raw/`, `Inbox/`, and `Archive/` stay outside ordinary
semantic recall.

Default result order is:

1. canonical memory;
2. shared shallow memory visible to the requester and matching the project/topic;
3. the requesting agent's shallow memory;
4. another agent's shallow memory only through an explicit cross-agent filter.

Phase 1 uses items 1 and 3 for Codex. Phase 2 activates shared and cross-agent
visibility. Phase 3 preserves the same ordering independently on each host.

Automatic recall is bounded across all layers. Initial defaults are approximately six results and 2,000 tokens, subject to empirical revision. Canonical and shallow contradictions remain separately labelled; recall never blends them into one asserted truth.

## Follow-on Curator apply

The delivery phases retain candidates for manual inspection but do not require
automatic canonical apply. When Curator planning and apply are separately
implemented, apply remains a guarded stage because a semantic proposal grants
no write authority.

Automation graduates by category:

```text
plan only
  -> explicit approval
  -> shadow
  -> bounded canary
  -> automatic routine apply
```

Sensitive People material, inferred medical/financial/legal claims, deletion, substantive contradiction resolution, structural rewrites, governance changes, and unconfirmed high-impact commitments always require review or remain prohibited.

The long-term target is automatic routine curation with exceptions held for review, not unrestricted autonomous canonical writing.

## Module seams

The implementation exposes a small MCP and job interface while keeping
complexity behind structural modules. Modules are introduced only when a phase
needs them:

- MCP interface: Phase 1 recall and capture; later phases reuse the same seam.
- Connector adapters: Codex in Phase 1, more local adapters in Phase 2, and
  Remote Agent in Phase 3 at one versioned seam.
- Conversation module: capture, segmentation, identity, and source manifests.
- Distillation module: provider interaction, semantic validation, and output coordination.
- Recall module: authority-aware retrieval and bounded result assembly.
- Governance module: local configuration and policy first; synchronized host
  authority is added only in Phase 3.
- Storage module: local atomic publication, checkpoints, locks, recovery, and
  manifests first; conflict containment is added only in Phase 3.
- Retrieval-backend seam: one replaceable implementation indexes configured
  Markdown and returns ranked, authority-labelled results.

Source ingestion, interaction profiles, and automatic Curator apply are
follow-on modules outside the three delivery phases.

The highest behavioral test seam is the public MCP/job interface over isolated replicas and fake provider/backend adapters. Internal tests exist only where a fail-closed parser, atomic writer, or policy evaluator has a materially independent contract.

## Selected retrieval implementation: AgentCairn

The architecture above does not require AgentCairn. Orca needs a backend that:

1. indexes configured canonical and permitted shallow Markdown without taking
   authority over those files;
2. returns a bounded relevant subset for local recall;
3. keeps its index local, disposable, and rebuildable;
4. can run through private stdio integration without a public service.

[AgentCairn](https://github.com/ccf/agentcairn) is selected because it provides
a Markdown-vault model, hybrid BM25/semantic retrieval, an optional reranker, a
rebuildable local DuckDB index, and local MCP/Codex integration. These
capabilities satisfy the retrieval interface while avoiding a custom indexing
engine in Phase 1.

Orca still owns which files may be indexed, authority labels, visibility,
capture classification, semantic derivation, candidate disposition, canonical
writes, and synchronization policy. The retained prototype verified that
AgentCairn `0.25.2` can be used unchanged through its public ingestion and
locking seams. That verification supports the current adapter choice; it does
not make AgentCairn part of the Orca domain model or prevent replacement.

## Migration from phase-shaped code

The manual integration adapter, Phase 6 scanner, and Phase 7 intake are sources of proven normalization, identity, hashing, complete-scan, checkpoint, precondition, locking, and atomic-write behavior. Their responsibilities move into structural modules; their workflow shape and phase identifiers do not.

After verified cutover, the prototype is retired from the implementation tree and may be preserved in private project history. Existing private reports, freeze manifests, canary evidence, IDs, paths, and hashes remain unchanged. Generated bytecode is discarded rather than preserved.
