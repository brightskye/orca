---
id: WORK-2026-08-29-PDS-HUMAN-DECISIONS
title: PDS Audit Owner Decisions
document_type: working-note
status: complete
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Owner decisions

> [!WARNING]
> This is a migration control record, not a canonical behavior specification.
> Current project documents remain the owners of accepted system behavior.

The Owner approved the following migration decisions on 2026-08-29. These
resolutions direct the migration but do not by themselves authorize source
archival or deletion.

## H-001 — Adopt PDS v0.2 Core profile

**Decision needed:** Confirm that Orca adopts `PDS-0.2` with the `core` profile
and the triggered runtime, deployment, data, security, and integration
architecture documents identified by this audit.

**Why human review is required:** PDS requires an explicit project declaration;
the audit can recommend but cannot adopt a governance standard.

**Effect:** Unblocks `docs/README.md`, control documents, metadata conversion,
and validation rules.

**Resolution:** Adopt `PDS-0.2` with the `core` profile and all architecture
documents triggered by this audit.

## H-002 — Resolve conflicting-memory supersession semantics

**Decision needed:** Choose between:

- a later trusted timestamp alone makes the later position current; or
- chronology is necessary but not sufficient, and the later trusted Owner turn
  must clearly state or confirm the applicable replacement.

**Evidence:** `docs/system-design.md` lines 205–209 versus
`docs/governance/memory-system-contract.md` lines 173–184 and
`docs/memory-record-contract.md` lines 306–315.

**Why human review is required:** All sources appear current/normative and the
choice materially changes durable conflict handling. No implementation exists
to disambiguate intent.

**Effect:** Unblocks requirements, glossary, memory-model specification, and
acceptance criteria.

**Resolution:** Chronology is necessary but insufficient. A later trusted Owner
turn wins only when it clearly states or confirms the applicable replacement.

## H-003 — Classify Phase 2 and Phase 3 commitment

**Decision needed:** Assign each later phase one PDS roadmap state:
`committed`, `candidate`, `exploratory`, or `deferred`.

**Evidence:** root README calls both `Planned`; active system design treats them
as intended delivery phases; `tbd/future/delivery-plan.md` is an accepted-labelled
but explicitly noncurrent baseline.

**Why human review is required:** “Planned” does not establish commitment under
PDS, and future exact designs must not be silently promoted.

**Effect:** Unblocks ROADMAP, future-state deployment summaries, and proposal
classification.

**Resolution:** Phase 2 and Phase 3 are `candidate` directions. Exact later-phase
design remains unaccepted proposal evidence unless separately approved.

## H-004 — Decide existing ADR status and placement

**Decision needed:** For ADRs 0001–0004, confirm:

- whether ADR 0004 is active accepted rationale for the current checkout/vault
  separation;
- whether ADRs 0002 and 0003 are accepted future decisions or proposal evidence;
- whether the set moves to `docs/04-decisions/` or remains noncurrent in `tbd/`.

**Why human review is required:** The ADRs say accepted/superseded, but their
parent directory says nothing in it defines current behavior. PDS forbids
inferring authority from names or placement.

**Effect:** Unblocks the active ADR registry. Numbers 0001–0004 must be preserved
and never reused regardless of the choice.

**Resolution:** ADR 0001 is superseded historical rationale. ADR 0004 is active
accepted rationale and will move to the active decision registry during
migration. ADRs 0002 and 0003 remain future-only proposal evidence under `tbd/`.
All four numbers remain reserved.

**Custody correction (2026-08-30):** The Owner subsequently directed that all
ADR records follow the PDS `docs/04-decisions/` location. ADR 0001 remains
superseded, ADRs 0002 and 0003 remain proposed future-only evidence, and ADR
0004 remains accepted; only their custody changed. `tbd/` retains future inputs,
not ADR records.

## H-005 — Define the Phase 1 role of ordinary Knowledge Candidates

**Decision needed:** Either:

1. confirm Knowledge Candidates are a Phase 1 artifact and authorize creation of
   a complete active specification for their schema, placement, lifecycle,
   review, retention, and recall exclusion; or
2. narrow Phase 1 claims until that behavior is intentionally designed.

**Why human review is required:** Current active docs require candidates but do
not define them completely. Legacy Curator/Phase 7 contracts and the specific
Conflict Overflow Candidate contract cannot safely be generalized.

**Effect:** Unblocks requirements, data architecture, specification registry,
and Phase 1 plan.

**Resolution:** Knowledge Candidates remain a Phase 1 artifact. The migration
will create a complete active specification for schema, placement, lifecycle,
review, retention, and recall exclusion without importing legacy behavior by
default.

## H-006 — Approve public project-status wording

**Decision needed:** Replace or retain `SECURITY.md`'s statement that Orca is
only architecture/manual prototype, using an accurate public support statement
that acknowledges the initial implementation slice without implying deployment.

**Why human review is required:** This is public-facing security/support
language, and current files conflict.

**Effect:** Unblocks `docs/STATUS.md`, root README, and root SECURITY cleanup.

**Resolution:** Describe Orca as an active but incomplete Phase 1 local
implementation that is not deployed or publicly supported. Canonical automatic
apply remains disabled.

## H-007 — Decide the long-term `tbd/` PDS exception

**Decision needed:** Confirm whether `tbd/` remains a project-specific,
noncurrent mixed code/test/document reference package outside the PDS docs tree.

**Recommended choice:** Retain it and declare the exception. Moving legacy code
and fixtures under `docs/_archive/` would misclassify repository content and
expand the migration beyond documentation.

**Why human review is required:** PDS allows explicit exceptions, but the audit
cannot create one unilaterally.

**Effect:** Unblocks documentation routing and legacy preservation strategy.

**Resolution:** Retain `tbd/` as an explicit PDS exception for noncurrent mixed
code, tests, fixtures, schemas, and documentation.

**Custody clarification (2026-08-30):** The exception does not include ADR
records. Those remain in `docs/04-decisions/` under their PDS lifecycle status.

**Final location correction (2026-08-30):** Standalone historical documents
moved to `docs/_archive/`. The remaining runnable source/test package moved
intact to `legacy/manual-prototype/`, with `legacy/README.md` and
`docs/README.md` recording the explicit exception. No `tbd/` content remains.

## H-008 — Decide custody of root `PDS.md`

**Decision needed:** Choose whether the complete draft standard is:

- intentionally vendored and tracked at repository root;
- retained as temporary/untracked migration input;
- moved to a noncurrent reference location; or
- removed only after another authoritative copy is verified.

**Why human review is required:** PDS itself recommends separate maintenance,
and the current untracked copy has no declared project role.

**Effect:** Unblocks the final target tree and link policy.

**Resolution:** Keep `PDS.md` at the repository root as the tracked authoritative
copy of the adopted standard.

## H-009 — Decide whether version `0.1.0` is a release

**Decision needed:** Confirm whether `pyproject.toml` version `0.1.0` represents
an actual released version requiring `CHANGELOG.md`.

**Evidence:** no Git tags exist and the repository log contains only the initial
baseline commit.

**Why human review is required:** Release history cannot be inferred from a
package version alone.

**Effect:** Determines whether the changelog trigger applies.

**Resolution:** Version `0.1.0` is package metadata, not a proven release. Do not
create a changelog until an actual release establishes the trigger.

## Readiness decision

All nine decisions are resolved. The repository is **ready to begin migration**
through `07-migration-manifest.md` and `08-validation-plan.md`. Readiness does not
authorize source archival or deletion; those actions remain gated on validated
target parity and explicit Owner acceptance.
