---
id: WORK-2026-08-29-PDS-MIGRATION-LOG
title: PDS Migration Log
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# PDS migration log

> [!WARNING]
> This is non-authoritative execution evidence. Current project truth is
> registered in [`docs/README.md`](../../README.md).

## Milestone 1 — Control plane and foundation

**State:** accepted

**Scope:** M-001 through M-006, plus non-authority boundary indexes.

**Created:**

- `docs/README.md`
- `docs/STATUS.md`
- `docs/ROADMAP.md`
- `docs/01-foundation/project-charter.md`
- `docs/01-foundation/requirements.md`
- `docs/01-foundation/glossary.md`
- `docs/_working/README.md`
- `docs/_archive/README.md`

**Preservation boundary:** No source document is moved, archived, or deleted in
this milestone. Transitional duplicates remain until target parity and Owner
acceptance are complete.

**Validation evidence (2026-08-29):**

- Required milestone files: pass.
- PDS frontmatter fields, controlled lifecycle/authority/implementation values,
  and unique IDs across the milestone: pass.
- Relative links in the new control and foundation documents: pass.
- Glossary term-name parity with `CONTEXT.md`: pass.
- Trailing-whitespace scan: pass.
- Active focused suites: 12 tests passed across conversation capture,
  AgentCairn adapter, and Step 3 pipeline tests.
- Source preservation: no source document was moved, archived, or deleted.

**Acceptance gate (satisfied):** The proposed charter, requirements, and glossary
did not become canonical owners until the Owner accepted this milestone.

**Accepted:** The Owner approved Milestone 1 on 2026-08-29. Canonical ownership
of project scope, requirements, and terminology transferred to the three
foundation documents. `CONTEXT.md` remains a labelled compatibility mirror until
later source cleanup is authorized.

## Milestone 2 — Architecture package

**State:** accepted

**Scope:** M-007 through M-013.

**Created:**

- `docs/02-architecture/overview.md`
- `docs/02-architecture/runtime.md`
- `docs/02-architecture/deployment.md`
- `docs/02-architecture/data-architecture.md`
- `docs/02-architecture/security-and-trust.md`
- `docs/02-architecture/integration-architecture.md`
- `docs/02-architecture/diagrams/system-context.mmd`
- `docs/02-architecture/diagrams/processing-flow.mmd`

**Authority boundary:** Every architecture target remains `status: proposed`
and `authority: working`. The flat `docs/system-design.md`,
`docs/architecture.md`, `docs/operations.md`, root `SECURITY.md`, and active
contracts retain their current ownership until parity validation and Owner
acceptance.

**Validation evidence (2026-08-29):**

- Relative links across the architecture package and its registry routes: pass.
- Required PDS frontmatter, unique architecture IDs, proposed/working authority
  boundary, and ownership statements: pass.
- PDS architecture-section checklist for overview, runtime, deployment, data,
  security, and integration views: pass.
- Diagram title, scope, flowchart declaration, and basic delimiter structure:
  pass.
- Trailing-whitespace scan: pass.
- M-007 through M-013 coverage: present. Exact schemas, budgets, and lifecycle
  rules remain linked to their current owning contracts rather than duplicated.
- Source preservation: no flat architecture, operations, security, or contract
  source was moved, archived, or deleted.
- Implementation tests were not rerun because this milestone changed
  documentation only; Milestone 1's 12-test result remains the latest code/test
  evidence.

**Acceptance gate (satisfied):** Semantic parity and Owner acceptance were
required before the architecture package became canonical.

**Accepted:** The Owner approved Milestone 2 on 2026-08-29. Canonical ownership
of system, runtime, deployment, data, security, and integration architecture
transferred to `docs/02-architecture/`. Flat sources remain labelled and
preserved for exact specification, operations, decision, and archive work.

## Milestone 3A — Direct specification migrations

**State:** accepted

**Scope:** M-014 plus direct-copy portions of M-017, M-019, M-021, and M-022.

**Created:**

- `docs/03-specifications/README.md`
- `docs/03-specifications/memory-model.md`
- `docs/03-specifications/provenance-ledger.md`
- `docs/03-specifications/interaction-preferences.md`
- `docs/03-specifications/interaction-guidance.md`

