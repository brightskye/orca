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
last_verified_against_code: 2026-08-29
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
Manifest publication, scan-based replay detection, checkpoint-last progress,
`no_memory`, source-revision rejection, and the prevalidated AgentCairn
Distiller seam. Assistant context, complete controlled outputs, interaction,
recall, runtime wiring, configuration loading, and deployment remain partial or
planned. [Current Status](../../STATUS.md) owns the detailed snapshot.

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

- [ ] Normalize only positively identified permitted visible/final assistant
  context while preserving Owner evidence and exact source identity.
- [ ] Exclude reasoning, tools, injected envelopes, private events, subagents,
  ambiguous records, and schema drift through deterministic fixtures.
- [ ] Treat a partial trailing JSONL record as incomplete input that may finish
  later without advancing progress.
- [ ] Apply accepted privacy controls and credential redaction before any retry
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

- [ ] Implement validated Typed Memory Record identities, controlled kinds,
  scope, status, review state, bodies, filenames, and physical placement.
- [ ] Implement local Project Root Mapping and the logical Project Registry
  boundary needed for safe project scope selection.
- [ ] Implement `add`, exact `support`, and confirmed `update` operations with
  Storage-owned identity, paths, timestamps, and renames.
- [ ] Refresh Conversation and Project Summaries after material changes and
  avoid rewrites after support-only or no-change outcomes.
- [ ] Extend Run Manifest output receipts and checkpoint-last publication for
  every new artifact.

### Exit criteria

- Valid records and summaries satisfy the Memory Model; invalid kind, scope,
  identity, transition, filename, relationship, and body fixtures fail closed.
- Add, support, update, replay, interrupted publication, and no-change tests
  prove stable identity and idempotent behavior.
- Project mappings cannot silently merge uncertain roots, clones, General,
  Unassigned, or another project scope.
- Published artifacts, Manifest, and checkpoint follow recoverable artifact-
  first/Manifest-next/checkpoint-last ordering.

## Milestone 3 — Complete bounded processing, provenance, and candidates

### Work

- [ ] Enforce total and per-context Processor budgets, chronological chunking,
  turn-boundary splitting, deterministic oversized-turn segmentation, and
  bounded related-record selection.
- [ ] Validate the complete memory and candidate proposal set, including
  supersession, conflict, abstention, and ordinary Knowledge Candidates.
- [ ] Implement Conflict Overflow and ordinary Knowledge Candidate publication
  without adding recall eligibility or canonical authority.
- [ ] Complete Run Manifest fields and failure receipts for every semantic
  outcome, and repair replay checkpoints with an available Manifest locator.
- [ ] Reject invalid, cross-scope, identity-changing, unsupported-transition,
  and credential-bearing output before partial publication.

### Exit criteria

- Budget, backlog, overlap, oversized-turn, proposal, abstention, secret-output,
  source-revision, replay, and interrupted-publication tests satisfy the
  Processing Pipeline and Provenance Ledger.
- Candidate schema, placement, terminal disposition, indefinite Phase 1
  retention, replay, and recall-exclusion tests satisfy Knowledge Candidates.
- Every successful semantic outcome has one durable Manifest; validation or
  publication failure leaves progress retryable and Canonical Memory untouched.

## Milestone 4 — Implement scoped interaction preferences and guidance

### Work

- [ ] Validate Interaction Observations using the controlled dimensions,
  contexts, evidence classes, and abstention rules.
- [ ] Consolidate scoped Adaptive Interaction Profiles with accepted activation,
  conflict, replacement, expiry, and evidence-retention behavior.
- [ ] Compile only active applicable entries through the fixed versioned
  guidance templates and deterministic precedence rules.
- [ ] Provide the bounded deterministic guidance-selection interface used by
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

- [ ] Build validated current-record, summary, conflict, authority, and exact-
  conversation Retrieval Projections from permitted artifacts.
- [ ] Apply authority, visibility, project, and status filters before Adapter
  ranking, then enforce relevance, overlap collapse, ordering, and budgets.
- [ ] Wire AgentCairn as the initial replaceable Adapter over prevalidated local
  projections without enabling its native capture, remember, or canonical path.
- [ ] Expose the accepted local explicit recall surface and return provenance-
  labelled Recall Results without an extra summarization call.
- [ ] Rebuild or reconcile disposable indexes without broad fallback vault scans.

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
- [ ] Connect Codex Desktop to the local WSL runtime and configured vault without
  exposing a public service or tracked private configuration.

### Exit criteria

- Configuration acceptance fixtures pass before any model call or vault write.
- Hook, duplicate-trigger, lock, crash, retry, expiry, catch-up, restart, and
  stale-index tests prove one recoverable processing path.
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
- Filesystem publication is recoverable rather than fully atomic; checkpoints
  must remain the final write.
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
  failure; replay from permitted source or retry state.
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
