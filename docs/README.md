# Orca documentation

This is the detailed project map for Orca's PLS 0.3 layout. Start at the root
[`README.md`](../README.md) for project orientation and use the routes below to
load only the material needed for a task.

## Project map

| Question | Owner |
|---|---|
| Why does Orca exist and what is in scope? | [Project details](project.md) |
| What happened, what is true now, and what comes next? | [Project Record](project-record/README.md) |
| How is the solution organized? | [Architecture](architecture/README.md) |
| Exactly how must Orca behave? | [Specifications](specifications/README.md) |
| How is Orca verified? | [Quality](quality/README.md) |
| How is Orca installed, run, diagnosed, and recovered? | [Operations](operations/README.md) |
| What inactive documentation is retained? | [Archive](archive/README.md) |

## Subject owners

| Subject | Owner |
|---|---|
| Current implementation and known divergence | [Current](project-record/current.md) |
| Phase direction and exit criteria | [Roadmap](project-record/roadmap.md) |
| Decisions and rationale | [Decisions](project-record/decisions/README.md) |
| Unaccepted substantial changes | [Proposals](project-record/proposals/README.md) |
| Execution plans | [Plans](project-record/plans/README.md) |
| Domain language and module boundaries | [Glossary](specifications/glossary.md) |
| Authority, privacy, capture, recall, and canonical behavior | [Memory system contract](specifications/memory-system-contract.md) |
| Capture and privacy handoff | [Capture](specifications/capture.md) |
| Bounded semantic processing | [Processing](specifications/processing.md) |
| Memory kinds, records, filenames, and lifecycle | [Memory](specifications/memory.md) |
| Knowledge Candidates | [Knowledge Candidates](specifications/knowledge-candidates.md) |
| Provenance, manifests, checkpoints, and replay | [Provenance](specifications/provenance.md) |
| Recall and retrieval projections | [Retrieval](specifications/retrieval.md) |
| Interaction evidence and profiles | [Interaction Preferences](specifications/interaction-preferences.md) |
| Compiled presentation guidance | [Interaction Guidance](specifications/interaction-guidance.md) |
| Host and vault configuration | [Configuration](specifications/configuration.md) |
| Lifecycle coordination, worker, catch-up, attention, and reminders | [Runtime](specifications/runtime.md) |
| Backup membership, verification, and staging | [Backup](specifications/backup.md) |
| Phase 1 acceptance | [Acceptance](quality/acceptance.md) |
| Test and evaluation mechanics | [Test Strategy](quality/test-strategy.md) |
| Post-install operation and recovery | [Runbook](operations/runbook.md) |
| Installation, hook setup, and first controlled test | [Set up Orca](operations/setup.md) |

## Reading routes

- To implement or review behavior: [Project details](project.md) →
  [Architecture](architecture/README.md) → the owning
  [Specification](specifications/README.md) → relevant code and tests →
  [Current](project-record/current.md).
- To investigate an operational failure: [Current](project-record/current.md) →
  [Operations](operations/README.md) → [Runbook](operations/runbook.md) → the
  owning specification and tests.
- To verify a completion claim: [Acceptance](quality/acceptance.md) →
  [Test Strategy](quality/test-strategy.md) → relevant tests →
  [Current](project-record/current.md).
- To change future direction: [Roadmap](project-record/roadmap.md) →
  [Proposals](project-record/proposals/README.md) →
  [Decisions](project-record/decisions/README.md) when a choice is accepted.

## Noncurrent and local material

Historical documents live under [`archive/`](archive/README.md); historical
implementation lives under [`legacy/`](../legacy/README.md). Neither is part of
normal reading unless a task concerns history or migration.

Private historical evidence and the former local index live under the ignored
`.local/` area. Temporary agent conversation notes live under ignored
`.local/agent-note/` and use `pending`, `reviewed`, and short-lived `retired`
states. They are non-authoritative context: durable outcomes belong in the
Project Record or the document that owns the subject. Machine configuration
remains in ignored `config/host.yaml`, and runtime state remains in ignored
`.runtime/`. These locations are not public project authority.