**Specification seam:** The registry assigns exact behavior to one deep module
interface per subject and prohibits copying schemas or lifecycle rules across
capture, processing, memory, candidate, provenance, retrieval, interaction, and
configuration owners.

**Authority boundary:** The four migrated specifications were proposed working
documents during parity review. Their root-level source contracts remained
normative until acceptance.

**Validation evidence (2026-08-29):**

- Direct contract-body parity after removing only source/target frontmatter,
  titles, the PDS ownership wrapper, and one intentional internal link rewrite:
  pass for all four specifications.
- Relative links: pass.
- Required metadata, unique IDs, and proposed/working authority boundary: pass.
- Trailing-whitespace and tracked-diff checks: pass.
- Source preservation: all four root-level contracts remain present and
  normative.
- Implementation tests were not rerun because this slice changed documentation
  only; Milestone 1's 12-test result remains the latest code/test evidence.

**Acceptance gate:** Owner acceptance is required before these four targets
become normative and their root-level source contracts become compatibility
sources. Capture, processing, candidate, retrieval, and configuration
specifications remain separate unfinished work.

**Accepted:** The Owner approved Milestone 3A on 2026-08-29. Memory Model,
Provenance Ledger, Interaction Preferences, and Interaction Guidance are now
the normative owners. Their root-level source contracts remain present as
labelled compatibility mirrors.

## Milestone 3B — Extracted and new specifications

**State:** accepted

**Scope:** M-015, M-016, M-018, M-020, and M-023.

**Created:**

- `docs/03-specifications/capture-pipeline.md`
- `docs/03-specifications/processing-pipeline.md`
- `docs/03-specifications/knowledge-candidates.md`
- `docs/03-specifications/retrieval-contract.md`
- `docs/03-specifications/configuration.md`

**Module interfaces:** Capture owns supported-event normalization and privacy
handoff; Processing owns bounded semantic work and deterministic proposal
validation; Retrieval owns filtered projections and bounded Recall Results;
Configuration owns validated local and vault settings. Each links to the
artifact-owning specification rather than copying its schema.

**New design boundary:** The Knowledge Candidate schema, `knowledge/` placement,
and `pending -> accepted|rejected` lifecycle are explicitly proposed. They are
not inferred from legacy Curator or AgentCairn behavior. Accepted candidate
status would remain noncanonical and would not expose automatic canonical apply.

**Known configuration gaps:** Current accepted sources do not define exact keys
for the Codex rollout store or Project Root Mappings, the complete
`orca-memory.yaml` schema, or dual vault-path precedence. The proposed
Configuration specification fails closed and records those questions rather
than inventing accepted behavior.

**Authority boundary before review:** All five specifications began as
`status: proposed` and `authority: working`. Existing governance and labelled
operational sources remained the exact owners until semantic review and Owner
acceptance.

**Validation evidence (2026-08-29):**

- Specification inventory, required frontmatter, unique IDs, required behavior
  coverage, and the pre-review four-accepted/five-proposed authority split:
  pass.
- Relative links across 37 current project Markdown files: pass. PDS template
  example links were excluded because they are examples in the root standard,
  not project navigation.
- Migration and navigation link fragments: pass.
- Processor, recall, interaction, retry, and retention limits are present in
  their owning specifications; Configuration links to those owners rather than
  creating a second normative default table.
- `config/host.example.yaml` fields match the proposed host interface: pass.
- Compatibility-source presence and labels: pass for all four accepted direct
  migrations.
- Trailing-whitespace and tracked-diff checks: pass.
- Ignore checks: `config/host.yaml`, `.runtime/`, `.agent-notes/`, `evidence/`,
  and `index.md` remain ignored.
- Implementation tests were not rerun because Milestone 3B changes
  documentation and agent routing only. Milestone 1's 12-test result remains the
  latest code/test evidence.

**Acceptance gate:** Owner semantic review is required before these five targets
become normative or any source is archived. Candidate and configuration open
questions require explicit resolution.

**Partial acceptance:** The Owner approved the recommended split on 2026-08-29.
Capture Pipeline, Processing Pipeline, and Retrieval Contract are now normative
owners. Their corresponding governance sections remain labelled compatibility
sources. Knowledge Candidates and Configuration remain proposed working
specifications; their open schema decisions are not accepted implicitly. No
source was archived or deleted.

