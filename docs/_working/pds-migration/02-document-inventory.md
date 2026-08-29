---
id: WORK-2026-08-29-PDS-INVENTORY
title: PDS Audit Document Inventory
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Document inventory

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

## Method and legend

This inventory covers every current project Markdown file, documentation-like
YAML/TOML file, JSON schema, and documentation fixture in the working tree.
Material mixed documents are classified by section. Source and tests are
recorded as implementation evidence in the final tables rather than treated as
documentation. Git-ignored local records are listed separately because project
instructions keep them outside public Git.

Each row records:

- **Class**: proposed PDS document type / lifecycle / authority /
  implementation status.
- **Evidence, overlap, conflict**: why the classification applies and where the
  subject repeats or disagrees. `C-*` identifiers refer to
  [`04-conflicts-and-divergence.md`](04-conflicts-and-divergence.md).
- **Preserve**: unique information that must survive migration.
- **Owner / target / links / action**: proposed canonical owner and target path,
  required cross-links, and migration action.

`unknown` is deliberate where current repository authority does not establish a
safe answer.

## Root and control material

| Current path / section | Apparent purpose and subjects | Class | Evidence, overlap, conflict | Preserve | Owner / target / links / action |
|---|---|---|---|---|---|
| `README.md` / Goal | Human orientation plus project purpose and authority boundary | project-charter summary / accepted / informative / not-applicable | Overlaps `system-design.md#Purpose`; no explicit authority metadata | Local-first governed-memory description | Charter owns purpose; root README summarizes and links / `docs/01-foundation/project-charter.md` / link docs index, status, roadmap, architecture / **decompose, update** |
| `README.md` / Delivery phases | Phase roadmap, phase scope rule, canonical-apply exclusion | roadmap / accepted-looking / informative / not-applicable | Overlaps system design and deferred delivery plan; Phase 2/3 commitment unknown (`C-006`) | Three-phase topology axis and core-capability rule | Roadmap / `docs/ROADMAP.md` / link plans and proposals / **move to roadmap; human decision required** |
| `README.md` / Architecture, Phase 1 scope | Architecture summary and requirements/capabilities | architecture + requirements / accepted-looking / normative-looking / partial | Repeats all active design files; code implements only a subset (`D-001`–`D-008`) | Concise end-to-end summary and no-canonical-apply boundary | Architecture overview and requirements / `docs/02-architecture/overview.md`, `docs/01-foundation/requirements.md` / link specs / **decompose** |
| `README.md` / Why AgentCairn is used | Integration choice and rationale | decision summary / accepted-looking / informative / partial | Repeats system design and architecture; adapter exists but not wired | Four fit criteria and replaceability boundary | ADR plus integration architecture / `docs/04-decisions/`, `docs/02-architecture/integration-architecture.md` / link research/evidence / **convert to ADR, retain summary** |
| `README.md` / Current status | Current implementation snapshot | project-status / accepted-looking / informative / partial | Overlaps architecture/operations and code; strongest concise current-state list | Explicit not-started/not-deployed statements | Status / `docs/STATUS.md` / link tests and active plan / **move to status** |
| `README.md` / Current philosophy, Where things live | Principles and repository navigation | orientation + charter constraint | accepted-looking / informative / not-applicable | Overlaps AGENTS and architecture | Safety aphorisms, workspace/vault/evidence locations | Root README plus charter/docs index / root `README.md`, `docs/README.md` / **retain and update** |
| `AGENTS.md` / Scope and Authority | Agent routing, current/deferred boundaries, required reading | agent-instructions / accepted / normative for agents / not-applicable | Project instruction file; no PDS routes yet (`C-009`) | Vault/project separation, `tbd/`, evidence/index boundaries | `AGENTS.md` / root / link docs index, status, roadmap / **update** |
| `AGENTS.md` / Working rules | Safety and coding/governance constraints | agent-instructions / accepted / normative for agents / not-applicable | Summarizes design but does not fully redefine it | No canonical apply, configuration and privacy constraints | `AGENTS.md`; link canonical security/data/spec owners / **retain, replace duplicated design with links** |
| `AGENTS.md` / Verification | Narrow test command | agent-instructions / accepted / normative for agents / partial | Omits Step 3 and AgentCairn active suites (`C-009`) | Known focused command | `AGENTS.md`; quality owner / link `docs/07-quality/test-strategy.md` / **update** |
| `CONTEXT.md` / Authority | Canonical active vocabulary for authority and evidence | glossary / accepted-looking / normative / partial | Used by AGENTS and system design; active terms match contracts | Exact preferred and avoided terms | Glossary / `docs/01-foundation/glossary.md` / link charter, specs / **retain, move** |
| `CONTEXT.md` / Working memory | Memory kinds, identity, scope, conflicts, recall | glossary / accepted-looking / normative / partial | Mirrors memory-record contract; one timestamp-rule tension inherited from design (`C-001`) | Controlled terminology and distinctions | Glossary; exact behavior remains specs / `docs/01-foundation/glossary.md` / link memory and recall specs / **move, replace behavioral detail with links** |
| `CONTEXT.md` / Interaction and Operation | Interaction and runtime role vocabulary | glossary / accepted-looking / normative / partial | Mirrors interaction/run contracts | Controlled contexts, observation/profile/guidance, connector/processor/manifest terms | Glossary / same target / link interaction/runtime specs / **move** |
| `SECURITY.md` / Supported state | Security support/status statement | project-status / unknown / informative / diverged | Says architecture/manual prototype despite active code (`C-002`) | Public-support and canonical-apply boundary | Status / `docs/STATUS.md`; root security policy links it / **update; human wording review** |
| `SECURITY.md` / Reporting a vulnerability | Vulnerability reporting policy | security policy / accepted-looking / normative / not-applicable | Unique public reporting route | Private reporting and prohibited disclosure content | Root `SECURITY.md` / link security-and-trust / **retain** |
| `SECURITY.md` / Deployment boundary, Secret containment | Trust boundary and security invariants | security / accepted-looking / normative / partial | Repeats governance contract; implementation only has pattern redaction/output scan | Local/private surface, secret containment scope | Security architecture / `docs/02-architecture/security-and-trust.md` / root policy summarizes and links / **decompose** |
| `PDS.md` / complete standard | External/internal house documentation standard used by this audit | historical/reference standard / draft / normative for this audit / not-applicable | Version 0.2.0 says the standard should normally live separately (`C-010`) | Exact PDS text/version used for adoption | Human decision: vendor at root or archive/reference outside normal routes / link from docs index only by declared version / **retain pending decision** |
| `pyproject.toml` | Package metadata, version, Python/dependency/build contract | configuration / accepted-looking / normative for build / implemented | Code imports optional AgentCairn; version `0.1.0` but no Git tag | Package identity and optional dependency pin | Build configuration remains root / link README/runbook/test strategy where needed / **retain** |
| `config/host.example.yaml` | Example local host/vault/runtime configuration | configuration reference / accepted-looking / normative example / partial | Active code has no config loader (`D-007`) | Field names and ignored-local pattern | Configuration spec / `docs/03-specifications/configuration.md`; example stays `config/` / **retain, cross-link** |
| `.github/workflows/ci.yml` | CI verification configuration | automation configuration / accepted-looking / normative for CI / partial | Runs conversation and AgentCairn tests, not Step 3 (`C-009`) | Exact CI command and dependency extra | Quality/test strategy owns explanation; workflow stays in place / **retain, update later if accepted** |
| `.github/ISSUE_TEMPLATE/bug.yml` | Safe public defect intake | user/contributor procedure / accepted-looking / normative for issues / implemented | Enforces sanitized issue content | Privacy warning and reproduction fields | Root support/security docs link it if needed / remains `.github/` / **retain** |
| `.github/ISSUE_TEMPLATE/config.yml` | Issue-routing configuration | support configuration / accepted-looking / normative / implemented | Routes security reports privately | Security advisory URL | Root `SECURITY.md`; remains `.github/` / **retain** |

