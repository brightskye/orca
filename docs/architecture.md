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

## Purpose

Orca Memory gives Codex, Remote Agent, ChatGPT, and future agents shared governed memory across a local machine and VPS without exposing canonical Orca through a public memory endpoint. It separates capture, provisional recall, semantic derivation, Curator judgment, and canonical apply so each stage has a clear authority.

The architecture replaces planning-phase names with structural responsibilities. Phase 6 and Phase 7 remain historical evidence, not target modules.

## System shape

```text
authorized connectors
  -> immutable conversation evidence
  -> Syncthing between two Orca replicas
  -> one authorized processor
       -> agent/shared shallow memory
       -> knowledge candidates
       -> interaction observations and profiles
       -> dated summary and run manifest
       -> Curator intake and plan
       -> policy-gated canonical apply

canonical Markdown + bounded shallow Markdown
  -> local AgentCairn cache per machine
  -> canonical-first recall
```

Orca is the governed system. Orca Memory Service is its executable layer. AgentCairn is a replaceable local backend, not a gateway or source of truth.

## Storage topology

Two Orca replicas exist: Owner's machine and the VPS. Syncthing provides eventual filesystem replication, not transactions or semantic merging.

```text
/workspace/projects/orca/      standalone project checkout
  config/host.yaml             local only; ignored by Git and Syncthing
  .runtime/                    local Cairn, locks, recovery, checkpoints

System/Orca Memory/            synchronized, noncanonical system area
  orca-memory.yaml             planned executable configuration
  governance/
  conversations/
  shallow/agents/
  shallow/shared/
  interaction/observations/
  interaction/profiles/
  curator/intakes/
  curator/plans/
  curator/dispositions/
  manifests/
```

External sources continue to enter `Raw/`. Accepted durable outputs continue to enter canonical Orca folders. `System/Orca Memory/` never becomes a shortcut around that promotion rule.

Artifact formats follow their use: sealed conversation segments use JSONL; shallow memory and knowledge candidates use Markdown with validated frontmatter; observations, Curator records, and manifests use structured JSON; adaptive profiles and configuration use YAML; contracts and human summaries use Markdown.

## Deployment topology

Every directly connected host installs the same pinned Orca Memory Service code as a standalone project checkout. Effective role is derived rather than configured twice:

```text
local host_id == synchronized processor.host_id
  -> processor deployment
otherwise
  -> client deployment
```

The initial topology is:

- Owner's machine: one selected WSL or native Windows client runtime shared by Codex Desktop and Codex CLI.
- VPS: the processor deployment used by Remote Agent and periodic processing.
- ChatGPT: a future constrained adapter to the VPS deployment; never a direct public administrative interface.

WSL is preferred locally, but native Windows remains a supported choice. Only one local runtime is active at a time, and WSL and Windows keep separate rebuildable Cairn caches.

## Interfaces

Codex and Remote Agent initially launch private MCP over local stdio. The milestone interface is intentionally small:

- `orca.recall`;
- `orca.capture`;
- `orca.ingest_source`;
- `orca.preference` for get and explicit feedback;
- `orca.curate` for inspect and plan only.

Conversation recording, processor tick, nightly processing, retention, reconciliation, and configuration validation are internal one-shot jobs. Canonical apply remains internal and unexposed until its independent readiness gates pass.

The future ChatGPT adapter exposes only recall, capture, preference get, and preference feedback. It cannot ingest sources, curate, run jobs, administer automation, retain data, or apply canonical changes.

## Capture

Connectors are configured identities, not inferences from paths or prose. Each connector writes immutable JSONL segments into its own namespace. Segments contain normalized owner messages, final user-visible agent responses once positively classifiable, stable turn ordering, and supported compaction evidence. Tool protocol, hidden reasoning, system envelopes, and raw tool output remain outside conversation evidence.

Codex capture uses incremental rollout-file scanning with file/offset checkpoints, positive event identification, event-level hashes, and periodic local capture ticks. No terminal-session marker is assumed. Remote Agent capture requires a VPS-local, read-only exporter proven against the deployed Hermes schema before production use. Historical backfill is always explicit.

## Periodic processing