**Post-acceptance validation:** The seven normative/two working behavioral
specification split, current-document links, governance routes, stale ownership
labels, whitespace, and tracked diffs all pass.

**Completed:** The two remaining working specifications were finalized and
accepted through Milestone 3C on 2026-08-30. Milestone 3B now has no unfinished
specification owner.

## Milestone 3C — Close proposed Candidate and Configuration interfaces

**State:** accepted

**Scope:** Complete the remaining design choices in M-018 and M-023 without
silently accepting them.

**Knowledge Candidate choices:**

- Use `pending`, `approved-for-manual-apply`, and `rejected` so disposition
  cannot be mistaken for authority.
- Keep ordinary candidates under a distinct `candidates/knowledge/` subtree.
- Make reviewed states terminal; corrected meaning creates a new candidate.
- Apply no age-based retention and expose no cleanup interface in Phase 1.
- Record no canonical target and expose no canonical-apply operation.

**Configuration choices:**

- Add exact `connectors.codex.rollout_store` and `project_root_mappings` host
  keys to `config/host.example.yaml`.
- Define the complete proposed `orca-memory-config/0.1` key shape in
  `config/orca-memory.example.yaml`.
- Default catch-up and index reconciliation to 15 minutes, retry to three
  attempts and 72 hours, and retain the accepted behavior-owner budgets.
- Treat differing `config/host.yaml` and `ORCA_VAULT_PATH` values as a
  validation error rather than silently choosing one.

**Authority boundary:** Both specifications remain `status: proposed` and
`authority: working`. The safe examples are structural fixtures, not separate
normative owners. No runtime loader or deployment is claimed.

**Validation evidence (2026-08-29):**

- Host and vault safe examples match their complete proposed key sets and
  defaults: pass.
- Processor and recall budget arithmetic and referenced accepted policy
  identifiers: pass.
- Candidate states, terminal transitions, indefinite retention, ordinary Recall
  exclusion, and no-canonical-apply rule: pass.
- Candidate and Configuration lifecycle metadata remains
  `proposed`/`working`/`planned`: pass.
- Relative links across 37 current project Markdown files: pass.
- Stale schema-gap and ambiguous `accepted` candidate-status language: absent.
- Trailing whitespace and tracked diff checks: pass.
- `config/orca-memory.example.yaml` is available to track; private
  `config/host.yaml` remains ignored.
- Implementation tests were not rerun because this milestone changes
  documentation and safe configuration examples only.

**Acceptance gate:** Owner semantic review is required before either
specification becomes normative and before Data Architecture or operational
ownership transfers.

**Accepted:** The Owner approved Milestone 3C on 2026-08-30. Knowledge
Candidates and Configuration are now normative. Data Architecture records the
accepted candidate lifecycle and configuration data classes; Phase 1 Operations
retains a labelled configuration compatibility section. No runtime
implementation, deployment, canonical-apply path, archive action, staging, or
commit was implied by this acceptance.

**Post-acceptance validation:** All nine behavioral specifications are accepted
and normative; final schema/policy identifiers, safe-example key sets, budget
arithmetic, Data Architecture, Operations compatibility routing, 37 current
project links, stale-label absence, whitespace, diffs, and ignore boundaries
pass. Implementation tests were not rerun because acceptance changed
documentation and safe examples only; code verification remains dated
2026-08-29.

## Milestone 4A — Decision registry and ADR migration

**State:** accepted

**Scope:** M-024, M-025, and M-026.

**Created:**

- `docs/04-decisions/README.md`
- `docs/04-decisions/template.md`
- accepted `ADR-0004`
- proposed `ADR-0005` through `ADR-0012`

**Historical classification:** ADR-0001 remains superseded by ADR-0004.
ADR-0002 and ADR-0003 remain future-only proposal evidence under `tbd/` despite
their retained internal `status: accepted` metadata. ADR-0004 is the active
accepted rationale for checkout/vault separation. Numbers 0001–0004 are never
reused.

