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
| Owner and final-assistant Codex normalization, privacy filtering, partial-tail deferral, and credential-pattern redaction | Implemented | `conversation.py`, `privacy.py`, synthetic deterministic capture tests, and Processor evidence/context separation tests |
| Continuation Summary semantic proposal and validation | Partial | Replaceable provider call, bounded evidence/context handoff, and controlled summary publication are implemented; Milestone 3 budgets and chunking remain |
| Run Manifest, scan-based replay detection, checkpoint-last publication, `no_memory`, and source-revision handling | Partial | Unsegmented Manifest/checkpoint `0.2`, source/operation/output joins, mixed `0.1` reads, and publication-intent recovery are implemented; segmented cursors remain Milestone 3 work |
| AgentCairn prevalidated Distiller seam | Partial | Adapter and focused tests exist; it is not wired into the Processor |
| Typed Memory Records, Project Summary, and project registration/relink | Implemented | Validated records, add/support/update, summary refresh, exact-worktree resolution, and recoverable mapping tests |
| Knowledge Candidates and conflict records | Planned | Accepted Phase 1 design; Milestone 3 implementation remains |
| Interaction observations, profiles, and compiled guidance | Planned | Accepted contracts exist; no active implementation |
| Recall, MCP surface, skills, and retrieval projections | Planned | Accepted design; no active implementation |
| Lifecycle hooks, queue, retry spool, catch-up scheduling, and `$orca-save` | Partial | Secure redacted spool creation, three-attempt accounting, 72-hour expiry, content-free receipt, and success cleanup are tested library behavior; no hook or worker wiring exists |
| Orca Status, Attention Items, and session reminder | Planned | Accepted content-free local interface; no active implementation |
| Host configuration loading and WSL deployment | Planned | Accepted safe configuration examples exist; loader and deployed runtime do not |
| Canonical automatic apply | Deliberately absent | Disabled and unexposed by Phase 1 governance |

## Known divergence

- Processor context budgets, chunking, overlap, related-record selection, and
  the full proposal set are designed but not implemented.
- Storage's `0.2` receipts currently cover the unsegmented Milestone 2 slice;
  multi-segment source cursors and the complete outcome set remain Milestone 3.
- Runtime hooks, secure retry handling, retrieval reconciliation, interaction
  consolidation, and routine deployment are designed but not implemented.
- Codex's internal rollout format remains non-public. The connector supports the
  accepted Responses-style `final_answer` marker and fails closed on drift, but
  isolated host-format verification remains required before routine use.

These are implementation gaps, not permission to weaken the accepted contracts.

## Active work

- Design hardening: RFC-0001, RFC-0002, and RFC-0003 are accepted and promoted.
  The four post-migration design-hardening steps are complete.
- Phase 1 implementation: Milestones 1 and 2 are implemented and
  deterministically verified. The next bounded slice is Processor budgets and
  segmentation, conflicts, candidates, and complete provenance outcomes.

The accepted plan owns Phase 1 implementation sequence and milestone progress;
this document continues to own the verified current-state snapshot.

## Open decisions and blockers

Architecture, specification, and ADR extraction are accepted. ADR-0001 remains
superseded history; ADR-0002 and ADR-0003 remain future-only proposal evidence;
ADR-0004 through ADR-0012 are accepted current rationale. Knowledge Candidate
and Configuration design choices are no longer open; implementation remains
planned. RFC-0001 resolved the Manifest, checkpoint, provenance-join, and
interrupted-publication design. Its unsegmented slice is implemented; segmented
receipts remain Milestone 3 work. RFC-0002 resolved Project Registration,
Project Relink, exact-worktree reuse, and mapping-intent recovery, which are now
implemented and deterministically tested.

RFC-0003 resolved human-attention visibility and readiness measurement: one
content-free reminder per session for any unresolved item, a minimum 100-case
common-use corpus, 95% overall, 90% per category, zero critical failures, and a
separate mandatory edge-safety set. Implementation remains planned.

Routine Phase 1 use remains blocked by the planned runtime, retrieval,
interaction, configuration, deployment, and readiness work listed above.

## Verification

- Repository and documentation review date: 2026-08-30.
- Code was compared with the active contracts during the PDS audit.
- The complete current active regression command passed 65 tests on
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
