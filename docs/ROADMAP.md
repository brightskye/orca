---
id: PROJECT-ROADMAP
title: Orca Roadmap
document_type: roadmap
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - all-phases
owners:
  - project-owner
last_reviewed: 2026-08-30
---

# Orca roadmap

## Purpose

This document owns Orca's phase direction, broad sequencing, intended outcomes,
dependencies, and exit criteria.

## This document owns

- The status and intended outcome of each delivery phase.
- Dependencies between phases and deliberately deferred capabilities.

## This document does not own

- Exact system behavior, implementation tasks, or current progress.
- Exact future architecture that has not been accepted.

## Phase 1

**Status:** active

**Outcome:** Codex Desktop uses one WSL runtime and one local Orca vault for a
complete governed memory loop: bounded capture and processing, provisional
memory and candidates, scoped interaction guidance, explicit recall, durable
provenance, and no automatic canonical mutation.

**Dependencies:** a supported Codex source, local configuration, a configured
vault, one authorized local processor, and a replaceable local retrieval
backend.

**Exit criteria:**

- Supported Owner and assistant context is selected with exact provenance and
  privacy exclusions.
- Processing is bounded, retry-safe, deduplicated through durable manifests, and
  advances checkpoints last.
- Phase 1 memory, candidate, interaction, and recall contracts are implemented
  through deterministic validation boundaries.
- Restart, replay, index rebuild, conflict, privacy, and secret-containment cases
  pass the accepted quality gates.
- Codex Desktop can run the local loop against the configured vault without
  exposing a public service or mutating Canonical Memory automatically.

Current progress belongs in [Current Status](STATUS.md), not this roadmap.
The accepted execution sequence is in the [Phase 1 Implementation
Plan](06-plans/active/phase-1-implementation.md).
The accepted evidence mapping is in the [Phase 1 Acceptance
Plan](07-quality/acceptance.md); it does not establish that any exit criterion
currently passes.

## Phase 2

**Status:** candidate

**Outcome:** Multiple local agents share one local vault with explicit agent
identity, private/shared visibility, and coordinated local writes while reusing
the complete Phase 1 authority and artifact model.

**Dependencies:** Phase 1 exit criteria; accepted agent identity, visibility,
connector, and write-coordination decisions.

**Exit criteria:** An Owner-approved Phase 2 proposal and acceptance plan define
and verify safe multi-agent local operation without weakening Phase 1 authority,
privacy, provenance, or canonical boundaries.

No exact Phase 2 design is accepted by this roadmap.

## Phase 3

**Status:** candidate

**Outcome:** Local and remote agents use synchronized local and VPS vault
replicas while host authorization and conflict containment preserve Orca's
authority model.

**Dependencies:** Phase 2 exit criteria; accepted synchronization, host
authorization, security, consistency, recovery, and operational proposals.

**Exit criteria:** An Owner-approved Phase 3 proposal and acceptance plan verify
that completed permitted vault artifacts synchronize safely while credentials,
indexes, locks, checkpoints, configuration, and other host-local state remain
local.

No exact Phase 3 deployment or synchronization design is accepted by this
roadmap.

## Intentionally deferred

- Automatic or agent-initiated canonical apply. It requires a separate governed
  decision and is not part of Phases 1–3.
- Automated retention beyond the narrow accepted Phase 1 recovery rules.
- General document ingestion, public administration interfaces, and a general
  semantic relationship graph.
- Dashboards and scheduled memory-health reporting beyond what is required for
  safe operation.

## Related documents

- **Documentation map:** [Documentation Index](README.md)
- **Current implementation state:** [Current Status](STATUS.md)
- **Stable scope:** [Project Charter](01-foundation/project-charter.md)
- **Accepted obligations:** [Requirements](01-foundation/requirements.md)
- **Unaccepted substantial changes:** [Proposal Registry](05-proposals/README.md)