**Proposed rationale drafts:** Direct source capture without a raw archive,
separate authority classes, Conversation/Processor/Storage Interfaces,
replaceable retrieval, complete Phase 1 behavior before topology expansion,
inspectable noncanonical interaction preferences, disabled automatic canonical
apply, and AgentCairn behind the Retrieval Interface.

**Authority boundary:** ADR-0005 through ADR-0012 remain `status: proposed` and
`authority: working`. They summarize rationale already reflected in accepted
architecture or specifications but do not become accepted historical rationale
without Owner review. ADRs do not own exact behavior.

**Validation evidence (2026-08-30):**

- Active numbering is contiguous from reserved ADR-0004 through ADR-0012; no
  number 0001–0004 was reused.
- ADR-0004 body parity with its retained source: exact pass.
- Original ADR-0001 through ADR-0004 status values remain present with explicit
  migration classifications: pass.
- ADR-0005 through ADR-0012 lifecycle is uniformly `proposed`/`working`: pass.
- Relative links across 49 current and explicitly routed Markdown files: pass.
- Proposed ADRs contain no accepted label: pass.
- Trailing whitespace and tracked diff checks: pass.
- Implementation tests were not rerun because this milestone changes decision
  documentation and noncurrent-source metadata only.

**Acceptance gate:** Owner review is required before proposed ADRs become
accepted. Source ADRs remain present; no archival or deletion is authorized.

**Accepted:** The Owner approved ADR-0005 through ADR-0012 on 2026-08-30.
Their lifecycle is now uniformly `accepted`/`historical`; they record rationale
for already accepted architecture, specifications, governance, roadmap, and
integration boundaries without becoming the sole owner of exact behavior.
ADR-0001 remains superseded history, and ADR-0002 and ADR-0003 remain
future-only proposal evidence with no current authority. No source was archived
or deleted.

**Post-acceptance validation:** ADR-0004 through ADR-0012 are uniformly
`accepted`/`historical`; active numbering, ADR-0004 retained-source body parity,
ADR-0001 through ADR-0003 migration classifications, current status wording,
and stale pending-review checks pass.

## Milestone 4B — Proposal registry and template

**State:** established

**Scope:** M-027.

**Created:**

- `docs/05-proposals/README.md`
- `docs/05-proposals/template.md`

**Candidate inputs:** Phase 2 local multi-agent operation, Phase 3 synchronized
multi-host operation, automatic canonical apply, and automated retention are
registered as undrafted topics only. No RFC number was allocated.

**Authority boundary:** The registry is accepted informative navigation. The
template defaults proposals to `draft`/`informative`; proposals do not change
current design or authorize implementation. Exact all-phase material and its
internal `accepted-baseline` labels remain noncurrent under `tbd/future/`.

**Promotion gate:** Creating any concrete RFC from deferred material requires
separate Owner approval and reconciliation with current accepted Phase 1
documents. No retained source was archived, deleted, or promoted.

**Validation evidence (2026-08-30):**

- The only `document_type: proposal` file is the template, and it is visibly
  `draft`/`informative`; no numbered RFC exists.
- The registry identifies four undrafted inputs without allocating IDs or
  copying exact future design: pass.
- Current architecture contains no link to the proposal package or
  `tbd/future/`: pass.
- Relative targets across 55 current and explicitly routed Markdown files (383
  links): pass.
- Stale current-milestone wording, trailing whitespace, and tracked diff
  whitespace checks: pass.
- Implementation tests were not rerun because this milestone changes
  navigation, lifecycle documentation, and a template only.

## Milestone 5A — Phase 1 implementation plan

**State:** accepted

**Scope:** M-028.

**Created:**

- `docs/06-plans/README.md`
- `docs/06-plans/active/phase-1-implementation.md`

**Sequence:** Complete assistant-context capture and partial-tail handling;
implement Typed Memory Record add/support/update and Project Summary refresh;
complete processing/provenance/candidates; implement interaction behavior;
implement explicit recall and replaceable retrieval; wire configuration and the
private local runtime; then verify Phase 1 readiness.

**Authority boundary before acceptance:** The plan was `proposed`/`working` and
did not become execution authority until Owner acceptance. It links accepted
owners instead of redefining exact behavior. `STATUS.md` remains the
current-state owner.

