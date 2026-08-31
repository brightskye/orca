---
id: PROJECT-STATUS
title: Orca Current Status
document_type: project-status
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-31
last_verified_against_code: 2026-08-31
---

# Orca current status

## Purpose

This document reports what Orca currently implements and where implementation
diverges from accepted Phase 1 design.

## This document owns

- The current project and implementation snapshot.
- Known design-to-implementation divergence and current blockers.

## This document does not own

- Requirements, exact behavior, architecture, or future direction.

## Current phase

[Phase 1](ROADMAP.md#phase-1) is complete and was accepted by the Owner on
2026-08-31. Orca implements the governed local capture, processing, provisional
memory, interaction guidance, explicit Recall, provenance, recovery, and
attention loop. Canonical automatic apply remains disabled and absent.

The PDS-0.2 Core-profile migration is complete and was committed on 2026-08-30
as `e686092`. The control plane, foundation, architecture, specifications,
decisions, plan, quality, limited operations, and archive boundaries are
accepted. [RFC-0001](05-proposals/0001-strengthen-run-manifest-provenance.md)
was accepted and promoted on 2026-08-30.
[RFC-0002](05-proposals/0002-define-project-registration-and-relinking.md)
was accepted and promoted on 2026-08-30. Every Phase 1 documentation subject has one registered
current owner.
[RFC-0003](05-proposals/0003-define-human-attention-and-common-use-gate.md)
was accepted and promoted on 2026-08-30.

## Capability status

| Capability | Status | Evidence or limitation |
|---|---|---|
| Owner and final-assistant Codex normalization, privacy filtering, partial-tail deferral, and credential-pattern redaction | Implemented | `conversation.py`, `privacy.py`, synthetic deterministic capture tests, and Processor evidence/context separation tests |
| Bounded Processor, Continuation Summary, and controlled proposal validation | Implemented | Category/total budgets, chunks, UTF-8 segments, overlap, related-record bounds, output limits, and controlled outcomes are directly tested |
| Run Manifest, replay, checkpoint-last publication, `no_memory`, and source/segmentation conflict handling | Implemented | Manifest/checkpoint `0.2`, exact segment cursors, strict source/operation/output joins, mixed `0.1` reads, and publication-intent recovery are directly tested |
| AgentCairn governed adapters | Implemented | Prevalidated Distiller seam and local BM25 retrieval over only prefiltered projections are directly tested; an earlier separate Codex CLI provider canary passed on one authorized redacted sample, and release requires a fresh exact-revision canary before push |
| Typed Memory Records, Project Summary, and project registration/relink | Implemented with operator commands | Validated records, add/support/update, summary refresh, exact-root lifecycle resolution, and recoverable registration/relink commands and tests |
| Knowledge Candidates, supersession, conflict records, and overflow | Implemented | Strict noncanonical schemas, stable variants, Owner-only review/disposition primitives, distinct placement, and joined publication tests |
| Owner candidate/conflict review and recovery commands | Implemented and tested synthetically | Separate candidate and conflict commands publish content-minimized receipts and private recoverable intents; `orca recovery owner-review`, `publication`, and `project-mapping` reconcile only fixed safe operation IDs and never make a semantic call |
| Encrypted vault backup and staging restore | Implemented and tested at the GPG boundary | `backup create` requires lifecycle disabled, no pending work, an explicit recipient, and a new output; `backup verify` checks every hash; `backup stage` exposes only a new staging directory and never overwrites live state. A real GPG backup has not run in this reconciliation |
| Interaction observations, profiles, and compiled guidance | Implemented | Exact-source Manifest observations, content-free abstentions, rebuildable scoped profiles, lifecycle rules, and fixed bounded guidance selection are directly tested |
| Explicit Recall and retrieval projections | Implemented | Hard-filtered bounded results, exact-conversation behavior, governed AgentCairn ranking, private rebuildable hash-checked indexes, and the local explicit CLI are directly tested |
| Lifecycle hooks, deterministic Project/General/Unassigned scope, bounded queue drain, retry spool, catch-up command/cadence, and explicit save | Implemented and installed; currently disabled; earlier canary passed | Exact mapped roots select Project, explicit content-free Owner conversation choices may select General, and unresolved roots stay Unassigned. Automatic work rechecks the toggle per queued unit, retries transient failures with bounded delays, continues after terminal failures, and uses private source cursors so only new complete bytes are handed off. Catch-up skips Unassigned history without provider access. An earlier authorized two-turn canary passed SessionStart, PreCompact, Luna/xhigh processing, SessionEnd deduplication, and detached replay. Release requires the same bounded canary on the exact commit before push. Orca installs no daemon or OS scheduler |
| Orca Status, Attention Items, and session reminder | Implemented | Content-free collection includes pending queue work and rejected catch-up sources, stable IDs, rebuild, routes, counts, privacy, failure visibility, and once-per-session suppression are directly tested |
| Host configuration loading and WSL deployment | Implemented for Phase 1 | Strict host/vault configuration validates; default-off and enabled paths are directly verified. The earlier authorized canary produced one secret-free noncanonical candidate, one Manifest/checkpoint pair, one review Attention Item, and no canonical output; exact-revision release evidence is retained locally rather than in tracked private data |
| Canonical automatic apply | Deliberately absent | Disabled and unexposed by Phase 1 governance |

## Known divergence

- The private local runtime and retrieval reconciliation are implemented and
  synthetically integrated. One authorized redacted private sample passed the
  provider/candidate path. The installed lifecycle dispatcher is verified both
  off and enabled on the bounded two-turn sample. This is earlier-sample
  evidence only; the release process therefore gates push on an authorized
  canary for the exact commit. The task sandbox blocks nested Codex state-database writes; normal
  local Codex state access was required for the provider worker and detached
  replay.
- Codex's internal rollout format remains non-public. The connector supports the
  accepted Responses-style `final_answer` marker and fails closed on drift, but
  isolated host-format verification remains required before routine use.
- Encrypted backup uses the local GPG boundary and has deterministic hash and
  staging tests. A real backup and restore of the configured private vault have
  not been executed here.

These are implementation gaps, not permission to weaken the accepted contracts.

## Phase completion

- Design hardening: RFC-0001, RFC-0002, and RFC-0003 are accepted and promoted.
  The four post-migration design-hardening steps are complete.
- Phase 1 implementation: all seven milestones, all 18 acceptance scenarios,
  the frozen quality gates, operational canaries, and Owner acceptance are
  complete. Milestone 6 and readiness implementation are checkpointed at
  `b8729d8`; the final accepted-status checkpoint follows this reconciliation.

The accepted plan owns Phase 1 implementation sequence and milestone progress;
this document continues to own the verified current-state snapshot.

## Decisions and remaining limitations

Architecture, specification, and ADR extraction are accepted. ADR-0001 remains
superseded history; ADR-0002 and ADR-0003 remain future-only proposal evidence;
ADR-0004 through ADR-0012 are accepted current rationale. Knowledge Candidate
and Configuration design choices are no longer open. Knowledge Candidates and
the complete segmented provenance slice are implemented. RFC-0001 resolved the
Manifest, checkpoint, provenance-join, and interrupted-publication design, now
implemented for the active pipeline. RFC-0002 resolved Project Registration,
Project Relink, exact-worktree reuse, and mapping-intent recovery, which are now
implemented and deterministically tested.

RFC-0003 resolved human-attention visibility and readiness measurement: one
content-free reminder per session for any unresolved item, a minimum 100-case
common-use corpus, 95% overall, 90% per category, zero critical failures, and a
separate mandatory edge-safety set. The Owner-approved frozen sets passed
100/100 common-use cases and 12/12 edge-safety cases with zero critical
failures. A separately labelled synthetic semantic rerun passed its fixed gates;
it is not deterministic proof.

Phase 1 has no open acceptance blocker. All 18 scenarios have passing direct
technical evidence and the ignored local acceptance record contains the Owner's
accepted verdict. Automatic Canonical Markdown indexing remains explicitly
deferred; canonical apply remains disabled. The one pending Knowledge Candidate
continues through its normal Owner review workflow and does not reopen the phase
gate.

## Verification

- Repository and documentation review date: 2026-08-31.
- Code was compared with the active contracts during the PDS audit.
- The complete current active regression command passed 228 tests on
  2026-08-31. Together with the retained operational and quality evidence it
  satisfied the technical gate; the Owner accepted the complete evidence set on
  2026-08-31.
- Historical migration evidence remains in the non-authoritative
  [migration working set](_working/pds-migration/README.md).

## Related documents

- **Documentation map:** [Documentation Index](README.md)
- **Roadmap phase:** [Phase 1](ROADMAP.md#phase-1)
- **Required behavior:** [Requirements](01-foundation/requirements.md)
- **Current design:** [Architecture Overview](02-architecture/overview.md)
- **Acceptance:** [Acceptance Plan](07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](07-quality/test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](08-operations/runbook.md)
