---
id: RUNBOOK-LOCAL
title: Phase 1 Local Runbook
document_type: runbook
status: accepted
authority: normative
implementation_status: implemented
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-31
last_verified_against_code: 2026-08-31
---

# Phase 1 local runbook

## Purpose

Describe the supported local Phase 1 operator procedures after deployment and
state their authority, privacy, and recovery limits plainly.

## This document owns

- Executable local start/stop, health, routine operation, diagnostics,
  backup/restore, recovery, rebuild, troubleshooting, and escalation procedures.

## This document does not own

- Installation, initial configuration, lifecycle activation, runtime behavior,
  configuration schemas, implementation status, or test strategy.

## Authority and status boundary

This runbook is `accepted`/`normative`. Phase 1 and its configured local
Codex/provider/vault deployment were accepted by the Owner on 2026-08-31. The
[Deployment Guide](deployment.md) owns installation, activation, and the
bounded first-canary procedure. This runbook does not authorize a different
vault, provider, sample, topology, or canonical mutation.

| Label | Meaning |
|---|---|
| **Verified repository procedure** | Executed successfully against the current checkout on the stated date |
| **Tested library behavior** | Covered by deterministic tests but not exposed as an operator command |
| **Unavailable** | Designed or expected, but no runnable Phase 1 procedure exists |

## Scope

This runbook covers the accepted `/workspace/projects/orca` Phase 1 deployment,
its configured local vault, and the current active regression command. It does
not authorize a synchronized vault, code under `legacy/manual-prototype/`, a
later-phase topology, or any canonical-memory mutation.

## Prerequisites

For the verified repository procedure:

- Work from the Orca project checkout.
- Use Python 3.11 or newer through `uv`.
- Use a writable cache outside the repository, such as
  `/tmp/orca-uv-cache`.
- Do not point tests at a personal vault or real Codex rollout store.

New private samples, providers, vaults, or expanded lifecycle scope require
separate Owner authorization.

## Installation

