---
id: ARCH-RUNTIME
title: Orca Runtime Architecture
document_type: architecture
status: accepted
authority: normative
implementation_status: implemented
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-31
last_verified_against_code: 2026-08-31
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
| Explicit Owner review | Approve/reject a candidate, select/resolve/acknowledge a conflict, and record the decision without a model call |
| Explicit recovery or backup | Reconcile one safe operation ID, verify a backup, or expose verified backup contents in new staging |
| `PreCompact` or `SessionEnd` hook | Perform bounded deterministic handoff and queue work |
| One-shot worker | Drain up to 20 queued units by default, processing each unit through the bounded pipeline |
| Periodic catch-up | Discover missed work and invoke the same one-shot worker |
| Retrieval reconciliation | Rebuild or update disposable projections and indexes from current Markdown |

No permanent daemon is required by the accepted design.

Installed lifecycle hooks first load the validated vault setting
`lifecycle.enabled`, which defaults to `false`. Disabled hooks return before
transcript access or other automatic work. Enabled hooks follow the same
mandatory local privacy and redaction path; the setting cannot enable
unredacted provider input. Explicit operator commands are separate.

Each enabled lifecycle event resolves its working directory before loading
project guidance or queueing work. A valid exact root mapping selects Project;
an unmapped conversation uses General only after the Owner records that explicit
conversation choice; otherwise it remains Unassigned. This decision is
content-free and deterministic, and Project evidence takes precedence.

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

1. Resolve Project, explicitly confirmed General, or Unassigned scope from
   local governance evidence without a model call.
2. Resolve applicable active interaction-profile entries by explicit precedence.
3. Compile only known values through fixed guidance templates within the
   configured budget.
4. Supply the bounded noncanonical guidance to Codex.
5. Check the local rebuildable attention projection and, when any item remains
   unresolved, show at most one counts-only reminder for the session.
6. Perform no automatic semantic memory recall or conversation processing.

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
4. Before each automatic unit, the worker reloads `lifecycle.enabled`. Disabled
   work stays pending without an attempt. Otherwise, the worker processes units
   until the queue is empty, a transient unit exhausts its current retry cycle,
   or the default 20-item safety limit is reached. Transient failures retry
   after one and two seconds, up to the configured three-attempt default;
   terminal failures are recorded while later independent units continue.
   Remaining work reports `pending` rather than claiming completion.
5. A local lock prevents concurrent processing of the same work.
6. The Connector reads after the private monotonic source byte cursor and
   durable processing checkpoint, then applies event, privacy, redaction,
   identity, and hashing rules.
7. Durable Run Manifests establish successful prior processing. Exact replay is
   skipped; an unexpected same-policy source revision fails closed.
8. Processor constructs one bounded chronological input and invokes one
   replaceable semantic provider.
9. Deterministic validation admits only controlled proposals with valid source,
   scope, identity, lifecycle, and safety properties.
10. Storage prepares all post-images plus fixed Manifest and checkpoint payloads,
   then publishes one private local publication intent.
11. Storage publishes validated derived artifacts and the durable Run Manifest.
12. The source-segment checkpoint advances last; successful retry-spool and
    publication-intent content is then deleted.
13. Retrieval reconciliation updates disposable projections and indexes.

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

Owner review has a separate fixed-intent path. Candidate and conflict commands
write a content-minimized receipt first, then publish the fixed candidate or
record post-image; conflict resolution removes overflow candidates only after
the resolved record and receipt are durable. `orca recovery owner-review
<operation-id>` resumes a valid interrupted plan without a semantic call. The
same recovery command family also handles publication and project-mapping
intents. Any identity, path, or before/after hash mismatch remains visible for
Owner repair.

Backup is an explicit maintenance flow, not part of automatic processing. With
lifecycle disabled and no pending queue or recovery work, Orca encrypts the
full vault and only validated source-cursor and scope-choice state. Verification
checks the archive manifest and every member hash. Decryption is exposed only
to a new private staging directory and never writes a live vault or runtime.

An optional SQLite projection may accelerate processed-source, audit, and
interaction-observation lookup. It is never the correctness baseline and must be
rebuildable from durable Manifests without conversation text.

## Failure boundaries

| Failure | Required behavior |
|---|---|
| Unsupported, private, injected, tool, reasoning, subagent, or ambiguous event | Exclude before semantic processing; retain at most a content-free local receipt where required |
| Partial trailing source record | Process complete preceding records, keep the cursor at the last complete byte, and wait for a later run |
| Lock contention | The competing worker exits; the active worker continues its bounded queue drain |
| Invalid semantic or deterministic output | Publish no affected derived artifact and leave checkpoint unchanged |
| Credential-like generated output | Reject before storage, indexing, synchronization, or recall |
| Index failure | Leave Markdown untouched and require reconciliation or rebuild |
| Summary/projection refresh failure after valid record change | Keep the source record valid, mark the derived view stale, and exclude it until bounded rebuild |
| Interrupted conflict-candidate cleanup | Use committed resolution lineage and Manifest state to ignore stale leftovers |
| Interrupted publication with a valid intent | Complete or reconcile the fixed plan without another semantic call |
| Interrupted Owner review with a valid intent | Complete or reconcile the fixed receipt and target post-images without another semantic call |
| Backup requested while lifecycle is enabled or work is pending | Fail closed; disable lifecycle and settle all pending queue/recovery state first |
| Backup verification or staging finds a path, type, permission, or hash mismatch | Fail closed; expose no staging contents and never alter live state |
| Orphan, before/after hash conflict, or Manifest/output mismatch | Stop; preserve evidence; expose a content-free human repair item |
| Project mapping intent conflict, orphan project record, or mapping/record disagreement | Stop; preserve local evidence; require Owner repair before project-scoped processing |

## Scheduling and concurrency

Hooks perform only bounded deterministic handoff. Semantic work runs in the
one-shot worker under a local OS lock. One invocation drains up to 20 items by
default, applies the bounded automatic retry delays, continues past terminal
failures, and reports `pending` when its limit is reached with work remaining.
Periodic catch-up considers only mapped Project or explicitly confirmed General
sources, skips Unassigned history without provider access, and queues only bytes
after the private source cursor. It resolves and contains each discovered source
inside the configured rollout store before reading metadata. An invalid source
creates only a content-free discovery Attention Item and does not prevent later
valid sources from being considered. Catch-up makes no model call when no
eligible new work exists. Phase 1 has one authorized local processor; later
multi-agent or multi-host coordination is not current runtime behavior.

## Implementation boundary

The accepted library and local CLI surfaces implement bounded hook queues,
one-shot locking, retry handling, catch-up, recoverable publication, typed
records, interaction guidance, explicit Owner review, recovery commands,
encrypted backup verification/staging, explicit Recall, rebuild, Orca Status,
and its session reminder. The project hook deployment is installed but
currently disabled. The earlier bounded lifecycle canary is evidence only for
its recorded sample and revision; release requires a fresh exact-revision
canary before push. New private samples, providers, vaults, or
expanded lifecycle scope still require Owner authorization. See
[Current Status](../STATUS.md) and the [Deployment
Guide](../08-operations/deployment.md).

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Specified by:** [Memory System Contract](../governance/memory-system-contract.md)
- **Provenance contract:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Operator procedures:** [Phase 1 Local Runbook](../08-operations/runbook.md)
