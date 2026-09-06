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
last_reviewed: 2026-09-04
last_verified_against_code: 2026-09-04
---

# Orca current status

> [!WARNING]
> Historical snapshot preserved before Orca's structural PLS 0.3 migration on
> 2026-09-04. It records earlier paths and does not own current project truth.

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

Orca follows the PLS 0.3 working model by Owner direction dated 2026-09-04.
This changed project layout governance and navigation only; it did not change
product behavior, phase scope, or any capability claim.

## Historical layout-standard transition

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

The draft PDS-0.3 successor was initially developed inside Orca as a compact
normative kernel, triggered modules, and separate informative guidance. The
exact PDS-0.2 project baseline remains preserved at
[`docs/archive/standards/PDS-0.2.md`](../docs/archive/standards/PDS-0.2.md). Draft standard development does
not upgrade this project's `PDS-0.2` declaration or establish PDS-0.3
conformance; that requires a separate review. The former PDS v0.3 release
acceptance plan defined eight
non-waivable gates for promoting the standard itself to stable. RC.1 through
rc.3 are superseded, with their review evidence preserved. The rc.2 Independent
Reviewer completed a correct-candidate fresh review in an Owner-observed 19
minutes, reported two major and three minor findings, and scored 18/20 overall
but 8/10 on authority/truth-role questions. On 2026-09-02, PDS Owner `victor`
accepted findings 001–003, rejected 004–005 with recorded rationales, and
authorized `PDS-0.3.0-rc.3`. RC.3 clarifies Gate 8's normative force and fixes
the two trace mappings. Its 22-file manifest verifies with combined digest
`sha256:86261c89c1bcbb9c785632df8d8d4938eefea8e9391527cbc50a2b0ef5982016`.
The regenerated inventory has 154 occurrences, 79 stable targets, and zero
unmapped rows. PDS Owner `victor` approved the exact rc.3 digest on 2026-09-02,
so Gate 1 passed and the candidate was frozen. Its Independent Reviewer package
has 21 reviewer-facing inputs and digest
`sha256:45ef3e01be8a26e7d69ade823f70f26b63e579d2ded0220d969e12b837b7afd6`.
The bundle excludes the scoring key, prior review evidence, correction map, and
trace-audit conclusions. The first fresh Independent Reviewer response was
completed in an Owner-observed 16 minutes and is countable review evidence. It
scored 18/20 overall but 8/10 on authority/truth-role questions, so its
comprehension exercise failed. It reported four Major and three Minor findings;
PDS Owner `victor` accepted all seven on 2026-09-02 and authorized rc.4. RC.4
adds normative force to the four change-Level minimum obligations and all
thirteen module semantic-review obligations, makes the ownership-map trigger
objective, clarifies Gate 6/7 ownership, and defines reviewer-facing inventory
and digest conventions. Its 22-file manifest verifies with combined digest
`sha256:4526887539c1421b6b220195d25b32cd3d074eda5cd6d11635e5d7b64d59671b`.
The regenerated rc.4 inventory has 171 occurrences, 79 stable targets, and zero
unmapped rows. PDS Owner `victor` approved the exact rc.4 digest on 2026-09-02,
so Gate 1 passed and the candidate is frozen. Gate 2 is in progress; its clean
Independent Reviewer package is ready with 22 reviewer-facing inputs and digest
`sha256:248872ed8cb8e2e7563a2a32b26dd5028271505f11aa63847ee23eca6e060485`.
It includes the new reviewer conventions and excludes the scoring key, prior
review evidence, correction map, and trace-audit conclusions. The first rc.4
Independent Reviewer response was completed in an Owner-observed 12 minutes,
including all waits, so its timing passes. It is countable review evidence but
scored 17/20 overall and 7/10 on authority/truth-role questions; both scoring
thresholds fail. The response reported five Major and two Minor findings. On
2026-09-02, PDS Owner `victor` accepted all seven and authorized rc.5 with the
recommended corrections. RC.5 gives every release pass condition and reset
rule explicit normative force, normalizes intended lowercase absolute
obligations, clarifies the ownership-map and compact-project split conditions,
makes the validator contract the sole check-list owner, maps final promotion to
Gate 8, and gives the Decisions and Roadmap responsibility pairs precise trace
targets. Its 22-file manifest verifies with combined digest
`sha256:0681312b9d9f9d540c5849d02c5cf8a507da9d474fc276969bc81c42e67e07fe`.
The current rc.5 inventory has 230 occurrences, 93 targets, and zero
unmapped rows. PDS Owner `victor` approved the exact rc.5 digest on 2026-09-02,
so Gate 1 passed and the candidate is frozen. Gate 2 is in progress; its clean
Independent Reviewer package is ready with 22 reviewer-facing inputs and digest
`sha256:d4e21f7e44be9c97f583a3ff5582e4c77e3e3bf61e283256c1103733ea1c7363`.
It excludes the scoring key, prior review evidence, correction map, and
trace-audit conclusions. The first rc.5 Independent Reviewer response was
completed in an Owner-observed 15 minutes, so timing passes. It is countable
with a disclosed VS Code workspace-isolation limitation, but scored 15/20
overall and 6/10 on authority/truth-role questions; both thresholds fail. Its
occurrence audit confirms all 230 rows, while qualitative trace review used
targeted sampling and is not exhaustive. The response reported five Minor
findings. PDS Owner `victor` rejected finding 001 with rationale, accepted and
resolved findings 002, 003, and 005, and accepted finding 004 as a constraint
against claiming boundary precision before Gate 3 evidence exists. All five
findings are dispositioned. The exact first-attempt bundle remains preserved
with its original digest. The Codex primary-author exercise then passed in 2
minutes 4 seconds with 20/20 overall and 10/10 authority/truth-role answers;
its response was frozen before the scoring key was opened. The Owner exercise
then stopped incomplete after 46 minutes 12 seconds without scoring because the
Owner could not reliably understand the candidate's terminology and multi-part
questions. Owner-raised Major finding `G2-RC5-OWNER-001` requests simple
English and simple terms throughout the standard and exercise; it remains open
pending formal disposition. A replacement Owner result, a passing fresh
Independent Reviewer exercise, and exhaustive corrected-inventory review
remain pending. No rc.4 result carries forward.
On 2026-09-03, work began in `pds/working/plain-english/` without assigning a
new release-candidate number. A complete first rewrite now covers the kernel,
all thirteen modules, release plan, validator contract, guides, checklist,
templates, and comprehension questions. Normalized normative-word totals match
the rc.5 sources, and all working-package links resolve. The normative
rule-by-rule meaning review is complete at a locked sixteen-file manifest: all
269 rule occurrences map as equivalent, including all 39 `MAY` permissions.
The review corrected ambiguous quantities, deactivation agency, adequacy versus
completeness, idempotency, migration evidence, trial measurements, and
validator-boundary wording. The adoption and migration guides, checklist,
templates, and comprehension questions have now passed an informative
consistency review. A no-timer, one-checkpoint-at-a-time Owner readability
walkthrough is ready. The Owner result remains pending. Frozen rc.5 is
unchanged, and the working draft does not yet resolve `G2-RC5-OWNER-001`.
The reference validator, conformance fixtures, real adoption trials,
effectiveness results, and final release approval do not yet exist.

