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
last_reviewed: 2026-08-29
last_verified_against_code: 2026-08-29
related:
  - ARCH-OVERVIEW
  - REQ-ORCA
---

# Orca runtime architecture

## Purpose

This document defines the proposed Phase 1 execution model, runtime flows,
concurrency boundaries, publication order, and recovery responsibilities.

## This document owns

- Lifecycle-hook, worker, publication, reconciliation, and recall flows.
- Runtime failure and recovery boundaries.

## This document does not own

- Exact record formats, token budgets, commands, or implementation progress.

## Execution contexts

| Context | Responsibility |
|---|---|
| Codex session-start path | Load bounded applicable interaction guidance only |
| Explicit Recall invocation | Retrieve permitted authority-labelled context for a specific request |
| `PreCompact` or `SessionEnd` hook | Perform bounded deterministic handoff and queue work |
| One-shot worker | Read, deduplicate, process, validate, and publish one bounded unit of work |
| Periodic catch-up | Discover missed work and invoke the same one-shot worker |
| Retrieval reconciliation | Rebuild or update disposable projections and indexes from current Markdown |

No permanent daemon is required by the accepted design.

## Session-start flow

1. Resolve applicable active interaction-profile entries by explicit precedence.
2. Compile only known values through fixed guidance templates within the
   configured budget.
3. Supply the bounded noncanonical guidance to Codex.
4. Perform no automatic semantic memory recall or conversation processing.

## Explicit recall flow

1. Receive the explicit memory question and permitted filters.
2. Apply authority, visibility, project, and status filters before ranking.
3. Ask the replaceable retrieval adapter for bounded candidate projections.
4. Select directly relevant results, collapse duplicates, and leave weak or
   ambiguous positions empty rather than filling a quota.
5. Return labelled excerpts and provenance without a second summarization call.

Exact selection and budget behavior remains owned by the current governance and
operations contracts until the retrieval specification is migrated.

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
9. Storage publishes validated derived artifacts and the durable Run Manifest.
10. The source checkpoint advances last; successful retry-spool content is then
    deleted.
11. Retrieval reconciliation updates disposable projections and indexes.

See the [processing-flow diagram](diagrams/processing-flow.mmd).

## Publication and recovery

Filesystem publication is recoverable, not fully transactional. Storage prepares
and publishes target artifacts, publishes the Run Manifest as the durable receipt,
and advances the checkpoint last. A crash before checkpointing permits replay;
Manifest lookup prevents a second semantic result and may repair progress.

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
partial. See [Current Status](../STATUS.md).

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Specified by:** [Memory System Contract](../governance/memory-system-contract.md)
- **Provenance contract:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Operator procedures:** [Phase 1 Local Runbook](../08-operations/runbook.md)