## Active design, contract, operations, and research material

| Current path / section | Apparent purpose and subjects | Class | Evidence, overlap, conflict | Preserve | Owner / target / links / action |
|---|---|---|---|---|---|
| `docs/system-design.md` / Purpose, goals, non-goals | Charter plus phase overview | project-charter + roadmap / accepted-looking / normative-looking / partial | Repeats README; Phase commitments unknown (`C-006`) | Goals, exclusions, three usable phases | Charter and roadmap / foundation charter + `ROADMAP.md` / **decompose** |
| `docs/system-design.md` / Authority and artifacts | Data authority taxonomy | data architecture + requirements / accepted-looking / normative / partial | Repeats governance and architecture | Artifact purpose/authority table | Data architecture / `docs/02-architecture/data-architecture.md` / link security/specs / **move, keep overview summary** |
| `docs/system-design.md` / System context, module responsibilities | Primary architecture plus semantic/deterministic seam | architecture / accepted-looking / normative / partial | Overlaps `architecture.md`; table overstates implementation (`D-003`) | Component boundaries and responsibility matrix | Architecture overview / `docs/02-architecture/overview.md` / link runtime/integration/specs / **decompose** |
| `docs/system-design.md` / Processor conflict rule | Exact conflict/supersession behavior | specification / accepted-looking / normative / unknown | Timestamp-only rule conflicts with contracts (`C-001`) | Both claims and source wording | Memory model specification / human decision before migration / **human decision required** |
| `docs/system-design.md` / Project identity and consolidation | Exact scope, identity, matching, Project Summary behavior | specification + data architecture / accepted-looking / normative / planned | Not implemented; repeats governance/memory contract | Project registry/root mapping and bounded summary rules | Memory model/data architecture specs / **merge** |
| `docs/system-design.md` / Storage, Recall, Governance, adapters | Component details and exact behavior | architecture + specifications / accepted-looking / normative / partial/planned | Most Recall/Governance unimplemented (`D-004`, `D-007`) | Clean responsibility boundaries | Overview plus capability specs / **decompose** |
| `docs/system-design.md` / Data locations, normal flow | Data/runtime architecture | data + runtime architecture / accepted-looking / normative / partial | Repeated in architecture/operations | Location ownership and 11-step flow | Data and runtime architecture / **decompose** |
| `docs/system-design.md` / Delivery topology | Roadmap and deployment future state | roadmap + deployment / accepted-looking / informative/normative mixed / partial | Later phases noncurrent; commitment unknown | Topology comparison and synchronization boundary | Roadmap and deployment architecture / **decompose** |
| `docs/system-design.md` / Key decisions | Decision rationale | decision / accepted-looking / historical / mixed | No active ADRs own these choices | Eight explicit decisions and rationales | ADRs / `docs/04-decisions/` / **convert to ADR** |
| `docs/system-design.md` / Interaction lifecycle, selected backend | Exact interaction spec plus integration decision | specification + decision / accepted-looking / normative/historical mixed / planned/partial | Repeats contracts; adapter not wired | Ten-step lifecycle and backend rationale | Interaction spec + ADR/integration architecture / **decompose** |
| `docs/system-design.md` / Document responsibilities | Informal authority map | documentation-index / accepted-looking / informative / not-applicable | First ownership attempt, but mixed owners remain | Existing reader routing | Docs index / `docs/README.md` / **replace after validation** |
| `docs/architecture.md` / Goal, non-goals, system shape | Phase 1 architecture/phase scope | architecture + roadmap scope / accepted-looking / normative / partial | Repeats README/system design | Current Phase 1 topology and exclusions | Architecture overview/deployment/roadmap / **decompose** |
| `docs/architecture.md` / Modules, interfaces | Component and integration responsibilities | architecture + specification / accepted-looking / normative / partial/planned | Code has no MCP/recall/hooks (`D-003`–`D-007`) | Module interfaces and `$orca-save` semantics | Overview, integration, capture/recall specs / **decompose** |
| `docs/architecture.md` / Storage | Data layout and runtime-local boundary | data architecture + specification / accepted-looking / normative / partial | Only continuation/manifests/checkpoints implemented | Vault/runtime tree and no-raw-copy boundary | Data architecture and memory specs / **decompose** |
| `docs/architecture.md` / Retrieval implementation | Integration architecture, decision, and status | integration + decision + project-status / accepted-looking / mixed / partial | Correctly says remaining items unimplemented | AgentCairn fit and exact implemented gap list | Integration architecture, ADR, status / **decompose** |
| `docs/architecture.md` / Completion criteria | Phase acceptance criteria | quality / accepted-looking / normative / partial | No centralized test mapping | Exact Phase 1 completion list | Acceptance plan / `docs/07-quality/acceptance.md` / link requirements/tests / **move** |
| `docs/governance/memory-system-contract.md` / Authority, Capture | Authority/privacy/capture requirements | specification / accepted-looking / normative / partial | Strongest current owner; capture code is a subset | Fail-closed authority, redaction, spool, dedupe, checkpoint rules | Capture and security specs / `docs/03-specifications/capture-pipeline.md`, security architecture / **decompose carefully** |
| `docs/governance/memory-system-contract.md` / Processing | Processing, identity, lifecycle, conflicts, relationships, recovery | specification / accepted-looking / normative / partial/planned | Overlaps memory-record/system design; provides clear-replacement claim (`C-001`) | Exact accepted-looking invariants | Processing + memory model specs / **decompose/merge** |
| `docs/governance/memory-system-contract.md` / Interaction preferences | Interaction security/lifecycle requirements | specification / accepted-looking / normative / planned | Repeats interaction contract | High-level prohibitions and lifecycle | Interaction preference spec; security invariants linked / **merge** |
| `docs/governance/memory-system-contract.md` / Recall, Local data | Recall and local-data requirements | specification + security/data / accepted-looking / normative / planned | Recall absent; local config exists | Hard filters, exact-conversation exception, local-only rules | Recall spec + data/security architecture / **decompose** |
| `docs/memory-record-contract.md` / Purpose, Responsibility | Contract boundary and ownership | specification / accepted-looking / normative / partial | Storage currently implements only continuation naming | Storage-only path ownership | Memory model spec / `docs/03-specifications/memory-model.md` / link architecture/ADRs/tests / **retain content, rename/merge** |
| `docs/memory-record-contract.md` / Structural summaries | Continuation and Project Summary schemas/bodies/budgets | specification / accepted-looking / normative / partial | Continuation implemented; Project Summary planned | Exact schemas and summary contracts | Memory model spec / **merge** |
| `docs/memory-record-contract.md` / Core record, provenance, status, ordinary body | Typed-record data contract and lifecycle | specification / accepted-looking / normative / planned | Research contains superseded candidate fields (`C-005`) | `orca-memory/0.2`, status/body/provenance rules | Memory model spec + data architecture / **merge** |
| `docs/memory-record-contract.md` / Conflict variants and review | Exact conflict state machine and review UX | specification / accepted-looking / normative / planned | Clear-replacement rule conflicts with system design (`C-001`) | Variant identity, review states, progressive disclosure | Memory model + workflow spec / human decision on conflict rule / **merge** |
| `docs/memory-record-contract.md` / Overflow candidates | Exact `v4+` candidate contract | specification / accepted-looking / normative / planned | Only detailed candidate contract currently present (`C-008`) | Schema, placement, retention, cleanup | Candidate/memory model spec / **retain** |
| `docs/memory-record-contract.md` / Layout, relationships, filenames | Data layout and exact storage policy | data architecture + specification / accepted-looking / normative / partial/planned | Continuation layout/slug partly implemented | Complete logical-to-physical mapping and version policies | Data architecture summary + memory model exact rules / **decompose** |
| `docs/run-manifest-contract.md` / Boundary, Manifest, Deduplication | Run-receipt schema and replay semantics | specification / accepted-looking / normative / implemented/partial | Code implements core fields and scan; no machine schema | `orca-run-manifest/0.1`, status and source-key rules | Provenance-ledger spec / `docs/03-specifications/provenance-ledger.md` / link tests / **retain content, rename** |
| `docs/run-manifest-contract.md` / Checkpoint | Checkpoint schema and publication order | specification / accepted-looking / normative / partial | Replay repair loses available manifest locator (`D-008`) | Recoverable three-step ordering | Provenance-ledger/capture spec / **merge, record divergence** |
| `docs/interaction-preference-contract.md` / Boundary, Observation | Observation schema and deterministic validation | specification / accepted-looking / normative / planned | No implementation | Exact evidence classes, abstentions, provenance boundary | Interaction-preferences spec / `docs/03-specifications/interaction-preferences.md` / link security/quality / **retain content, rename** |
| `docs/interaction-preference-contract.md` / Dimensions, Profile | Controlled vocabulary and profile schema | specification / accepted-looking / normative / planned | Research is informative precursor | Exact dimensions/contexts/profile states | Same spec / **merge** |
| `docs/interaction-preference-contract.md` / Consolidation | Exact activation, expiry, conflict, precedence | specification / accepted-looking / normative / planned | Repeats governance/system design | Deterministic lifecycle and evaluation boundary | Same spec / **merge** |
| `docs/interaction-guidance-contract.md` / Purpose, Prefixes, Clauses | Fixed guidance templates | specification / accepted-looking / normative / planned | No implementation/tests | Exact versioned strings | Interaction-guidance spec / `docs/03-specifications/interaction-guidance.md` / link preference spec/tests / **retain content, rename** |
| `docs/interaction-guidance-contract.md` / Compilation | Deterministic compile/budget rules | specification / accepted-looking / normative / planned | Repeats interaction preference contract | Exact lookup and precedence behavior | Same spec / **merge** |
| `docs/operations.md` / Current status, Configuration | Status plus configuration contract | project-status + specification / accepted-looking / mixed / partial/planned | Configuration loader absent (`D-007`) | Budget defaults, configuration locations/mapping | Status, configuration spec, data architecture / **decompose** |
| `docs/operations.md` / Normal operation | Runtime flow and exact behavioral contracts | runtime architecture + specification / accepted-looking / normative / partial/planned | Most steps unimplemented; repeats all active docs | End-to-end hook/worker/processing/recall flow | Runtime architecture; link exact specs / **decompose** |
| `docs/operations.md` / Conflict recovery, Scheduling, Failure behavior | Recovery and runtime policy | runbook + specification / accepted-looking / normative / partial/planned | Partial-line claim diverges from parser (`D-002`) | Recovery, retry, scheduler, index behavior | Runbook plus runtime/provenance specs / **decompose** |
| `docs/operations.md` / Phase 1 readiness | Acceptance/evaluation checklist | quality / accepted-looking / normative / partial | No traceability owner | Comprehensive readiness cases | Acceptance/test strategy / **move** |
| `docs/research/interaction-preference-measurement.md` / complete | Primary-source research and recommendations | historical research / accepted as report / informative / not-applicable | Precedes contracts; some proposed lifecycle differs (`C-005`) | Sources, psychometric limits, 4/2/1 rejection | Archive research / `docs/_archive/research/interaction-preference-measurement.md` / ADR/spec may cite evidence / **archive after validation** |
| `docs/research/memory-categorization-landscape.md` / comparison | Primary-source landscape | historical research / accepted as report / informative / not-applicable | No current-behavior authority | Comparative evidence and graph cost analysis | Archive research / `docs/_archive/research/` / **archive after validation** |
| `docs/research/memory-categorization-landscape.md` / recommendations | Pre-decision proposed record/schema/link design | proposal evidence / superseded/unknown / informative / not-applicable | Conflicts with current memory contract (`C-005`) | Rationale for scope/kind separation and graph deferral | ADR evidence or archived research; never canonical spec / **archive, cross-link from decisions** |
| `docs/research/recall-context-budget.md` / evidence | Model-window and handoff research | historical research / accepted as report / informative / not-applicable | Contains absolute local skill link (`C-011`) | First-party evidence and model-window cautions | Archive research / `docs/_archive/research/` / **archive after link preservation** |
| `docs/research/recall-context-budget.md` / recommendations | Proposed/accepted-looking budget rationale | decision evidence + proposal / unknown / informative / not-applicable | Budget values are repeated as normative elsewhere | Rationale for 20K/4K/2K/4K limits | ADR and configuration/processing specs / **extract rationale; archive report** |

