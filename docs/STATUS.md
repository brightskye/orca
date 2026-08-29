---
id: PROJECT-STATUS
title: Orca Current Status
document_type: project-status
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-30
---

# Orca current status

## Purpose

This document reports what Orca currently implements and where implementation
diverges from accepted Phase 1 design.

## This document owns

- The current project and implementation snapshot.
- Known design-to-implementation divergence and current blockers.

## This document does not own

- Requirements, exact behavior, architecture, or future direction.

## Current phase

[Phase 1](ROADMAP.md#phase-1) is active. Orca has an initial local
capture/processing/storage slice but is not deployed for routine use. Canonical
automatic apply is disabled and absent.

The PDS migration has begun. The control plane, Core foundation, architecture,
specification, and decision packages are accepted. The proposals package is
established with no active or accepted RFC. The Phase 1 implementation plan is
accepted; quality, operations, and archive milestones remain incomplete.

The Owner accepted the direct Memory Model, Provenance Ledger, Interaction
Preferences, and Interaction Guidance migrations on 2026-08-29. Their
root-level contracts remain as compatibility mirrors. The Owner also accepted
the extracted Capture, Processing, and Retrieval specifications. The Owner
accepted Knowledge Candidates and Configuration on 2026-08-30. Every Phase 1
subject in the Specification Index now has a normative owner.

## Capability status

| Capability | Status | Evidence or limitation |
|---|---|---|
| Owner-turn Codex normalization and credential-pattern redaction | Implemented | `conversation.py`, `privacy.py`, and focused capture tests |
| Visible assistant-response normalization | Diverged | Accepted design requires supported visible/final assistant context; current normalizer accepts Owner messages only |
| Continuation Summary semantic proposal and validation | Partial | One replaceable provider call and one controlled output are implemented |
| Run Manifest, scan-based replay detection, checkpoint-last publication, `no_memory`, and source-revision handling | Partial | Implemented for the initial Continuation Summary slice |
| AgentCairn prevalidated Distiller seam | Partial | Adapter and focused tests exist; it is not wired into the Processor |
| Typed Memory Records, Project Summary, project registry, and Knowledge Candidates | Planned | Accepted Phase 1 design; no active implementation |
| Interaction observations, profiles, and compiled guidance | Planned | Accepted contracts exist; no active implementation |
| Recall, MCP surface, skills, and retrieval projections | Planned | Accepted design; no active implementation |
| Lifecycle hooks, queue, retry spool, catch-up scheduling, and `$orca-save` | Planned | No active runtime wiring |
| Host configuration loading and WSL deployment | Planned | Accepted safe configuration examples exist; loader and deployed runtime do not |
| Canonical automatic apply | Deliberately absent | Disabled and unexposed by Phase 1 governance |

## Known divergence

- Partial trailing JSONL currently raises an error instead of waiting for a
  later run.
- Replay checkpoint repair does not retain an available Manifest locator.
- Processor context budgets, chunking, overlap, related-record selection, and
  the full proposal set are designed but not implemented.
- Runtime hooks, secure retry handling, retrieval reconciliation, interaction
  consolidation, and routine deployment are designed but not implemented.
- CI still omits the Step 3 pipeline suite. AGENTS now uses the accepted
  canonical three-module command, so C-009 remains a CI-route divergence rather
  than an agent-verification ambiguity.

These are implementation gaps, not permission to weaken the accepted contracts.

## Active work

- Documentation migration: the control, foundation, architecture,
  specification, decision, plan, quality, and limited-operations packages are
  accepted. Root routing is current, and superseded sources are preserved in
  the [Documentation Archive](_archive/README.md). The runbook records that no
  supported runtime operator interface exists yet.
- Phase 1 implementation: the next bounded slice is permitted assistant-context
  normalization, followed by Typed Memory Record add/support/update behavior and
  Project Summary refresh through Storage.

The accepted plan owns Phase 1 implementation sequence and milestone progress;
this document continues to own the verified current-state snapshot.

## Open decisions and blockers

Architecture, specification, and ADR extraction are accepted. ADR-0001 remains
superseded history; ADR-0002 and ADR-0003 remain future-only proposal evidence;
ADR-0004 through ADR-0012 are accepted current rationale. Knowledge Candidate
and Configuration design choices are no longer open; implementation remains
planned.

Routine Phase 1 use remains blocked by the planned runtime, retrieval,
interaction, configuration, deployment, and readiness work listed above.

## Verification

- Repository and documentation review date: 2026-08-30.
- Code was compared with the active contracts during the PDS audit.
- The complete current three-module regression command passed 12 tests on
  2026-08-30; it is not Phase 1 end-to-end acceptance.
- Focused suite results for this migration milestone are recorded in the
  [migration working set](_working/pds-migration/README.md).

## Related documents

- **Documentation map:** [Documentation Index](README.md)
- **Roadmap phase:** [Phase 1](ROADMAP.md#phase-1)
- **Required behavior:** [Requirements](01-foundation/requirements.md)
- **Current design:** [Architecture Overview](02-architecture/overview.md)
- **Acceptance:** [Acceptance Plan](07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](07-quality/test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](08-operations/runbook.md)
