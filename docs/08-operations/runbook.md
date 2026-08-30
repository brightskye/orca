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

This runbook is `accepted`/`normative`. The active Phase 1 runtime is not deployed
and has no supported CLI, launcher, MCP server, lifecycle-hook installation,
health check, recall command, index rebuild command, or operator recovery
command. Sections marked **Unavailable** describe a real implementation gap, not
a hidden or implied procedure.

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

Runtime prerequisites such as a validated host configuration, configured vault,
provider credentials, lifecycle hooks, local worker, and retrieval index remain
planned and are not sufficient to make the service runnable today.

## Installation

**Unavailable:** There is no supported Phase 1 runtime installation procedure.
The project defines a Python package and test dependencies, but it exposes no
runtime entry point or installation verification command.

`uv run` may resolve the isolated environment needed for the verified regression
procedure below. That is test-environment preparation, not Orca deployment.

## Configuration

**Unavailable:** No active configuration loader or validator consumes the
accepted host and vault configuration interfaces.

- [`config/host.example.yaml`](../../config/host.example.yaml) is a safe tracked
  structural fixture for local host fields.
- [`config/orca-memory.example.yaml`](../../config/orca-memory.example.yaml) is a
  safe tracked structural fixture for vault policy fields.
- Actual `config/host.yaml`, credentials, paths, mappings, `.runtime/` state, and
  private memory must remain local and ignored.
- The vault path may eventually come only from `config/host.yaml` or
  `ORCA_VAULT_PATH`, with conflict-on-difference validation defined by the
  [Configuration Specification](../03-specifications/configuration.md).

Do not copy an example and infer that configuration is operational. No supported
operator procedure consumes private configuration yet.

## Start

**Unavailable:** The repository has no supported Orca runtime start command,
launcher, daemon, or deployed local MCP entry point.

## Stop

**Unavailable:** No runtime process is deployed, so there is no supported stop
procedure. Do not kill unrelated Codex, WSL, Python, or retrieval processes in
an attempt to stop Orca.

## Health check

**Unavailable:** No runtime health endpoint or command exists. A passing test
suite is regression evidence and must not be reported as deployed health.

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
  tests/agentcairn/test_distiller.py
```

Expected result for the current checkout:

```text
Ran 103 tests

OK
```

This command passed 103 tests on 2026-08-30. It covers the implemented capture,
retry-spool primitives, Typed Memory and Project Summary contracts, project
mapping, bounded segmented processing, conflicts, candidates,
Manifest/checkpoint `0.2`, recoverable publication, and AgentCairn Distiller
seams. It is not a runtime health check or Phase 1 acceptance.
The accepted [Test Strategy](../07-quality/test-strategy.md) owns suite coverage.

## Routine operations

**Unavailable:** Startup interaction-guidance loading, explicit recall,
`$orca-save`, `$orca-recall`, conflict review, lifecycle-hook processing,
periodic catch-up, index reconciliation, and routine vault operation are
accepted design but have no active operator interface.

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
| Missing or stale retrieval index | **Unavailable** | Leave Markdown unchanged; no rebuild command exists |
| Retry-spool failure or expiry | **Tested library behavior; operator procedure unavailable** | Private redacted creation, three attempts, 72-hour expiry, content-free receipt, and success cleanup are tested; no lifecycle hook invokes them yet |
| Interrupted project registration or relink | **Tested library behavior; operator procedure unavailable** | Preserve the Project Mapping Intent; matching partial state completes, while mismatch requires Owner repair |

Do not manually edit immutable Manifests or advance checkpoints to force
recovery. Record the failure and escalate until the owning implementation and
procedure exist.

## Human attention

**Unavailable:** Orca Status and its session reminder are accepted but not
implemented. The eventual local view will show content-free counts, safe IDs,
severity, and owning-workflow routes for unresolved repair and review work. It
will not show memory content, resolve an item, make a model call, or expose a
public notification surface.

Until that interface exists, do not claim that pending candidates, Unassigned
records, conflicts, stale blocking state, or repair items are reliably surfaced.
Use the owning accepted documents and preserve observed failure evidence.

## Rebuild derived data

**Unavailable:** No active projection/index reconciliation or rebuild command
exists. Retrieval indexes are designed to be disposable and rebuildable, but
that property is not yet exposed or verified operationally.

## Troubleshooting

| Symptom | Meaning in the current repository | Action |
|---|---|---|
| No Orca start or health command | Expected implementation gap | Do not invent one; check [Current Status](../STATUS.md) |
| Example configuration has no runtime effect | Configuration loader is planned | Do not treat examples as deployment |
| A Codex source item has an unknown shape | Expected fail-closed connector behavior | Preserve the source and update only after the supported adapter contract is verified |
| Partial final JSONL raises an error | Known capture divergence | Do not truncate or repair the agent-owned source manually |
| Recall, interaction guidance, hooks, or catch-up are unavailable | Planned capability | Do not substitute `legacy/manual-prototype/` behavior |
| Project setup or relink is unavailable | Accepted implementation gap | Do not hand-edit `project.md` and `config/host.yaml` as a substitute |
| Orca Status is unavailable | Accepted implementation gap | Do not claim unresolved human work is centrally visible or build an ad hoc dashboard |
| A regression test fails | Current code no longer matches the exercised baseline | Preserve output and diagnose before making a current verification claim |

## Known limitations

- Phase 1 is not deployed for routine use.
- The only verified executable procedure here is the repository regression
  command.
- Configuration, deployment, hooks, worker, spool, `0.2` publication intent,
  project setup/relink, retrieval, interaction, and operator recovery interfaces
  remain planned or partial. Orca Status and its session reminder are also
  planned.
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