**Preserved scope:** The plan covers D-001 through D-010 and C-009 without
importing obsolete future tasks. Phase 2, Phase 3, canonical apply, general
ingestion, public services, general graph behavior, and deferred retention stay
out of scope.

**Acceptance gate:** Satisfied by Owner review on 2026-08-30 for the milestone
order, dependency boundaries, and exit criteria.

**Accepted:** The Owner approved the seven-milestone Phase 1 sequence and exit
criteria on 2026-08-30. The plan is now `accepted`/`informative` execution
authority; requirements, architecture, specifications, governance, and ADRs
remain the exact behavior owners. Acceptance does not claim that any unfinished
milestone is implemented or verified.

**Validation evidence (2026-08-30):**

- Required plan metadata and PDS plan sections were present; initial lifecycle
  was `proposed`/`working`/`partial`: pass.
- Every accepted Phase 1 requirement ID appears in the traceability table, with
  no unknown requirement ID: pass.
- Milestone work and exit criteria cover D-001 through D-010 and the C-009 test
  route gap without linking working notes as authority: pass.
- The plan links the Roadmap, requirements, architecture, specifications,
  governance, and decision owners and contains no link to `tbd/`: pass.
- Relative targets and fragments across 57 current and explicitly routed
  Markdown files (432 links, 20 fragments): pass.
- Current-document IDs remain unique; stale wording, trailing whitespace, and
  tracked diff whitespace checks pass.
- The current seven-source-file/three-test-module implementation inventory and
  12 focused test cases were reviewed for plan baseline parity.
- Implementation tests were not rerun because this milestone changes
  documentation and execution planning only; behavioral verification remains
  dated 2026-08-29.

**Post-acceptance validation:** The active plan and registry now agree on
`accepted`/`informative`/`partial`; Roadmap, Status, and Documentation Index
routes no longer describe the plan as proposed. No implementation or evidence
status was upgraded.

## Milestone 5B — Acceptance and test strategy

**State:** ready for Owner review

**Scope:** M-029 and M-030.

**Created:**

- `docs/07-quality/acceptance.md`
- `docs/07-quality/test-strategy.md`

**Acceptance design:** Fifteen stable scenario IDs cover Codex classification,
privacy/incomplete source, bounded processing, provenance/recovery, memory,
conflicts/candidates, summaries, interaction lifecycle/guidance, recall,
retrieval rebuild, configuration, runtime, end-to-end behavior, and the
zero-canonical/public-surface boundary. Roadmap exit criteria map to scenarios.

**Evidence boundary:** Deterministic tests, retrieval evaluation, semantic
evaluation, operational canaries, and human review remain separate. The current
12 focused tests are regression evidence only. Historical labels such as
`PASS — SMALL SAMPLE` remain limited and are not upgraded to Phase 1 proof.

**Test-route truth:** AGENTS runs capture only; CI runs capture plus AgentCairn;
the Step 3 pipeline suite is omitted from both. The proposed strategy identifies
the complete current three-module command but does not claim that AGENTS or CI
already uses it.

**Authority boundary:** Both quality documents remain
`proposed`/`working`/`partial`. Their IDs, gates, and canonical command require
Owner review before they become quality authority.

**Validation evidence (2026-08-30):**

- Fifteen unique acceptance scenario IDs each contain Given/When/Then and a
  required evidence class: pass.
- Every accepted Phase 1 requirement ID appears in at least one scenario, with
  no unknown requirement ID: pass.
- All five Roadmap Phase 1 exit criteria map to scenarios; Test Strategy
  references all scenarios and no nonexistent scenario: pass.
- Required quality sections, proposed lifecycle metadata, unique current
  document IDs, and absence of quality-document links to working/deferred
  authority: pass.
- The proposed canonical command ran all three current modules on 2026-08-30:
  12 tests passed in 0.077 seconds. This is regression-command evidence only.
- Relative targets and fragments across 59 current and explicitly routed
  Markdown files (484 links, 22 fragments): pass.
- Trailing whitespace and tracked diff whitespace checks: pass.
- No source, test, CI, AGENTS, private configuration, evidence, or legacy file
  was changed by this quality milestone.

## Milestone 6A — Limited Phase 1 runbook

**State:** ready for Owner review

