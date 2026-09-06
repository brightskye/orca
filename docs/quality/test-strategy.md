---
id: QUALITY-TEST-STRATEGY
title: Phase 1 Test Strategy
document_type: quality
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-09-06
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
specifications define exact expected behavior; [Current Status](../project-record/current.md)
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

[Runtime](../specifications/runtime.md) owns exact coordination and attention
expectations; [Backup](../specifications/backup.md) owns archive and staging
expectations. These complement the existing capture, configuration, and
provenance contracts.

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
- Evaluation-only runners live with their maintained cases under `tests/evals/`
  and are excluded from the installed `orca_memory` package.
- Regression datasets are immutable per version; corrections create a new
  version and retain the reason rather than silently changing expected results.

## Current suite inventory

| Suite | Current cases | Current route | Coverage boundary |
|---|---:|---|---|
| `tests/conversation/test_codex_capture.py` | 10 | AGENTS and CI | Owner/final-assistant classification, bounded offsets, exclusions, privacy, partial tails, drift failure, redaction, deterministic no-write behavior |
| `tests/conversation/test_retry_spool.py` | 4 | AGENTS and CI | Private redacted spool permissions, attempt bound, expiry receipt, and success cleanup |
| `tests/step3/test_pipeline.py` | 8 | AGENTS and CI | Evidence/context separation plus initial Continuation Summary, Manifest, replay, checkpoint, `no_memory`, output-secret, source-revision behavior |
| `tests/memory/test_records.py` | 14 | AGENTS and CI | Typed Memory schemas, kinds, scope, identity, bodies, filenames, add/support/update, and Project Summary validation |
| `tests/memory/test_conflicts.py` | 6 | AGENTS and CI | Stable variants, conflict review states, overflow, support, supersession lineage, and Owner-only resolution |
| `tests/candidates/test_candidates.py` | 9 | AGENTS and CI | Ordinary candidate schema, kinds, scopes, placement, support, terminal dispositions, receipts, and recall exclusion |
| `tests/project/test_registry.py` | 9 | AGENTS and CI | Stable project identity, exact mapping, Owner choice, Unassigned, registration, relink, and exact-worktree reuse |
| `tests/project/test_mapping_publication.py` | 5 | AGENTS and CI | Intent-first project registration/relink recovery, configured-host binding, mismatch handling, and content-free orphan detection |
| `tests/step3/test_typed_pipeline.py` | 9 | AGENTS and CI | Typed add/support/update, allocated Project Summary IDs, same-scope existing context, exact per-operation source references and timestamps, joined receipts, and interrupted recovery |
| `tests/step3/test_segmentation.py` | 11 | AGENTS and CI | Accepted budgets, conservative estimation, UTF-8 segments, chronological chunks, context measurement, and related-record bounds |
| `tests/step3/test_processor_budgets.py` | 12 | AGENTS and CI | Pre-call context rejection, optional context fitting, shared record/candidate bounds, output ceiling without duplicated rendered summaries, exact Owner source locators, and project-context scope |
| `tests/step3/test_segmented_pipeline.py` | 2 | AGENTS and CI | Sequential segment Manifests, exact replay/checkpoint repair, and segmentation-policy conflict |
| `tests/step3/test_outcomes.py` | 4 | AGENTS and CI | Conflict/overflow, active and overflow support, candidates, abstention, supersession, and exact joined publication |
| `tests/step3/test_provenance.py` | 5 | AGENTS and CI | Manifest/checkpoint `0.2`, mixed `0.1` reads, segment sequence, strict joins, exact replay, and conflict detection |
| `tests/step3/test_publication.py` | 5 | AGENTS and CI | Intent/artifact/Manifest/checkpoint order, fault recovery, mismatch, and path containment |
| `tests/agentcairn/test_distiller.py` | 3 | AGENTS and CI | Prevalidated Distiller seam and fail-closed unknown/canonical cases |
| `tests/interaction/test_interaction.py` | 12 | AGENTS and CI | Controlled observations, abstention, activation, conflict, replacement, expiry, scope precedence, overrides, and exact bounded templates |
| `tests/interaction/test_pipeline.py` | 2 | AGENTS and CI | Exact-source Manifest admission, content-free abstention, replay, profile rebuild, text exclusion, and deterministic selection |
| `tests/retrieval/test_retrieval.py` | 14 | AGENTS and CI | Projection/hash validation, hard filters, conflicts, relevance/authority ordering, duplicate collapse, exact conversation, budgets, governed AgentCairn ranking, and disposable-index recovery |
| `tests/config/test_configuration.py` | 15 | AGENTS and CI | Strict schemas, precedence, project/Git/symlink path guards, policy versions, default-off lifecycle toggle, budgets, provider registration, project mappings, examples, and ignored local state |
| `tests/runtime/test_runtime.py` | 15 | AGENTS and CI | Hook deduplication, content-free terminal failure categories, private spool cleanup, bounded queue drain, one-shot lock, retries, content-free attention, cursors, scope choices, catch-up, and idle behavior |
| `tests/runtime/test_attention.py` | 7 | AGENTS and CI | Accepted attention sources, pending and orphan recovery state, content-free stable views, rebuild, safe routes, and once-per-session reminders |
| `tests/runtime/test_application.py` | 21 (one opt-in) | AGENTS and CI | Isolated process/restart/rebuild/guidance/Recall loop, scope/cursor catch-up, lifecycle guards, Owner-review commands, mapped or explicit CLI scope, no startup search, configured staging protection, and opt-in real GPG recovery/recall drill |
| `tests/runtime/test_owner_review.py` | 12 | AGENTS and CI | Explicit candidate/conflict outcomes, canonical-path and symlink checks, complete receipts, race-safe fixed-intent recovery, overflow cleanup, and no canonical writes |
| `tests/runtime/test_backup.py` | 9 | AGENTS and CI | Full-vault and essential-runtime boundary, fake-GPG encryption seam, pending/orphan-work blocking, manifest/hash verification, project/Git and temporary plaintext path guards, staging-only restore, and CLI recovery without valid host configuration |
| `tests/runtime/test_codex_provider.py` | 10 (one opt-in) | AGENTS and CI | Isolated exact-model Codex CLI invocation, selected source/candidate serialization, exact stored fields for support, local prompt/instructions/schema ceiling, structured proposal validation, content-free failure, and opt-in actual CLI tool/file-access rejection |
| `tests/runtime/test_codex_hook.py` | 14 | AGENTS and CI | Official lifecycle payloads, deterministic scope resolution, default-off no-op before transcript access, source containment, mandatory redacted handoff, cursor-aware replay, exact worker settings, safe failures, scoped recall instructions without startup search, and hook configuration |
| `tests/acceptance/test_readiness_boundaries.py` | 7 | AGENTS and CI | Frozen corpus distribution and digests, selector-backed execution, fail-closed scoring, separate edge set, and negative canonical/public surface |
| `tests/acceptance/test_semantic_evaluation.py` | 5 | AGENTS and CI | Strict synthetic semantic manifest, separate usefulness/validity/safety scoring, allowed extras, content-safe failures, and immutable result retention |

