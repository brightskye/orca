---
type: system
status: accepted-baseline
created: 2026-08-25
updated: 2026-08-25
tags:
  - orca
  - agent-memory
  - architecture
---

# Orca Memory System

> [!WARNING]
> Archived all-phase overview. Current project truth is routed through the
> [Documentation Index](../../README.md).

This directory is the design and operating-document home of the accepted Orca
Memory architecture baseline. It belongs to the standalone project at
`/workspace/projects/orca`, not to the Orca vault. The baseline is approved for
design and implementation planning; it is not evidence that the new service
has been deployed or that the transitional workflow has been disabled.

## Authority

The system data tree inside the configured vault has explicit authority by
kind. It is local in Phases 1 and 2 and synchronized in Phase 3:

- Project `docs/governance/` defines the accepted target contract and semantic policy.
- Conversation records are transient evidence.
- Shallow memory is provisional and time-limited.
- Interaction profiles are derived and rebuildable.
- Curator artifacts are proposals, plans, and dispositions.
- Manifests are operational lineage.

None of these become canonical merely because they are synchronized. Canonical memory remains in `Daily/`, `Projects/`, `Knowledge/`, `People/`, and `System/Assistant/`.

## Read next

- [Architecture](architecture.md) — target structure, flows, deployment topology, and module seams.
- [Delivery plan](delivery-plan.md) — the three phase scopes, architectures,
  operating flows, exclusions, and completion criteria.
- [Memory system contract](memory-system-contract.md) — invariants, authority, lifecycle, and fail-closed rules.
- [Operations](operations.md) — configuration, installation, scheduling, cutover, recovery, and deferred canaries.
- [Prototype migration notes](../legacy-docs/prototype-migration-notes.md) — structural mapping and source-provenance cautions.
- [Domain language](CONTEXT-all-phases.md) — all-phase vocabulary retained for later work.

## Status boundary

The current manual prototype remains under `prototype/` until a separately verified cutover. Private operational evidence remains local under `evidence/`; superseded phase records are outside the implementation workspace.

The system data directories and `orca-memory.yaml` described by the baseline
are created by implementation and deployment work, not by this documentation
pass. They remain local in Phases 1 and 2 and become synchronized only in Phase
3.
