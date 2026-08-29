---
id: DOCS-INDEX
title: Orca Documentation Index
document_type: documentation-index
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - all-phases
owners:
  - project-owner
last_reviewed: 2026-08-30
documentation_standard: PDS-0.2
documentation_profile: core
---

# Orca documentation index

## Purpose

This document is the registry, authority map, and reading router for Orca's
project documentation.

## This document owns

- Documentation navigation and reading routes.
- The canonical owner for each major subject.
- The adopted PDS version, profile, and project-specific exceptions.

## This document does not own

- System behavior or implementation status.
- Project direction, requirements, or architectural decisions.

## Start here

1. Read the root [README](../README.md) for orientation.
2. Read [Current Status](STATUS.md) for what exists now.
3. Read the [Roadmap](ROADMAP.md) when phase scope or future direction matters.
4. Read the [Project Charter](01-foundation/project-charter.md) for stable scope
   and goals.
5. Follow the task route below rather than loading every document.

## Canonical ownership

| Subject | Canonical owner |
|---|---|
| Documentation routes and authority map | This document |
| Current implementation state and divergence | [Current Status](STATUS.md) |
| Phase direction and future outcomes | [Roadmap](ROADMAP.md) |
| Project purpose, scope, and constraints | [Project Charter](01-foundation/project-charter.md) |
| Project requirements | [Requirements](01-foundation/requirements.md) |
| Domain terminology | [Glossary](01-foundation/glossary.md) |
| Current system boundaries and component responsibilities | [Architecture Overview](02-architecture/overview.md) |
| Current Phase 1 architecture | [Architecture Overview](02-architecture/overview.md) |
| Current runtime and recovery design | [Runtime Architecture](02-architecture/runtime.md) |
| Deployment topology and location boundaries | [Deployment Architecture](02-architecture/deployment.md) |
| Data ownership, lifecycle, retention, and rebuildability | [Data Architecture](02-architecture/data-architecture.md) |
| Security and trust boundaries | [Security and Trust](02-architecture/security-and-trust.md) |
| Integration and replaceable-adapter boundaries | [Integration Architecture](02-architecture/integration-architecture.md) |
| Authority, privacy policy, and canonical behavior | [Memory System Contract](governance/memory-system-contract.md) |
| Capture eligibility, normalization, privacy handoff, and retry behavior | [Capture Pipeline](03-specifications/capture-pipeline.md) |
| Bounded semantic processing and proposal validation | [Processing Pipeline](03-specifications/processing-pipeline.md) |
| Memory records, summaries, conflicts, naming, and layout | [Memory Model](03-specifications/memory-model.md) |
| Ordinary Knowledge Candidate schema, placement, review, and retention | [Knowledge Candidates](03-specifications/knowledge-candidates.md) |
| Run Manifests, checkpoints, deduplication, and progress recovery | [Provenance Ledger](03-specifications/provenance-ledger.md) |
| Recall requests, projections, filtering, ranking, and result budgets | [Retrieval Contract](03-specifications/retrieval-contract.md) |
| Interaction observation and profile lifecycle | [Interaction Preferences](03-specifications/interaction-preferences.md) |
| Exact compiled presentation guidance | [Interaction Guidance](03-specifications/interaction-guidance.md) |
| Host and vault configuration fields, defaults, validation, and precedence | [Configuration](03-specifications/configuration.md) |
| Significant architectural rationale and ADR numbering | [Decision Registry](04-decisions/README.md) |
| Substantial unaccepted future changes and RFC lifecycle | [Proposal Registry](05-proposals/README.md) |
| Current implementation sequence and milestone progress | [Plan Registry](06-plans/README.md) |
| Phase 1 acceptance scenarios and phase gate | [Acceptance Plan](07-quality/acceptance.md) |
| Test levels, suites, fixtures, and evaluation boundaries | [Test Strategy](07-quality/test-strategy.md) |
| Vulnerability reporting | Root [Security Policy](../SECURITY.md) |
| PDS rules for this repository | Root [PDS v0.2](../PDS.md) |

The [Project Charter](01-foundation/project-charter.md),
[Requirements](01-foundation/requirements.md), and
[Glossary](01-foundation/glossary.md) were accepted on 2026-08-29 after parity
validation. The architecture package was accepted on 2026-08-29. Flat source
documents remain labelled migration sources for exact content not yet moved into
specifications or operations. This index must be updated as those remaining
ownership rows move.

## Task routes

### Understand the project

[Current Status](STATUS.md) → [Roadmap](ROADMAP.md) →
[Project Charter](01-foundation/project-charter.md) →
[Architecture Overview](02-architecture/overview.md)

### Implement or review Phase 1 behavior

[Requirements](01-foundation/requirements.md) →
[Architecture Overview](02-architecture/overview.md) → the owning specification
in the registry above → [Phase 1 Implementation Plan](06-plans/active/phase-1-implementation.md)
→ [Current Status](STATUS.md)

### Investigate a runtime failure

[Current Status](STATUS.md) → [Local Runbook](08-operations/runbook.md) →
[Provenance Ledger](03-specifications/provenance-ledger.md) → relevant code and tests

### Verify Phase 1 behavior or completion

[Acceptance Plan](07-quality/acceptance.md) →
[Test Strategy](07-quality/test-strategy.md) → owning specification → relevant
code, tests, and retained evidence

### Change memory authority, privacy, or canonical behavior

[Project Charter](01-foundation/project-charter.md) →
[Requirements](01-foundation/requirements.md) →
[Memory System Contract](governance/memory-system-contract.md) → affected exact
contract