## Deferred all-phase documents

The parent `tbd/README.md` explicitly makes these noncurrent. Their internal
`accepted` labels are therefore not treated as current authority.

| Current path / section | Apparent purpose and subjects | Class | Evidence, overlap, conflict | Preserve | Owner / target / links / action |
|---|---|---|---|---|---|
| `tbd/README.md` | Deferred/reference boundary, navigation, legacy test command | documentation-index / accepted-looking / informative / not-applicable | Clear noncurrent warning; `tbd/` is outside standard PDS tree | Boundary and historical runnable command | `docs/README.md` registers a PDS exception; retain `tbd/README.md` / **retain, update metadata/warning later** |
| `tbd/future/system-overview.md` | All-phase architecture index and old status boundary | historical/future overview / accepted-labelled / historical/informative / diverged | Says manual prototype under old path and has accepted baseline (`C-003`, `C-004`) | Original baseline navigation and authority text | Frozen legacy-future source under `tbd/`; roadmap/proposals receive accepted current direction only / **archive after validation or retain as declared exception** |
| `tbd/future/CONTEXT-all-phases.md` / Authority, Working Memory, Operation | All-phase vocabulary including Curator, replicas, client/processor deployment | glossary/proposal evidence / accepted-labelled unknown / informative / not-applicable | Conflicts with active transient evidence and current terminology (`C-003`) | Later-phase terminology and definitions | Later-phase proposals/roadmap; keep source frozen / **decompose when phase is activated; otherwise retain** |
| `tbd/future/delivery-plan.md` / Purpose, Common design | Mixed roadmap and architecture baseline | roadmap + architecture / accepted-labelled / informative / diverged | Persistent evidence, canonical-first recall, and capture module conflict with active design (`C-003`) | Historical three-phase baseline | Current roadmap links source only as history / **archive/retain; do not merge blindly** |
| `tbd/future/delivery-plan.md` / Phases 1–3 | Detailed roadmap plus implementation plans and acceptance | roadmap + plan + quality / accepted-labelled / mixed / diverged/unknown | Phase 1 exclusions contradict current Phase 1 (`C-003`); later commitment unknown (`C-006`) | Phase outcomes, entry/exit criteria, later topology risks | `ROADMAP.md`, proposals, active plan after human review / **decompose; human decision required** |
| `tbd/future/architecture.md` / complete | Future architecture, data/deployment/integration, retention/apply | architecture + proposal / accepted-labelled / mixed / planned/unknown | Noncurrent by parent; overlaps active design and later phases | Later synchronization/Curator/retention topology and seams | Future proposals + roadmap + later ADRs; keep frozen source / **convert selected future designs to proposals; retain** |
| `tbd/future/memory-system-contract.md` / active-looking invariants | All-phase authority/capture/derivation/recall rules | specification / accepted-labelled / normative-looking / diverged | Conflicts with current transient evidence and interaction evidence (`C-003`) | Original invariant set and deferred retention/apply gates | Later proposals/specs only after decisions / **retain historical; human review before promotion** |
| `tbd/future/memory-system-contract.md` / retention, apply, privacy | Deferred automation and later security rules | proposal + future requirement / accepted-labelled / informative/normative mixed / planned | Explicitly deferred | Retention periods, Curator gates, processor authority | Roadmap plus proposals; security/data architecture summarizes only accepted scope / **convert to proposals as activated** |
| `tbd/future/operations.md` / configuration through scheduling | Future runbook/deployment architecture | runbook + deployment / accepted-labelled / historical/future / diverged | Scheduler/capture model differs from active hooks (`C-003`) | Later release, processor-transfer and scheduling procedures | Later active plan/runbook when phase activated / **retain** |
| `tbd/future/operations.md` / transfer, conflicts, apply recovery, cutover, canaries | Future operations, plans, acceptance | plan + quality + runbook / accepted-labelled / mixed / planned | Not current operation | Detailed safety/cutover procedures | Roadmap/proposals/future plans; preserve exact historical source / **decompose later** |
| `tbd/future/adr/0001-separate-local-and-synchronized-system-state.md` | Superseded design decision | decision / superseded / historical / not-applicable | Explicit supersession to ADR 0004 | Original rejected partially synchronized hidden tree rationale | Decisions archive/current ADR sequence / preserve number and links / **retain or migrate as superseded ADR** |
| `tbd/future/adr/0002-authorize-one-processor-by-host-identity.md` | Future Phase 3 processor decision | decision / accepted-labelled but current applicability unknown / historical / planned | Parent says noncurrent (`C-004`) | Host/generation rationale | Future proposal/ADR set; roadmap Phase 3 link / **human status decision** |
| `tbd/future/adr/0003-graduate-canonical-apply-by-category.md` | Follow-on automatic-apply decision | decision / accepted-labelled but outside current phases / historical / planned | Parent says noncurrent; auto apply disabled | Per-category graduation rationale | Future proposal/ADR; roadmap deferred capability / **human status decision** |
| `tbd/future/adr/0004-separate-project-workspace-from-vault.md` | Checkout/vault separation decision | decision / accepted-labelled / historical / implemented | Current repository follows it; parent says noncurrent (`C-004`) | Exact accepted rationale and supersession link | Active ADR package, preserving number / `docs/04-decisions/0004-...md` / link architecture/data / **promote after human confirmation** |

