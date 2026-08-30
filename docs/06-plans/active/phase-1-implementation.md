---
id: PLAN-PHASE-1
title: Phase 1 Implementation Plan
document_type: implementation-plan
status: accepted
authority: informative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-30
---

# Phase 1 implementation plan

## Purpose

Define the execution sequence and measurable milestones for completing the
accepted Phase 1 governed-memory loop from the existing initial vertical slice.

## This document owns

- The proposed order, dependency boundaries, progress, and exit criteria for
  Phase 1 implementation work.

## This document does not own

- Requirements, schemas, architecture, governance, roadmap commitment, or
  evidence that a capability is complete.

## Objective

Complete one Codex Desktop agent's local WSL memory loop against one configured
local vault: bounded capture and processing, controlled provisional memory,
interaction guidance, explicit recall, durable provenance, recovery, and zero
automatic Canonical Memory mutation.

## Roadmap phase

- [Phase 1](../../ROADMAP.md#phase-1) — active.

## Authority boundary

The Owner accepted this plan on 2026-08-30. It summarizes accepted obligations
for sequencing, but exact behavior remains owned by the
linked requirements, architecture, specifications, governance contract, and
ADRs. Checklist state alone is not implementation evidence; verified current
state belongs in [Current Status](../../STATUS.md).

## Scope

- Complete the active Codex capture, Processor, Storage, interaction, retrieval,
  configuration, runtime, and recovery paths required by Phase 1.
- Extend the existing initial slice rather than replacing its interfaces without
  an accepted design change.
- Add direct deterministic tests and bounded semantic evaluation appropriate to
  each owning contract.
- Prepare one private local WSL deployment suitable for routine Owner use.

## Non-goals

- Phase 2 multi-agent sharing or Phase 3 synchronization.
- Automatic or agent-initiated canonical apply.
- General ingestion, public services, dashboards, a general graph, or automated
  retention beyond accepted Phase 1 recovery rules.
- Importing exact design or task order from archived snapshots or legacy implementation
  material.

## Preconditions

- The Phase 1 [Requirements](../../01-foundation/requirements.md),
  [Architecture](../../02-architecture/overview.md),
  [Specification Index](../../03-specifications/README.md), and
  [Memory System Contract](../../governance/memory-system-contract.md) remain
  accepted.
- A private vault path is supplied through the accepted
  [Configuration](../../03-specifications/configuration.md) boundary; no
  personal path or credential enters tracked source.
- Each implementation change preserves the separate Conversation, Processor,
  Storage, and Retrieval responsibilities recorded in the
  [Decision Registry](../../04-decisions/README.md).

## Current baseline

The repository currently implements Owner-turn normalization, basic credential
redaction, one Continuation Summary proposal and validator, immutable Run
Manifest `0.1` publication, scan-based replay detection, checkpoint `0.1`
progress, `no_memory`, source-revision rejection, and the prevalidated
AgentCairn Distiller seam. Accepted Manifest/checkpoint `0.2`, publication
intents, assistant context, complete controlled outputs, interaction, recall,
runtime wiring, configuration loading, and deployment remain partial or planned.
[Current Status](../../STATUS.md) owns the detailed snapshot.

## Traceability

| Milestone | Requirements | Owning specifications or architecture |
|---|---|---|
| All milestones | REQ-AUTH-001, REQ-AUTH-002, REQ-AUTH-003, REQ-SAFE-001 | [Memory System Contract](../../governance/memory-system-contract.md), [Security and Trust](../../02-architecture/security-and-trust.md) |
| 1 — Complete capture | REQ-CAP-001, REQ-CAP-002, REQ-CAP-003, REQ-SAFE-001 | [Capture Pipeline](../../03-specifications/capture-pipeline.md), [Security and Trust](../../02-architecture/security-and-trust.md) |
| 2 — Add typed memory and project summaries | REQ-MEM-001, REQ-MEM-002, REQ-MEM-003, REQ-PROC-002, REQ-PROC-003 | [Memory Model](../../03-specifications/memory-model.md), [Provenance Ledger](../../03-specifications/provenance-ledger.md) |
| 3 — Complete processing, provenance, and candidates | REQ-PROC-001, REQ-PROC-002, REQ-PROC-003, REQ-AUD-001, REQ-CAND-001 | [Processing Pipeline](../../03-specifications/processing-pipeline.md), [Knowledge Candidates](../../03-specifications/knowledge-candidates.md), [Provenance Ledger](../../03-specifications/provenance-ledger.md) |
| 4 — Implement interaction behavior | REQ-INT-001, REQ-INT-002 | [Interaction Preferences](../../03-specifications/interaction-preferences.md), [Interaction Guidance](../../03-specifications/interaction-guidance.md) |
| 5 — Implement explicit recall | REQ-REC-001, REQ-REC-002, REQ-SAFE-001 | [Retrieval Contract](../../03-specifications/retrieval-contract.md), [Integration Architecture](../../02-architecture/integration-architecture.md) |
| 6 — Wire configuration and local runtime | REQ-OPS-001, REQ-OPS-002, REQ-OPS-003, REQ-CAP-003 | [Configuration](../../03-specifications/configuration.md), [Runtime Architecture](../../02-architecture/runtime.md), [Deployment Architecture](../../02-architecture/deployment.md) |
| 7 — Verify Phase 1 readiness | REQ-QUAL-001 and all Phase 1 requirements | [Roadmap Phase 1 exit criteria](../../ROADMAP.md#phase-1), [Current Status](../../STATUS.md) |

## Milestone 1 — Complete Codex capture and privacy handoff

### Work

- [x] Normalize only positively identified permitted visible/final assistant
  context while preserving Owner evidence and exact source identity.
- [x] Exclude reasoning, tools, injected envelopes, private events, subagents,
  ambiguous records, and schema drift through deterministic fixtures.
- [x] Treat a partial trailing JSONL record as incomplete input that may finish
  later without advancing progress.
- [x] Apply accepted privacy controls and credential redaction before any retry
  payload or provider handoff; retain no second raw transcript archive.

### Exit criteria

- Every inclusion, exclusion, deterministic replay, redaction, schema-drift, and
  partial-tail case in the Capture Pipeline acceptance criteria has a passing
  direct test.
- The normalized batch retains stable conversation/turn identities and permitted
  assistant context without making assistant text memory evidence.
- Capture writes no raw or merged transcript copy and does not advance a
  checkpoint for incomplete input.

## Milestone 2 — Add Typed Memory Records and Project Summary publication

### Work

- [x] Implement validated Typed Memory Record identities, controlled kinds,
  scope, status, review state, bodies, filenames, and physical placement.
- [x] Implement deterministic Project Registration and Project Relink, the
  `orca-project/0.1` registry record, exact local Git-worktree reuse, and
  `orca-project-mapping-intent/0.1` recovery.
- [x] Implement `add`, exact `support`, and confirmed `update` operations with
  Storage-owned identity, paths, timestamps, and renames.
- [x] Refresh Conversation and Project Summaries after material changes and
  avoid rewrites after support-only or no-change outcomes.
- [x] Implement `orca-run-manifest/0.2` source/operation/output joins and
  `orca-checkpoint/0.2` for the unsegmented Typed Memory slice while preserving
  immutable `0.1` read compatibility.
- [x] Prepare one fixed private publication intent before artifact mutation and
  recover matching before/after states without another semantic call.

### Exit criteria

- Valid records and summaries satisfy the Memory Model; invalid kind, scope,
  identity, transition, filename, relationship, and body fixtures fail closed.
- Add, support, update, replay, interrupted publication, and no-change tests
  prove stable identity and idempotent behavior.
- Exact mapping, new registration, explicit relink, exact Git worktree, clone,
  move, ambiguity, Keep Unassigned, and interrupted mapping tests prove one
  stable identity, no silent scope merge, and no vault path or Git-evidence
  leak.
- Publication-intent, artifact, Manifest, checkpoint, and cleanup fault tests
  prove safe completion or content-free human repair without duplicate semantic
  work.
- Publication follows intent-first/artifact-next/Manifest-next/checkpoint-last
  ordering, and mixed `0.1`/`0.2` scans preserve old receipts.

## Milestone 3 — Complete bounded processing, provenance, and candidates

### Work

- [x] Enforce total and per-context Processor budgets, chronological chunking,
  turn-boundary splitting, deterministic oversized-turn segmentation, and
  bounded related-record selection. Complete the uniform source-segment receipt
  and segment-cursor behavior for multi-segment turns.
- [x] Validate the complete memory and candidate proposal set, including
  supersession, conflict, abstention, and ordinary Knowledge Candidates.
- [x] Implement Conflict Overflow and ordinary Knowledge Candidate publication
  without adding recall eligibility or canonical authority.
- [x] Complete Run Manifest operations for every semantic outcome and artifact
  kind, and repair replay checkpoints with the exact Manifest locator and
  source-segment cursor.
- [x] Reject invalid, cross-scope, identity-changing, unsupported-transition,
  and credential-bearing output before partial publication.

### Exit criteria

- Budget, backlog, overlap, oversized-turn, exact-segment replay,
  source/operation/output join, proposal, abstention, secret-output,
  source/segmentation conflict, and interrupted-publication tests satisfy the
  Processing Pipeline and Provenance Ledger.
- Candidate schema, placement, terminal disposition, indefinite Phase 1
  retention, replay, and recall-exclusion tests satisfy Knowledge Candidates.
- Every successful semantic outcome has one durable Manifest; validation or
  publication failure leaves progress retryable and Canonical Memory untouched.

## Milestone 4 — Implement scoped interaction preferences and guidance

### Work

- [x] Validate Interaction Observations using the controlled dimensions,
  contexts, evidence classes, and abstention rules.
- [x] Consolidate scoped Adaptive Interaction Profiles with accepted activation,
  conflict, replacement, expiry, and evidence-retention behavior.
- [x] Compile only active applicable entries through the fixed versioned
  guidance templates and deterministic precedence rules.
- [x] Provide the bounded deterministic guidance-selection interface used by
  startup, resume, and post-compaction continuation without triggering semantic
  recall.

### Exit criteria

- Observation, scope, lifecycle, conflict, expiry, precedence, and compilation
  tests cover every controlled state and context.
- Missing, ambiguous, sensitive, one-turn, and session-only evidence creates no
  silent durable preference or improvised guidance.
- Generated guidance is byte-deterministic, bounded, inspectable, noncanonical,
  and measurably changes only the specified presentation behavior.

## Milestone 5 — Implement explicit recall and replaceable retrieval

### Work

- [x] Build validated current-record, summary, conflict, authority, and exact-
  conversation Retrieval Projections from permitted artifacts.
- [x] Apply authority, visibility, project, and status filters before Adapter
  ranking, then enforce relevance, overlap collapse, ordering, and budgets.
- [x] Wire AgentCairn as the initial replaceable Adapter over prevalidated local
  projections without enabling its native capture, remember, or canonical path.
- [x] Expose the accepted local explicit recall surface and return provenance-
  labelled Recall Results without an extra summarization call.
- [x] Rebuild or reconcile disposable indexes without broad fallback vault scans.

### Exit criteria

- Projection, hard-filter, relevance, duplicate, ambiguity, result-count, token-
  budget, exact-conversation, hash-mismatch, stale-summary, and missing-index
  tests satisfy the Retrieval Contract.
- Adapter replacement tests preserve results' authority and safety semantics.
- Recall occurs only after explicit invocation, never returns candidates or
  another project's private scope, and leaves every memory artifact unchanged.

## Milestone 6 — Wire validated configuration and the private local runtime

### Work

- [ ] Load and validate host and vault configuration with the accepted source
  precedence, version, path, mapping, budget, cadence, retry, and unknown-key
  behavior.
- [ ] Implement bounded `PreCompact`, `SessionEnd`, and explicit-save handoff to
  one queued one-shot worker under the local processor lock.
- [ ] Implement the secure local retry spool, three-attempt/72-hour lifecycle,
  content-free failure receipt, and successful cleanup.
- [ ] Run periodic catch-up and index reconciliation through the same idempotent
  path with no model call when no eligible work exists.
- [ ] Connect startup, resume, and post-compaction continuation to the accepted
  interaction-guidance selection interface.
- [ ] Implement deterministic Attention Item collection, the local rebuildable
  Orca Status view, owning-workflow routes, and one counts-only reminder per
  session when any item remains unresolved.
- [ ] Connect Codex Desktop to the local WSL runtime and configured vault without
  exposing a public service or tracked private configuration.

### Exit criteria

- Configuration acceptance fixtures pass before any model call or vault write.
- Hook, duplicate-trigger, lock, crash, retry, expiry, catch-up, restart, and
  stale-index tests prove one recoverable processing path.
- Attention classification, severity, stable-ID, rebuild, privacy, resolution,
  route, and reminder-suppression tests prove unresolved work remains visible
  without content exposure or source-state mutation.
- A clean local installation can process a permitted controlled conversation,
  load interaction guidance, perform explicit recall, and restart safely.
- Private paths, credentials, spools, checkpoints, locks, and caches remain
  local and ignored; no public or canonical-apply surface exists.

## Milestone 7 — Verify Phase 1 readiness

### Work

- [ ] Establish the canonical active test command and align local guidance and
  CI with every active Phase 1 suite.
- [ ] Execute deterministic acceptance scenarios for capture, privacy, secrets,
  processing, storage, conflicts, candidates, interaction, recall, replay,
  recovery, configuration, and deployment.
- [ ] Run separately labelled bounded semantic evaluations without presenting
  model quality as deterministic proof.
- [ ] Run the Owner-approved frozen common-use corpus and separate edge-safety
  set with the accepted binary rubric and retained versions.
- [ ] Exercise installation, routine operation, failure recovery, index rebuild,
  and restart against an isolated configured test vault.
- [ ] Reconcile Current Status, implementation metadata, quality evidence, and
  the operational runbook with observed results.

### Exit criteria

- Every Phase 1 requirement and Roadmap exit criterion maps to passing direct
  evidence or remains a visible blocker; no criterion is inferred from test
  count or model agreement alone.
- The complete accepted suite passes through one documented local command and
  CI runs the same required coverage.
- End-to-end controlled use demonstrates the local governed-memory loop with
  zero automatic Canonical Memory mutations and no public service.
- Common-use results meet 95% overall and 90% in every category, with zero
  critical safety failure; every edge-safety case succeeds safely, clearly
  abstains/rejects, or exposes human attention.
- The Owner accepts readiness; otherwise Phase 1 remains active and incomplete.

## Dependencies and sequencing

- Milestone 1 is the next bounded implementation slice.
- Milestone 2 follows it and establishes the artifact foundation required by
  later processing, interaction, and retrieval work.
- Milestones 3–6 proceed in order unless a separately accepted plan revision
  records a safe dependency change.
- Milestone 7 depends on all prior milestone exit criteria and the accepted
  [Acceptance Plan](../../07-quality/acceptance.md),
  [Test Strategy](../../07-quality/test-strategy.md), and
  [Phase 1 Local Runbook](../../08-operations/runbook.md).

## Risks

- Codex's non-public source format may drift; positive identification must fail
  closed without losing later retryability.
- Model output may appear authoritative; deterministic validation and Storage-
  assigned authority must remain explicit at every milestone.
- Filesystem publication is recoverable rather than fully atomic; the fixed
  local publication intent must precede artifact mutation and the checkpoint
  must remain the final durable progress write.
- Fixtures or diagnostics may expose private conversation content; use synthetic
  or explicitly permitted data and keep local runtime artifacts ignored.
- A broad end-to-end rewrite would obscure the existing verified slice; each
  milestone should land as the smallest vertically testable change.

## Validation

- Run the narrow owning tests during each change, then the canonical active suite
  once the quality milestone defines it.
- Verify observable behavior at the artifact and runtime boundary, not only
  schema shape or command exit status.
- Keep deterministic tests, semantic evaluations, and deployment evidence
  separately labelled.
- Update [Current Status](../../STATUS.md) only after implementation evidence is
  current; update accepted design only through its own review process.

## Rollback or recovery

- Disable lifecycle integration before repairing a faulty runtime path.
- Leave the last valid checkpoint unchanged after processing or publication
  failure; complete a valid fixed publication intent without another semantic
  call, or replay from permitted source/retry state only when no prepared result
  exists.
- Rebuild disposable indexes and projections from durable permitted artifacts.
- Do not delete or rewrite immutable Manifests to conceal a failed attempt.
- Revert a milestone's bounded implementation change when safe; do not weaken an
  accepted contract merely to restore a passing test.

## Completion criteria

- All seven milestone exit criteria are satisfied with current direct evidence.
- Every Phase 1 requirement and Roadmap exit criterion is verified or explicitly
  accepted as out of scope through a governed design change.
- Routine private local use, restart, recovery, and index rebuild work against
  the configured vault.
- Canonical automatic apply remains disabled, absent, and unexposed.
- Current Status and operational/quality documentation match the deployed
  behavior, and the Owner accepts Phase 1 completion.

## Progress notes

- 2026-08-29 — Initial Owner-turn, Continuation Summary, Manifest, replay, and
  checkpoint-last vertical slice verified by focused tests.
- 2026-08-30 — Plan drafted from accepted Phase 1 owners and current D-001
  through D-010 gaps.
- 2026-08-30 — Owner accepted the seven-milestone sequence and exit criteria as
  Phase 1 execution authority.
- 2026-08-30 — Owner accepted RFC-0001; Manifest/checkpoint `0.2` and local
  publication-intent recovery were promoted into the accepted Phase 1 design.
- 2026-08-30 — Owner accepted RFC-0002; Project Registration, Project Relink,
  exact local Git-worktree reuse, and mapping-intent recovery were promoted.
- 2026-08-30 — Owner accepted RFC-0003; Orca Status, one quiet session reminder,
  and the common-use/edge-safety readiness gate were promoted.
- 2026-08-30 — Milestone 1 implemented final-assistant context classification,
  private and unsupported-event exclusion, partial-tail deferral, strict
  complete-record failure, bounded source-offset reading, and secure redacted
  retry-spool primitives. Processor receives Owner evidence separately from
  assistant context. The
  active four-module suite passed 25 tests and CI was aligned to the same route.
- 2026-08-30 — Milestone 2 implemented validated Typed Memory Records, stable
  add/support/update identity, Project Summary refresh, project registration,
  relink and exact-worktree resolution, Manifest/checkpoint `0.2`, mixed `0.1`
  reads, and intent-first recoverable publication. The aligned active suite
  passed 65 deterministic tests.
- 2026-08-30 — Milestone 3 implemented conservative category/total budgets,
  chronological chunks, UTF-8 segment receipts/cursors, related-record bounds,
  supersession and conflict variants through overflow, ordinary Knowledge
  Candidates and Owner-only dispositions, controlled abstention, and strict
  Manifest source/operation/output validation. The aligned active suite passed
  103 deterministic tests.
- 2026-08-30 — Milestone 4 implemented content-free Interaction Observations
  and abstentions, immutable Manifest authority, rebuildable scoped Adaptive
  Interaction Profiles, accepted activation/conflict/replacement/expiry rules,
  and fixed bounded guidance selection shared by all context boundaries. The
  aligned active suite passed 117 deterministic tests.
- 2026-08-30 — Milestone 5 implemented explicit bounded Recall over validated
  projections, hard filters before ranking, the governed local AgentCairn BM25
  adapter over prefiltered projections, deterministic provenance-labelled
  excerpts, exact-conversation behavior, and private disposable index rebuild,
  hash validation, and missing-index failure. The aligned active suite passed
  128 deterministic tests.

## Implementation review log

| ID and milestone | Type | Description | Evidence or affected files | Impact | Safe action taken | Status | Recommended Owner decision |
|---|---|---|---|---|---|---|---|
| IRL-001 — Milestone 1 | risk | Codex Desktop's internal rollout JSONL remains a non-public and drift-prone source format. | `src/orca_memory/conversation.py`; `tests/conversation/test_codex_capture.py` | Synthetic deterministic coverage proves fail-closed behavior but not the current host's private rollout shape. | Support only positively identified Owner events and Responses-style assistant items marked `phase: final_answer`; exclude unknown shapes and require an isolated canary before routine use. | open | Permit a private local format canary during Milestone 7 without copying rollout content into tracked evidence. |
| IRL-002 — Milestone 3 | follow-up | Processor token accounting uses a versioned conservative UTF-8 byte estimate rather than a model-specific tokenizer. | `src/orca_memory/segmentation.py`; `tests/step3/test_segmentation.py` | Some multilingual or long inputs may be chunked earlier than strictly necessary, but accepted ceilings cannot be exceeded. | Record the estimator in segmentation parameters so a later governed policy can replace it without silent replay ambiguity. | resolved | None; retain the conservative policy unless measured routine-use evidence justifies a versioned replacement. |

## Related documents

- **Documentation map:** [Documentation Index](../../README.md)
- **Plan registry:** [Plan Registry](../README.md)
- **Current state:** [Current Status](../../STATUS.md)
- **Roadmap phase:** [Phase 1](../../ROADMAP.md#phase-1)
- **Requirements:** [Orca Requirements](../../01-foundation/requirements.md)
- **Architecture:** [Architecture Overview](../../02-architecture/overview.md)
- **Specifications:** [Specification Index](../../03-specifications/README.md)
- **Decisions:** [Decision Registry](../../04-decisions/README.md)
- **Acceptance:** [Phase 1 Acceptance Plan](../../07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](../../07-quality/test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](../../08-operations/runbook.md)
