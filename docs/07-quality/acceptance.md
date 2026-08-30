---
id: QUALITY-ACCEPTANCE
title: Phase 1 Acceptance Plan
document_type: quality
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-30
---

# Phase 1 acceptance plan

## Purpose

Define the direct evidence required to accept the Phase 1 governed-memory loop
against its requirements, specifications, and Roadmap exit criteria.

## This document owns

- Stable Phase 1 acceptance scenario IDs, evidence expectations, phase gates,
  and the mapping from Roadmap exit criteria to verification.

## This document does not own

- System behavior, implementation sequence, current status, test mechanics, or
  the meaning of a historical evaluation result.

## Authority boundary

This plan is `accepted`/`normative`. A scenario passes only with current
retained evidence at the specified layer. Structural validation,
test counts, model agreement, an earlier canary, or document acceptance cannot
substitute for the required observable behavior.

## Evidence classes and verdicts

| Evidence class | Establishes | Does not establish |
|---|---|---|
| Deterministic contract test | Exact local validation, state, ordering, safety, and failure behavior | Semantic quality or deployed operation |
| Retrieval evaluation | Relevance, filtering, overlap, ordering, and budget behavior on a frozen corpus | General model quality or authority correctness without filter assertions |
| Semantic evaluation | Bounded provider proposal quality on frozen permitted inputs | Deterministic correctness, safety, or authority |
| Operational canary | Observed behavior in an isolated representative local runtime | General completion beyond the exercised sample |
| Human review | Owner judgment for semantic usefulness and final phase acceptance | Missing deterministic evidence |

Allowed scenario verdicts are `not-run`, `pass`, `fail`, and `blocked`. `pass`
requires an evidence locator, tested revision, environment, and observed result.

## Acceptance scenarios

### TEST-CAP-001 — Supported Codex records are positively identified

**Given** frozen startup, resume, fork, subagent, archived-session, schema-drift,
Owner, visible/final assistant, system, tool, reasoning, injected, private, and
ambiguous source fixtures
**When** the Codex Connector normalizes eligible records
**Then** only positively identified Owner evidence and permitted assistant
context are returned with exact conversation and turn provenance, while every
excluded or unknown class fails closed.

**Related requirements:** REQ-CAP-001, REQ-SAFE-001
**Related specification:** [Capture Pipeline](../03-specifications/capture-pipeline.md)
**Required evidence:** deterministic connector tests

### TEST-CAP-002 — Capture contains secrets and incomplete source safely

**Given** explicit privacy controls, credential-like values, permitted context,
and a partial trailing JSONL record
**When** capture prepares provider or retry input
**Then** excluded content leaves no payload, obvious credentials are redacted
before handoff, no secondary transcript is created, and incomplete input waits
without checkpoint advancement.

**Related requirements:** REQ-CAP-002, REQ-CAP-003, REQ-OPS-003
**Related specifications:** [Capture Pipeline](../03-specifications/capture-pipeline.md), [Security and Trust](../02-architecture/security-and-trust.md)
**Required evidence:** deterministic privacy, filesystem, and partial-input tests

### TEST-PROC-001 — Processing is bounded and semantic output grants no authority

**Given** normal, backlog, oversized-turn, over-budget, malformed, cross-scope,
identity-changing, unsupported-transition, and credential-bearing proposals
**When** Processor constructs and validates a semantic run
**Then** accepted context ceilings and splitting rules are enforced, invalid
output publishes nothing, every accepted operation cites its exact current-run
source segments, provider fields grant no identity or authority, and a valid
abstention becomes a successful `no_memory` result.

**Related requirements:** REQ-PROC-001, REQ-PROC-002, REQ-SAFE-001
**Related specification:** [Processing Pipeline](../03-specifications/processing-pipeline.md)
**Required evidence:** deterministic budget, validation, and failure tests

### TEST-PROV-001 — Publication, replay, and progress recovery are idempotent

