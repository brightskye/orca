---
id: DEPLOYMENT-LOCAL
title: Phase 1 Local Deployment Guide
document_type: deployment-guide
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

# Phase 1 local deployment guide

## Purpose

Deploy the accepted Orca Phase 1 runtime in one WSL checkout with one local
vault and Codex project lifecycle hooks. This is the authoritative installation,
configuration, activation, and first-verification procedure.

The deployment is local and project-scoped. It installs no daemon, exposes no
network service, and does not enable Canonical Memory mutation.

## Deployment result

After this procedure:

- the `orca` and `orca-codex-hook` entry points run from the checkout;
- ignored host configuration points to one authorized vault, runtime directory,
  and Codex rollout store;
- the vault selects the `codex-cli` adapter and `gpt-5.6-luna` model;
- the tracked `.codex/hooks.json` dispatcher is available to Codex in this
  project;
- automatic lifecycle handling is controlled by the exact
  `lifecycle.enabled` boolean in the vault; and
- validation, health, rebuild, status, and a bounded lifecycle canary establish
  deployment readiness.

## Before starting

Use the repository root as the working directory:

```bash
cd /workspace/projects/orca
```

Required local tools and access:

- Python 3.11 or newer through `uv`;
- a locally installed `codex` CLI;
- an authenticated Codex session, verified with `codex login status`;
- the authorized Orca vault directory;
- the Codex rollout directory; and
- a private runtime directory outside the vault.

For the optional encrypted-backup procedure, also install a local `gpg`
executable and have an Owner-selected recipient available. Orca does not store
or manage the recipient's private key.

Do not put the vault, runtime state, credentials, or real host configuration in
Git. Do not use a synchronized or remote-vault topology for Phase 1.

## 1. Install the local environment

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv sync --extra agentcairn
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca --help
```

This creates the checkout-local environment. Orca uses one-shot workers, so
there is no service to install or daemon to start.

## 2. Create the required directories

The configured vault, runtime directory, and rollout store must already exist
as directories before validation. The runtime directory must be outside the
vault. Create only the directory selected for this deployment; do not copy the
vault into the checkout.

For a new deployment, create the selected runtime directory and vault
configuration parent with their literal absolute paths:

```bash
mkdir -p "<absolute-private-runtime-path>"
mkdir -p "<absolute-vault-path>/System/Orca Memory"
```

The rollout store is owned by Codex. Point configuration at the existing Codex
rollout directory; do not create an empty substitute.

## 3. Configure the host

Copy the tracked structure and replace every placeholder with an authorized
local value:

```bash
cp --no-clobber config/host.example.yaml config/host.yaml
```

Do not overwrite an existing `config/host.yaml`; inspect and update it in place.

The resulting ignored `config/host.yaml` has this shape:

```yaml
schema_version: 1
host_id: <stable-local-host-id>
runtime: wsl
vault_path: <absolute-vault-path>
runtime_path: <absolute-private-runtime-path>
connectors:
  codex:
    rollout_store: <absolute-codex-rollout-directory>
project_root_mappings: []
```

Use WSL-visible absolute paths. `ORCA_VAULT_PATH` may supply the vault path, but
if it is also present in `config/host.yaml`, both values must resolve to the
same directory.

After validation, create mappings only through the recoverable operator
workflow documented in the [runbook](runbook.md#project-registration-and-relink),
not by editing `project_root_mappings` and `project.md` independently.

## 4. Configure the vault

For a new vault configuration, copy the example without overwriting an existing
file:

```bash
cp --no-clobber config/orca-memory.example.yaml \
  "<absolute-vault-path>/System/Orca Memory/orca-memory.yaml"
```

For the accepted Phase 1 deployment, set:

```yaml
provider:
  adapter: codex-cli
  model: gpt-5.6-luna
lifecycle:
  enabled: false
```

Keep the remaining accepted policy versions and budgets from the example.
Credentials never belong in this file; the `codex-cli` adapter uses the local
authenticated Codex session.

Start with lifecycle handling disabled. `false` returns before transcript
access, redaction, queueing, guidance loading, or a provider call.

## 5. Verify configuration and local state

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca validate
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca health
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca rebuild
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca status
```

Expected minimum results:

- `validate` prints `configuration: valid`;
- `health` reports valid configuration and a nonnegative queue count;
- `rebuild` refreshes derived profiles, indexes, and status state without
  changing governed Markdown; and
- `status` shows only content-free attention information.

`health` is not provider health and does not call the semantic provider.
Provider readiness requires both `codex login status` and the authorized
lifecycle canary.

## 6. Confirm the project hook installation

The deployed hook configuration is tracked at [`.codex/hooks.json`](../../.codex/hooks.json).
It must match [`config/codex-hooks.example.json`](../../config/codex-hooks.example.json)
and contain only the accepted `SessionStart`, `PreCompact`, and `SessionEnd`
dispatchers. No manual copy is required in this checkout.

