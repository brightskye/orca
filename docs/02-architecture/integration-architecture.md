---
id: ARCH-INTEGRATION
title: Orca Integration Architecture
document_type: architecture
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-29
related:
  - ARCH-OVERVIEW
  - REQ-ORCA
---

# Orca integration architecture

## Purpose

This document defines the proposed boundaries and assumptions for Orca's Codex,
semantic-provider, AgentCairn, MCP/skill, filesystem, and configuration
integrations.

## This document owns

- Responsibilities and trust assumptions at external or replaceable seams.
- Which integration may supply data, proposals, storage, or retrieval services.

## This document does not own

- Vendor tutorials, exact event parsing, record schemas, or operation commands.

## Integration map

| Integration | Direction | Orca boundary | Current state |
|---|---|---|---|
| Codex rollout | Source → Orca | Connector positively identifies supported records and normalizes permitted redacted evidence | Owner-turn slice implemented; assistant context and full drift handling incomplete |
| Codex lifecycle hooks | Codex → local runtime | Bounded handoff only; semantic work belongs to one-shot worker | Planned |
| Semantic provider | Processor ↔ provider | Receives minimized bounded redacted input; returns untrusted controlled proposals | One Continuation Summary seam implemented |
| Configured Orca vault | Storage ↔ filesystem | Storage maps logical artifacts to approved locations and publishes recoverably | Initial summary/Manifest slice implemented |
| AgentCairn | Orca ↔ replaceable adapter | May distil prevalidated input and index permitted Markdown; never owns authority or canonical apply | Adapter tested, not wired |
| MCP and explicit skills | Agent ↔ Recall/runtime | Local private invocation for recall, save, and review workflows | Planned |
| Local host configuration | Operator → Governance | Supplies validated machine-specific paths, mappings, and policies outside Git | Example only; loader planned |
| Optional SQLite projections | Manifests/Markdown → local cache | Accelerate lookup only; disposable and rebuildable | Planned |

## Codex source integration

Codex rollouts are agent-owned append-only source files, not a stable public Orca
contract. The Connector must positively identify supported event types and
versions, distinguish Owner evidence from permitted assistant context, preserve
stable conversation/turn identity, and exclude reasoning, tools, injected
envelopes, subagents, private content, and ambiguity.

The Connector produces transient normalized evidence or a secure permitted retry
payload. It does not decide memory meaning.

## Semantic-provider integration

Processor constructs a bounded request with exact source references and only the
minimum accepted context classes. The provider may return controlled proposals
or abstain. Orca validates schemas, referenced sources, scope, target identity,
lifecycle, conflict bounds, and safety locally. Invalid output grants no partial
publication and does not advance progress.

Provider configuration must not silently expand context budgets or bypass local
privacy. Provider identity and policy context belong in durable provenance.

## AgentCairn integration

AgentCairn is a replaceable implementation component behind Orca-owned
interfaces. The accepted use is limited to capabilities such as prevalidated
distillation and local retrieval over configured Markdown. Orca owns source
classification, artifact kinds, authority, scope, paths, candidate disposition,
retrieval filters, and canonical boundaries.

AgentCairn's native capture, remember, or canonical pipeline must not run in
parallel with Orca unless separately allowlisted and governance-adapted.

## MCP and skill integration

Phase 1 intends local explicit surfaces for recall, save, and conflict review.
Invocation does not grant authority: each action still passes Governance and
Storage constraints. Startup automatically loads only interaction guidance;
semantic memory recall requires explicit invocation.

No public MCP or administrative endpoint is accepted.

## Filesystem and configuration integration

Storage is the only component that maps logical artifacts to physical paths.
The vault path is loaded from local configuration or `ORCA_VAULT_PATH` and is
never hard-coded in tracked source. Host mappings, credentials, locks,
checkpoints, spools, and indexes remain local and unsynchronized.
The [Configuration Specification](../03-specifications/configuration.md) owns
the exact configuration interface and precedence.

## Replaceability requirements

- A new semantic provider must preserve the controlled proposal contract and
  local deterministic validation.
- A new retrieval backend must index only permitted projections, remain
  rebuildable, and accept Orca hard filters and result bounds.
- A new agent Connector must positively identify source records and normalize
  them into the same provenance-preserving envelope.
- A synchronization product, if later accepted, transports eligible artifacts
  but cannot establish authority or resolve meaning.

## Failure assumptions

- Source schemas drift and must fail closed when not positively recognized.
- Providers may timeout, return invalid structures, hallucinate targets, or emit
  secrets.
- Retrieval may return weak, stale, duplicate, or cross-scope candidates.
- Filesystem operations may stop between artifact, Manifest, checkpoint, and
  cleanup steps.

Each failure is contained by the owning deterministic boundary rather than
delegated to an external product.

## Candidate future integrations

Additional local agents and remote connectors belong to candidate Phases 2 and
3. Hermes and synchronized-host material under `legacy/manual-prototype/` is evidence only until an
Owner-approved proposal and decision activates it.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Runtime:** [Runtime Architecture](runtime.md)
- **Deployment:** [Deployment Architecture](deployment.md)
- **Security:** [Security and Trust](security-and-trust.md)
- **Current state:** [Current Status](../STATUS.md)
