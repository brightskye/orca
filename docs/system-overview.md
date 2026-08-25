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

This directory is the design and operating-document home of the accepted Orca Memory architecture baseline. It belongs to the standalone project at `/workspace/projects/orca`, not to the synchronized Orca vault. The baseline is approved for design and implementation planning; it is not evidence that the new service has been deployed or that the transitional workflow has been disabled.

## Authority

The future synchronized data tree inside the configured vault has explicit authority by kind:

- Project `docs/governance/` defines the accepted target contract and semantic policy.
- Conversation records are transient evidence.
- Shallow memory is provisional and time-limited.
- Interaction profiles are derived and rebuildable.
- Curator artifacts are proposals, plans, and dispositions.
- Manifests are operational lineage.

None of these become canonical merely because they are synchronized. Canonical memory remains in `Daily/`, `Projects/`, `Knowledge/`, `People/`, and `System/Assistant/`.

## Read next

- [Architecture](architecture.md) — target structure, flows, deployment topology, and module seams.
- [Memory system contract](governance/memory-system-contract.md) — invariants, authority, lifecycle, and fail-closed rules.
- [Operations](operations.md) — configuration, installation, scheduling, cutover, recovery, and deferred canaries.
- [Prototype migration notes](prototype-migration-notes.md) — structural mapping and source-provenance cautions.
- [Domain language](../CONTEXT.md) — canonical vocabulary for discussing and implementing the system.

## Status boundary

The current manual prototype remains under `prototype/` until a separately verified cutover. Private operational evidence remains local under `evidence/`; superseded phase records are outside the implementation workspace.

The synchronized data directories and `orca-memory.yaml` described by the baseline are created by implementation and deployment work, not by this documentation pass.