**Given** new input, a multi-segment turn, exact segment replay, source or
segmentation conflict, changed redaction/segmentation policy, mixed `0.1` and
`0.2` receipts, artifact/Manifest/checkpoint/intent-cleanup interruption points,
a missing checkpoint, and an orphan or before/after hash mismatch
**When** Storage publishes or recovers a processing run
**Then** one complete local intent publishes before final artifacts, every
operation joins exact sources to stable artifact identity and physical effects,
one immutable Manifest publishes before the source-segment checkpoint, safe
recovery makes no second semantic call, conflicts fail closed for human repair,
and an available Manifest repairs progress without duplicate output.

**Related requirements:** REQ-PROC-003, REQ-AUD-001, REQ-OPS-003
**Related specification:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
**Required evidence:** deterministic schema, source/operation/output join,
mixed-version scan, filesystem fault-injection, recovery, and replay tests

### TEST-MEM-001 — Typed memory preserves identity, scope, and controlled state

**Given** valid and invalid add, support, update, supersede, conflict, close,
scope, project-root, filename, relationship, and body fixtures
**When** Processor proposes operations and Storage materializes permitted records
**Then** logical identity remains stable, uncertain matches remain separate,
Project, General, and Unassigned scopes do not leak, and only accepted states,
kinds, bodies, names, and relationships publish.

**Related requirements:** REQ-MEM-001, REQ-MEM-002, REQ-PROC-002
**Related specification:** [Memory Model](../03-specifications/memory-model.md)
**Required evidence:** deterministic schema, lifecycle, scope, and storage tests

### TEST-MEM-002 — Conflicts and candidates remain visible and noncanonical

**Given** clear replacement, ambiguous chronology, two- and multi-position
conflicts, overflow, ordinary candidate, disposition, replay, and resolution
fixtures
**When** the memory and candidate lifecycles run
**Then** only a clear trusted replacement supersedes prior meaning, unresolved
variants remain visible, candidates remain outside ordinary recall, and no
candidate state or conflict action mutates Canonical Memory automatically.

**Related requirements:** REQ-MEM-003, REQ-CAND-001, REQ-AUTH-003
**Related specifications:** [Memory Model](../03-specifications/memory-model.md), [Knowledge Candidates](../03-specifications/knowledge-candidates.md)
**Required evidence:** deterministic conflict, candidate, recall-exclusion, and zero-canonical-write tests

### TEST-MEM-003 — Structural summaries refresh without gaining authority

**Given** material record changes, support-only evidence, no-change input,
unresolved conflict, resolution, and a failed derived-summary refresh
**When** Conversation and Project Summaries are refreshed or rebuilt
**Then** only material changes rewrite the applicable summary, stable supporting
identities remain visible, stale state is recoverable, and summaries confer no
new authority.

**Related requirements:** REQ-AUTH-002, REQ-MEM-001, REQ-OPS-003
**Related specification:** [Memory Model](../03-specifications/memory-model.md)
**Required evidence:** deterministic summary lifecycle and rebuild tests

### TEST-INT-001 — Interaction evidence is scoped, contextual, and abstention-safe

**Given** explicit lasting preferences, one-turn/session-only instructions,
aligned corrections, conflicts, expiry, missing context, ambiguous scope,
sensitive inference, and surface-linguistic signals
**When** observations are validated and profiles consolidated
**Then** only qualified presentation evidence enters the correct profile state,
missing or sensitive context abstains, conflicts generate no automatic guidance,
and no provisional profile becomes Canonical Memory.

**Related requirements:** REQ-INT-001, REQ-INT-002, REQ-AUTH-002
**Related specification:** [Interaction Preferences](../03-specifications/interaction-preferences.md)
**Required evidence:** deterministic observation, consolidation, lifecycle, scope, and expiry tests

### TEST-INT-002 — Guidance compilation is exact, bounded, and deterministic

