---
id: SPEC-CONFIGURATION
title: Orca Configuration Specification
document_type: specification
status: accepted
authority: normative
implementation_status: planned
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-29
supersedes: []
host-schema: orca-host-config/1
vault-schema: orca-memory-config/0.1
project-mapping-intent-schema: orca-project-mapping-intent/0.1
---

# Orca Configuration Specification

## Purpose

Define the Configuration interface for one authorized Phase 1 WSL runtime and
one configured Orca vault. The Governance module hides source loading,
precedence, normalization, and validation behind this interface.

## Scope

This specification owns configuration sources, local-versus-vault field
ownership, current defaults, precedence, deterministic validation, and secret
and path handling. It does not own operational commands, deployment steps, or
the artifact schemas selected by configuration.

## Configuration sources

| Source | Owns | Location and authority |
|---|---|---|
| `config/host.yaml` | Host identity, WSL runtime kind, vault path, runtime path, connector source location, and machine-specific Project Root Mappings | Local, required, ignored, unsynchronized |
| `ORCA_VAULT_PATH` | Optional alternate source for the vault path only | Local process environment |
| `System/Orca Memory/orca-memory.yaml` | Phase 1 policies, cadence, provider selection, privacy and interaction policy versions, and budgets | Configured private vault |
| Project `project.md` records | Permanent `project_id` and current unique Project Alias | Configured private vault; collectively the Project Registry |
| Local runtime state | Rebuildable mappings, indexes, locks, queues, checkpoints, retry material, and receipts | Outside vault and Git; never configuration authority for memory semantics |

Tracked source MUST contain only a safe example. Actual host values,
credentials, private memory, and generated runtime state MUST NOT be copied into
the repository.

## Host configuration

The `orca-host-config/1` interface is represented by the tracked safe
fixture [`config/host.example.yaml`](../../config/host.example.yaml):

```yaml
schema_version: 1
host_id: replace-with-unique-host-id
runtime: wsl
vault_path: /absolute/path/to/Orca
runtime_path: /workspace/projects/orca/.runtime
connectors:
  codex:
    rollout_store: /absolute/path/to/Codex/rollouts
project_root_mappings: []
```

| Field | Required rule |
|---|---|
| `schema_version` | Exactly integer `1` |
| `host_id` | Required nonempty stable local host identity |
| `runtime` | Exactly `wsl` in Phase 1 |
| `vault_path` | Absolute normalized path to the configured Orca vault unless supplied by `ORCA_VAULT_PATH` |
| `runtime_path` | Absolute normalized local path outside the vault |
| `connectors.codex.rollout_store` | Absolute normalized path to the agent-owned Codex rollout store |
| `project_root_mappings` | Sequence of zero or more exact `root` and `project_id` mappings |

