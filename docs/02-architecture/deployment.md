---
id: ARCH-DEPLOYMENT
title: Orca Deployment Architecture
document_type: architecture
status: accepted
authority: normative
implementation_status: planned
applies_to:
  - phase-1
  - phase-2-candidate
  - phase-3-candidate
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-29
related:
  - ARCH-OVERVIEW
  - PROJECT-ROADMAP
---

# Orca deployment architecture

## Purpose

This document defines the proposed Phase 1 deployment boundary and clearly
labels candidate later-phase topology without accepting its exact design.

## This document owns

- Host, checkout, runtime, vault, and network deployment boundaries.
- High-level current and candidate topology views.

## This document does not own

- Installation commands, exact runtime behavior, or roadmap commitment.

## Phase 1 intended topology

```text
Windows host
  Codex Desktop
      |
      | local invocation / private transport
      v
  WSL runtime
      |-- Orca project checkout
      |-- local configuration and .runtime state
      `-- configured Orca vault
```

Phase 1 uses one Codex Desktop agent, one authorized WSL processor runtime, and
one local vault. The active code exists, but this topology is not yet deployed
for routine use.

## Location boundaries

| Location | Owns | Publication/synchronization rule |
|---|---|---|
| Project checkout | Source, tests, public technical documentation, example configuration | May be tracked and published; contains no private vault data or host secrets |
| Configured Orca vault | Canonical Memory and permitted noncanonical memory artifacts | Local in Phase 1; not part of the project checkout |
| Local `config/host.yaml` or environment | Vault/runtime/source paths and host mappings | Ignored, machine-specific, never synchronized |
| Local `.runtime/` | Locks, queues, retry spools, receipts, checkpoints, and disposable indexes | Ignored, private, local-only, rebuildable where specified |
| Codex rollout store | Agent-owned source conversation history | Read through the Connector; never copied into a second raw Orca archive |

## Configuration boundary

The vault path comes from local `config/host.yaml` or `ORCA_VAULT_PATH`; tracked
source must not hard-code a personal path. Configuration validation is local and
deterministic. Credentials, private memory, absolute host mappings, and generated
dependency caches remain outside Git.

Exact host and vault fields, conflict-on-difference precedence, and safe
fixtures are defined by the
[Configuration Specification](../03-specifications/configuration.md).
The separation between project checkout and configured vault is recorded by
[ADR-0004](../04-decisions/0004-separate-project-workspace-from-vault.md).

## Network and service boundary

Phase 1 exposes no public memory, administrative, curation, ingestion,
scheduling, or canonical-apply service. MCP uses local stdio or another
explicitly authenticated private transport. External semantic-provider use, when
configured, crosses a trust boundary only after local privacy and redaction.

## Candidate Phase 2 topology

**Status:** candidate

Multiple local agents would share one local vault and processor boundary. Phase
2 depends on accepted agent identity, visibility, connector, and coordinated
write decisions. No exact Phase 2 deployment design is current.

## Candidate Phase 3 topology

**Status:** candidate

Local and remote agents would use local and VPS runtimes with synchronized vault
replicas. Only completed permitted vault artifacts would be eligible to
synchronize; credentials, host configuration, checkpoints, locks, indexes,
queues, and retry spools would remain local. Host authorization, conflict
containment, recovery, and security require accepted proposals before Phase 3
can be committed.

Synchronization would be transport, not authority or semantic merge.

## Deployment risks

- WSL/Windows path identity and permissions may differ from repository assumptions.
- A vault accidentally placed inside the checkout could publish private memory.
- A public or weakly authenticated transport could expose personal context or
  administrative actions.
- Later replicas could synchronize partial or conflicting state if publication
  and host-local boundaries are not enforced.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Roadmap:** [Roadmap](../ROADMAP.md)
- **Security boundary:** [Security and Trust](security-and-trust.md)
- **Current state:** [Current Status](../STATUS.md)