## Retained legacy documentation and machine schemas

All paths below are under the explicit historical boundary
`tbd/reference/legacy/`. They must not be rewritten to match current Orca.

| Current path | Purpose/subjects | Class and implementation status | Overlap/conflict and unique preservation | Target/action |
|---|---|---|---|---|
| `tbd/reference/legacy/docs/prototype-migration-notes.md` | Prototype responsibility and provenance map | historical / archived-looking / historical / not-applicable | Unique legacy mapping and cautions | Retain frozen; docs index marks historical; **retain** |
| `tbd/reference/legacy/prototype/README.md` | Manual prototype orientation | historical user/developer doc / archived-looking / historical / verified historically | Old phase model and commands; boundary link was adjusted | Retain with legacy tree; **retain** |
| `tbd/reference/legacy/prototype/integration/phase6/adapter-contract.md` | Cairn delta/checkpoint v0.1.2 contract | historical specification / archived-looking / historical / verified historically | Exact former transport contract | Retain; **retain** |
| `tbd/reference/legacy/prototype/integration/phase7/intake-contract.md` | Curator intake v0.1.4 contract | historical specification / archived-looking / historical / verified historically | Exact former intake/planning/apply contract | Retain; **retain** |
| `tbd/reference/legacy/prototype/workflows/semantic-provider-rules.md` | Former provider instruction contract | historical specification / archived-looking / historical / verified historically | Exact provider rules; never current authority | Retain; **retain** |
| `tbd/reference/legacy/prototype/integration/phase6/schemas/checkpoint.schema.json` | Phase 6 checkpoint schema | historical machine schema / archived-looking / historical / verified historically | Machine-validatable former format | Retain beside contract; **retain** |
| `tbd/reference/legacy/prototype/integration/phase6/schemas/delta.schema.json` | Phase 6 delta schema | historical machine schema / archived-looking / historical / verified historically | Machine-validatable former format | Retain; **retain** |
| `tbd/reference/legacy/prototype/integration/phase7/schemas/authorization.schema.json` | Former apply authorization schema | historical machine schema / archived-looking / historical / verified historically | Exact former authority gate | Retain; **retain** |
| `tbd/reference/legacy/prototype/integration/phase7/schemas/intake.schema.json` | Former Curator intake schema | historical machine schema / archived-looking / historical / verified historically | Exact former intake format | Retain; **retain** |
| `tbd/reference/legacy/prototype/integration/phase7/schemas/plan.schema.json` | Former Curator plan schema | historical machine schema / archived-looking / historical / verified historically | Exact former plan format | Retain; **retain** |
| `tbd/reference/legacy/prototype/integration/phase7/schemas/processing-state.schema.json` | Former operational state schema | historical machine schema / archived-looking / historical / verified historically | Exact former replay/state format | Retain; **retain** |