This inventory records the suites and their intended coverage. The canonical
command below is the current regression baseline; its test count changes when
the listed suites change. It is not the complete Phase 1 suite and not
end-to-end acceptance.

## Current and target commands

AGENTS and CI use the canonical active-suite command:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache \
uv run --extra agentcairn python -m unittest \
  tests/conversation/test_codex_capture.py \
  tests/conversation/test_retry_spool.py \
  tests/memory/test_records.py \
  tests/memory/test_conflicts.py \
  tests/candidates/test_candidates.py \
  tests/project/test_registry.py \
  tests/project/test_mapping_publication.py \
  tests/step3/test_pipeline.py \
  tests/step3/test_typed_pipeline.py \
  tests/step3/test_segmentation.py \
  tests/step3/test_processor_budgets.py \
  tests/step3/test_segmented_pipeline.py \
  tests/step3/test_outcomes.py \
  tests/step3/test_provenance.py \
  tests/step3/test_publication.py \
  tests/interaction/test_interaction.py \
  tests/interaction/test_pipeline.py \
  tests/retrieval/test_retrieval.py \
  tests/config/test_configuration.py \
  tests/runtime/test_runtime.py \
  tests/runtime/test_attention.py \
  tests/runtime/test_application.py \
  tests/runtime/test_owner_review.py \
  tests/runtime/test_backup.py \
  tests/runtime/test_codex_provider.py \
  tests/runtime/test_codex_hook.py \
  tests/acceptance/test_readiness_boundaries.py \
  tests/acceptance/test_semantic_evaluation.py \
  tests/agentcairn/test_distiller.py
