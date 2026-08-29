---
id: WORK-2026-08-29-PDS-SYSTEM-DESIGN
title: PDS Audit System-Design Map
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# System-design map

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

## Coverage map

| System-design concern | Existing locations | Current quality | Gap/duplication | PDS destination |
|---|---|---|---|---|
| Problem and project purpose | `README.md#Goal`; `docs/system-design.md#Purpose`; `CONTEXT.md` intro | Clear and consistent | Duplicated; no charter owner | Project charter; overview summarizes |
| Goals and non-goals | `docs/system-design.md#Design-goals`, `#Non-goals`; architecture non-goals; README philosophy | Strong | Goals, requirements, and phase exclusions are mixed | Project charter; requirements; roadmap |
| Requirements | README Phase 1 scope; governance invariants; architecture completion criteria | Substantive but unindexed | No stable requirement IDs; exact contracts and acceptance are intermixed | Requirements document linked to specs/tests |
| System boundaries | System design context; architecture system shape; README architecture | Strong | Repeated in three files | Architecture overview |
| Major components | System design module responsibilities; architecture modules | Strong | Two competing levels with repeated exact rules | Overview owns components; specs own exact behavior |
| Component responsibilities | System design seam/table and module sections; architecture module list | Very strong | Some claims overstate implementation | Overview plus status; implementation status explicit |
| Dependencies | AgentCairn sections; `pyproject.toml`; Codex/WSL/MCP references | Partial | No single integration map; external semantic provider is abstract | Integration architecture; ADRs; configuration spec |
| Runtime flows | Operations normal flow; system design normal flow; architecture system shape | Detailed | Three copies; intended behavior mixed with executable procedures | Runtime architecture; runbook links it |
| Data ownership | System design artifact table/data locations; governance authority; architecture storage | Strong | Repeated exact trees and authority lists | Data architecture; overview summary |
| Data lifecycle | Governance capture/processing; memory-record lifecycle; run manifest; operations | Strong for intended Phase 1 | Spread across four contracts; ordinary candidates incomplete | Data architecture plus capability specs |
| Provenance | Run manifest contract; memory record provenance boundary; governance | Strong | No machine schema/traceability owner | Provenance-ledger specification; data architecture summary |
| Raw evidence retention | Active direct-source/transient rule; deferred immutable-evidence rules; local evidence policy | Current active rule is clear; historical conflict preserved | Deferred accepted labels obscure supersession | Capture spec + data/security architecture; ADR rationale |
| Security and trust boundaries | `SECURITY.md`; governance; architecture; operations | Strong intent, partial implementation | No consolidated threat/trust document or residual-risk register | Security-and-trust architecture |
| Detailed data formats | Memory, run, interaction contracts; host example; legacy JSON schemas | Strong prose for active formats | Active JSON/YAML formats lack machine schemas; candidate/config gaps | Specifications plus conditional machine schemas |
| Workflow behavior | Governance, operations, memory/interaction contracts | Very detailed | Mixed across runbook, architecture, and specs | Capture, processing, recall, interaction specs |
| Failure behavior | Operations failure/recovery; governance; run contract; code/tests | Strong intent; one known parser divergence | Duplicated and not traceable to tests | Runtime architecture summary; exact specs; runbook procedures |
| Idempotency | Run contract; storage code/tests; governance | Strong and partly verified | Replay checkpoint locator divergence | Provenance-ledger spec + acceptance criterion |
| Retrieval behavior | Governance Recall; system design Recall; operations; architecture | Detailed design | No implementation; deferred ordering conflicts | Retrieval specification; status marks planned |
| Technical decisions and rationale | System design key decisions; AgentCairn rationale; deferred ADRs; research | Valuable | No active ADR registry; statuses ambiguous | ADR package preserving existing numbering/history |
| Quality and acceptance | Architecture completion; operations readiness; tests/CI; local evidence reports | Broad list and narrow direct tests | No IDs, traceability, or strategy; commands inconsistent | Acceptance and test-strategy documents |
| Installation and operations | Operations; README; tbd legacy command | Mostly intended model | No verified Phase 1 install/start/health commands | Runbook; deployment architecture; status |
| Future phases | README, system design topology, `tbd/future/` | Extensive | Roadmap, proposal, design, plan, and status are mixed | Roadmap plus proposals; later plans only when active |

## Proposed PDS system-design package

```text
Project Charter
  purpose, Owner, goals, non-goals, scope, constraints

Requirements
  stable Phase 1 obligations and quality/security/operational requirements

Architecture Overview (primary entry point)
  boundaries, components, responsibilities, architecture principles,
  high-level data and runtime flows, detailed-design routes
  ├── Runtime Architecture
  ├── Deployment Architecture
  ├── Data Architecture
  ├── Security and Trust
  └── Integration Architecture

Specifications
  ├── Capture Pipeline
  ├── Processing Pipeline
  ├── Memory Model
  ├── Knowledge Candidates
  ├── Provenance Ledger
  ├── Retrieval Contract
  ├── Interaction Preferences
  ├── Interaction Guidance
  └── Configuration

ADRs
  accepted rationale, including current/deferred applicability

Quality
  requirements/specification-to-test acceptance map and test strategy

Operations
  verified install/configure/run/recover procedures only
```

## Gaps that migration must expose, not fill

- No explicit accepted requirements set or stable requirement identifiers.
- No status document reconciling every designed capability with code/tests.
- No current ADR package for most significant design choices.
- No ordinary Knowledge Candidate contract.
- No active machine-readable schemas for Run Manifest, checkpoint, memory,
  interaction observations/profiles, or configuration.
- No threat model or residual-risk register beyond distributed security prose.
- No verified install/start/stop/health-check path for the Phase 1 runtime.
- No traceability from roadmap exit criteria through requirements,
  specifications, tests, and evidence.
- No documentation validator or link/metadata checks.
- No commitment classification for Phase 2 or Phase 3.

## Duplication to remove during migration

- Phase tables in README, system design, architecture, and future delivery plan.
- Artifact authority tables/lists in system design, governance, architecture,
  and operations.
- Module responsibilities in system design and architecture.
- The normal operating flow in system design and operations.
- Memory conflict and record lifecycle rules in three active documents.
- Recall budgets and ordering in architecture, governance, operations, system
  design, and research.
- Interaction lifecycle rules in system design, governance, and the interaction
  contract.
- Completion/readiness criteria in architecture and operations.

The later migration should replace these copies with short summaries and
semantic links. It should not remove a source until unique-information and
conflict checks pass.