## Retained documentation fixtures

Fixtures are implementation evidence, not project guidance. Each remains beside
the legacy tests that consume it; none should enter normal documentation routes.

| Current path | Purpose and unique information | Class | Target/action |
|---|---|---|---|
| `tbd/reference/legacy/tests/integration/fixtures/agent-workspace/AGENTS.md` | Isolated Cairn test instruction fixture | historical test fixture / historical / verified historically | Retain in place |
| `tbd/reference/legacy/tests/phase6/fixtures/development/store/alpha.md` | Phase 6 source-store fixture A | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/phase6/fixtures/development/store/beta.md` | Phase 6 source-store fixture B | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/phase6/fixtures/development/store/gamma.md` | Phase 6 source-store fixture C | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/phase7/fixtures/development/cairn/alpha.md` | Phase 7 Cairn candidate fixture | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/phase7/fixtures/development/canonical/Knowledge/existing.md` | Phase 7 canonical comparison fixture | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/phase7/fixtures/development/governance-cases.json` | Phase 7 governance-case fixture | historical machine fixture | Retain in place |
| `tbd/reference/legacy/tests/skills/fixtures/scenarios.json` | Former skill scenario catalog | historical machine fixture | Retain in place |
| `tbd/reference/legacy/tests/skills/fixtures/vault/Inbox/candidate-correction.md` | Candidate correction fixture | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/skills/fixtures/vault/Inbox/curator-disposition.md` | Curator disposition fixture | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/skills/fixtures/vault/Projects/Example/current.md` | Current-project fixture | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/skills/fixtures/vault/Projects/Example/historical.md` | Historical-project fixture | historical test fixture | Retain in place |
| `tbd/reference/legacy/tests/skills/fixtures/vault/Raw/sources/source-s1.md` | Raw-source fixture | historical test fixture | Retain in place |

