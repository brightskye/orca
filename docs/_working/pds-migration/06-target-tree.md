---
id: WORK-2026-08-29-PDS-TARGET-TREE
title: PDS Audit Proposed Target Tree
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Proposed smallest sufficient target tree

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

## Tree

```text
README.md
AGENTS.md
SECURITY.md
PDS.md                              # tracked authoritative PDS-0.2 copy

docs/
├── README.md
├── STATUS.md
├── ROADMAP.md
├── 01-foundation/
│   ├── project-charter.md
│   ├── requirements.md
│   └── glossary.md
├── 02-architecture/
│   ├── overview.md
│   ├── runtime.md
│   ├── deployment.md
│   ├── data-architecture.md
│   ├── security-and-trust.md
│   ├── integration-architecture.md
│   └── diagrams/
│       ├── system-context.mmd
│       └── processing-flow.mmd
├── 03-specifications/
│   ├── README.md
│   ├── capture-pipeline.md
│   ├── processing-pipeline.md
│   ├── memory-model.md
│   ├── knowledge-candidates.md
│   ├── provenance-ledger.md
│   ├── retrieval-contract.md
│   ├── interaction-preferences.md
│   ├── interaction-guidance.md
│   └── configuration.md
├── 04-decisions/
│   ├── README.md
│   ├── template.md
│   └── ADR records                 # preserve 0001–0004; allocate new numbers
├── 05-proposals/
│   ├── README.md
│   ├── template.md
│   └── later-phase records only when under review
├── 06-plans/
│   ├── README.md
│   ├── active/
│   │   └── phase-1-implementation.md
│   └── completed/
├── 07-quality/
│   ├── acceptance.md
│   └── test-strategy.md
├── 08-operations/
│   └── runbook.md
├── _working/
│   ├── README.md
│   └── pds-migration/              # this audit; later migration records
└── _archive/
    ├── README.md
    ├── legacy-docs/                # former active docs after validation
    └── research/                   # completed informative research

config/
├── host.example.yaml
└── host.yaml                       # ignored, local, never migrated

tbd/                                # retained exception: mixed future/legacy code package
├── README.md
├── future/
└── reference/legacy/
```

No `09-user-docs/` or `CHANGELOG.md` is proposed yet. No additional diagram,
quality, operations, schema, or proposal file should be created until it has
material content and an owner.

## Document responsibilities