During the Owner walkthrough, the Owner concluded that the profile, module,
activation, gate, evidence, and validator model was itself too abstract and
process-heavy. On 2026-09-03 the Owner authorized a substantive structure-first
rewrite that became the independently maintained PLS 0.3 working model.
The new working direction uses one root README, question-based default document
locations, a combined Project Record, optional supporting artifact directories,
direct human judgment, and a short agent placement procedure. It does not
require profiles, module declarations, PDS-specific validators, evidence
folders, or release gates. The exact rc.5 plain-English rewrite remains
preserved as earlier work, frozen rc.5 still verifies unchanged, and no
successor release candidate has been assigned.

Successor standard development was then moved out of Orca into that independent
project and renamed Project Layout Standard (PLS) on 2026-09-04. Later that day,
the Owner explicitly adopted its 0.3 working model for Orca while retaining
Orca's useful existing locations. Future changes in the independent PLS project
do not silently alter Orca's recorded version or layout.

## Current capability status

| Capability | Status | Evidence or limitation |
|---|---|---|
| Owner and final-assistant Codex normalization, privacy filtering, partial-tail deferral, and credential-pattern redaction | Implemented | `conversation.py`, `privacy.py`, synthetic deterministic capture tests, and Processor evidence/context separation tests |
| Bounded Processor, Continuation Summary, and controlled proposal validation | Implemented | Category/total budgets, chunks, UTF-8 segments, overlap, related-record bounds, output limits, and controlled outcomes are directly tested |
| Run Manifest, replay, checkpoint-last publication, `no_memory`, and source/segmentation conflict handling | Implemented | Manifest/checkpoint `0.2`, exact segment cursors, strict source/operation/output joins, mixed `0.1` reads, and publication-intent recovery are directly tested |
| AgentCairn governed adapters | Implemented | Prevalidated Distiller seam and local BM25 retrieval over only prefiltered projections are directly tested; a separate Codex CLI provider canary passed on one authorized redacted sample, and exact-revision lifecycle verification is recorded below |
| Typed Memory Records, Project Summary, and project registration/relink | Implemented with operator commands | Validated records, add/support/update, summary refresh, exact-root lifecycle resolution, and recoverable registration/relink commands and tests |
| Knowledge Candidates, supersession, conflict records, and overflow | Implemented | Strict noncanonical schemas, stable variants, Owner-only review/disposition primitives, distinct placement, and joined publication tests |
| Owner candidate/conflict review and recovery commands | Implemented and tested synthetically | Separate candidate and conflict commands publish content-minimized receipts and private recoverable intents; `orca recovery owner-review`, `publication`, and `project-mapping` reconcile only fixed safe operation IDs and never make a semantic call |
| Encrypted vault backup and staging restore | Implemented and tested at the GPG boundary | `backup create` requires lifecycle disabled, no pending work, an explicit recipient, and a new output; `backup verify` checks every hash; `backup stage` exposes only a new staging directory and never overwrites live state. A real GPG backup has not run in this reconciliation |
| Interaction observations, profiles, and compiled guidance | Implemented | Exact-source Manifest observations, content-free abstentions, rebuildable scoped profiles, lifecycle rules, and fixed bounded guidance selection are directly tested |
| Explicit Recall and retrieval projections | Implemented | Hard-filtered bounded results, exact-conversation behavior, governed AgentCairn ranking, private rebuildable hash-checked indexes, and the local explicit CLI are directly tested |
| Lifecycle hooks, deterministic Project/General/Unassigned scope, bounded queue drain, retry spool, catch-up command/cadence, and explicit save | Implemented and installed; currently disabled; exact-revision canary passed | Exact mapped roots select Project, explicit content-free Owner conversation choices may select General, and unresolved roots stay Unassigned. Automatic work rechecks the toggle per queued unit, retries transient failures with bounded delays, continues after terminal failures, and uses private source cursors so only new complete bytes are handed off. Catch-up skips Unassigned history without provider access. The authorized exact-revision canary passed before `497fc5f` was pushed. Orca installs no daemon or OS scheduler. |
| Orca Status, Attention Items, and session reminder | Implemented | Content-free collection includes pending queue work and rejected catch-up sources, stable IDs, rebuild, routes, counts, privacy, failure visibility, and once-per-session suppression are directly tested |
| Host configuration loading and WSL deployment | Implemented for Phase 1 | Strict host/vault configuration validates; default-off and enabled paths are directly verified. The earlier authorized canary produced one secret-free noncanonical candidate, one Manifest/checkpoint pair, one review Attention Item, and no canonical output; exact-revision release evidence is retained locally rather than in tracked private data |
| Canonical automatic apply | Deliberately absent | Disabled and unexposed by Phase 1 governance |

