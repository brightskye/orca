---
id: QUALITY-TEST-STRATEGY
title: Phase 1 Test Strategy
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

# Phase 1 test strategy

## Purpose

Define how Orca tests deterministic contracts, integration boundaries,
recovery, retrieval, semantic behavior, and the complete private local Phase 1
loop.

## This document owns

- Test levels, environments, fixture rules, suite responsibilities, regression
  policy, and evidence separation for Phase 1.

## This document does not own

- System behavior, acceptance verdicts, implementation progress, or permission
  to use private conversation data.

## Authority boundary

This strategy is `accepted`/`normative`. The
[Acceptance Plan](acceptance.md) owns what must be demonstrated; owning
specifications define exact expected behavior; [Current Status](../STATUS.md)
owns what currently passes.

## Principles

- Test deterministic safety and authority boundaries without a model call.
- Keep semantic evaluation separate from deterministic acceptance.
- Verify artifact and runtime outcomes, not only schemas or exit codes.
- Use synthetic or explicitly permitted frozen inputs; never copy a private
  rollout or vault into tracked fixtures.
- Fail closed on ambiguity, schema drift, secrets, scope, identity, lifecycle,
  provenance, and stale derived state.
- Retain enough environment, revision, policy, provider, and fixture identity to
  reproduce every claimed result.

## Test levels

| Level | Scope | Typical evidence |
|---|---|---|
| Unit/contract | Pure normalization, validation, compilation, state, naming, budgets, and filtering | Deterministic assertions and valid/invalid fixtures |
| Module integration | Conversation → Processor, Processor → Storage, Storage → filesystem, projection → Adapter | Deterministic boundary tests with fakes at the semantic or external seam |
| Filesystem recovery | Publication and project-mapping interruption, replay, retry, stale view, index loss, and rebuild | Temporary directories, fault injection, immutable-output/hash assertions |
| Runtime integration | Configuration, hooks, queue, lock, worker, catch-up, skills/MCP, restart | Isolated WSL runtime and synthetic agent source |
| Retrieval evaluation | Hard filters, relevance, ordering, overlap, budgets, and Adapter replacement | Frozen synthetic corpus, expected eligible set, ranked assertions |
| Semantic evaluation | Provider proposal meaning and abstention | Frozen permitted inputs, rubric fixed before run, model/policy/sample labels |
| Common-use and edge gate | Representative normal behavior plus unusual safe handling | Owner-approved frozen corpus, binary rubric, category scores, critical-failure count, separate adversarial results |
| End to end | One controlled conversation through processing, restart, and explicit recall | Isolated test vault, deterministic artifact assertions, bounded canary, Owner review |

## Module responsibilities

| Area | Required deterministic coverage | Acceptance scenarios |
|---|---|---|
| Conversation and privacy | Positive event identity, assistant context, exclusions, partial tail, redaction, no raw archive | TEST-CAP-001, TEST-CAP-002 |
| Processor | Budgets, chunking, context selection, controlled proposals, validation, abstention, secret rejection | TEST-PROC-001 |
| Storage and provenance | Schemas, source segments, operation/artifact/output joins, placement, publication intent, Manifest/checkpoint, replay, recovery | TEST-PROV-001, TEST-MEM-001, TEST-MEM-003 |
| Conflicts and candidates | Replacement intent, variants, overflow, dispositions, recall exclusion, zero canonical writes | TEST-MEM-002 |
| Interaction | Observation admission, scope, lifecycle, expiry, conflict, precedence, exact guidance | TEST-INT-001, TEST-INT-002 |
| Retrieval | Projections, filters, ranking, budgets, stale/hash failure, rebuild, Adapter replacement | TEST-REC-001, TEST-REC-002 |
| Configuration/runtime | Source precedence, paths, project registration/relink, mapping intents, hooks, locks, retries, catch-up, restart, private boundary | TEST-CONFIG-001, TEST-PROJECT-001, TEST-RUNTIME-001 |
| Human attention | Source classification, severity, stable ID, deduplication, rebuild, resolution, privacy, reminder suppression, owning-workflow routes | TEST-ATTN-001 |
| Complete loop | Cross-module outcomes, restart, explicit recall, absence of public/canonical surfaces | TEST-E2E-001, TEST-SAFE-001 |
| Readiness quality | Frozen common-use cases, per-category and overall thresholds, zero critical failure, separate adversarial safe handling | TEST-QUAL-001 |

