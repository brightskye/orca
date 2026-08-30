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

The PDS-0.2 Core-profile migration is complete and was committed on 2026-08-30
as `e686092`. The control plane, foundation, architecture, specifications,
decisions, plan, quality, limited operations, and archive boundaries are
accepted. [RFC-0001](05-proposals/0001-strengthen-run-manifest-provenance.md)
was accepted and promoted on 2026-08-30.
[RFC-0002](05-proposals/0002-define-project-registration-and-relinking.md)
was accepted and promoted on 2026-08-30. Every Phase 1 documentation subject has one registered
current owner.
[RFC-0003](05-proposals/0003-define-human-attention-and-common-use-gate.md)
was accepted and promoted on 2026-08-30.

## Capability status

| Capability | Status | Evidence or limitation |
|---|---|---|
| Owner-turn Codex normalization and credential-pattern redaction | Implemented | `conversation.py`, `privacy.py`, and focused capture tests |
| Visible assistant-response normalization | Diverged | Accepted design requires supported visible/final assistant context; current normalizer accepts Owner messages only |
| Continuation Summary semantic proposal and validation | Partial | One replaceable provider call and one controlled output are implemented |
| Run Manifest, scan-based replay detection, checkpoint-last publication, `no_memory`, and source-revision handling | Diverged | Initial `0.1` slice works; accepted `0.2` source/operation/output joins, segment cursor, and publication intent are not implemented |
| AgentCairn prevalidated Distiller seam | Partial | Adapter and focused tests exist; it is not wired into the Processor |
| Typed Memory Records, Project Summary, project registration/relink, and Knowledge Candidates | Planned | Accepted Phase 1 design; no active implementation |
| Interaction observations, profiles, and compiled guidance | Planned | Accepted contracts exist; no active implementation |
| Recall, MCP surface, skills, and retrieval projections | Planned | Accepted design; no active implementation |
| Lifecycle hooks, queue, retry spool, catch-up scheduling, and `$orca-save` | Planned | No active runtime wiring |
| Orca Status, Attention Items, and session reminder | Planned | Accepted content-free local interface; no active implementation |
| Host configuration loading and WSL deployment | Planned | Accepted safe configuration examples exist; loader and deployed runtime do not |
| Canonical automatic apply | Deliberately absent | Disabled and unexposed by Phase 1 governance |

## Known divergence

- Partial trailing JSONL currently raises an error instead of waiting for a
  later run.
- Replay checkpoint repair does not retain an available Manifest locator.
- Processor context budgets, chunking, overlap, related-record selection, and
  the full proposal set are designed but not implemented.
- Storage still writes `orca-run-manifest/0.1` and `orca-checkpoint/0.1`; it has
  no accepted `0.2` segment/operation/output joins or publication-intent
  recovery.
- Runtime hooks, secure retry handling, retrieval reconciliation, interaction
  consolidation, and routine deployment are designed but not implemented.
- CI still omits the Step 3 pipeline suite. AGENTS now uses the accepted
  canonical three-module command, so C-009 remains a CI-route divergence rather
  than an agent-verification ambiguity.

These are implementation gaps, not permission to weaken the accepted contracts.

## Active work

- Design hardening: RFC-0001, RFC-0002, and RFC-0003 are accepted and promoted.
  The four post-migration design-hardening steps are complete.
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
planned. RFC-0001 resolved the Manifest, checkpoint, provenance-join, and
interrupted-publication design. Their accepted `0.2` implementation remains
planned for Milestones 2 and 3. RFC-0002 resolved Project Registration, Project
Relink, exact-worktree reuse, and mapping-intent recovery; their implementation
also remains planned.

RFC-0003 resolved human-attention visibility and readiness measurement: one
content-free reminder per session for any unresolved item, a minimum 100-case
common-use corpus, 95% overall, 90% per category, zero critical failures, and a
separate mandatory edge-safety set. Implementation remains planned.

Routine Phase 1 use remains blocked by the planned runtime, retrieval,
interaction, configuration, deployment, and readiness work listed above.

## Verification

- Repository and documentation review date: 2026-08-30.
- Code was compared with the active contracts during the PDS audit.
- The complete current three-module regression command passed 12 tests on
  2026-08-30; it is not Phase 1 end-to-end acceptance.
- Historical migration evidence remains in the non-authoritative
  [migration working set](_working/pds-migration/README.md).

## Related documents

- **Documentation map:** [Documentation Index](README.md)
- **Roadmap phase:** [Phase 1](ROADMAP.md#phase-1)
- **Required behavior:** [Requirements](01-foundation/requirements.md)
- **Current design:** [Architecture Overview](02-architecture/overview.md)
- **Acceptance:** [Acceptance Plan](07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](07-quality/test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](08-operations/runbook.md)
