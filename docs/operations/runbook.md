---
id: RUNBOOK-LOCAL
title: Using and maintaining Orca
document_type: runbook
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-09-06
---

# Using and maintaining Orca

Use this guide after [setting up Orca](setup.md). It covers daily commands,
project registration, recall, troubleshooting, backup, and recovery for the
local Phase 1 installation.

Check [Current](../project-record/current.md) for deployment readiness and
known limits before using private memory. Exact runtime behavior and
configuration rules belong to [Specifications](../specifications/README.md).

## Find a task

- [Register or relink a project](#project-registration-and-relink)
- [Start](#start), [stop](#stop), or [check health](#health-check)
- [Recall a conversation](#conversation-recall)
- [Check pending work](#routine-operations) or [run catch-up](#optional-periodic-catch-up)
- [Review candidates and conflicts](#owner-review-workflows)
- [Back up](#backup), [restore to staging](#restore), or [recover an interrupted operation](#recovery)
- [Troubleshoot](#troubleshooting)

## Prerequisites

For the commands in this guide:

- Work from the Orca project checkout.
- Use Python 3.11 or newer through `uv`.
- Use a writable cache outside the repository, such as
  `/tmp/orca-uv-cache`.
- Do not point tests at a personal vault or real Codex rollout store.

New private samples, providers, vaults, or expanded lifecycle scope require
separate Owner authorization.

The [controlled continuity test](setup.md#controlled-two-session-continuity-test)
uses its own test host configuration, vault, and runtime. Its Codex rollout
store is used only for the new synthetic session; do not run catch-up or inspect
other histories during that test.

## Installation

Follow the [Setup guide](setup.md#1-install-the-local-environment).
It installs the local package environment and verifies the tracked project hook
configuration. It installs no daemon.

## Configuration

Follow the [Setup guide](setup.md#3-configure-the-host) to create the
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
  [Configuration Specification](../specifications/configuration.md).

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

### Automatic session handling

Follow [hook setup](setup.md#6-review-and-install-the-codex-hook) to choose one
hook source, review its command and paths in Codex, and trust it. Changed hook
definitions need another review. The
[activation step](setup.md#7-enable-automatic-lifecycle-handling) explains when
to enable `lifecycle.enabled`.

Enabled hooks apply local eligibility checks and credential redaction before
handoff. To pause them, follow [Stop](#stop). Explicit commands remain available.

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

To stop new automatic handling, set this in the vault configuration:

```yaml
lifecycle:
  enabled: false
```

Hooks and catch-up stop before transcript discovery. Workers leave
automatic units that have not started pending, without consuming an attempt.
A provider request already in progress cannot be cancelled this way. Explicit
commands remain available.

Check the result:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca validate
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca health
```

`uv run orca stop` confirms that there is no daemon to terminate; it does not
replace the lifecycle setting. Preserve queued work and published memory. Use
[Recovery](#recovery) if health or status reports an unresolved operation.

## Health check

Run `uv run orca health`. It
validates configuration and reports queue count; it is not provider health.

## Repository regression check

Run the canonical active regression command in
[Test Strategy](../quality/test-strategy.md#current-and-target-commands)
from the repository root. That document owns suite selection and verification
mechanics. [Current](../project-record/current.md) owns recorded results and
their limits. A regression pass does not establish deployment readiness.

## Routine operations

After [setup](setup.md), use `orca status` to check pending work,
`orca rebuild` to refresh derived data, and `orca recall <question>` to
retrieve a discussion.

Hooks hand work to a separate worker. `orca queue-pointer` provides the
bounded PreCompact or explicit-save handoff. SessionEnd saves only permitted,
redacted evidence before returning, then starts the worker separately. The
measured shutdown time and its limits are recorded in
[Current](../project-record/current.md#controlled-cli-trial--2026-09-06).

A worker handles up to 20 queued items by default. Transient failures retry
after one and two seconds, up to three attempts. A terminal failure is retained
while other independent work continues.

If the worker reports `pending`, check `orca status` for `pending-work`.
The queue may remain because the worker reached its limit, lifecycle handling
is disabled, or a retry cycle could not finish. Pending work is not completion.
Use the reported workflow to investigate; candidate and conflict decisions
belong to [Owner review](#owner-review-workflows).

Catch-up reads source metadata and queues only mapped Project or explicitly
confirmed General histories. Unassigned histories are skipped without provider
access. It remembers the last handed-off byte, so later runs read only new
complete records; an existing history may need an initial scan. Sources must
stay inside the configured rollout store. An unsafe source produces a
`source-discovery` item while other histories continue.

## Optional periodic catch-up

Orca exposes a bounded catch-up command but installs no daemon or OS scheduler:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca catch-up \
  --reasoning-effort xhigh --max-sources 20
```

The configured `cadence.catch_up_minutes` is the accepted interval, not an
installed timer. Run the command manually, or connect it to a separately
authorized local scheduler. It makes no provider call when it finds no eligible
work.

## Conversation recall

Active recall means asking Codex to resume or remember a discussion. Passive
recall means Codex using the same command when prior context is needed. An enabled
SessionStart hook supplies an executable command with the resolved project or
confirmed General scope. It supplies instructions, not an automatic memory
search. Actual agent-initiated use remains subject to Codex following the guidance.

From a mapped project, `orca recall "<specific question>"` resolves the exact
workspace mapping. Select another project explicitly with `--project-id` or
`--project-alias`. Use `--scope general` or `--scope unassigned` for those scopes;
an unmapped workspace cannot search all projects by default. Existing scripts
that depended on an unscoped search must now supply an explicit selector.
When the command is run from another mapped repository, run it through the Orca
checkout environment with its absolute `--host-config` path, as in the
[controlled continuity procedure](setup.md#controlled-two-session-continuity-test).

To continue a known conversation, use its returned `conv:<purpose>--<id>`
reference as the question. The exact summary comes first and includes its state
and next steps within the configured budgets. Returned Markdown paths identify
the stored source. Missing or ambiguous context should be reported rather than
filled in from guesses.

The existing designated storage area is
`System/Orca Memory/shallow/projects/<project-alias>/conversation-summaries/`
inside the configured wiki vault, with corresponding `general` and `unassigned`
areas. The files remain distilled conversation context, separate from accepted
wiki knowledge. No vault move or schema migration is needed for this alignment.

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

The component flow is in [Runtime Architecture](../architecture/README.md#runtime).
Exact coordination belongs to [Runtime](../specifications/runtime.md).
Its design description must not be executed as if it were a current command.

## Logs and diagnostics

**Unavailable as an operator procedure:** There is no supported log command or
diagnostics interface.

The library slice publishes immutable `0.2` Run Manifests and local `0.2`
checkpoints with source-segment/operation/output joins and intent-first recovery.
Its meaning and paths are defined by the [Provenance
Ledger](../specifications/provenance.md), but no public inspection tool
exists. Do not inspect or publish local
`.local/evidence/`, `.local/index.md`, personal rollouts, private vault contents, credentials,
or retry material as a substitute for diagnostics.

## Backup

[Backup](../specifications/backup.md) owns archive membership, validation, and
staging semantics. This section owns the operator procedure.

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

The [Backup specification](../specifications/backup.md#membership) owns the
exact contents and exclusions. Confirm that the selected vault and local GPG
recipient are correct before relying on this recovery copy.

Verify an archive before relying on it:

```bash
uv run orca backup verify --source <absolute-private-backup-path>
```

Verification works without host configuration or the original vault. It still
requires locally installed GPG and the backup's decryption key.

Check the verification result before relying on the archive. The
[Backup specification](../specifications/backup.md#verification) owns validation
semantics; [Current](../project-record/current.md) records whether a real GPG
drill has been performed.

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

If the original installation or its configuration is lost, use explicit
standalone staging:

```bash
uv run orca backup stage --standalone \
  --source <absolute-private-backup-path> \
  --destination <absolute-new-private-recovery-path>
```

Choose a destination outside all live vaults, runtimes, and project checkouts.
Standalone mode does not load configuration and therefore cannot discover the
old live roots. It still verifies the archive, keeps staging private, and
rejects any destination that already exists. It never silently replaces normal
staging after a configuration error. Keep the decryption key recoverable
separately from the installation; Orca does not back up or manage it.

The recovered directory contains `vault/`, `manifest.json`, and any included
runtime cursor/scope-choice state. To validate recovery in a disposable setup,
create a fresh host configuration pointing to the recovered vault and a new
runtime, run `orca rebuild`, then check scoped recall and its source references.
Resuming automatic capture and reconnecting old source paths remain separate
operator decisions.

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
| Orca Status reports `runtime-retry` after exhaustion | Processing did not finish within the attempt limit | Read the indicated `failure-<work_id>.json` under local runtime receipts. New receipts include a fixed `failure_code`; `unobserved` or an older receipt without a code does not prove a model failure. Preserve the receipt and diagnose the category before retrying. Check the worker's result and Status, not only its process exit code. |
| Orca Status reports `source-discovery` | Catch-up rejected one malformed or out-of-store source without retaining its path or content | Inspect the configured rollout store through the owning Codex workflow; a later valid scan clears the matching receipt |
| Orca Status reports an integrity item | An owning source cannot be safely resolved | Use the reported owning workflow; Status itself never repairs state |
| A regression test fails | Current code no longer matches the exercised baseline | Preserve output and diagnose before making a current verification claim |

## Readiness and limitations

[Current](../project-record/current.md) records readiness findings, repairs,
and trial results. Keep private capture disabled until the remaining checks
are resolved and the Owner authorizes its use.

The [Acceptance plan](../quality/acceptance.md) owns acceptance criteria and
historical evidence limits. A documented command alone does not establish
readiness for routine capture. These procedures do not authorize canonical
mutation or a public service.

## When to ask for help

Ask the Owner before continuing when:

- a procedure would require a different private sample, vault, provider,
  credential mechanism, or lifecycle scope than the accepted deployment;
- recovery would require deletion, checkpoint manipulation, Manifest rewriting,
  or an unverified rebuild;
- observed behavior differs from [Current Status](../project-record/current.md) or an accepted
  specification;
- a command exists only in `legacy/manual-prototype/`, historical evidence, or a prototype; or
- implementation or product-design work is required. That work belongs in the
  separate implementation task.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Installation and activation:** [Setup guide](setup.md)
- **Current implementation state:** [Current Status](../project-record/current.md)
- **Runtime behavior:** [Runtime](../specifications/runtime.md)
- **Deployment boundary:** [Deployment Architecture](../architecture/deployment.md)
- **Data and recovery boundary:** [Data Architecture](../architecture/data.md)
- **Security boundary:** [Security and Trust](../architecture/README.md#security-and-trust)
- **Configuration contract:** [Configuration](../specifications/configuration.md)
- **Provenance contract:** [Provenance Ledger](../specifications/provenance.md)
- **Acceptance:** [Phase 1 Acceptance Plan](../quality/acceptance.md)
- **Test mechanics:** [Test Strategy](../quality/test-strategy.md)