Only the authorized processor performs semantic derivation. A scheduler wakes a one-shot processor tick; synchronized configuration determines whether a processing window is due. Deterministic window IDs, processor generation, local OS locking, checkpoints, and immutable manifests make retries safe.

The processor reads unprocessed evidence directly. It does not create a persistent merged transcript. One semantic extraction per bounded chunk may propose:

1. shallow memory;
2. knowledge candidates;
3. interaction observations.

The same run produces a dated reference summary under `Raw/Memory Summaries/YYYY/` and a run manifest. Reviewed summaries later move to `Archive/sources/Memory Summaries/`. Shared shallow eligibility is expressed by project, topic, visibility, and source-agent metadata; it does not require a separate aggregation copy.

Execution details such as provider, model, chunk sizes, cadence, and thresholds remain configurable and are tuned from operating evidence.

## Lineage

Full connector provenance is normalized once on source evidence and the relevant run manifest. Derived memory stores its own ID, run ID, compact evidence references, authority, scope, and content rather than copying paths and hashes repeatedly. Canonical promotion references the Curator disposition, which resolves back through candidate, run, and source records.

After processed conversation text expires, a compact source tombstone retains identity, hash, connector/session provenance, processing disposition, deletion time, and archived-summary reference without retaining the full conversation.

## Interaction memory

Interaction behavior has four runtime levels:

1. turn directive;
2. session adjustment;
3. adaptive interaction profile;
4. confirmed canonical preference.

Automatic adaptation is limited to presentation dimensions such as detail, structure, question frequency, technical depth, tone formality, and progress-update frequency. It does not infer personality, emotion, mental health, motives, or sensitive traits.

Connectors publish immutable preference feedback. The processor alone derives profiles using deterministic weighting, recency, contradiction, decay, and hysteresis. A confirmed durable preference becomes a Curator-ready candidate for `System/Assistant/`.

## Recall

AgentCairn indexes canonical Markdown and bounded agent/shared shallow Markdown. Conversation evidence, observations, candidates, Curator plans, manifests, `Raw/`, `Inbox/`, and `Archive/` stay outside ordinary semantic recall.

Default result order is:

1. canonical memory;
2. shared shallow memory visible to the requester and matching the project/topic;
3. the requesting agent's shallow memory;
4. another agent's shallow memory only through an explicit cross-agent filter.

Automatic recall is bounded across all layers. Initial defaults are approximately six results and 2,000 tokens, subject to empirical revision. Canonical and shallow contradictions remain separately labelled; recall never blends them into one asserted truth.

## Curator and apply

Curator planning is a normal processor responsibility. Apply is a separate guarded stage because a semantic proposal grants no write authority.

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

The implementation exposes a small MCP and job interface while keeping complexity behind structural modules:

- MCP interface: recall, capture, source ingestion, preference access/feedback, and Curator inspect/plan.
- Connector adapters: Codex and Remote Agent normalization at one versioned seam.
- Conversation module: capture, segmentation, identity, and source manifests.
- Distillation module: provider interaction, semantic validation, and output coordination.
- Recall module: authority-aware retrieval and bounded result assembly.
- Interaction module: observations and deterministic profiles.
- Curator module: intake, planning, and internal apply.
- Governance module: synchronized contract and configuration loading.
- Storage module: atomic publication, checkpoints, locks, recovery, and manifests.
- Backend seam: AgentCairn today, replaceable without changing the memory domain.

The highest behavioral test seam is the public MCP/job interface over isolated replicas and fake provider/backend adapters. Internal tests exist only where a fail-closed parser, atomic writer, or policy evaluator has a materially independent contract.

## Migration from phase-shaped code

The manual integration adapter, Phase 6 scanner, and Phase 7 intake are sources of proven normalization, identity, hashing, complete-scan, checkpoint, precondition, locking, and atomic-write behavior. Their responsibilities move into structural modules; their workflow shape and phase identifiers do not.

After verified cutover, the prototype is retired from the implementation tree and may be preserved in private project history. Existing private reports, freeze manifests, canary evidence, IDs, paths, and hashes remain unchanged. Generated bytecode is discarded rather than preserved.