**Given** every controlled context, dimension, value/direction, lifecycle state,
and precedence combination
**When** applicable guidance is selected and compiled
**Then** only active entries use the accepted versioned phrases, higher
precedence wins, conflicts/unknowns emit nothing, complete sentences fit within
the configured budget, and repeated compilation is byte-identical.

**Related requirement:** REQ-INT-002
**Related specification:** [Interaction Guidance](../03-specifications/interaction-guidance.md)
**Required evidence:** deterministic golden-template and precedence tests

### TEST-REC-001 — Explicit recall filters before ranking and stays bounded

**Given** mixed authority, visibility, project, status, relevance, duplicate,
ambiguous, exact-conversation, and budget-boundary fixtures
**When** an explicit Recall Request is executed
**Then** hard filters run before Adapter ranking, strongly relevant Shallow
Memory is not displaced by weak Canonical Memory, comparable Canonical results
come first, duplicates collapse, ambiguity returns fewer results or refinement,
and all count/token/excerpt limits and labels are enforced without another
summarization call.

**Related requirements:** REQ-REC-001, REQ-AUTH-002, REQ-SAFE-001
**Related specification:** [Retrieval Contract](../03-specifications/retrieval-contract.md)
**Required evidence:** deterministic retrieval evaluation on a frozen synthetic corpus

### TEST-REC-002 — Retrieval projections and indexes are replaceable

**Given** current, conflicting, resolved, closed, candidate, stale-summary,
hash-mismatch, missing-index, and Adapter-replacement fixtures
**When** projections reconcile, indexes rebuild, and recall repeats
**Then** projections expose only permitted meaning, a missing or stale index
never causes a broad unsafe scan, rebuilding reproduces eligible results, and
changing the Adapter does not change authority or safety semantics.

**Related requirements:** REQ-REC-002, REQ-OPS-003
**Related specifications:** [Retrieval Contract](../03-specifications/retrieval-contract.md), [Integration Architecture](../02-architecture/integration-architecture.md)
**Required evidence:** deterministic projection, rebuild, failure, and Adapter-contract tests

### TEST-CONFIG-001 — Configuration fails before unsafe execution

**Given** valid examples plus missing, relative, conflicting, unknown-version,
unknown-key, cross-location, inconsistent-budget, and uncertain-root fixtures
**When** host and vault configuration loads
**Then** only the accepted file/environment combinations and normalized mappings
are admitted before any model call or vault write, while private values and
runtime state remain local and ignored.

**Related requirements:** REQ-OPS-001, REQ-SAFE-001
**Related specification:** [Configuration](../03-specifications/configuration.md)
**Required evidence:** deterministic configuration and Git-ignore tests

### TEST-PROJECT-001 — Project registration and relinking preserve identity

**Given** exact mapping, new registration, explicit relink, exact Git worktree,
move, clone, matching-remote, non-Git, alias-collision, ambiguous, Unassigned,
interrupted-write, lost-intent, and conflicting-state fixtures
**When** project resolution and mapping run
**Then** only an exact mapping or exact nonconflicting local worktree resolves
automatically; every other uncertain case requires one Owner choice or remains
Unassigned; retries reuse one permanent identity; conflicts fail closed for
human repair; and host paths and Git evidence never enter the vault or Manifest.

**Related requirements:** REQ-MEM-001, REQ-OPS-001, REQ-SAFE-001
**Related specifications:** [Memory Model](../03-specifications/memory-model.md), [Configuration](../03-specifications/configuration.md)
**Required evidence:** deterministic resolution, registration, relink,
fault-injection, case-comparison, idempotency, and path-leakage tests

### TEST-RUNTIME-001 — One private local runtime recovers lifecycle work