`host_id` MUST match `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Each mapping `root`
MUST be an absolute normalized machine-local path. Each `project_id` MUST name
one existing Project Registry identity. Normalized roots MUST be unique;
multiple distinct roots MAY map to one project. Unknown keys MUST fail schema
validation.

## Vault configuration and defaults

`System/Orca Memory/orca-memory.yaml` uses the schema
`orca-memory-config/0.1`. The tracked safe fixture
[`config/orca-memory.example.yaml`](../../config/orca-memory.example.yaml)
defines its complete key shape.

| Group | Required fields and rules |
|---|---|
| `provider` | `adapter` is a registered Semantic Provider Adapter identity; `model` is the exact configured model identity |
| `cadence` | `catch_up_minutes` and `index_reconcile_minutes` are positive integers; both default to `15` |
| `privacy` | `redaction_policy` is exactly `orca-secret-containment/0.1` |
| `processing` | `processor_policy` is exactly `orca-processor/0.1` |
| `retry` | `max_attempts` defaults to `3`; `retention_hours` defaults to `72`; both are positive integers |
| `interaction` | Exact accepted observation, aggregation, and guidance policy versions |
| `budgets` | The three groups below with exact keys and behavior-owner ceilings |

The provider Adapter and model have no repository-wide default. Both MUST be
configured explicitly and recognized by the local runtime before a semantic
call. Credentials and command arguments MUST NOT be stored in this file; an
Adapter obtains them through its separately authorized local mechanism.

The `budgets` mapping exposes three groups whose exact defaults and behavioral
meanings have one owner:

| Configuration group | Required keys | Default owner |
|---|---|---|
| `processor` | `model_window_tokens`, `input_tokens`, `output_tokens`, `new_evidence_tokens`, `preceding_overlap_tokens`, `continuation_summary_tokens`, `project_summary_tokens`, `related_records_tokens`, `max_related_records` | [Processing Pipeline](processing-pipeline.md#context-budget) |
| `recall` | `total_tokens`, `per_document_tokens`, `exact_continuation_tokens`, `max_results` | [Retrieval Contract](retrieval-contract.md#result-budget-and-excerpts) |
| `interaction` | `auto_load_tokens` | [Interaction Guidance](interaction-guidance.md#compilation) |

Configuration MAY lower a behavior owner's default. It MUST NOT silently raise
a ceiling above the accepted behavior owner's value. Unknown top-level, group,
or budget keys MUST fail schema validation.

## Precedence

The vault path MUST come from `config/host.yaml` or `ORCA_VAULT_PATH`; it MUST
never be hard-coded in tracked source.

The precedence rule is:

1. If exactly one source supplies a valid path, use its normalized value.
2. If both supply the same normalized path, use that path.
3. If both supply different normalized paths, fail validation and identify the
   conflict without printing private file contents.

No other environment variable may override host or vault configuration. A later
change requires a new accepted schema version.

## Project resolution and mapping

Project resolution is deterministic and makes no model call. It returns exactly
one of `mapped`, `worktree-reused`, `owner-choice-required`, `unassigned`, or
`error`.

Discovery validates configuration and Project Registry records, requires an
existing directory, and normalizes the workspace root. A Git workspace uses its
absolute Git top level; a non-Git workspace uses the explicitly selected root.
Normalization resolves symlinks, removes unnecessary trailing separators, and
uses the host filesystem's case-comparison rule.

An exact valid root mapping returns `mapped` with no write. A recognized Git
worktree may return `worktree-reused` and add a mapping automatically only when
its normalized Git common directory exactly matches one mapped local worktree,
that mapping resolves to one valid Project Identity, and no evidence conflicts.
Remote URL, branch, commit, repository name, folder name, and semantic
similarity are suggestions only and never authorize mapping.

Every other unknown root, move, clone, non-worktree checkout, alias collision,
or ambiguous state requires one Owner choice:

1. create a new project with a confirmed unique Project Alias;
2. link to one explicitly selected existing Project Identity; or
3. keep Unassigned and make no registry or configuration write.

Unknown never becomes General. Registration lets Storage allocate one permanent
ID and publish the fixed `orca-project/0.1` record before atomically adding the
mapping. Relinking adds only the confirmed mapping and does not rewrite
`project.md`. An old missing mapping is not removed automatically.

Before either final file changes, the workflow writes one private
`orca-project-mapping-intent/0.1` at
`.runtime/project-mappings/<operation-id>/intent.json` under one local mapping
lock. It records the action, normalized local evidence, fixed identity and
alias, target record before/after hash, host-config before/after hash and staged
post-image, time, and policy versions. It contains no memory content or
credentials and never enters the vault or a Run Manifest.

Recovery reuses the same identity and fixed post-images. Matching partial state
is completed and verified; state matching neither before nor after, a missing or
invalid intent with an unlinked record, or a mapping/record disagreement stops
for Owner repair. The intent is deleted only after both final states verify.
Atomic host-config replacement preserves every unrelated validated value.

## Output

Successful loading returns one immutable validated configuration value for the
current process. It contains normalized host, vault, runtime, connector,
Project Root Mapping, provider, policy-version, cadence, and budget settings
whose fields are defined by the applicable schemas. It contains no fallback guesses,
raw credential values in diagnostics, or memory authority derived from paths.

## Required behavior

1. Governance MUST load and validate configuration before capture, processing,
   publication, recall, or interaction-profile loading.
2. Validation MUST be deterministic and make no model call.
3. All configured paths MUST be absolute after normalization. The runtime path
   MUST be outside the configured vault.
4. `config/host.yaml`, runtime state, raw sessions, retry material, credentials,
   caches, and locks MUST remain outside Git. Runtime state and raw sessions MUST
   also remain outside the vault.
5. Project Root Mappings MUST remain local and unsynchronized. Multiple roots
   MAY map to one permanent `project_id` only through an accepted mapping or
   Owner-confirmed relink.
6. Recognized Git worktrees MAY reuse an existing project mapping through their
   common Git directory. A moved folder or new clone MUST NOT silently inherit
   another project's identity.
7. A Project Alias MUST resolve to one permanent `project_id`; an alias is never
   itself authority or project identity.
8. A larger provider model window MUST NOT increase Orca budgets automatically.

## Validation invariants

- Every active host has one stable `host_id`, one `wsl` runtime, one vault root,
  and one runtime root.
- The configured vault owns memory artifacts; the checkout owns code and
  documentation; the runtime root owns disposable and recovery state.
- Processor category ceilings fit within `processor.input_tokens`, and input
  plus output ceilings fit within `model_window_tokens`, as defined by the
  Processing Pipeline.
- Recall exact-conversation allocations and ordinary document allocations fit
  within `recall.total_tokens`, as defined by the Retrieval Contract.
- Every budget is a positive integer; record and result counts are integers.
- Missing, ambiguous, conflicting, or unsupported security-relevant settings
  fail closed.

## Error behavior

| Condition | Required result |
|---|---|
| Missing `config/host.yaml` | Refuse startup; `ORCA_VAULT_PATH` supplies no other required host fields |
| Conflicting file/environment vault paths | Refuse startup pending explicit correction |
| Relative, inaccessible, or invalid vault/runtime path | Refuse the affected operation |
| Runtime path inside vault | Refuse startup |
| Unknown schema version or policy version | Fail closed; do not guess compatibility |
| Invalid or inconsistent budget | Reject configuration before any model call |
| Unknown Project Root | Use `unassigned` or require Owner mapping; never guess a project |
| Ambiguous alias or relink | Require Owner resolution |
| Project mapping intent or final-state mismatch | Stop, preserve the intent, and require Owner repair |
| Missing retrieval index | Disable semantic recall until rebuild; leave Markdown unchanged |

Validation diagnostics MAY name keys and normalized non-secret paths needed for
repair. They MUST NOT print credential values or private memory content.
When the local status interface can load safely, a blocking validation failure
contributes one content-free urgent Attention Item. The item cannot make invalid
configuration usable or expose its private values.

## Idempotency and compatibility

Loading unchanged configuration MUST produce the same validated interface.
Validation MUST NOT mutate project records, mappings, or runtime state.

`config/host.example.yaml` and `config/orca-memory.example.yaml` are structural
compatibility fixtures. This specification remains their human-readable owner.
The connector key, mapping representation, vault schema, 15-minute cadence
defaults, and conflict-on-difference precedence are accepted Phase 1 behavior.

There is no active configuration loader or deployed runtime. See
[Current Status](../STATUS.md).

## Acceptance criteria

- Example configuration validates without containing personal paths or secrets.
- Missing, relative, conflicting, cross-location, unknown-version, and budget
  inconsistency fixtures fail before any model call.
- File-only, environment-only, and same-normalized-path dual-source cases choose
  the defined vault path deterministically.
- Git-ignore checks cover `config/host.yaml`, `.runtime/`, credentials, caches,
  and generated dependency state.
- Root-mapping tests prevent silent cross-project inheritance.
- Registration, relink, exact-worktree reuse, Unassigned, and interrupted
  mapping tests prove stable identity, idempotency, and local-only path evidence.
- The two tracked safe examples contain every required key and no private value.
- The keys, cadence defaults, and precedence rule match the accepted safe
  fixtures and this specification.

## Open questions

None.

## Related documents

- **Requirements:** [REQ-OPS-001](../01-foundation/requirements.md#req-ops-001--local-configuration-boundary)
- **Deployment:** [Deployment Architecture](../02-architecture/deployment.md)
- **Data ownership:** [Data Architecture](../02-architecture/data-architecture.md)
- **Security:** [Security and Trust](../02-architecture/security-and-trust.md)
- **Operator procedures:** [Phase 1 Local Runbook](../08-operations/runbook.md)
- **Host fixture:** [`config/host.example.yaml`](../../config/host.example.yaml)
- **Vault fixture:** [`config/orca-memory.example.yaml`](../../config/orca-memory.example.yaml)
