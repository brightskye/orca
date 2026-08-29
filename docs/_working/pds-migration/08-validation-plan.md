---
id: WORK-2026-08-29-PDS-VALIDATION
title: PDS Migration Validation Plan
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Migration validation plan

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

## Validation gates

The later migration should pass these gates in order. A structural validator is
evidence, not proof that semantic content is correct.

### Gate 1 — Scope and change isolation

- Capture `git status --short` immediately before migration.
- Compare against the pre-existing state in this audit.
- Confirm that migration commits contain only documentation and explicitly
  authorized documentation-validation assets.
- Confirm no source, tests, runtime configuration, dependency files, local
  ignored records, evidence hashes, or legacy executable assets changed.
- Confirm no original mixed document was deleted before all later gates passed.

**Pass evidence:** path-level diff manifest and explicit statement that source
code changes are absent.

### Gate 2 — Unique-information preservation

For every source section in `02-document-inventory.md` and every M-ID in the
migration manifest:

1. identify its target paragraph/section or its frozen archive location;
2. compare meanings, controlled values, numeric limits, identifiers, statuses,
   exclusions, examples, and rationale;
3. record `preserved`, `intentionally summarized with canonical link`,
   `historical only`, or `blocked`;
4. reject migration if any unique statement has no destination or explicit
   historical-retention record.

High-risk exact-content checks:

- interaction template strings and policy versions;
- memory schemas, status values, state tables and examples;
- conflict-variant and overflow behavior;
- run-manifest/checkpoint fields and ordering;
- token/result budgets and their exception;
- privacy exclusions and secret-containment wording;
- ADR numbers and supersession links.

**Pass evidence:** completed source-section-to-target matrix with zero
unclassified rows.

### Gate 3 — Canonical ownership

- `docs/README.md` lists exactly one owner for every subject in
  `03-canonical-ownership-map.md`.
- Search current docs for duplicated normative field lists, state machines,
  budget tables, phase tables, and component responsibility lists.
- Ensure non-owning documents contain only the minimum explanatory summary plus
  a semantic link.
- Confirm no ADR, plan, proposal, research note, working note, archive, or
  `tbd/` file is the only source of current behavior.

**Pass evidence:** ownership table review and duplicate-definition report with
all intentional summaries justified.

### Gate 4 — Status, authority, and implementation truth

- Parse frontmatter for every substantial current document.
- Validate PDS lifecycle, authority, and implementation-status values.
- Confirm every designed-but-unimplemented capability is `planned` or `partial`,
  never implicitly `verified`.
- Recheck code/tests for claims in `STATUS.md`; use direct behavioral tests where
  the migration claims verified behavior.
- Confirm C-001, C-002, C-003/C-004, C-006, C-008, and D-001–D-010 are either
  resolved by explicit decision or still visible.

**Pass evidence:** metadata report and signed-off divergence table.

### Gate 5 — Link integrity and navigation

- Check every repository-relative Markdown link.
- Reject absolute personal filesystem links from current/public docs.
- Ensure root README, AGENTS, docs index, STATUS, ROADMAP, charter, and overview
  link according to PDS routes.
- Ensure every substantial current document links back to the docs index.
- Ensure current documents do not require `_archive/`, `_working/`, `tbd/`,
  `.agent-notes/`, `evidence/`, or `index.md` for normal understanding.
- Ensure archived files link to replacements and carry historical warnings.

**Pass evidence:** automated link report plus manual task-route walkthrough.

### Gate 6 — System-design navigation and completeness

Starting only at `docs/02-architecture/overview.md`, verify a reviewer can locate:

- purpose/scope/non-goals;
- requirements;
- components/responsibilities/dependencies;
- current deployment and runtime flow;
- data owners/lifecycle/provenance/recovery;
- security/trust boundaries;
- exact formats/workflows/errors/idempotency;
- decisions/rationale;
- acceptance/test strategy;
- operation/recovery;
- future phases.

No route may require reading one giant legacy source.

