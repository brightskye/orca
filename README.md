---
type: Project
title: Orca Agent Memory System
status: active
updated: 2026-08-30
tags:
  - project
  - orca
  - agent-memory
---

# Orca Agent Memory System

## Documentation

- [Documentation map](docs/README.md)
- [Current status](docs/STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture overview](docs/02-architecture/overview.md)
- [Security policy](SECURITY.md)

## Purpose

Orca is a governed, local-first memory system for AI agents. It preserves
durable knowledge in the Owner's configured vault, keeps provisional memory
separate from accepted knowledge, and gives authorized agents bounded recall
without making any agent or retrieval technology authoritative.

## Current status

Phase 1 is complete and was accepted by the Owner on 2026-08-31. The local
governed-memory loop, lifecycle hooks, explicit Recall, recovery, attention,
frozen quality gates, and operational canaries passed. Automatic canonical
apply remains disabled and absent. See [Current Status](docs/STATUS.md) for the
verified capability and limitation inventory.

Phase 2 and Phase 3 are candidate directions, not accepted exact designs. The
[Roadmap](docs/ROADMAP.md) owns their status and intended outcomes.

## Design orientation

The accepted Phase 1 design reads permitted agent-owned history without creating
a second raw transcript, derives visibly noncanonical memory through deterministic
validation boundaries, and returns bounded authority-labelled context only after
explicit recall. Exact behavior belongs to the [requirements](docs/01-foundation/requirements.md),
[architecture](docs/02-architecture/overview.md), and
[specifications](docs/03-specifications/README.md).

AgentCairn is the selected initial replaceable retrieval component; it does not
own Orca authority, scope, artifact semantics, privacy, or canonical behavior.
See [ADR-0012](docs/04-decisions/0012-use-agentcairn-behind-retrieval-interface.md)
and [Integration Architecture](docs/02-architecture/integration-architecture.md).

## Use and installation

There is no supported Phase 1 runtime installation, start, health, recall,
rebuild, or recovery command yet. The [Local
Runbook](docs/08-operations/runbook.md) records the one verified repository
regression procedure and explicitly labels unavailable operator interfaces.
Do not treat tests or documented design as deployed health.

## Where things live

- Current project documentation and navigation: `docs/`
- Active Phase 1 implementation: `src/orca_memory/`
- Active Phase 1 tests: `tests/`
- Retained manual prototype: `legacy/manual-prototype/`
- Local machine configuration: `config/host.yaml`
- Local verification evidence: `evidence/` (preserved locally, not published)
- PDS standard adopted by this repository: `PDS.md`

The project checkout and configured vault remain separate. Local configuration,
runtime state, credentials, private memory, `evidence/`, and `index.md` remain
outside the public repository.