## Known divergence

- The private local runtime and retrieval reconciliation are implemented and
  synthetically integrated. The installed lifecycle dispatcher passed the
  authorized exact-revision canary before `497fc5f` was pushed and is currently
  disabled. The task sandbox blocked nested Codex state-database writes, so
  normal local Codex state access was required for the provider worker and
  detached replay.
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
  complete. Milestone 6 and readiness implementation were checkpointed at
  `b8729d8`; release hardening and the accepted current state are in `497fc5f`,
  which matches `origin/main`.

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

- Repository layout and documentation review date: 2026-09-04.
- Code was last compared with the active contracts on 2026-08-31.
- The complete current active regression command passed 228 tests on
  2026-09-04 and is current regression evidence.
- The 2026-08-31 suite run, together with the retained operational and quality
  evidence, satisfied the technical gate; the Owner accepted that complete
  evidence set on 2026-08-31.
- Historical migration material remains in the non-authoritative
  [documentation archive](_archive/pds-migration/README.md).

## Related documents

- **Documentation map:** [Documentation Index](README.md)
- **Roadmap phase:** [Phase 1](ROADMAP.md#phase-1)
- **Required behavior:** [Requirements](01-foundation/requirements.md)
- **Current design:** [Architecture Overview](02-architecture/README.md)
- **Acceptance:** [Acceptance Plan](07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](07-quality/test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](08-operations/runbook.md)
