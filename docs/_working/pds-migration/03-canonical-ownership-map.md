---
id: WORK-2026-08-29-PDS-OWNERSHIP
title: PDS Audit Canonical Ownership Map
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Canonical ownership map

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

This map proposes one PDS owner per material subject. It does not confer
authority. `Decision` identifies a question that requires Owner review before
the later migration can establish the proposed owner.

| Subject | Current locations | Proposed canonical owner | Proposed target | Conflicts | Decision |
|---|---|---|---|---|---|
| Documentation registry, authority map, reading routes | `docs/system-design.md#Document-responsibilities`, `README.md`, `AGENTS.md` | Documentation index | `docs/README.md` | No current PDS registry | Resolved: PDS-0.2 Core with tracked root standard |
| Current implementation state | `README.md#Current-status`, `docs/architecture.md#Retrieval-implementation`, `docs/operations.md#Current-status`, `SECURITY.md#Supported-state`, code/tests | Project status | `docs/STATUS.md` | Detailed status remains distributed | Resolved public wording; extract factual status owner |
| Project problem and purpose | `README.md#Goal`, `docs/system-design.md#Purpose`, `CONTEXT.md` intro | Project charter | `docs/01-foundation/project-charter.md` | Minor wording duplication | None if extraction is literal |
| Goals, non-goals, constraints, success criteria | `docs/system-design.md#Design-goals`, `#Non-goals`, `docs/architecture.md#Non-goals`, README philosophy, completion criteria | Project charter for goals/boundaries; requirements/quality for obligations/evidence | `docs/01-foundation/project-charter.md`; `docs/01-foundation/requirements.md`; `docs/07-quality/acceptance.md` | Currently mixed | None if section purposes are preserved |
| Phase direction and topology axis | `README.md#Delivery-phases`, `docs/system-design.md#Delivery-topology`, `tbd/future/delivery-plan.md` | Roadmap | `docs/ROADMAP.md` | Current versus deferred phase detail differs | Resolved: Phase 2/3 are candidate directions |
| Immediate Phase 1 execution | `.agent-notes/current.md`, architecture gaps, README status; no public plan | Active implementation plan | `docs/06-plans/active/phase-1-implementation.md` | Local notes are not authority | Approve plan baseline and included work |
| Domain terminology | `CONTEXT.md`, `tbd/future/CONTEXT-all-phases.md`, contracts | Glossary | `docs/01-foundation/glossary.md` | Active and all-phase definitions differ | Later-phase terms stay proposal-scoped until activated |
| System boundaries and components | `docs/system-design.md`, `docs/architecture.md`, README architecture | Architecture overview | `docs/02-architecture/overview.md` | Duplication, not a material current contradiction | None after conflict-preserving extraction |
| Runtime flow and failure boundaries | `docs/operations.md`, `docs/system-design.md#Normal-operating-flow`, architecture hooks/jobs, run contract | Runtime architecture | `docs/02-architecture/runtime.md` | Partial-line and other implementation gaps | None; status must link divergences |
| Deployment topology | README phases, system design topology/data locations, architecture system shape, current/future operations | Deployment architecture | `docs/02-architecture/deployment.md` | Deferred docs describe former Phase 1 deployment flow | Phase 2/3 commitment/status only |
| Integration boundaries | Codex connector in architecture/governance, AgentCairn rationale, semantic-provider seam, future connectors | Integration architecture | `docs/02-architecture/integration-architecture.md` | Active adapter not wired; future connector contracts noncurrent | None; record implementation status |
| Data categories and authority | System design artifact table, governance authority, memory/run contracts, architecture storage | Data architecture | `docs/02-architecture/data-architecture.md` | Deferred data lifecycle differs | None for Phase 1; future rules remain proposals |
| Data lifecycle, provenance, derived/rebuildable state | Governance capture/processing, memory record provenance, run manifest, operations | Data architecture at overview level; exact specs own formats | `docs/02-architecture/data-architecture.md` plus specs | Repeated across four documents | None after links replace copies |
| Security assets, trust, privacy, secret handling | `SECURITY.md`, governance contract, architecture, operations, issue template | Security and trust architecture; root policy owns reporting | `docs/02-architecture/security-and-trust.md`; root `SECURITY.md` | Current implementation only partially enforces design | Public supported-state wording |
| Project requirements | README Phase 1 scope, governance invariants, system design goals, architecture completion criteria | Requirements | `docs/01-foundation/requirements.md` | Requirements are not identified or traceable | Owner review of extracted stable IDs |
| Codex event selection and privacy gate | Governance Capture, architecture Conversation module, operations normal flow, `conversation.py` | Capture pipeline specification | `docs/03-specifications/capture-pipeline.md` | Docs include assistant/private/partial behavior absent in code | None; mark partial/diverged |
| Processor input, chunking, semantic seam | System design Processor, governance Processing, operations, context-budget research | Processing specification | `docs/03-specifications/processing-pipeline.md` | Code implements only one simple provider input | None; mark partial |
| Memory record model, summaries, scope, conflicts, filenames | `docs/memory-record-contract.md`, governance Processing, system design, context glossary, research | Memory model specification | `docs/03-specifications/memory-model.md` | Research is superseded; active conflict rule reconciled | Resolved: clear applicable Owner replacement required |
| Ordinary Knowledge Candidate model | README, system design, governance, legacy candidate material | Candidate specification | `docs/03-specifications/knowledge-candidates.md` | No complete active contract | Resolved: create full Phase 1 contract without importing legacy behavior |
| Run Manifest, processed-source dedupe, checkpoint | Run contract, governance, operations, storage code/tests | Provenance ledger specification | `docs/03-specifications/provenance-ledger.md` | Replay checkpoint locator differs from contract | None; status records divergence |
| Recall contract | Governance Recall, system design Recall, architecture, operations | Retrieval contract | `docs/03-specifications/retrieval-contract.md` | Deferred canonical-first rule differs; code absent | None for current rule; keep future source historical |
| Interaction observations and profile lifecycle | Interaction preference contract, governance, system design, research | Interaction preference specification | `docs/03-specifications/interaction-preferences.md` | Research precursor differs from accepted-looking contract | None after research is historical |
| Compiled interaction guidance | Guidance contract and references in preference/governance/system design | Interaction guidance specification | `docs/03-specifications/interaction-guidance.md` | No implementation | None |
| Configuration behavior | operations, architecture, `config/host.example.yaml`, environment variable rule | Configuration specification | `docs/03-specifications/configuration.md` | No loader/validator in code | None; mark planned |
| Significant technical rationale | `docs/system-design.md#Key-design-decisions`, AgentCairn section, deferred ADRs, research | ADR set | `docs/04-decisions/` | Existing numbered files require migration placement | Resolved: 0001 superseded, 0004 active, 0002/0003 future-only; never reuse numbers |
| Substantial unaccepted future designs | `tbd/future/architecture.md`, contract, operations, delivery plan | Proposals | `docs/05-proposals/` when a future design becomes active for review | Files say accepted-baseline but parent says noncurrent | Resolved: candidate phases do not accept exact future designs |
| Acceptance and phase exit evidence | Architecture completion criteria, operations readiness, future canaries, tests/evidence | Acceptance plan | `docs/07-quality/acceptance.md` | No requirement/test IDs | Owner review of acceptance IDs and phase linkage |
| Test/evaluation strategy | AGENTS test command, CI, current tests, research/evidence caveats | Test strategy | `docs/07-quality/test-strategy.md` | Active suites are inconsistently invoked | None; document current suite truthfully |
| Installation, configuration procedure, operation, recovery | `docs/operations.md`, README, `tbd/README.md` legacy command | Runbook | `docs/08-operations/runbook.md` | Current file mixes intended and executable procedures; deployment not implemented | None; clearly label unverified commands |
| Vulnerability reporting | `SECURITY.md`, issue config | Root security policy | `SECURITY.md` | None after supported-state correction | Resolved public wording |
| Research evidence | `docs/research/*.md`, local evidence reports | Historical research/evaluation | `docs/_archive/research/` for public research; local evidence remains ignored | Some recommendations conflict with current specs | None if archived and linked only as evidence |
| Deferred and legacy package | `tbd/**` | Project-specific noncurrent reference boundary | Retain `tbd/` as documented PDS exception; optionally mirror doc-only history in `_archive` later | Internal accepted labels require explicit routing | Resolved: retain exception and classified ADRs |
| Release history | `pyproject.toml` version only; Git has no tags | Changelog if released versions exist | No target until a release exists | No release evidence | Resolved: `0.1.0` is not a proven release |

## Ownership constraints for migration

- The architecture overview may summarize exact rules but must link to the
  corresponding specification.
- `STATUS.md` may report implementation gaps but must not redefine the accepted
  contracts.
- `ROADMAP.md` may own phase outcomes and commitments but must not import exact
  deferred designs from `tbd/future/`.
- Root `SECURITY.md` should remain the vulnerability-reporting entry point;
  security architecture belongs under `docs/02-architecture/`.
- Root `AGENTS.md` should route agents and preserve safety rules, not remain a
  parallel architecture source.
- Local ignored records must never become canonical merely because the migration
  found useful evidence in them.
