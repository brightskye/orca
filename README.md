---
type: Project
title: Orca Agent Memory System
status: active
updated: 2026-09-05
tags:
  - project
  - orca
  - agent-memory
---

# Orca Agent Memory System

Project layout standard: PLS 0.3 (working model)

## Start here

- [Project record](docs/project-record/README.md)
- [Documentation map](docs/README.md)
- [Current state](docs/project-record/current.md)
- [Roadmap](docs/project-record/roadmap.md)
- [Architecture](docs/architecture/README.md)
- [Security policy](SECURITY.md)

## Purpose

Orca connects two functions: an LLM wiki that serves as the Owner's durable
knowledge and second brain, and agent memory that preserves conversation
continuity. This repository implements the agent-memory workstream. Phase 1
helps the Owner resume discussions and work across Codex sessions using
distilled conversation history stored in a designated area of the Orca vault.
The wiki's broader rules and knowledge-distillation workflows will be reviewed
separately. Conversation memory remains distinct from accepted wiki knowledge.

This repository contains the active Phase 1 implementation and its supporting
project material. Private memory, machine runtime state, and development of the
PLS standard itself remain outside this repository.

## Current status

Phase 1 received Owner acceptance on 2026-08-31. A later readiness review
identified unresolved implementation and deployment findings; routine private
Codex capture remains disabled pending their disposition. Automatic canonical
apply is absent. [Current](docs/project-record/current.md) owns the capability,
verification, and readiness snapshot.

Phase 2 and Phase 3 are candidate directions, not accepted exact designs. The
[Roadmap](docs/project-record/roadmap.md) owns their status and intended outcomes.

## Design orientation

The accepted Phase 1 design reads permitted agent-owned history without creating
a second raw transcript, derives visibly noncanonical memory through deterministic
validation boundaries, and returns bounded authority-labelled context through
Owner-requested or agent-initiated scoped recall. Exact behavior belongs to the [requirements](docs/specifications/requirements.md),
[architecture](docs/architecture/README.md), and
[specifications](docs/specifications/README.md).

AgentCairn is the selected initial replaceable retrieval component; it does not
own Orca authority, scope, artifact semantics, privacy, or canonical behavior.
See [ADR-0012](docs/project-record/decisions/0012-use-agentcairn-behind-retrieval-interface.md)
and [Integration Architecture](docs/architecture/integrations.md).

## Use and installation

Follow [Set up Orca](docs/operations/setup.md) for installation, configuration,
lifecycle activation, and first-canary procedures. After deployment, use the
[Runbook](docs/operations/runbook.md) for health, status, Recall, rebuild,
disablement, troubleshooting, and recovery boundaries.

The Phase 1 runtime uses local one-shot workers rather than a daemon. Automatic
Codex lifecycle handling is controlled by the vault's `lifecycle.enabled`
boolean and always applies local eligibility filtering and Secret Containment
before provider input. Canonical automatic apply remains unavailable.

## Project map

| Question | Location |
|---|---|
| What happened, what is true now, and what comes next? | [Project Record](docs/project-record/README.md) |
| Where are documentation routes and subject owners? | [Documentation map](docs/README.md) |
| Where is the installed Orca product implemented? | `src/orca_memory/` |
| Where are repeatable checks? | `tests/` |
| Where are maintained evaluation cases and runners? | `tests/evals/` |
| Where are safe configuration examples? | `config/`; machine-local values use ignored `config/host.yaml` |
| How is Orca installed and operated? | [Operations](docs/operations/README.md) and [Runbook](docs/operations/runbook.md) |
| What inactive implementation is retained? | `legacy/manual-prototype/` |
| Where is private local verification history retained? | Ignored `.local/` |
| Where are temporary agent conversation notes kept? | Ignored `.local/agent-note/`; durable outcomes belong in the [Project Record](docs/project-record/README.md) or the owning document |
| Where is the former layout standard preserved? | Historical [PDS 0.2 baseline](docs/archive/standards/PDS-0.2.md) |

The project checkout and configured vault remain separate. Local configuration,
runtime state, credentials, private memory, and `.local/` remain outside the
public repository.

## Source boundary

Only code delivered as the supported Orca library, command-line interface,
hooks, or runtime integrations belongs under `src/orca_memory/`. Repeatable
tests and evaluation-only runners belong under `tests/`; maintained development
automation belongs under `tools/`; temporary local helpers and output remain
outside Git. A supported optional integration remains product source even when
it is loaded by an integrator rather than Orca's default command-line path.