| Proposed document | Why needed | Owns | Must not own | Source material |
|---|---|---|---|---|
| Root `README.md` | Human orientation and quick start are required | Concise description, actual status summary, quick start, primary links | Full phases, exact contracts, active plan | Current README orientation, AgentCairn summary, locations |
| Root `AGENTS.md` | Required agent entry point | Reading protocol, safety, dev/verification commands | Architecture, roadmap, detailed contracts | Current AGENTS plus PDS protocol |
| Root `SECURITY.md` | Public vulnerability entry point | Reporting route and concise support boundary | Complete threat/trust design or project status | Current SECURITY reporting section |
| `docs/README.md` | Required registry and router | PDS version/profile, ownership map, reading routes, exceptions | System behavior | System-design responsibility list, this audit |
| `docs/STATUS.md` | Required current-state owner | Implemented/partial/planned/diverged capabilities, active plan, blockers | Requirements, exact behavior, future direction | README status, architecture status, code/tests, conflict report |
| `docs/ROADMAP.md` | Triggered by three phases | Phase outcomes/status/dependencies/exit criteria/deferred capabilities | Task lists, exact designs, current progress | README phases, system design topology, reviewed future delivery plan |
| Project charter | Core foundation | Problem, Owner/stakeholders, goals, scope, non-goals, constraints, success | Component or workflow detail | README Goal/philosophy, system-design goals/non-goals |
| Requirements | Core foundation | Stable testable obligations | Architecture or implementation steps | Governance invariants, Phase 1 scope, completion criteria |
| Glossary | Existing terminology is substantial | Canonical terms and avoided synonyms | Behavioral contracts | Active `CONTEXT.md`; accepted later terms only when in scope |
| Architecture overview | Required primary system-design entry | Boundaries, components, responsibilities, principles, high-level flows, routing | Exact fields, budgets, algorithms, plan/status | System design + Phase 1 architecture |
| Runtime architecture | Substantial triggered runtime flow | Hooks/jobs/worker/index/recall sequence and failure boundaries | Copy-paste procedures or exact schemas | Operations normal flow, system-design flow, run contract summaries |
| Deployment architecture | WSL/vault and future topology materially differ | Current deployment boundary and clearly labelled future topology summary | Installation steps, roadmap commitment | Architecture system shape/data locations, system-design topology |
| Data architecture | PDS trigger is met | Data classes, owners, canonical/derived status, lifecycle, retention/deletion/rebuild/sync | Exact record fields | Artifact tables, storage trees, record/run contracts |
| Security and trust | PDS trigger is met | Assets, actors, trust boundaries, external risks, invariants, mitigations, residual risk | Vulnerability-report procedure or general plans | SECURITY deployment/containment, governance privacy, architecture |
| Integration architecture | Several replaceable and external seams exist | Codex, MCP, semantic provider, AgentCairn, connector boundaries | Exact connector parsing rules or vendor tutorial | System design seam/adapters, AgentCairn rationale, capture docs |
| System diagrams | Current repeated ASCII flows need one checked source | Context and processing-flow relationships | Independent behavior definitions | Existing ASCII/Mermaid diagrams |
| Specifications index | Required Core navigation | Spec registry and boundaries | Behavior itself | Current contract set |
| Capture pipeline | Exact capture behavior is safety-critical | Event selection, normalization, privacy gate, source identity, partial input, spool handoff | General architecture | Governance Capture, Conversation module, code/tests |
| Processing pipeline | Exact semantic/deterministic flow needs one owner | Input selection, budgets, proposal validation, errors/idempotency | Memory schemas owned elsewhere | System design Processor, governance Processing, operations |
| Memory model | Largest coherent exact contract | Summaries, typed records, project identity, statuses/conflicts, layout/naming/relationships | Processing schedule or roadmap | Memory Record Contract plus accepted governance rules |
| Knowledge candidates | Required Phase 1 gap owner | Ordinary candidate schema, lifecycle, review/retention/exclusion | Conflict Overflow Candidate unless shared behavior is explicit | Current mentions plus reviewed legacy evidence |
| Provenance ledger | Implemented receipt/checkpoint behavior deserves exact owner | Manifest/checkpoint fields, dedupe, publication order, recovery | Full memory semantics | Run Manifest Contract, storage/tests |
| Retrieval contract | Recall behavior is detailed and distinct | Request, filters, projection, ranking, budgets, response, errors | Interaction guidance or backend internals | Governance Recall, system design, operations |
| Interaction preferences | Existing precise contract | Observation/profile schema, validation, consolidation, expiry/conflict | Fixed guidance wording | Interaction Preference Contract, accepted governance rules |
| Interaction guidance | Exact versioned strings are a separate change surface | Templates and compiler rules | Observation inference | Interaction Guidance Contract |
| Configuration | Config fields/budgets are cross-cutting | Host/vault config, environment overrides, validation and precedence | Operational procedures | Operations config, host example, AGENTS rule |
| Decisions index/template/ADRs | Current rationale is embedded and history exists | One significant decision per immutable record | Complete current architecture | System-design key decisions, existing ADRs, research |
| Proposals index/template | Later exact designs must remain unaccepted | Substantial designs under review | Accepted behavior | Selected `tbd/future/` material only when activated |
| Plans index/active Phase 1 plan | Current work needs a public execution owner | Milestones, dependencies, progress, completion | Requirements/architecture/roadmap | STATUS gaps, current objective, architecture completion list |
| Acceptance | Phase exit and requirement evidence is scattered | Acceptance IDs, traceability, phase exit gates | Test implementation details | Architecture criteria, operations readiness, tests/evidence |
| Test strategy | AI/deterministic boundaries and suites need coordination | Test levels, commands, fixtures, semantic evaluation policy, CI gates | Product design | AGENTS, CI, tests, system-design deterministic seam |
| Runbook | Core operations owner | Verified install/config/start/stop/health/backup/recovery/troubleshooting | Architecture rationale or unimplemented promises | Current operations, only commands verified later |
| `_working/README.md` | PDS requires visible non-authority boundary | Working material policy | Current project truth | PDS rules and this audit warning |
| `_archive/README.md` | PDS requires visible historical boundary | Archive policy and replacement routing | Current project truth | PDS rules, legacy preservation needs |
| `_archive/legacy-docs/` | Old mixed sources must survive migration verification | Frozen former active docs | Normal reading route | Current README/system-design/architecture/operations/contracts after extraction |
| `_archive/research/` | Completed research should remain evidence, not design | Historical reports and sources | Current requirements/specs | Current `docs/research/` |

## PDS exception for `tbd/`

Retain `tbd/` because it is a mixed code/test/document reference package, not
merely a documentation archive. Moving its code and fixtures under `docs/` would
misclassify them and broaden this migration. `docs/README.md` should declare:

- `tbd/` is excluded from normal reading routes;
- its contents are noncurrent historical or future evidence;
- internal `accepted` labels do not make a file current;
- only explicit proposal/decision promotion can move conclusions into active
  canonical documents;
- legacy files remain frozen unless a historical correction is explicitly
  authorized.

The Owner approved this exception on 2026-08-29. It must be declared in
`docs/README.md` during migration.