**Pass evidence:** completed PDS system-design checklist and two reader
walkthroughs: “implement capture” and “investigate replay failure.”

### Gate 7 — Roadmap separation

- Verify `ROADMAP.md` alone owns phase names, commitment status, broad outcomes,
  dependencies, deferred capabilities, and exit criteria.
- Verify active plan owns tasks/progress and `STATUS.md` owns present state.
- Verify later exact designs live in proposals and are visibly unaccepted.
- Verify future-state architecture is clearly labelled and cannot be mistaken
  for current deployment.
- Verify release history is absent unless the changelog trigger is confirmed.

**Pass evidence:** roadmap/plan/status/proposal responsibility review with no
duplicate phase tables.

### Gate 8 — Data and security coverage

Data architecture review must identify for each data class:

- authority and owner;
- canonical/derived/operational classification;
- representation/store;
- lifecycle and provenance;
- retention/deletion;
- rebuildability and recovery;
- synchronization status;
- security classification.

Security review must identify:

- protected assets and sensitive data;
- Owner, agent, connector, runtime, provider, retrieval, and future-host trust
  boundaries;
- authentication/authorization applicability;
- secret handling and private-session behavior;
- untrusted semantic input/output controls;
- tool/public-interface controls;
- logging/audit, backup, retention, incident handling, and residual risk;
- linked security tests or explicit test gaps.

**Pass evidence:** completed PDS data/security checklists; no triggered section
left blank or replaced by a generic statement.

### Gate 9 — Legacy and local record preservation

- Verify every pre-existing deleted tracked documentation/schema path is either
  restored, committed as an intentional relocation, or explicitly excluded from
  the migration commit pending a separate decision.
- Compare content hashes for byte-preserved legacy files.
- Preserve ADR numbering and supersession.
- Confirm `tbd/` exception is declared if retained.
- Confirm `.agent-notes/`, `evidence/`, `index.md`, and `config/host.yaml` remain
  Git-ignored and unchanged.
- Confirm historical evidence labels such as `PASS — SMALL SAMPLE` remain exact
  and are not upgraded to general verification.

**Pass evidence:** legacy hash/relocation manifest and `git check-ignore` output.

### Gate 10 — Source-code absence and final review

- Run a final path-filtered diff check for `src/`, `tests/`, `pyproject.toml`,
  `uv.lock`, `.github/workflows/`, configuration, and runtime paths.
- Run documentation validator and relevant existing tests only if a documentation
  claim depends on their current pass status.
- Review the final `git status --short` against the captured baseline.
- Do not archive/delete source documents until the Owner accepts the migrated
  canonical package and all gates pass.

**Pass evidence:** final status, validator output, any test output, and human
approval record.

## Minimum automated checks

A later documentation validator should check:

- required Core entry points and triggered architecture files;
- PDS version/profile declaration;
- YAML frontmatter parsing and allowed metadata values;
- unique document and requirement/ADR/test identifiers;
- relative links and orphaned current documents;
- ADR numbering/supersession;
- current document registration;
- warning blocks in `_working/` and `_archive/`;
- forbidden normative dependency on working/archive/`tbd` material;
- duplicate canonical owners;
- roadmap phase status/outcome/exit criteria;
- active plan links and specification/acceptance links;
- absence of absolute personal paths in public current documentation.

## Manual semantic checks

Automation cannot decide whether:

- C-001 was resolved correctly;
- Phase 2/3 commitment labels match Owner intent;
- extracted requirements preserve the intended obligation;
- an ADR's rationale is complete;
- security mitigations are sufficient;
- an implementation-status claim is honest;
- a summary subtly redefines its canonical source.

Those checks require explicit human review of the relevant source and target.

## Archive/delete conditions

A source document may be archived only after Gates 1–9 pass for all of its
sections. It may be deleted only after:

- its archive value is explicitly reviewed;
- all unique information and rationale have validated destinations;
- no current or external link depends on it;
- its replacement is accepted;
- the migration manifest records the deletion authorization.

This audit recommends no deletions.
