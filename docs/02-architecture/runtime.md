---
id: ARCH-RUNTIME
title: Orca Runtime Architecture
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

# Orca runtime architecture

## Purpose

This document defines the accepted Phase 1 execution model, runtime flows,
concurrency boundaries, publication order, and recovery responsibilities.

## This document owns

- Lifecycle-hook, worker, publication, reconciliation, and recall flows.
- Runtime failure and recovery boundaries.

## This document does not own

- Exact record formats, token budgets, commands, or implementation progress.

## Execution contexts

| Context | Responsibility |
|---|---|
| Explicit project setup or resolution | Resolve a known root, register a new project, relink a root, or keep it Unassigned |
| Explicit `Orca Status` | Build and show content-free unresolved Attention Items without a model call or state mutation |
| Codex session-start path | Load bounded applicable interaction guidance only |
| Explicit Recall invocation | Retrieve permitted authority-labelled context for a specific request |
| `PreCompact` or `SessionEnd` hook | Perform bounded deterministic handoff and queue work |
| One-shot worker | Read, deduplicate, process, validate, and publish one bounded unit of work |
| Periodic catch-up | Discover missed work and invoke the same one-shot worker |
| Retrieval reconciliation | Rebuild or update disposable projections and indexes from current Markdown |

No permanent daemon is required by the accepted design.

## Project setup flow

1. Load valid local configuration and discover the normalized root without a
   model call or file change.
2. Use an exact valid mapping silently, or reuse an exact local Git common
   directory when it proves one existing mapped identity.
3. For every other unknown or ambiguous root, ask the Owner once to create,
   link, or keep Unassigned.
4. Before registration or relinking writes, publish one fixed private local
   Project Mapping Intent under the mapping lock.
5. Publish the project identity record when required, atomically update the
   local host mapping, verify both results, then remove the intent.

Project setup does not process memory and cannot grant canonical authority.

## Session-start flow

1. Resolve applicable active interaction-profile entries by explicit precedence.
2. Compile only known values through fixed guidance templates within the
   configured budget.
3. Supply the bounded noncanonical guidance to Codex.
4. Check the local rebuildable attention projection and, when any item remains
   unresolved, show at most one counts-only reminder for the session.
5. Perform no automatic semantic memory recall or conversation processing.

## Human-attention flow

1. Collect accepted unresolved source states deterministically from runtime
   failures and intents, configuration validation, stale blocking views,
   Unassigned records, Memory Conflicts, and pending candidates.
2. Assign each content-free item one stable ID, owning workflow, and `urgent`,
   `action-required`, or `review` severity.
3. Rebuild the local status projection without changing any source state.
4. On explicit `Orca Status`, show counts by class and severity plus safe IDs
   and owning-workflow routes; private content remains closed.
5. Resolve an item only through its owning workflow. If resolution cannot be
   proved, keep the item visible.

The session reminder contains counts only, runs at most once after session start
or resume, and makes no model call or memory recall. There is no background
notification, public endpoint, or separate status authority.

## Explicit recall flow

1. Receive the explicit memory question and permitted filters.
2. Apply authority, visibility, project, and status filters before ranking.
3. Ask the replaceable retrieval adapter for bounded candidate projections.
4. Select directly relevant results, collapse duplicates, and leave weak or
   ambiguous positions empty rather than filling a quota.
5. Return labelled excerpts and provenance without a second summarization call.

Exact selection and budget behavior is owned by the
[Retrieval Contract](../03-specifications/retrieval-contract.md).

## Processing flow

1. A lifecycle hook or explicit save identifies pending source work.
2. `SessionEnd` writes only permitted redacted unprocessed evidence to a secure
   local retry spool when the source may disappear; `PreCompact` may pass a
   stable rollout pointer.
3. The hook queues work and starts the one-shot worker.
4. One per-run local lock prevents concurrent processing of the same work.
5. The Connector reads after the durable checkpoint and applies event,
   privacy, redaction, identity, and hashing rules.