```

The full command with both `ORCA_RUN_GPG_DRILL=1` and
`ORCA_RUN_CODEX_ISOLATION_DRILL=1` passed 259 tests on 2026-09-06 after the
controlled-trial repairs. Without those flags, the two integration drills are skipped
and the remaining 257 cases form the deterministic baseline. The drills add
real encryption/recovery and actual Codex executable isolation evidence; they
do not establish complete Phase 1 acceptance, private deployed-vault recovery,
or a live semantic or two-session lifecycle canary.

New deterministic Phase 1 suites must be added to this command and CI as their
milestones land. A later quality update may replace explicit paths with
discovery only after discovery is verified to select exactly the intended
active suites and exclude `legacy/manual-prototype/` tests.

## Deterministic versus model-dependent evidence

The real encryption/recovery drill is opt-in so the deterministic baseline does
not require GPG or a key agent. Run it with:

```bash
ORCA_RUN_GPG_DRILL=1 UV_CACHE_DIR=/tmp/orca-uv-cache \
uv run --extra agentcairn python -m unittest \
  tests.runtime.test_application.ApplicationTests.test_cli_real_gpg_recovery_after_installation_loss
```

It uses real local `gpg` and `gpgconf`, a disposable synthetic vault, separate
temporary keyrings, and a generated test key. It makes no model call and reads
no Owner key or private vault. It verifies recovery without the old installation,
all restored vault hashes, fresh-index recall, source references, and rejection
of damaged archives and missing keys. It does not prove deployed-vault recovery
or automatic capture resumption. The same environment flag includes this drill
when running the full suite above.

The Codex isolation drill is also opt-in:

```bash
ORCA_RUN_CODEX_ISOLATION_DRILL=1 UV_CACHE_DIR=/tmp/orca-uv-cache \
uv run --extra agentcairn python -m unittest \
  tests.runtime.test_codex_provider.CodexIsolationTests
```

It requires Linux, bubblewrap, and the qualified static Codex CLI 0.153.4.
It uses synthetic authentication and a local loopback Responses server to
exercise the real executable. Forced tool execution must fail, an external
sentinel file must be unreadable before any model request, and host environment
sentinels must not leak. It makes no real model call and uses no Owner key.
This verifies the tested process boundary, not live authentication, semantic
usefulness, or hook timing. Set both drill flags on the full command to include
both integration checks.

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
- Fault-inject candidate and conflict Owner-review receipts, target post-images,
  overflow cleanup, intent cleanup, identity/path/hash mismatches, and recovery;
  prove no semantic call or canonical write occurs.
- Verify encrypted backup boundaries with a fake GPG runner and, separately,
  test private file permissions, allowed archive roots, manifest/member hashes,
  pending-work blocking, and staging-only restore without live mutation. A real
  GPG backup is a deployment verification step, not a hermetic test requirement.
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
  [Phase 1 Local Runbook](../operations/runbook.md) is implemented and
  verified, and the Owner accepts the retained evidence.
- A historical canary or `PASS — SMALL SAMPLE` label remains limited to its
  recorded sample and never substitutes for the current phase gate.

## Current implementation evidence

- Interaction, retrieval, runtime, attention, and complete-loop contracts have
  active deterministic implementation tests in the canonical suite.
- The accepted local-runtime lifecycle canary remains evidence only for its
  authorized two-turn sample and exact recorded environment; it does not prove
  broad semantic usefulness or a different revision.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Acceptance scenarios:** [Phase 1 Acceptance Plan](acceptance.md)
- **Implementation sequence:** [Phase 1 Implementation Plan](../project-record/plans/completed/phase-1-implementation.md)
- **Specifications:** [Specification Index](../specifications/README.md)
- **Operations:** [Phase 1 Local Runbook](../operations/runbook.md)
- **Current evidence state:** [Current Status](../project-record/current.md)