Scenario definitions and verdicts remain in the
[Acceptance Plan](acceptance.md#acceptance-scenarios).

## Test environments

### Hermetic deterministic tests

- Use temporary directories and synthetic fixtures.
- Use fake semantic providers and deterministic clocks/identities where the
  contract allows injection.
- Deny network access by default; a unit or module integration test must not
  require an external model or personal vault.
- Assert file content, paths, hashes, permissions, publication order, and
  negative side effects directly.

### Isolated local integration

- Use a dedicated disposable test vault outside any personal or synchronized
  vault.
- Use explicit test host/vault configuration and a synthetic Codex source.
- Record platform, Python/package revisions, policy/schema versions, and the Git
  revision under test.
- Verify no public listener and no writes outside the declared test roots.

### Controlled semantic evaluation

- Freeze permitted redacted inputs, expected evidence class, rubric, provider,
  model, policy version, budgets, and sample size before execution.
- Score semantic proposal usefulness separately from schema validity and safety.
- Run deterministic validation on every model output; invalid output is a
  rejection, not a near-pass.
- Report sampling and model/version limits with the result.

## Fixture and privacy rules

- Tracked fixtures contain synthetic or explicitly approved nonprivate content.
- Fixture names and bodies must not include real personal vault paths,
  credentials, tokens, private project data, or copied conversation text.
- Secret tests use unmistakably fake values designed for the versioned pattern
  under test.
- Source-format fixtures must cover supported and excluded classes without
  importing an entire real rollout.
- Generated vaults, indexes, spools, checkpoints, locks, caches, and evaluation
  outputs stay temporary or ignored.
- Regression datasets are immutable per version; corrections create a new
  version and retain the reason rather than silently changing expected results.

## Current suite inventory

| Suite | Current cases | Current route | Coverage boundary |
|---|---:|---|---|
| `tests/conversation/test_codex_capture.py` | 3 | AGENTS and CI | Owner-only normalization, basic redaction, deterministic no-write behavior |
| `tests/step3/test_pipeline.py` | 6 | AGENTS only | Initial Continuation Summary, Manifest, replay, checkpoint, `no_memory`, output-secret, source-revision behavior |
| `tests/agentcairn/test_distiller.py` | 3 | AGENTS and CI | Prevalidated Distiller seam and fail-closed unknown/canonical cases |

This 12-test inventory is a current regression baseline, not the complete Phase
1 suite and not end-to-end acceptance.

## Current and target commands

AGENTS uses the canonical active-suite command for the current three modules:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache \
uv run --extra agentcairn python -m unittest \
  tests/conversation/test_codex_capture.py \
  tests/step3/test_pipeline.py \
  tests/agentcairn/test_distiller.py
```

This exact command passed all 12 current tests on 2026-08-30. That verifies the
command and current regression baseline only; it does not satisfy the complete
Phase 1 acceptance scenarios. CI must adopt the same command to resolve the
remaining C-009 route divergence.

New deterministic Phase 1 suites must be added to this command and CI as their
milestones land. A later quality update may replace explicit paths with
discovery only after discovery is verified to select exactly the intended
active suites and exclude `legacy/manual-prototype/` tests.

## Deterministic versus model-dependent evidence

Deterministic tests own schema, allowed values, state transitions, source and
target identity, scope, authority, privacy exclusion, redaction, secret-output
rejection, budgets, ordering, idempotency, replay, publication, permissions,
filtering, result limits, compilation, and zero canonical mutation.

Semantic evaluation may assess whether a provider extracts useful supported
meaning, chooses an appropriate controlled operation, or abstains when it
should. It cannot override deterministic rejection or prove authorization,
privacy, storage, retrieval, recovery, or deployment behavior.

## Retrieval evaluation

- Freeze the corpus, Recall Requests, allowed filters, expected eligible set,
  required/forbidden results, relevance judgments, and token budgets.
- Assert hard-filter exclusion before comparing ranks.
- Evaluate weak-Canonical/strong-Shallow ordering, comparable-result authority
  ordering, duplicate collapse, ambiguous/refinement behavior, and the exact-
  conversation exception separately.
- Record Adapter and index-policy versions; an Adapter replacement must rerun
  the same contract corpus.

## Security and recovery testing

- Cover explicit privacy exclusion, every supported source class, schema drift,
  fake credential patterns, generated-output scanning, local permissions, and
  path traversal/cross-root rejection.
- Fault-inject before each publication intent, artifact, Manifest, checkpoint,
  intent/spool cleanup, summary, and index step; assert the exact recoverable or
  human-repair state and no canonical write.
- Cover multi-segment turns, exact segment replay, mixed `0.1`/`0.2` Manifest
  scans, source/operation/output joins, before/after reconciliation, orphan
  detection, and Manifest/output integrity mismatch.
- Fault-inject project registration and relink before and after `project.md`,
  host-config, verification, and intent cleanup. Prove stable identity, exact
  worktree-only automatic reuse, Owner choice for clones and moves, and no vault
  or Manifest leakage of host paths or Git evidence.
- Test lock contention, duplicate triggers, source revision, policy revision,
  retry exhaustion, retention expiry, restart, checkpoint loss, index loss,
  stale projection, and hash mismatch.
- Inspect process/network surfaces to prove no public listener or administrative
  endpoint is introduced.
- Inspect attention projections and reminders for memory text, credentials,
  unsafe paths, duplicate notices, hidden unresolved items, and mutation of the
  owning source state.

## Performance and resource testing

- Test exact configured boundary values for Processor input/output categories,
  Recall result/token limits, related-record count, guidance budget, retry count,
  and cadence behavior.
- Verify overflow splits or removes allowed optional context in the specified
  order and never silently truncates new evidence.
- Measure bounded hook handoff separately from background semantic processing.
- Record performance observations as informative until an accepted requirement
  defines a pass threshold beyond the existing budgets.

## Common-use and edge evaluation

- Freeze at least 100 Owner-approved representative cases before execution:
  capture/privacy 15, processing/provenance 20, project/memory 20, interaction
  10, recall 20, and runtime/recovery 15.
- Score each expected outcome pass/fail with no partial credit. Require 95%
  overall, 90% in every category, and zero critical safety violation.
- Run unusual, malformed, ambiguous, and unsupported cases in a separate edge
  set. Every case must succeed safely, abstain or reject clearly, or expose an
  Attention Item; do not average this set into the common-use score.
- Record repository, provider, model, policy, corpus, and rubric versions. Rerun
  after a material change and retain the Owner's corpus, rubric, and final-gate
  approval.

## Regression policy

- Every bug fix begins with a failing deterministic case at the narrowest owning
  boundary when reproducible.
- A contract change updates its accepted owner and fixtures before or with the
  implementation; tests must not silently redefine the contract.
- Preserve replay and privacy regressions permanently unless the owning behavior
  is explicitly superseded.
- A flaky deterministic test is a failure to diagnose, not a pass to rerun until
  green.
- A semantic regression changes evaluation evidence, not deterministic verdicts,
  unless the output also violates a deterministic contract.

## CI and phase gates

- CI must run the canonical deterministic active suite on supported repository
  changes.
- Semantic/model-dependent evaluations and local WSL canaries run as separately
  labelled gates with their required environment; they must not make ordinary CI
  nondeterministic.
- Phase 1 cannot complete until every Acceptance Plan scenario passes, the
  [Phase 1 Local Runbook](../08-operations/runbook.md) is implemented and
  verified, and the Owner accepts the retained evidence.
- A historical canary or `PASS — SMALL SAMPLE` label remains limited to its
  recorded sample and never substitutes for the current phase gate.

## Adoption gaps

- CI currently omits the Step 3 pipeline suite.
- Most accepted Phase 1 contracts have no implementation tests yet.
- No current local-runtime end-to-end or operational canary proves Phase 1.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Acceptance scenarios:** [Phase 1 Acceptance Plan](acceptance.md)
- **Implementation sequence:** [Phase 1 Implementation Plan](../06-plans/active/phase-1-implementation.md)
- **Specifications:** [Specification Index](../03-specifications/README.md)
- **Operations:** [Phase 1 Local Runbook](../08-operations/runbook.md)
- **Current evidence state:** [Current Status](../STATUS.md)