Follow the [Deployment Guide](deployment.md#1-install-the-local-environment).
It installs the local package environment and verifies the tracked project hook
configuration. It installs no daemon.

## Configuration

Follow the [Deployment Guide](deployment.md#3-configure-the-host) to create the
ignored host configuration and vault-local policy, then validate:

```bash
uv run orca validate
```

- [`config/host.example.yaml`](../../config/host.example.yaml) is a safe tracked
  structural fixture for local host fields.
- [`config/orca-memory.example.yaml`](../../config/orca-memory.example.yaml) is a
  safe tracked structural fixture for vault policy fields.
- Actual `config/host.yaml`, credentials, paths, mappings, `.runtime/` state, and
  private memory must remain local and ignored.
- The vault path comes only from `config/host.yaml` or `ORCA_VAULT_PATH`, with
  conflict-on-difference validation defined by the
  [Configuration Specification](../03-specifications/configuration.md).

Validation is read-only and must pass before another runtime command.

### Project registration and relink

Register one Owner-confirmed workspace and permanent Project Alias with:

```bash
uv run orca project register \
  --root <absolute-existing-workspace-root> --alias <unique-project-alias>
```

For another checkout that the Owner confirms is the same project, relink it to
the existing permanent identity:

```bash
uv run orca project relink \
  --root <absolute-existing-workspace-root> --project-id <project-id>
```

`--project-alias <existing-alias>` may be used instead of `--project-id`. Both
commands publish a private mapping intent first and reconcile the Project
Registry record and ignored host mapping recoverably. Registration creates one
permanent identity; relink does not create or rewrite the project record.

## Start

Run the deterministic session-start path with:

```bash
uv run orca start \
  --session-id <safe-session-id> --context general
```

This loads only guidance and the counts-only reminder; it performs no Recall or
conversation processing.

### Codex lifecycle-hook activation

The tracked [`.codex/hooks.json`](../../.codex/hooks.json) is the installed
project hook definition for `SessionStart`, `PreCompact`, and `SessionEnd`.
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
back to `false` stops new hook handling and catch-up before transcript discovery.
The worker reloads the setting before each automatic queued unit and leaves
disabled work pending without consuming an attempt. It cannot cancel a provider
request already in progress. Explicit operator commands remain available.

### Conversation scope

Enabled lifecycle hooks normalize the Codex working directory and use an exact
valid `project_root_mappings` entry automatically. To confirm that one unmapped,
genuinely projectless conversation belongs to General, record the explicit
Owner choice using its Codex session identity:

```bash
uv run orca scope general --conversation-id <safe-session-id>
```

To make the conversation Unassigned again:

```bash
uv run orca scope unassigned --conversation-id <safe-session-id>
```

The choice is a private, content-free local runtime record. A valid Project
mapping takes precedence over it. Without either proof, the lifecycle stays
Unassigned; Orca never asks the model to guess.

## Stop

Run `uv run orca stop`. Orca uses
one-shot workers, so the command confirms that there is no daemon to terminate.

## Health check

Run `uv run orca health`. It
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
  tests/runtime/test_owner_review.py \
  tests/runtime/test_backup.py \
  tests/runtime/test_codex_provider.py \
  tests/runtime/test_codex_hook.py \
  tests/acceptance/test_readiness_boundaries.py \
  tests/acceptance/test_semantic_evaluation.py \
  tests/agentcairn/test_distiller.py
```

Expected result for the current checkout:

```text
Ran 228 tests

OK
```

The current baseline command passed 228 tests on 2026-08-31. It covers the implemented capture,
retry-spool primitives, Typed Memory and Project Summary contracts, project
mapping, bounded segmented processing, conflicts, candidates,
Manifest/checkpoint `0.2`, recoverable publication, scoped interaction profiles,
deterministic guidance, explicit bounded Recall, private disposable indexes,
AgentCairn adapters, configuration, one-shot runtime, attention, isolated
restart loop, Owner-review/recovery commands, encrypted backup boundaries, and
negative safety surfaces. It is not a deployed provider health check, a real
GPG backup, an exact-revision lifecycle canary, or a Phase 1 acceptance.
The accepted [Test Strategy](../07-quality/test-strategy.md) owns suite coverage.

## Routine operations

Use `orca rebuild`, `orca status`, and `orca recall <question>` after the
[Deployment Guide](deployment.md) passes. `orca queue-pointer` provides
the bounded PreCompact/explicit-save handoff. SessionEnd redacted spool handoff
and one-shot handling run through the local hook adapter. A worker invocation
drains up to 20 queued items by default. A transient failure retries after one
and two seconds, up to three attempts by default; a terminal failure is retained
while later independent work continues. `worker: pending` means queued work
remains because the limit was reached, lifecycle was disabled, or a retry cycle
could not complete. Pending units appear as content-free `pending-work` items in
`orca status`. Run bounded catch-up
explicitly with `uv run orca catch-up --reasoning-effort xhigh --max-sources 20`;
Orca installs no timer or OS scheduler. Catch-up reads metadata first, queues
only mapped Project or explicitly confirmed General histories, skips Unassigned
histories without provider access, and remembers the last durably handed-off
byte so later runs read only new complete records. An existing history may need
one initial scan before its cursor exists. Each source is contained inside the
configured rollout store before metadata access. A malformed or unsafe source
creates a content-free `source-discovery` item while catch-up continues to later
histories. Conflict/candidate resolution still uses its owning explicit
workflow.

## Owner review workflows

These commands are explicit Owner decisions. They make no semantic-provider
call and never write Canonical Memory:

```bash
uv run orca candidate approve <candidate_id>
uv run orca candidate reject <candidate_id>

uv run orca conflict select <memory_id> --variant <variant_id>
uv run orca conflict acknowledge <memory_id>
uv run orca conflict resolve <memory_id> \
  --resolution-file <absolute-private-file> \
  --resolution-at <UTC-timestamp>
```

Candidate disposition requires the current status to be `pending`. Conflict
selection accepts an active or overflow variant; `acknowledge` keeps the
conflict unresolved; `resolve` reads an Owner-supplied private file. Each
operation writes one content-minimized receipt under the vault's
`System/Orca Memory/provenance/owner-reviews/` directory and keeps its fixed
post-images in a private local intent until verification. Status reports a
pending review or recovery item with a safe ID; it does not perform the
decision.

If a command is interrupted, recover only the safe operation ID:

```bash
uv run orca recovery owner-review <operation-id>
```

A path, identity, receipt, or before/after hash mismatch fails closed. Do not
edit the receipt, candidate, conflict record, or intent by hand; preserve it
for Owner repair.

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

**Operator command available; real private-vault execution not yet verified.**
The checkout, configured vault, agent-owned source, and local runtime state have
different authority and recovery roles and must not be copied as one
undifferentiated backup.

Before creating a backup:

- set the exact vault `lifecycle.enabled` value to `false`;
- settle all queue, retry-spool, publication, project-mapping, and Owner-review
  intents; and
- choose an absolute new output path outside both the vault and runtime, plus an
  explicit local GPG recipient.

Create the encrypted archive with:

```bash
uv run orca backup create \
  --recipient <gpg-recipient> \
  --output <absolute-private-backup-path>
```

The archive contains the full configured vault and only validated,
content-minimized runtime `source-cursors/` and `scope-choices/` JSON. It
excludes raw Codex rollouts, host configuration, credentials, queues, retry material, checkpoints,
indexes, locks, and other disposable runtime state. The command never
overwrites an existing output. The backup is encrypted by the locally
installed `gpg`; no recipient or key material is stored by Orca.

Verify an archive before relying on it:

```bash
uv run orca backup verify --source <absolute-private-backup-path>
```

Verification requires a private regular backup file, decrypts it into a private
temporary workspace, and checks the archive manifest, allowed paths, file types,
and every member hash. A real GPG backup and verification remain an operator
step for the configured deployment, not a claim of this repository check.

## Restore

**Staging only; never a live overwrite.** First verify the backup, then expose
its checked contents in a new private staging directory outside the live vault
and runtime:

```bash
uv run orca backup stage \
  --source <absolute-private-backup-path> \
  --destination <absolute-new-staging-path>
```

The destination must not already exist. Decryption and hash checks complete
before staging is published. The command reports `live_state_changed: false`;
it does not restore or merge any file into the configured vault, runtime,
configuration, credentials, or Codex source. Any later migration from staging
is a separate Owner-authorized procedure and is not defined in Phase 1.

## Recovery

Recovery commands are available for one safe operation ID. They never choose a
new outcome or make a semantic-provider call. The following boundaries and
commands apply:

| Condition | Current evidence | Safe boundary |
|---|---|---|
| Exact replay after checkpoint loss | **Tested library behavior** | Durable Manifest scan prevents a second semantic result and repairs the checkpoint with the exact Manifest locator |
| Failure before checkpoint publication | **Tested library behavior** | Leave progress unchanged so a later retry can recover |
| Interrupted `0.2` publication | **Tested library behavior; operator command available** | Run `orca recovery publication <operation-id>`; a valid fixed publication intent completes without another semantic call, while mismatch requires human repair |
| Partial trailing JSONL | **Tested library behavior** | Complete preceding records proceed while the incomplete tail remains deferred at the last complete byte position |
| Invalid or credential-bearing generated output | **Tested library behavior for output secrets** | Publish no affected output and leave progress retryable |
| Missing or stale retrieval index | **Verified isolated procedure** | Run `orca rebuild`; it rebuilds only from governed permitted source roots and leaves Markdown unchanged |
| Retry-spool failure or expiry | **Implemented lifecycle behavior; manual repair unavailable** | SessionEnd creates only permitted redacted retry material, the one-shot worker applies three attempts and 72-hour expiry, and success removes the spool |
| Interrupted project registration or relink | **Tested library behavior; operator command available** | Run `orca recovery project-mapping <operation-id>` with the same host configuration; matching partial state completes, while mismatch requires Owner repair |
| Interrupted Owner candidate/conflict review | **Tested library behavior; operator command available** | Run `orca recovery owner-review <operation-id>`; the fixed receipt and post-images complete without a semantic call, while mismatch requires Owner repair |

Do not manually edit immutable Manifests or advance checkpoints to force
recovery. Record the failure and escalate until the owning implementation and
procedure exist.

## Human attention

Run `uv run orca status`. The view
shows content-free counts, safe IDs, severity, and owning-workflow routes. It
does not resolve source state, recall memory, or make a model call.

Resolve every item only through its reported owning workflow. Status itself
never repairs or changes source state.

## Rebuild derived data

Run `uv run orca rebuild` to rebuild
interaction profiles, the private retrieval index, and Orca Status from their
governed sources. A mismatch fails closed without broad Recall fallback.

## Troubleshooting

| Symptom | Meaning in the current repository | Action |
|---|---|---|
| Orca start or health rejects configuration | Invalid or unauthorized local setup | Correct configuration through its owning file; do not bypass validation |
| Example configuration is still unchanged | Placeholder adapter, model, or paths are not deployable | Supply authorized ignored/local values; do not commit them |
| A Codex source item has an unknown shape | Expected fail-closed connector behavior | Preserve the source and update only after the supported adapter contract is verified |
| Recall reports missing or stale index | Derived state needs reconciliation | Run `orca rebuild`; do not scan or edit vault Markdown as a workaround |
| A project root is Unassigned | No exact approved mapping exists | Run `orca project register` for a new project or Owner-confirmed `orca project relink` for an existing identity; do not hand-edit `project.md` and `config/host.yaml` |
| Orca Status reports `pending-work` | One queued unit has not reached a terminal outcome | If lifecycle is intentionally off, leave it pending; otherwise run the owning worker path and preserve any reported failure receipt |
| Orca Status reports `source-discovery` | Catch-up rejected one malformed or out-of-store source without retaining its path or content | Inspect the configured rollout store through the owning Codex workflow; a later valid scan clears the matching receipt |
| Orca Status reports an integrity item | An owning source cannot be safely resolved | Use the reported owning workflow; Status itself never repairs state |
| A regression test fails | Current code no longer matches the exercised baseline | Preserve output and diagnose before making a current verification claim |

## Known limitations

- Phase 1 is accepted for the configured local runtime. The lifecycle toggle is
  normally disabled; release requires a bounded exact-revision lifecycle canary.
- The CLI and isolated local loop are verified with synthetic data. An earlier
  authorized, redacted two-turn private provider/candidate canary passed; it did
  not establish broad routine usefulness or verify this exact revision.
- Automatic future-session handling is normally disabled. Keep the exact
  boolean `false` except during the authorized bounded lifecycle canary.
- The encrypted backup and staging restore paths are covered at the fake-GPG
  boundary. A real GPG backup and verification of the configured private vault
  have not run in this reconciliation.
- The configured rebuild and explicit Recall procedures passed after the
  enabled canary. Recall correctly returned no candidate content because
  Knowledge Candidates are excluded from retrieval projections.
- The accepted Acceptance Plan and Test Strategy define quality authority but
  do not make unavailable runtime procedures executable.
- No procedure in this runbook authorizes Canonical Memory mutation, public
  service exposure, or use of later-phase/legacy code.

## Escalation

Stop and request Owner direction when:

- a procedure would require a different private sample, vault, provider,
  credential mechanism, or lifecycle scope than the accepted deployment;
- recovery would require deletion, checkpoint manipulation, Manifest rewriting,
  or an unverified rebuild;
- observed behavior differs from [Current Status](../STATUS.md) or an accepted
  specification;
- a command exists only in `legacy/manual-prototype/`, historical evidence, or a prototype; or
- implementation or product-design work is required. That work belongs in the
  separate implementation task.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Installation and activation:** [Phase 1 Local Deployment Guide](deployment.md)
- **Current implementation state:** [Current Status](../STATUS.md)
- **Runtime behavior:** [Runtime Architecture](../02-architecture/runtime.md)
- **Deployment boundary:** [Deployment Architecture](../02-architecture/deployment.md)
- **Data and recovery boundary:** [Data Architecture](../02-architecture/data-architecture.md)
- **Security boundary:** [Security and Trust](../02-architecture/security-and-trust.md)
- **Configuration contract:** [Configuration](../03-specifications/configuration.md)
- **Provenance contract:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Acceptance:** [Phase 1 Acceptance Plan](../07-quality/acceptance.md)
- **Test mechanics:** [Test Strategy](../07-quality/test-strategy.md)