6. Durable Run Manifests establish successful prior processing. Exact replay is
   skipped; an unexpected same-policy source revision fails closed.
7. Processor constructs one bounded chronological input and invokes one
   replaceable semantic provider.
8. Deterministic validation admits only controlled proposals with valid source,
   scope, identity, lifecycle, and safety properties.
9. Storage prepares all post-images plus fixed Manifest and checkpoint payloads,
   then publishes one private local publication intent.
10. Storage publishes validated derived artifacts and the durable Run Manifest.
11. The source-segment checkpoint advances last; successful retry-spool and
    publication-intent content is then deleted.
12. Retrieval reconciliation updates disposable projections and indexes.

See the [processing-flow diagram](diagrams/processing-flow.mmd).

## Publication and recovery

Filesystem publication is recoverable, not fully transactional. Before changing
a final artifact, Storage writes one complete private local publication intent
containing the fixed source, operation, output, Manifest, and checkpoint plan.
It then publishes target artifacts, the immutable Run Manifest, and the
checkpoint in that order.

After interruption, matching before/after hashes let Storage finish the same
plan without another semantic call. A target that matches neither recorded hash,
a missing or corrupt intent with an unreceipted artifact, or a Manifest/output
hash mismatch fails closed for human repair. A crash after Manifest publication
permits checkpoint repair from the Manifest. Exact rules belong to the
[Provenance Ledger](../03-specifications/provenance-ledger.md).

An optional SQLite projection may accelerate processed-source, audit, and
interaction-observation lookup. It is never the correctness baseline and must be
rebuildable from durable Manifests without conversation text.

## Failure boundaries

| Failure | Required behavior |
|---|---|
| Unsupported, private, injected, tool, reasoning, subagent, or ambiguous event | Exclude before semantic processing; retain at most a content-free local receipt where required |
| Partial trailing source record | Wait for a later run; current code diverges and raises |
| Lock contention | Exit without processing |
| Invalid semantic or deterministic output | Publish no affected derived artifact and leave checkpoint unchanged |
| Credential-like generated output | Reject before storage, indexing, synchronization, or recall |
| Index failure | Leave Markdown untouched and require reconciliation or rebuild |
| Summary/projection refresh failure after valid record change | Keep the source record valid, mark the derived view stale, and exclude it until bounded rebuild |
| Interrupted conflict-candidate cleanup | Use committed resolution lineage and Manifest state to ignore stale leftovers |
| Interrupted publication with a valid intent | Complete or reconcile the fixed plan without another semantic call |
| Orphan, before/after hash conflict, or Manifest/output mismatch | Stop; preserve evidence; expose a content-free human repair item |
| Project mapping intent conflict, orphan project record, or mapping/record disagreement | Stop; preserve local evidence; require Owner repair before project-scoped processing |

## Scheduling and concurrency

Hooks perform only bounded deterministic handoff. Semantic work runs in the
one-shot worker under a local OS lock. Periodic catch-up invokes the same path
and makes no model call when no eligible work exists. Phase 1 has one authorized
local processor; later multi-agent or multi-host coordination is not current
runtime behavior.

## Implementation boundary

Owner-turn normalization, basic credential redaction, one Continuation Summary
proposal, Run Manifest publication, replay detection, and checkpoint-last
behavior exist in the initial slice. Hooks, assistant-context normalization,
retry spooling, scheduling, complete processing budgets, typed records,
interaction consolidation, recall, and index reconciliation remain planned or
partial. Project Registration, Project Relink, and Project Mapping Intent
recovery, Orca Status, and its session reminder are accepted but unimplemented.
See [Current Status](../STATUS.md).

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Specified by:** [Memory System Contract](../governance/memory-system-contract.md)
- **Provenance contract:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Operator procedures:** [Phase 1 Local Runbook](../08-operations/runbook.md)