## Local ignored records and configuration

These are present in the workspace but intentionally excluded from public Git.
They are inventoried to prevent accidental promotion.

| Current path / group | Purpose | Class | Conflict/unique preservation | Owner/target/action |
|---|---|---|---|---|
| `.agent-notes/README.md` | Local continuity-note protocol | working-note index / accepted locally / working / not-applicable | Explicitly subordinate to tracked docs | Keep ignored; no PDS migration |
| `.agent-notes/current.md` | Current objective, decisions, status, next action | conversation handoff / draft / working / unknown | Contains useful evidence but cannot establish acceptance | Keep ignored; reconcile into canonical owners only through explicit review |
| `.agent-notes/issues.md` | Local issue register | working issue record / draft / working / unknown | ORCA-001 is stale because budgets are now documented (`C-007`) | Keep ignored; close/update only under separate authority |
| `.agent-notes/lessons.md` | Durable local agent lessons | working process record / draft / working / not-applicable | Unique agent-process lessons | Keep ignored; promote only generic accepted rules to AGENTS if requested |
| `config/host.yaml` | Actual machine-specific host/vault/runtime configuration | local configuration / accepted locally / normative for host / unknown | Contains private machine paths; must remain ignored | Keep in place; never migrate or quote values |
| `index.md` / complete file | Pre-reorganization project hub, phase history, decisions, tasks, lessons, sources | historical mixed document / superseded-looking / historical / diverged | Stale links and former phase numbering (`C-007`); unique history must remain local | Keep ignored as local historical record; do not move into public docs |
| `evidence/README.md` | Local evidence registry | historical index / accepted as record / historical / not-applicable | Defines privacy and frozen-evidence boundary | Keep ignored; public docs may cite only sanitized reports if authorized |
| `evidence/cairn-fit/README.md` | Cairn fit test-area guide | historical test guide / historical / verified historically | Exact isolated test setup | Keep ignored |
| `evidence/cairn-fit/CAIRN_FIT_REPORT.md` | AgentCairn fit verdict and caveats | historical evaluation / historical / verified historically | Unique `USE AS-IS` evidence and limitations | Keep ignored; ADR may cite sanitized verdict |
| `evidence/provider-backed-smoke/PROVIDER_SMOKE_REPORT.md` | Provider-backed smoke evidence | historical evaluation / historical / verified historically | Unique smoke counts and safety results | Keep ignored |
| `evidence/real-use-canary-20260823/CANARY_REVIEW.md` | Controlled real-use canary | historical evaluation / historical / verified historically | Unique `PASS — SMALL SAMPLE` evidence and limits | Keep ignored |
| `evidence/**/*.json`, `evidence/**/*.jsonl`, evidence Markdown notes, text outputs, checkpoints, indexes, locks, ledgers | Frozen run artifacts and private/local machine evidence | historical machine evidence / historical / verified historically or unknown | May contain prompts, paths, hidden records, and exact hashes | Keep ignored and frozen; never bulk-promote; inspect only for explicit evidence tasks |