The hooks resolve `config/host.yaml` from the repository. Set the absolute
`ORCA_HOST_CONFIG` environment variable only when intentionally using a
different host-config location.

This is a project-local hook deployment. Opening an unrelated repository does
not deploy Orca hooks there.

## 7. Enable automatic lifecycle handling

After the disabled-state checks pass and the Owner authorizes automatic use,
change only this vault setting:

```yaml
lifecycle:
  enabled: true
```

Enabling the lifecycle permits future eligible project sessions to use the
automatic path. It does not permit unredacted provider input: local eligibility
filtering and Secret Containment remain mandatory and fail closed.

The stop control for new automatic work is to set the exact boolean back to
`false`. Hooks and catch-up then stop before transcript discovery, and workers
leave not-yet-started automatic queue units pending. This cannot cancel a
provider request already in progress. It does not disable explicit operator
commands or delete queued or previously published state.

## 8. Run the first lifecycle canary

Use a new disposable Codex conversation in this project containing only two
short, non-sensitive Owner turns selected for the canary. Obtain Owner approval
for that exact sample before the provider call.

Exercise these lifecycle events through normal Codex use:

1. `SessionStart` loads only deterministic guidance and a counts-only reminder.
2. `PreCompact` queues the bounded rollout pointer and starts the detached
   `gpt-5.6-luna` worker at `xhigh` reasoning.
3. `SessionEnd` retains only permitted, locally redacted unprocessed evidence
   and deduplicates already completed work.

Then verify:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca health
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca rebuild
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca status
```

The canary passes when the queue returns to zero, generated output contains no
credential-like value, every output remains noncanonical, and any Knowledge
Candidate appears only in the Owner review workflow. No Canonical Memory file
may be created or changed.

On this host, detached provider work needs normal local Codex state access. A
task sandbox that blocks nested Codex state-database writes cannot establish
provider readiness; run the authorized canary from the normal local Codex
environment.

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

## 9. Optional encrypted backup

Create backups only while `lifecycle.enabled: false` and after all queue,
retry-spool, publication, project-mapping, and Owner-review intents are settled.
Choose a new private output path outside the vault and runtime, then run:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca backup create \
  --recipient <gpg-recipient> \
  --output <absolute-private-backup-path>
```

The encrypted archive contains the full configured vault plus only validated,
content-minimized `source-cursors/` and `scope-choices/` runtime JSON. It excludes
raw rollouts, host configuration, credentials, queues, retry material,
checkpoints, indexes, locks, and other disposable runtime state. Existing
output is never overwritten.

Verify before relying on the file:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca backup verify \
  --source <absolute-private-backup-path>
```

To inspect a verified backup, stage it into a new private directory outside the
live vault and runtime:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca backup stage \
  --source <absolute-private-backup-path> \
  --destination <absolute-new-staging-path>
```

Staging never overwrites or merges into live state. A real GPG backup of the
configured vault is an operator verification step and is not claimed by this
repository procedure.

## Disable or roll back

To stop new automatic handling, set `lifecycle.enabled: false`, then run:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca validate
UV_CACHE_DIR=/tmp/orca-uv-cache uv run orca health
```

Do not delete queues, retry spools, Manifests, checkpoints, or published memory
as a rollback technique. Preserve the state and follow the [Local
Runbook](runbook.md) when health or status reports an unresolved item.

## Deployment checklist

- [ ] Checkout is `/workspace/projects/orca` on the intended branch.
- [ ] `uv sync --extra agentcairn` and `orca --help` pass.
- [ ] `codex login status` confirms local authentication.
- [ ] Vault, runtime, and rollout directories exist and are separate as required.
- [ ] Ignored `config/host.yaml` contains only authorized absolute local paths.
- [ ] Vault configuration uses `codex-cli` and `gpt-5.6-luna`.
- [ ] Lifecycle starts disabled.
- [ ] Validate, health, rebuild, and status checks pass.
- [ ] The tracked project hook configuration is present.
- [ ] The Owner authorizes automatic lifecycle use and the exact canary sample.
- [ ] Lifecycle is enabled and the bounded canary passes.
- [ ] If periodic catch-up is required, its separate local scheduling decision
      is recorded.
- [ ] Queue returns to zero; outputs are secret-free and noncanonical.
- [ ] Canonical Memory remains unchanged.
- [ ] If backups are required, GPG is installed, the recipient is Owner-selected,
      lifecycle is disabled, and no pending recovery or queue state remains.

## Related documents

- **Routine operation and recovery:** [Phase 1 Local Runbook](runbook.md)
- **Current implementation:** [Current Status](../STATUS.md)
- **Configuration contract:** [Configuration](../03-specifications/configuration.md)
- **Deployment boundaries:** [Deployment Architecture](../02-architecture/deployment.md)
- **Security boundaries:** [Security and Trust](../02-architecture/security-and-trust.md)
- **Acceptance evidence:** [Phase 1 Acceptance Plan](../07-quality/acceptance.md)
