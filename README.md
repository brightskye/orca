---
type: Project
title: Orca Agent Memory System
status: active
updated: 2026-08-25
tags:
  - project
  - orca
  - agent-memory
---

# Orca Agent Memory System

## Goal

Orca is the durable shared second brain. Agents and Cairn are replaceable;
Orca owns the lasting rules, history, and governed knowledge.

## Architecture

```text
authorized connectors
  -> synchronized conversation evidence
  -> one authorized processor
  -> shallow memory + candidates + interaction observations
  -> Curator plan
  -> policy-gated canonical Orca
```

See [the system overview](docs/system-overview.md) for the accepted target
baseline. [The architecture](docs/architecture.md) distinguishes that target
from the current manual prototype. Superseded phase-era contracts and routing
records are retained privately outside the implementation workspace.

## Current status

- Cairn fit: `USE AS-IS`
- Provider-backed semantic path: `PASS`
- Controlled real-use canary: `PASS — SMALL SAMPLE`
- Structural architecture baseline: accepted 2026-08-25
- Replacement client/processor deployment: not implemented
- Canonical automatic apply: disabled
- Operating direction: implement structurally, cut over through shadow evidence,
  then operate and tune from real data

## Current philosophy

> Missing some useful memory is acceptable. Wrong durable memory is more serious.

> Use the system, preserve evidence, and improve recurring problems rather than trying to perfect semantics in advance.

## Where things live

- Accepted target architecture and governance: `docs/`
- Current manual prototype source: `prototype/`
- Local machine configuration: `config/host.yaml`
- Relevant tests and fixtures: `tests/`
- Local verification evidence: `evidence/` (preserved locally, not published)
- Superseded private history: `/workspace/projects/orca-private-history/`

The project workspace is `/workspace/projects/orca`. Its local configuration
points to the Orca vault; it is not part of the vault itself. Future
synchronized noncanonical memory-system data belongs under the configured
vault's `System/Orca Memory/`. Local `evidence/` and `index.md` records are
excluded from the public repository because they contain private operational
history and source material.
