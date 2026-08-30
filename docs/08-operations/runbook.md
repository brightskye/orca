---
id: RUNBOOK-LOCAL
title: Phase 1 Local Runbook
document_type: runbook
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

# Phase 1 local runbook

## Purpose

Describe only the procedures an operator can execute against the current Phase
1 repository and state plainly where the designed runtime has no runnable
operator interface yet.

## This document owns

- Once accepted, executable local installation, start/stop, health, routine
  operation, diagnostics, backup/restore, recovery, rebuild, troubleshooting,
  and escalation procedures.

## This document does not own

- Runtime behavior, configuration schemas, implementation status, test
  strategy, or permission to operate on a personal vault.

## Authority and status boundary

This runbook is `accepted`/`normative`. A local one-shot CLI and composition
root are implemented, but private Codex/provider/vault deployment is not yet
Owner-authorized. The commands below are verified against isolated synthetic
fixtures; they do not authorize personal data or credentials.

| Label | Meaning |
|---|---|
| **Verified repository procedure** | Executed successfully against the current checkout on the stated date |
| **Tested library behavior** | Covered by deterministic tests but not exposed as an operator command |
| **Unavailable** | Designed or expected, but no runnable Phase 1 procedure exists |

## Scope

This limited runbook covers the `/workspace/projects/orca` checkout and the
current active regression command. It does not authorize use of a personal
or synchronized vault, code under `legacy/manual-prototype/`, later-phase topology, or any
canonical-memory mutation.

## Prerequisites

For the verified repository procedure:

- Work from the Orca project checkout.
- Use Python 3.11 or newer through `uv`.
- Use a writable cache outside the repository, such as
  `/tmp/orca-uv-cache`.
- Do not point tests at a personal vault or real Codex rollout store.

Private operation additionally requires Owner authorization for the configured
vault, Codex rollout, and semantic-provider mechanism.

## Installation

Install the local package environment with `uv sync --extra agentcairn`. Verify
the entry point with `uv run orca --help`. This installs no daemon or hook.

`uv run` may resolve the isolated environment needed for the verified regression
procedure below. That is test-environment preparation, not Orca deployment.

## Configuration

Create ignored `config/host.yaml` and vault-local
`System/Orca Memory/orca-memory.yaml` from the safe examples, then validate:

```bash
uv run orca --registered-adapter <configured-adapter-id> validate
```

- [`config/host.example.yaml`](../../config/host.example.yaml) is a safe tracked
  structural fixture for local host fields.
- [`config/orca-memory.example.yaml`](../../config/orca-memory.example.yaml) is a
  safe tracked structural fixture for vault policy fields.
- Actual `config/host.yaml`, credentials, paths, mappings, `.runtime/` state, and
  private memory must remain local and ignored.
- The vault path may eventually come only from `config/host.yaml` or
  `ORCA_VAULT_PATH`, with conflict-on-difference validation defined by the
  [Configuration Specification](../03-specifications/configuration.md).

Validation is read-only and must pass before another runtime command.

## Start

Run the deterministic session-start path with:

```bash
uv run orca --registered-adapter <configured-adapter-id> start \
  --session-id <safe-session-id> --context general
```

This loads only guidance and the counts-only reminder; it performs no Recall or
conversation processing.

### Codex lifecycle-hook activation

[`config/codex-hooks.example.json`](../../config/codex-hooks.example.json) is a
validated hook definition for `SessionStart`, `PreCompact`, and `SessionEnd`.
The installed dispatcher is inert while the vault configuration contains or
defaults to:

```yaml
lifecycle:
  enabled: false
```

Change the exact boolean to `true` only when the Owner wants automatic handling
of future permitted sessions in this trusted project. When enabled, Orca
locally applies eligibility and credential redaction before queue or provider
handoff. If exclusion or redaction cannot complete, nothing is sent. Setting it
back to `false` stops automatic transcript access, redaction, queueing, guidance
loading, and model calls; explicit operator commands remain available.

## Stop