## Pre-existing absent tracked documentation paths

The following tracked paths were already deleted before the audit. Their current
counterparts are inventoried above; this audit does not classify the deletion as
accepted migration:

- `docs/adr/0001-separate-local-and-synchronized-system-state.md`
- `docs/adr/0002-authorize-one-processor-by-host-identity.md`
- `docs/adr/0003-graduate-canonical-apply-by-category.md`
- `docs/adr/0004-separate-project-workspace-from-vault.md`
- `docs/prototype-migration-notes.md`
- `docs/system-overview.md`
- `prototype/README.md`
- `prototype/integration/phase6/adapter-contract.md`
- `prototype/integration/phase6/schemas/checkpoint.schema.json`
- `prototype/integration/phase6/schemas/delta.schema.json`
- `prototype/integration/phase7/intake-contract.md`
- `prototype/integration/phase7/schemas/authorization.schema.json`
- `prototype/integration/phase7/schemas/intake.schema.json`
- `prototype/integration/phase7/schemas/plan.schema.json`
- `prototype/integration/phase7/schemas/processing-state.schema.json`
- `prototype/workflows/semantic-provider-rules.md`
- the corresponding legacy documentation fixtures under `tests/integration/`,
  `tests/phase6/`, `tests/phase7/`, and `tests/skills/`.