**Scope:** M-031 under the Owner's migration-only boundary.

**Created:**

- `docs/08-operations/runbook.md`

**Procedure classification:** The repository regression command is the only
current executable procedure and was already verified on 2026-08-30. Initial
Manifest/checkpoint replay behavior is labelled tested library behavior, not an
operator interface. Installation, configuration loading, start, stop, health,
routine operation, diagnostics, backup, restore, operator recovery, and derived-
data rebuild are explicitly unavailable.

**Preserved behavior:** Configuration, runtime, deployment, data, security,
provenance, failure, and readiness details remain owned by their accepted
documents. The runbook links those owners and does not convert design flows into
commands.

**Migration-only boundary:** No runtime, configuration, source, test, CI,
deployment, private data, or product design was changed. No destructive command
or inferred legacy procedure was added.

**Acceptance gate:** Owner review is required before the runbook becomes
normative operational authority. Until then, `docs/operations.md` remains the
transitional source for unmigrated runbook behavior.

**Validation evidence (2026-08-30):**

- PDS runbook metadata and every required procedure section are present;
  lifecycle remains `proposed`/`working`/`partial`: pass.
- Exactly one shell-command block exists. It matches the current three-module
  regression command already verified at 12/12 passing tests: pass.
- Ten runtime-facing sections or procedures are explicitly labelled
  unavailable rather than represented as executable: pass.
- Destructive-command, personal-path, deferred-link, and trailing-whitespace
  scans: pass.
- Relative targets and fragments across 60 current and explicitly routed
  Markdown files (516 links, 22 fragments): pass.
- Acceptance Plan and Test Strategy remain proposed; no quality, runtime,
  implementation, deployment, or Phase 1 completion status was upgraded.
- The regression suite was not rerun for M-031 because the runbook copies the
  exact command verified during M-030 and makes no newer behavioral claim.

## Milestone 6B — Repository entry-point routing

**State:** complete

**Scope:** M-032 and M-033.

**Changed:**

- Narrowed `SECURITY.md` to supported-state and vulnerability-reporting
  guidance, with architecture, governance, and status details routed to their
  current owners.
- Reduced the root `README.md` to repository orientation, current status,
  documentation routes, high-level design context, and repository locations.
- Kept the absence of a supported runtime quick start explicit and routed
  operational status to the proposed runbook.

**Boundary:** No roadmap detail, specification text, executable runtime
procedure, implementation behavior, or private path was introduced at either
entry point.

## Milestone 6C — Retained-material and custody validation

**State:** complete

**Scope:** M-037 through M-041.

**Validated:**

- Current-document links into `tbd/` are limited to the Documentation Index,
  Decision Registry, and Proposal Registry, and each route identifies the
  target as noncurrent evidence or future input.
- `.gitignore` continues to exclude `config/host.yaml`, `.runtime/`,
  `.agent-notes/`, `evidence/`, and root `index.md`; none is tracked.
- Root `PDS.md` remains the exact migration source with SHA-256
  `84d883bc3e885ba142cf4a8a430dcf5daebcf5fbdd622824fc1a25a9fc1fd8c0`.
- No Git tags or changelog establish a release to migrate, so M-040 remains an
  intentional no-op.
- M-041 is an implementation/CI validator task and remains outside this
  migration-only task.

**Custody boundary:** These checks did not stage, commit, release, move, or
delete any retained material.

**Validation evidence (2026-08-30):**

- Relative targets and fragments across 60 current and explicitly routed
  Markdown files (518 links, 22 fragments): pass.
- README/security duplication and personal-path scans: pass.
- PDS hash, zero-tag release check, local-ignore coverage, untracked-private-
  path check, trailing whitespace, and tracked diff whitespace: pass.

## Milestone 6D — Owner acceptance, agent routing, and archival completion

**State:** complete

**Scope:** M-029 through M-036 after Owner approval on 2026-08-30.

**Accepted authority:**

- `docs/07-quality/acceptance.md` is `accepted`/`normative`.
- `docs/07-quality/test-strategy.md` is `accepted`/`normative`.
- `docs/08-operations/runbook.md` is `accepted`/`normative` while retaining all
  unavailable-runtime labels and partial implementation status.