### Change domain terminology

[Glossary](01-foundation/glossary.md) → affected requirements, architecture, and
specifications. The root `CONTEXT.md` is a retained migration source until the
glossary transition is accepted.

### Review future direction

[Roadmap](ROADMAP.md) → [Proposal Registry](05-proposals/README.md). Exact
later-phase snapshots under [`docs/_archive/legacy-design/`](_archive/README.md#legacy-all-phase-design)
are historical proposal inputs only and must not be treated as accepted design.

### Review architectural rationale

[Decision Registry](04-decisions/README.md) → the relevant accepted ADR.
A proposed ADR is review material and does not change accepted architecture or
specifications.

## Current document registry

| Document | Role | Authority |
|---|---|---|
| [Current Status](STATUS.md) | Current project and implementation state | Informative |
| [Roadmap](ROADMAP.md) | Phase direction and outcomes | Informative |
| [Project Charter](01-foundation/project-charter.md) | Stable purpose, scope, and constraints | Normative |
| [Requirements](01-foundation/requirements.md) | Externally meaningful obligations | Normative |
| [Glossary](01-foundation/glossary.md) | Canonical domain language | Normative |
| [Architecture Overview](02-architecture/overview.md) | Primary system-design entry point | Normative |
| [Runtime Architecture](02-architecture/runtime.md) | Runtime and recovery boundaries | Normative |
| [Deployment Architecture](02-architecture/deployment.md) | Deployment and topology boundaries | Normative |
| [Data Architecture](02-architecture/data-architecture.md) | Data ownership and lifecycle | Normative |
| [Security and Trust](02-architecture/security-and-trust.md) | Security boundaries and mitigations | Normative |
| [Integration Architecture](02-architecture/integration-architecture.md) | External and replaceable seams | Normative |
| [Specification Index](03-specifications/README.md) | Exact behavior registry and seam map | Informative |
| [Capture Pipeline](03-specifications/capture-pipeline.md) | Capture interface | Normative |
| [Processing Pipeline](03-specifications/processing-pipeline.md) | Processing interface | Normative |
| [Memory Model](03-specifications/memory-model.md) | Memory model specification | Normative |
| [Knowledge Candidates](03-specifications/knowledge-candidates.md) | Ordinary-candidate schema and lifecycle | Normative |
| [Provenance Ledger](03-specifications/provenance-ledger.md) | Provenance and checkpoint specification | Normative |
| [Retrieval Contract](03-specifications/retrieval-contract.md) | Recall and projection interface | Normative |
| [Interaction Preferences](03-specifications/interaction-preferences.md) | Preference evidence and lifecycle specification | Normative |
| [Interaction Guidance](03-specifications/interaction-guidance.md) | Guidance compilation specification | Normative |
| [Configuration](03-specifications/configuration.md) | Host and vault configuration interface | Normative |
| [Decision Registry](04-decisions/README.md) | ADR navigation, numbering, lifecycle, and applicability | Informative |
| [ADR-0004](04-decisions/0004-separate-project-workspace-from-vault.md) | Accepted checkout/vault separation rationale | Historical |
| [Proposal Registry](05-proposals/README.md) | RFC navigation, lifecycle, and noncurrent input boundary | Informative |
| [Plan Registry](06-plans/README.md) | Active/completed plan navigation and lifecycle | Informative |
| [Phase 1 Implementation Plan](06-plans/active/phase-1-implementation.md) | Accepted Phase 1 sequence and exit criteria | Informative |
| [Acceptance Plan](07-quality/acceptance.md) | Accepted Phase 1 scenarios and gate | Normative |
| [Test Strategy](07-quality/test-strategy.md) | Accepted test/evaluation mechanics and suite ownership | Normative |
| [Phase 1 Local Runbook](08-operations/runbook.md) | Accepted truthful local procedures and explicit operational gaps | Normative |
| [Memory System Contract](governance/memory-system-contract.md) | Governance contract | Normative |

Root `README.md`, `AGENTS.md`, `SECURITY.md`, and `PDS.md` are registered entry
points outside `docs/`.

## Non-authoritative material

- [`docs/_working/`](_working/README.md) contains temporary migration and review
  material. It cannot define accepted project truth.
- [`docs/_archive/`](_archive/README.md) is reserved for inactive historical
  documentation whose replacement parity and Owner-acceptance gates passed.
- [`legacy/`](../legacy/README.md) is excluded from normal reading routes and
  contains noncurrent implementation evidence only.
- `.agent-notes/`, `evidence/`, `index.md`, and `config/host.yaml` are ignored
  local records or configuration, not public project authority.

## Project-specific exceptions

`legacy/manual-prototype/` remains outside the PDS documentation tree because
PDS does not prescribe a location for historical source code and tests. The
package stays together so its schemas, fixtures, runtime rules, code-adjacent
contracts, and tests retain their original context. It is owned by the project
Owner and should be reviewed for removal only after verified Phase 1 cutover and
provenance preservation in Git history.

The root `PDS.md` is the repository's authoritative copy of PDS-0.2 and must be
included in the migration commit. A changelog is not required until an actual
release exists.

## Migration state

The control plane, foundation, architecture, specification, decision, quality,
and limited-operations packages are accepted. The proposal registry and
template are established; no RFC is active or accepted. The Phase 1
implementation plan is accepted. Root-agent routing and source archival are
complete. See the non-authoritative
[migration working set](_working/pds-migration/README.md) for execution
evidence.
