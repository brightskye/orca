---
id: DEPLOYMENT-LOCAL
title: Set up Orca
document_type: deployment-guide
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-09-06
---

# Set up Orca

Use this guide to install Orca, configure its local vault, connect Codex hooks,
and run a first controlled test. For everyday use, troubleshooting, backup,
and recovery, see [Using and maintaining Orca](runbook.md).

Phase 1 runs locally with one WSL runtime and one vault. It exposes no network
service and does not enable Canonical Memory changes.

## Readiness before activation

Read [Current](../project-record/current.md) before deployment or activation.
The pending RFC-0004 review limits routine private capture; historical Phase 1
acceptance does not clear those findings. The steps below describe the local
installation procedure and do not establish that its outstanding gaps are fixed.

## What setup provides

After setup:

- the `orca` and `orca-codex-hook` entry points run from the checkout;
- ignored host configuration points to one authorized vault, runtime directory,
  and Codex rollout store;
- the vault selects the `codex-cli` adapter and `gpt-5.6-luna` model;
- one selected project-local or user-level Codex hook definition is reviewed
  and trusted for the intended scope;
- automatic lifecycle handling is controlled by the exact
  `lifecycle.enabled` boolean in the vault; and
- validation, health, rebuild, status, and a bounded lifecycle canary provide
  deployment evidence for assessment against Current and the Acceptance plan.

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

## 6. Review and install the Codex hook

Codex can load hooks from the current repository or from the user configuration
under `~/.codex/hooks.json`. Use one Orca hook definition on a host. If both
sources contain the Orca hook, Codex runs both and one conversation can be
queued twice.

[`config/codex-hooks.example.json`](../../config/codex-hooks.example.json) is
the project-local template. It resolves the Orca package from the current Git
root, so use it only when the hook is installed in the Orca checkout. The
tracked [`.codex/hooks.json`](../../.codex/hooks.json) is the current checkout
copy; compare it with the template before trusting it.

For other mapped repositories, use the reviewed
[`config/codex-hooks.user.example.json`](../../config/codex-hooks.user.example.json)
from the user-level hook layer. It runs the package from the Orca checkout and
does not assume that the active repository has a `uv` project. Set these values
in the same environment that starts Codex:

```bash
export ORCA_CHECKOUT=/absolute/path/to/orca
export ORCA_HOST_CONFIG=/absolute/path/to/orca/config/host.yaml
export UV_CACHE_DIR=/tmp/orca-uv-cache
```

The user-level command checks both variables, then uses
`uv run --project "$ORCA_CHECKOUT" --no-sync`; it therefore runs the installed
Orca environment without treating the active repository as the project or
performing a package sync inside a hook. Run the installation step in this
guide first, including the `agentcairn` extra. The hook uses
`ORCA_HOST_CONFIG` to load the shared host configuration. Keep both paths
absolute. The project and user templates cover `startup`, `resume`, `clear`,
and `compact`; their `SessionEnd` timeout is the Codex-supported maximum of
three seconds.

Before a controlled run, open `/hooks` in Codex, review the exact active hook
source and command, and trust it only after the command and paths are correct.
Codex asks for review again when the hook definition changes. Do not use a
trust bypass for this test. A hook trust review and the template timeout are
configuration evidence; they do not prove observed hook wall time.

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

The provider canary uses the isolated Codex test environment prepared for this
run. Do not connect the test to the normal private Codex state or to a private
vault.

### Controlled two-session continuity test

Run this test only with a separate test host configuration, test vault, test
runtime, and disposable Git workspace. Do not point it at the normal
`config/host.yaml`, the normal vault, or the normal runtime. The configured
rollout store may remain the Codex-owned store, but this test must use one new
synthetic conversation and must not run catch-up or scan other histories.

Set the test paths in the shell that starts Codex:

```bash
export ORCA_CHECKOUT=/absolute/path/to/orca
export ORCA_HOST_CONFIG=/absolute/path/to/test-host.yaml
export UV_CACHE_DIR=/tmp/orca-uv-cache
```

The test host file must point to a new test vault and test runtime and keep
`lifecycle.enabled: false` until the setup checks pass. The registration command
adds the exact mapping for the disposable workspace; do not hand-edit the
registry or host mapping.

If the workspace is not already registered, run this from any directory:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run --project "$ORCA_CHECKOUT" orca \
  --host-config "$ORCA_HOST_CONFIG" project register \
  --root "<absolute-disposable-workspace>" --alias orca-control
```

Install one project-local hook in the disposable workspace only. Do not copy an
Orca hook into `~/.codex/hooks.json` for this test, and do not keep another Orca
hook source active. The portable template is used here because the disposable
workspace is not the Orca package checkout:

```bash
mkdir -p "<absolute-disposable-workspace>/.codex"
cp "$ORCA_CHECKOUT/config/codex-hooks.user.example.json" \
  "<absolute-disposable-workspace>/.codex/hooks.json"