**Agent routing:** `AGENTS.md` now points conditionally to the current
documentation map, status, roadmap, architecture, specifications, quality
documents, and runbook. Its verification command matches the accepted
three-module active-suite command. CI remains unchanged and still omits Step 3;
that implementation-route divergence remains visible as C-009.

**Archived with Owner approval:**

- Seven superseded design, architecture, operations, and compatibility-source
  documents moved to `docs/_archive/legacy-docs/`.
- Three completed research reports moved to `docs/_archive/research/`.
- Every archived file retains its original content and metadata, adds an
  archival warning/current-owner route, and has valid relative links.
- Current documents no longer depend on superseded legacy-document paths. The
  Retrieval Contract retains one explicit historical research-evidence link.

**Migration-only boundary:** No implementation, test, CI, runtime,
configuration, deployment, or product-design behavior changed in this
milestone.

**Final validation evidence (2026-08-30):**

- Accepted three-module regression command: 12 tests passed in 0.153 seconds;
  regression evidence only.
- Relative targets and fragments across 61 current, archived, and explicitly
  routed Markdown files (532 links, 22 fragments): pass.
- Accepted quality/runbook lifecycle scan, current legacy-path independence,
  archive ownership map, archival warnings, and archive link scan: pass.
- PDS SHA-256 remains
  `84d883bc3e885ba142cf4a8a430dcf5daebcf5fbdd622824fc1a25a9fc1fd8c0`;
  zero Git tags still establish no changelog trigger.
- Local-ignore coverage, untracked-private-path check, trailing whitespace, and
  tracked diff whitespace: pass.

**Remaining repository action:** The complete migration working tree has not
been staged or committed. Root `PDS.md` becomes tracked when the Owner chooses
to commit the migration diff. M-041 remains separate implementation/CI work.

## Milestone 6E — PDS ADR custody correction

**State:** complete

**Owner direction:** Keep all ADR records in the PDS `docs/04-decisions/`
location rather than extending the `tbd/` exception to decision records.

**Changed:**

- ADR-0001 moved into the decision registry as superseded historical rationale
  with its ADR-0004 relationship intact.
- ADR-0002 and ADR-0003 moved into the decision registry as `proposed`/`working`
  future-only evidence. Their original `accepted` source labels remain recorded
  as `source_status` and do not grant current authority.
- ADR-0004 remains the single accepted registry record; its redundant `tbd/`
  compatibility copy was removed after preserving its exact rationale and
  migration classification.
- Decision and proposal routes now use `docs/04-decisions/`; `tbd/README.md`
  states that the exception does not own ADR records.

**Boundary:** Lifecycle and applicability did not change. ADR-0001 remains
superseded, ADR-0002/0003 remain unaccepted future-only evidence, and ADR-0004
remains accepted. No system design or implementation behavior changed.

**Validation evidence (2026-08-30):**

- ADR numbering is contiguous from 0001 through 0012 in
  `docs/04-decisions/`: pass.
- ADR-0001 through ADR-0004 rationale bodies match their original tracked
  `docs/adr/` bodies exactly: pass.
- ADR-0001/0002/0003/0004 lifecycle and authority are respectively
  `superseded`/`historical`, `proposed`/`working`, `proposed`/`working`, and
  `accepted`/`historical`: pass.
- No ADR file or current ADR link remains under `tbd/`: pass.
- Relative targets and fragments across 60 current, archived, and explicitly
  routed Markdown files (532 links, 22 fragments): pass.
- Trailing whitespace and tracked diff whitespace: pass.
- The regression suite was not rerun because this correction changes ADR
  custody and metadata only.

**Commit-order blocker:** A migration-only commit against current `HEAD` would
reference untracked Phase 1 source and test modules that are not present in
`HEAD`. Staging those modules would cross the Owner's migration-only boundary;
omitting them would make the documentation commit internally inconsistent.
Nothing was staged pending Owner direction on commit order.

## Milestone 6F — Safe `tbd/` document archival

**State:** complete

**Owner direction:** Move the standalone documents that can safely follow the
PDS archive layout while keeping the runnable legacy implementation package
intact.

**Archived:**

- Six all-phase vocabulary, overview, architecture, delivery, governance, and
  operations snapshots moved from `tbd/future/` to
  `docs/_archive/legacy-design/`.