Their relocation/alteration remains pre-existing working-tree state to validate
separately before any commit.

## Source and test evidence used for implementation status

| Path | Evidence established |
|---|---|
| `src/orca_memory/conversation.py` | Positive `UserMessage` selection, transient normalization, secret-pattern redaction, deterministic hashes; no assistant capture, partial-line tolerance, private-directive classifier, or persisted evidence archive. |
| `src/orca_memory/privacy.py` | Four deterministic credential-pattern families and output detection. |
| `src/orca_memory/processor.py` | One replaceable semantic call and validation of a Continuation Summary only; no budgets, chunking, records, candidates, profiles, or project consolidation. |
| `src/orca_memory/storage.py` | Continuation publication, date-sharded immutable manifest, manifest-scan dedupe, source-revision failure, checkpoint-last publication and replay repair. |
| `src/orca_memory/pipeline.py` | Minimal select-process-publish orchestration. |
| `src/orca_memory/agentcairn.py` | Prevalidated noncanonical Distiller seam; no active Processor wiring. |
| `tests/conversation/test_codex_capture.py` | Direct normalization, injected-envelope exclusion, redaction, deterministic no-copy behavior. |
| `tests/step3/test_pipeline.py` | Continuation/manifest/checkpoint, replay, checkpoint failure recovery, no-memory, output secret rejection, source revision. |
| `tests/agentcairn/test_distiller.py` | AgentCairn public-seam behavior, unknown-candidate fail-closed, canonical rejection. |

No source file is a canonical owner of intended design; these paths establish
implementation reality only.