**Given** startup, resume, post-compaction, `PreCompact`, `SessionEnd`, explicit
save, duplicate trigger, lock contention, retry, retry exhaustion, retention
expiry, catch-up, restart, and stale-index cases
**When** Codex Desktop uses the configured local WSL runtime
**Then** bounded hooks feed one idempotent worker, applicable interaction
guidance loads without semantic recall, retry state follows the accepted private
lifecycle, no-op catch-up makes no model call, and no public interface exists.

**Related requirements:** REQ-CAP-003, REQ-OPS-002, REQ-OPS-003
**Related specifications:** [Runtime Architecture](../02-architecture/runtime.md), [Deployment Architecture](../02-architecture/deployment.md)
**Required evidence:** deterministic runtime integration tests plus an isolated local operational canary

### TEST-ATTN-001 — Human attention is visible, quiet, and content-free

**Given** terminal failure, orphan, integrity mismatch, stuck publication and
mapping intents, invalid configuration, blocking stale derived state,
Unassigned records, Memory Conflicts, overflow, pending Knowledge Candidates,
resolved items, duplicate observations, restart, and projection-loss fixtures
**When** attention state rebuilds, session start or resume runs, and the Owner
invokes Orca Status
**Then** unresolved items receive stable classes, severities, IDs, and owning
workflow routes; resolved items disappear only when their source proves
resolution; startup shows at most one counts-only reminder per session; and no
memory text, credential, model call, recall, mutation, public notification, or
separate authority is introduced.

**Related requirements:** REQ-OPS-003, REQ-OPS-004, REQ-SAFE-001
**Related specifications:** [Runtime Architecture](../02-architecture/runtime.md), [Data Architecture](../02-architecture/data-architecture.md)
**Required evidence:** deterministic classification, severity, deduplication,
rebuild, resolution, privacy, reminder, and route tests

### TEST-E2E-001 — A bounded conversation is processed and recalled locally

**Given** an isolated configured test vault and one permitted controlled Codex
conversation containing useful memory and presentation feedback
**When** the lifecycle path processes one bounded range and a later explicit
recall requests the result
**Then** the expected provisional artifacts, profile, Manifest, checkpoint,
projection, and authority-labelled Recall Result are observable after restart,
with no raw transcript archive, cross-scope leakage, public service, or automatic
Canonical Memory mutation.

**Related requirements:** REQ-AUTH-001, REQ-AUTH-002, REQ-AUTH-003, REQ-QUAL-001
**Related specifications:** [Specification Index](../03-specifications/README.md), [Architecture Overview](../02-architecture/overview.md)
**Required evidence:** deterministic end-to-end assertions, isolated operational canary, and Owner review

### TEST-SAFE-001 — Canonical mutation and public exposure remain absent

**Given** every Phase 1 entry point, candidate disposition, conflict action,
recall action, failure path, and runtime configuration
**When** deterministic surface and filesystem checks execute
**Then** no automatic or agent-initiated canonical-apply operation, public
listener, administration service, or cross-project default is reachable, and
the Owner remains final authority.

**Related requirements:** REQ-AUTH-001, REQ-AUTH-003, REQ-OPS-002, REQ-QUAL-001
**Related specifications:** [Memory System Contract](../governance/memory-system-contract.md), [Security and Trust](../02-architecture/security-and-trust.md)
**Required evidence:** deterministic negative-surface, filesystem-diff, and network-boundary tests

### TEST-QUAL-001 — Common use passes without averaging away unsafe edges

**Given** an Owner-approved frozen corpus of at least 100 representative cases
with the accepted category minimums and expected binary outcomes, plus a
separate frozen adversarial set
**When** Orca runs with recorded repository, provider, model, policy, corpus,
and rubric versions
**Then** at least 95% of common-use cases pass overall, every category passes at
least 90%, no critical authority/privacy/secret/scope/canonical-write/identity/
silent-loss violation occurs, and every adversarial case succeeds safely,
abstains or rejects clearly, or exposes human attention.