- `prototype-migration-notes.md` moved from the legacy package to
  `docs/_archive/legacy-docs/`.
- Each file retains its content and metadata, adds a visible historical warning,
  and routes to the accepted current owner.

**Retained exception:** `tbd/reference/legacy/` still contains the historical
prototype code, tests, schemas, fixtures, README, and code-adjacent contracts.
Moving those documents separately would break the preserved package context;
they remain noncurrent implementation evidence rather than documentation-tree
authority.

**Routing:** The Proposal Registry now cites archived all-phase snapshots as
historical inputs. `tbd/README.md` describes only the remaining legacy-package
boundary. The legacy prototype README points to the archived overview.

**Validation evidence (2026-08-30):**

- Six legacy-design files and one migration note are present at their approved
  archive destinations with warnings and current-owner routes: pass.
- `tbd/future/` contains no remaining file: pass.
- Relative targets and fragments across 82 current, archived, and retained
  legacy Markdown files (563 links, 22 fragments): pass.
- Current-route stale-`tbd/future/`, trailing-whitespace, and tracked diff
  whitespace checks: pass.
- Tests were not rerun because this milestone only relocates historical
  documents and repairs navigation.

**Commit state:** Nothing is staged. The previously recorded implementation-
baseline commit-order blocker remains.

## Milestone 6G — Explicit legacy implementation boundary

**State:** complete

**Owner direction:** Use `docs/_archive/` for PDS historical documentation and
top-level `legacy/manual-prototype/` for the retained runnable source/test
package.

**Relocated intact:**

- Former `tbd/reference/legacy/prototype/` moved to
  `legacy/manual-prototype/prototype/`.
- Former `tbd/reference/legacy/tests/` moved to
  `legacy/manual-prototype/tests/`.
- The boundary README moved to `legacy/README.md` and now records the changed
  PDS rule, reason, substitute location, Owner, and removal-review trigger.

**Necessary path repairs:** The prototype README now points to the archived
all-phase overview from its new location. The semantic-provider rule retains
its runtime content and remains the adapter's default input; only its relative
governance-document path changed for the new package root.

**Current routing:** Root README, AGENTS, Documentation Index, architecture,
specifications, plan, quality strategy, and runbook now identify `legacy/` as
noncurrent implementation evidence. No current route names `tbd/`.

**Validation evidence (2026-08-30):**

- All 30 originally tracked prototype/test files exist under the new package;
  28 are byte-identical and the only changed files are the two documented
  relocation-dependent Markdown paths: pass.
- Legacy focused suite from `legacy/manual-prototype/`: 90 tests passed in
  2.859 seconds.
- Relative targets and fragments across 82 current, archived, and legacy
  Markdown files (564 links, 23 fragments): pass.
- No file remains under `tbd/`; generated bytecode under `legacy/` remains
  ignored and outside the migration diff.
- Current stale-path, trailing-whitespace, and tracked diff whitespace checks:
  pass.

**Commit state:** Nothing is staged. The implementation-baseline commit-order
blocker remains unchanged.

## Milestone 6H — Migration commit preparation

**State:** complete

The active Phase 1 baseline was committed separately as `4cfef24` before the
migration, resolving the commit-order blocker without combining implementation
and documentation scope.

**Prepared migration scope:** PDS documentation, current documentation,
historical documentation, safe configuration examples, repository navigation,
and the intact legacy-package relocation. No active source, active test, build,
lock, or CI file is included.

**Final preparation checks:**

- All 12 active Phase 1 regression tests passed on the prerequisite baseline.
- The 90-test focused legacy suite and the 564-link/23-fragment migration check
  remain the latest direct validation; subsequent changes only removed three
  extra end-of-file blank lines.
- The staged migration passes the path-scope check and whitespace validation
  except for trailing spaces preserved byte-for-byte in the Owner-supplied
  `PDS.md`.
- `PDS.md` still matches SHA-256
  `84d883bc3e885ba142cf4a8a430dcf5daebcf5fbdd622824fc1a25a9fc1fd8c0`.

**Commit boundary:** Create one migration commit after `4cfef24`; do not push as
part of this milestone.