Run `uv run orca --registered-adapter <configured-adapter-id> stop`. Orca uses
one-shot workers, so the command confirms that there is no daemon to terminate.

## Health check

Run `uv run orca --registered-adapter <configured-adapter-id> health`. It
validates configuration and reports queue count; it is not provider health.

## Repository regression check

**Verified repository procedure — 2026-08-30**

Working directory:

```text
/workspace/projects/orca
```

Command:

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
  tests/runtime/test_codex_provider.py \
  tests/runtime/test_codex_hook.py \
  tests/acceptance/test_readiness_boundaries.py \
  tests/acceptance/test_semantic_evaluation.py \
  tests/agentcairn/test_distiller.py
```

Expected result for the current checkout:

```text
Ran 185 tests

OK
```

This command passed 185 tests on 2026-08-30. It covers the implemented capture,
retry-spool primitives, Typed Memory and Project Summary contracts, project
mapping, bounded segmented processing, conflicts, candidates,
Manifest/checkpoint `0.2`, recoverable publication, scoped interaction profiles,
deterministic guidance, explicit bounded Recall, private disposable indexes,
AgentCairn adapters, configuration, one-shot runtime, attention, isolated
restart loop, and negative safety surfaces. It is not a deployed provider
health check or Phase 1 acceptance.
The accepted [Test Strategy](../07-quality/test-strategy.md) owns suite coverage.

## Routine operations

Use `orca rebuild`, `orca status`, and `orca recall <question>` only after valid
configuration and authorized private deployment. `orca queue-pointer` provides
the bounded PreCompact/explicit-save handoff. SessionEnd redacted spool handoff,
one-shot handling, and catch-up are library interfaces for the local hook
adapter. Conflict/candidate resolution still uses its owning explicit workflow.

The intended flow remains in [Runtime Architecture](../02-architecture/runtime.md).
Its design description must not be executed as if it were a current command.

## Logs and diagnostics

**Unavailable as an operator procedure:** There is no supported log command or
diagnostics interface.

The library slice publishes immutable `0.2` Run Manifests and local `0.2`
checkpoints with source-segment/operation/output joins and intent-first recovery.
Its meaning and paths are defined by the [Provenance
Ledger](../03-specifications/provenance-ledger.md), but no public inspection tool
exists. Do not inspect or publish local
`evidence/`, `index.md`, personal rollouts, private vault contents, credentials,
or retry material as a substitute for diagnostics.

## Backup

**Unavailable:** No Orca-specific backup procedure has been implemented or
verified. The checkout, configured vault, agent-owned source, and local runtime
state have different authority and recovery roles and must not be copied as one
undifferentiated backup.

No backup or synchronization command is currently supported. [Data
Architecture](../02-architecture/data-architecture.md) owns the classification
and recovery boundaries that a future procedure must preserve.

## Restore

**Unavailable:** No Orca-specific restore procedure has been implemented or
verified. Do not restore checkpoints, indexes, Manifests, or memory artifacts by
guessing from filenames or modification times.

## Recovery

No operator recovery command exists. The following are tested or designed
boundaries, not executable procedures:

| Condition | Current evidence | Safe boundary |
|---|---|---|
| Exact replay after checkpoint loss | **Tested library behavior** | Durable Manifest scan prevents a second semantic result and repairs the checkpoint with the exact Manifest locator |
| Failure before checkpoint publication | **Tested library behavior** | Leave progress unchanged so a later retry can recover |
| Interrupted `0.2` publication | **Tested library behavior; operator procedure unavailable** | A valid fixed publication intent completes without another semantic call; mismatch requires human repair |
| Partial trailing JSONL | **Tested library behavior** | Complete preceding records proceed while the incomplete tail remains deferred at the last complete byte position |
| Invalid or credential-bearing generated output | **Tested library behavior for output secrets** | Publish no affected output and leave progress retryable |
| Missing or stale retrieval index | **Verified isolated procedure** | Run `orca rebuild`; it rebuilds only from governed permitted source roots and leaves Markdown unchanged |
| Retry-spool failure or expiry | **Tested library behavior; operator procedure unavailable** | Private redacted creation, three attempts, 72-hour expiry, content-free receipt, and success cleanup are tested; no lifecycle hook invokes them yet |
| Interrupted project registration or relink | **Tested library behavior; operator procedure unavailable** | Preserve the Project Mapping Intent; matching partial state completes, while mismatch requires Owner repair |

Do not manually edit immutable Manifests or advance checkpoints to force
recovery. Record the failure and escalate until the owning implementation and
procedure exist.

## Human attention

Run `uv run orca --registered-adapter <configured-adapter-id> status`. The view
shows content-free counts, safe IDs, severity, and owning-workflow routes. It
does not resolve source state, recall memory, or make a model call.

Until that interface exists, do not claim that pending candidates, Unassigned
records, conflicts, stale blocking state, or repair items are reliably surfaced.
Use the owning accepted documents and preserve observed failure evidence.

## Rebuild derived data

Run `uv run orca --registered-adapter <configured-adapter-id> rebuild` to rebuild
interaction profiles, the private retrieval index, and Orca Status from their
governed sources. A mismatch fails closed without broad Recall fallback.

## Troubleshooting

| Symptom | Meaning in the current repository | Action |
|---|---|---|
| Orca start or health rejects configuration | Invalid or unauthorized local setup | Correct configuration through its owning file; do not bypass validation |
| Example configuration is still unchanged | Placeholder adapter, model, or paths are not deployable | Supply authorized ignored/local values; do not commit them |
| A Codex source item has an unknown shape | Expected fail-closed connector behavior | Preserve the source and update only after the supported adapter contract is verified |
| Recall reports missing or stale index | Derived state needs reconciliation | Run `orca rebuild`; do not scan or edit vault Markdown as a workaround |
| Project setup or relink is unavailable | Accepted implementation gap | Do not hand-edit `project.md` and `config/host.yaml` as a substitute |
| Orca Status reports an integrity item | An owning source cannot be safely resolved | Use the reported owning workflow; Status itself never repairs state |
| A regression test fails | Current code no longer matches the exercised baseline | Preserve output and diagnose before making a current verification claim |

## Known limitations

- Phase 1 is not deployed for routine use.
- The CLI and isolated local loop are verified with synthetic data. One
  authorized, redacted two-turn private provider/candidate canary passed; it did
  not establish broad routine usefulness.
- The Owner enabled automatic handling and the bounded lifecycle canary passed
  SessionStart, PreCompact, processing, SessionEnd deduplication, and detached
  replay. This task's sandbox blocked nested Codex state-database writes; the
  provider worker and replay required normal local Codex state access.
- Automatic future-session handling is currently enabled. Set the exact boolean
  back to `false` to stop it before transcript access.
- The accepted Acceptance Plan and Test Strategy define quality authority but
  do not make unavailable runtime procedures executable.
- No procedure in this runbook authorizes Canonical Memory mutation, public
  service exposure, or use of later-phase/legacy code.

## Escalation

Stop and request Owner direction when:

- a procedure would require a personal vault, private rollout, credential,
  ignored runtime state, or external provider access;
- recovery would require deletion, checkpoint manipulation, Manifest rewriting,
  or an unverified rebuild;
- observed behavior differs from [Current Status](../STATUS.md) or an accepted
  specification;
- a command exists only in `legacy/manual-prototype/`, historical evidence, or a prototype; or
- implementation or product-design work is required. That work belongs in the
  separate implementation task.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Current implementation state:** [Current Status](../STATUS.md)
- **Runtime behavior:** [Runtime Architecture](../02-architecture/runtime.md)
- **Deployment boundary:** [Deployment Architecture](../02-architecture/deployment.md)
- **Data and recovery boundary:** [Data Architecture](../02-architecture/data-architecture.md)
- **Security boundary:** [Security and Trust](../02-architecture/security-and-trust.md)
- **Configuration contract:** [Configuration](../03-specifications/configuration.md)
- **Provenance contract:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Acceptance:** [Phase 1 Acceptance Plan](../07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](../07-quality/test-strategy.md)