**Related requirements:** REQ-QUAL-001, REQ-QUAL-002, REQ-SAFE-001
**Related specifications:** [Specification Index](../03-specifications/README.md), [Runtime Architecture](../02-architecture/runtime.md)
**Required evidence:** frozen permitted corpus, expected outcomes, fixed binary
rubric, per-case results, per-category and overall scores, critical-failure
count, version record, and Owner verdict

## Requirement coverage

Every Phase 1 requirement ID is referenced by at least one scenario above.
Detailed test mechanics and suite placement belong to the
[Test Strategy](test-strategy.md).

## Phase exit verification

| Roadmap Phase 1 exit criterion | Required scenarios |
|---|---|
| Supported Owner and assistant context with provenance and privacy exclusions | TEST-CAP-001, TEST-CAP-002 |
| Bounded, retry-safe processing with durable Manifests and checkpoint-last progress | TEST-PROC-001, TEST-PROV-001, TEST-RUNTIME-001 |
| Memory, project, candidate, interaction, and recall contracts through deterministic validation | TEST-MEM-001, TEST-MEM-002, TEST-MEM-003, TEST-PROJECT-001, TEST-INT-001, TEST-INT-002, TEST-REC-001, TEST-REC-002 |
| Restart, replay, rebuild, conflict, privacy, secret containment, and visible human attention | TEST-CAP-002, TEST-PROV-001, TEST-MEM-002, TEST-REC-002, TEST-CONFIG-001, TEST-PROJECT-001, TEST-RUNTIME-001, TEST-ATTN-001 |
| Complete private local loop with no public service or automatic canonical mutation | TEST-E2E-001, TEST-SAFE-001, TEST-QUAL-001 |

## Phase gate

Phase 1 remains active until:

- every scenario above has a current `pass` verdict with retained evidence;
- no unresolved failure or divergence can invalidate a requirement, security
  boundary, recovery claim, or Roadmap exit criterion;
- the canonical test command and CI cover every required deterministic suite;
- required procedures in the [Phase 1 Local Runbook](../08-operations/runbook.md)
  are implemented and verified against an isolated local vault;
- TEST-QUAL-001 passes its frozen common-use corpus and separate edge-safety set
  with zero critical failure;
- semantic evaluations retain their model, policy, dataset, and sample-size
  limits and are not used as deterministic proof; and
- the Owner reviews the complete evidence set and accepts Phase 1 completion.

This is a phase gate, not proof that version `0.1.0` was released.

## Existing evidence boundary

The current 12 focused tests passed together on 2026-08-30. They cover only the
initial capture, Continuation-Summary/Manifest/checkpoint, and AgentCairn
Distiller seams. They are regression evidence, not a pass for any complete
Phase 1 scenario above.

Historical canary evidence remains historical. A result labelled
`PASS — SMALL SAMPLE` keeps that exact limitation and cannot become general or
end-to-end verification without a current controlled rerun against the accepted
scenario and retained inputs. Static or structural validation proves saved
structure only, not deployed behavior.

## Known evaluation limitations

- Model interpretation is probabilistic and provider/version sensitive.
- Synthetic fixtures prove controlled boundaries but not real-use usefulness.
- A local canary proves only its frozen inputs, environment, revision, and
  exercised paths.
- Human approval cannot replace missing privacy, authority, replay, recovery, or
  zero-canonical-write assertions.
- Retrieval relevance thresholds and semantic rubrics must be frozen before a
  run; post-hoc success criteria are invalid.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Roadmap:** [Phase 1](../ROADMAP.md#phase-1)
- **Implementation sequence:** [Phase 1 Implementation Plan](../06-plans/active/phase-1-implementation.md)
- **Requirements:** [Orca Requirements](../01-foundation/requirements.md)
- **Specifications:** [Specification Index](../03-specifications/README.md)
- **Test mechanics:** [Test Strategy](test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](../08-operations/runbook.md)
- **Current evidence state:** [Current Status](../STATUS.md)