```

Start Codex in the disposable workspace. Run `/hooks`, review the project-local
definition and its exact command, and trust it only after confirming that it
uses the exported test paths. The hook receives `ORCA_HOST_CONFIG` from the
Codex process environment. The Orca CLI does not read that variable by itself;
every CLI command below therefore passes `--host-config "$ORCA_HOST_CONFIG"`.

Before enabling the lifecycle, run:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run --project "$ORCA_CHECKOUT" orca \
  --host-config "$ORCA_HOST_CONFIG" validate
UV_CACHE_DIR=/tmp/orca-uv-cache uv run --project "$ORCA_CHECKOUT" orca \
  --host-config "$ORCA_HOST_CONFIG" health
UV_CACHE_DIR=/tmp/orca-uv-cache uv run --project "$ORCA_CHECKOUT" orca \
  --host-config "$ORCA_HOST_CONFIG" rebuild
UV_CACHE_DIR=/tmp/orca-uv-cache uv run --project "$ORCA_CHECKOUT" orca \
  --host-config "$ORCA_HOST_CONFIG" status
```

Confirm the commands use only the test vault and test runtime. Then set
`lifecycle.enabled: true` in the test vault configuration and begin the
disposable canary. Do not enable the normal vault.

In Session A, in the registered disposable workspace, send these two short
Owner messages:

```text
Message 1:
The Orca continuity canary topic is Paper Lantern.

Message 2:
Remember only this temporary test discussion: the next step is to compare Markdown and JSON export, and the open question is whether the export should include timestamps.
```

End Session A and wait for the bounded worker to finish. Then run the same
`health`, `rebuild`, and `status` commands with the test host config. Confirm
that the queue is empty, the summary is under the test vault's mapped project
`conversation-summaries` directory, and no Canonical Memory file changed. Keep
the generated conversation reference and source path for Session B.

Start a fresh Session B in the same mapped workspace for the active recall
check. Ask:

```text
Please resume the Paper Lantern discussion. What was the next step, and what question was still open?
```

If Codex does not invoke the supplied command, run the equivalent explicit
query from the Orca checkout, with the exact mapped project selector:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache uv run --project "$ORCA_CHECKOUT" orca \
  --host-config "$ORCA_HOST_CONFIG" recall \
  "Paper Lantern next step and open question" --project-alias orca-control
```

The active recall result passes when it stays in `orca-control`, identifies the
Markdown and JSON comparison as the next step, identifies timestamps as the
open question, and shows a source reference. Equivalent wording is expected;
invented decisions or a result from another project fail the check.

Repeat Session B from a fresh conversation for the passive recall check. Say
only:

```text
Let's continue deciding the Paper Lantern export.
```

The passive check passes only if Codex recognizes that earlier context is
needed, uses the supplied scoped recall command, and responds with the same
topic, next step, open question, and source reference. If it does not use the
command, record passive recall as not demonstrated and use explicit recall for
continued testing; do not treat the startup instructions as proof of automatic
agent behavior.

When the checks finish, set `lifecycle.enabled` back to `false` in the test
vault, run the test-host `health` and `status` commands, and preserve the
content-free evidence. Record any hook timeout or failure warning. The
configured `SessionEnd` limit is three seconds, but no observed wall-time
result is claimed until the controlled run measures or reports it. Leave the
normal vault, runtime, hook layer, and lifecycle setting unchanged.

## After the first test

Use [Using and maintaining Orca](runbook.md) for routine commands:
[catch-up](runbook.md#optional-periodic-catch-up),
[backup](runbook.md#backup), [restore to staging](runbook.md#restore),
and [stopping automatic handling](runbook.md#stop).

If health or status reports a problem, preserve queues, retry spools, Manifests,
checkpoints, and published memory. Follow the
[recovery procedure](runbook.md#recovery); deleting this state is not a rollback.

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
- [ ] Any controlled continuity test uses a separate test host, vault, and runtime.
- [ ] The controlled test installs one project-local hook in the disposable workspace only.
- [ ] No user-level Orca hook is active during the controlled test.
- [ ] The Owner authorizes automatic lifecycle use and the exact canary sample.
- [ ] Lifecycle is enabled and the bounded canary passes.
- [ ] If periodic catch-up is required, its separate local scheduling decision
      is recorded.
- [ ] Queue returns to zero; outputs are secret-free and noncanonical.
- [ ] Canonical Memory remains unchanged.
- [ ] If backups are required, GPG is installed, the recipient is Owner-selected,
      lifecycle is disabled, and no pending recovery or queue state remains.

## Related documents

- **Routine operation and recovery:** [Using and maintaining Orca](runbook.md)
- **Current implementation:** [Current Status](../project-record/current.md)
- **Configuration contract:** [Configuration](../specifications/configuration.md)
- **Deployment boundaries:** [Deployment Architecture](../architecture/deployment.md)
- **Security boundaries:** [Security and Trust](../architecture/README.md#security-and-trust)
- **Acceptance evidence:** [Phase 1 Acceptance Plan](../quality/acceptance.md)
