---
id: RFC-0002
title: Define project registration and relinking
document_type: proposal
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
---

# RFC-0002: Define project registration and relinking

## Summary

This draft defines how Orca connects a local workspace root to one permanent
Project Identity.

It proposes two explicit workflows:

- **Project Registration** creates a new Project Identity, Owner-selected
  Project Alias, `project.md`, and local Project Root Mapping.
- **Project Relink** connects another local root to an existing Project Identity
  without changing that identity or its Project Alias.

Known mappings and exact Git worktrees can resolve automatically. New projects,
moves, clones, remote matches, and ambiguous cases require one clear Owner
choice. Until then, memory remains Unassigned.

The Owner accepted this RFC on 2026-08-30. Its conclusions are promoted into
the current Configuration, Memory Model, architecture, quality, operations, and
implementation-plan documents. This file remains the informative review record.

## Motivation

The accepted design says that an unknown Project Root becomes Unassigned or
requires an Owner mapping. It does not define the complete first-use workflow:

- who creates `project_id`;
- how the first Project Alias is selected;
- how `project.md` and `config/host.yaml` change safely;
- how a retry avoids creating a second project;
- when a Git worktree can reuse a mapping; or
- what evidence is too weak for automatic relinking.

This is common-path behavior. Every new project reaches it.

## Roadmap context

This change supports Phase 1 Milestone 2. Capture and General/Unassigned memory
work may continue, but Project Registry implementation should not freeze a
workflow until this decision is accepted or rejected.

## Goals

- Give one local root one clear Project Identity or the safe Unassigned result.
- Ask the Owner only when meaning or ownership cannot be proved
  deterministically.
- Keep Project Alias human-readable and Owner-selected.
- Prevent moves, clones, matching remotes, or folder names from silently merging
  project memory.
- Reuse an existing mapping automatically for an exact Git worktree of the same
  local repository.
- Make registration and relinking idempotent and recoverable.
- Keep host paths local and out of the vault, Manifests, and Git.

## Non-goals

- Changing Project Identity, Project Memory, or Project Root Mapping meaning.
- Defining Project Alias rename behavior beyond the existing governed rule.
- Synchronizing mappings between hosts.
- Automatically merging projects by remote URL, folder name, topic, or semantic
  similarity.
- Adding a central `registry.md`, database authority, or public administration
  service.
- Implementing the workflow in this documentation task.

## Current behavior

The [Glossary](../01-foundation/glossary.md) owns Project Identity, Project
Alias, Project Registry, and Project Root Mapping terms. The [Memory
Model](../03-specifications/memory-model.md) owns `project.md`, the Project
Registry, and project directory layout. [Configuration](../03-specifications/configuration.md)
owns local root mappings and their validation.

Current code implements none of these workflows.

## Proposed design

### Workflow result states

Project resolution returns exactly one of:

| Result | Meaning |
|---|---|
| `mapped` | The normalized root already maps to one existing Project Identity |
| `worktree-reused` | The root has the same normalized Git common directory as a mapped local worktree and safely reuses its Project Identity |
| `owner-choice-required` | One or more possible actions exist but Orca cannot choose their meaning |
| `unassigned` | No accepted mapping exists and the Owner did not approve a change |
| `error` | Configuration, registry, identity, path, or recovery state is invalid or conflicting |

Only `mapped` and `worktree-reused` allow project-scoped processing without a
new Owner choice.

### Read-only discovery

Before proposing a write, Orca must:

1. load and validate host and vault configuration;
2. identify the current workspace root;
3. require that the root exists and is a directory;
4. normalize it through the platform path policy;
5. inspect the local Project Root Mappings and durable `project.md` records;
6. when Git is present, resolve the absolute normalized repository top level and
   Git common directory; and
7. return a result without making a model call or changing files.

The normalized root is the Git top level for a Git workspace. For a non-Git
workspace it is the explicitly selected existing workspace directory. Path
normalization resolves symlinks, removes a trailing separator except at the
filesystem root, and applies the host filesystem's case-comparison rule.

### Automatic cases

#### Existing exact mapping

If the normalized root has one mapping and its `project_id` resolves to one valid
`project.md`, Orca uses that Project Identity. No file changes.

If the mapping points to a missing or conflicting registry identity, Orca
returns `error`; it does not create a replacement project.

#### Exact Git worktree reuse

Orca may add a new root mapping automatically only when all of these are true:

- the root is a recognized Git worktree;
- its normalized Git common directory exactly matches the common directory of
  one already mapped local worktree;
- that mapped root resolves to one valid Project Identity;
- no mapping or registry evidence points to another Project Identity; and
- the local mapping update passes the recovery and idempotency rules below.

Remote URL, branch name, commit hash, repository name, and folder name are not
enough for automatic reuse. They may be shown only as Owner decision evidence.

### Owner-choice cases

Orca must ask for one explicit choice when the root is not safely resolved.

The choices are:

1. **Create a new project** with a confirmed unique Project Alias.
2. **Link to an existing project** selected by Project Alias and confirmed
   permanent `project_id`.
3. **Keep Unassigned** and change nothing.

The prompt may show bounded evidence:

- normalized local root;
- proposed alias;
- exact existing aliases and short project IDs;
- whether an old mapped root is now missing;
- Git remote match, when present, labelled as suggestion only; and
- clone, move, or ambiguity warnings.

It must not show private memory content or silently preselect a relink.

Owner choice is always required for:

- a new Project Identity;
- a moved root;
- a new clone, even when the remote matches;
- a non-worktree second checkout;
- more than one possible existing project;
- an alias or alias-slug collision; or
- conflicting mapping, registry, or Git evidence.

### Project Registration

After the Owner chooses **Create a new project**, the workflow must:

1. accept an explicit Project Alias or show one suggestion for confirmation;
2. validate alias and alias-slug uniqueness under case-insensitive comparison;
3. reject aliases or slugs reserved for `general` or `unassigned`;
4. let Storage assign one permanent opaque `project_id`;
5. prepare one fixed `orca-project/0.1` record and one exact local mapping
   post-image;
6. write the local recovery intent before either final file changes;
7. publish `project.md` in the new project directory;
8. atomically add the root-to-`project_id` mapping to `config/host.yaml` while
   preserving every unrelated validated configuration value;
9. verify both results; and
10. delete the recovery intent.

The Project Alias suggestion may come from the Git top-level directory name or
workspace directory name. It remains a suggestion until the Owner confirms it.

### Project record 0.1

The proposed `project.md` frontmatter is:

```yaml
schema_version: orca-project/0.1
project_id: proj_<opaque-id>
project_alias: Orca
authority: noncanonical
registration_method: owner-confirmed
created_at: 2026-08-30T10:00:00Z
updated_at: 2026-08-30T10:00:00Z
```

The body is:

```markdown
# Orca

Project registry identity record.
```

Rules:

- `project_id` never changes or derives from a path, remote, alias, or hash.
- `project_alias` is the current Owner-selected unique alias.
- `authority: noncanonical` prevents project identity metadata from becoming
  Canonical Memory.
- `registration_method` is `owner-confirmed` for new projects.
- Storage assigns UTC timestamps; support or root relinking does not rewrite the
  record or advance `updated_at`.
- No host path, Git common directory, remote URL, branch, credential, or source
  conversation is stored in `project.md`.

The durable collection of these records remains the Project Registry. No
central registry file is added.

### Project Relink

After the Owner chooses **Link to an existing project**, the workflow must:

1. resolve the selected alias to exactly one `project_id` and valid
   `project.md`;
2. show the permanent ID and warn that the new root will share that Project
   Memory;
3. require explicit confirmation;
4. prepare the exact local mapping post-image and recovery intent;
5. atomically add the new root mapping;
6. verify it; and
7. delete the recovery intent.

Relinking creates no Project Identity, changes no Project Alias, rewrites no
`project.md`, and copies no memory. Several roots may map to the same permanent
Project Identity.

An old missing mapping is not removed automatically. Cleanup or replacement of
old mappings requires a separately confirmed local configuration change.

### Keep Unassigned

If the Owner chooses **Keep Unassigned**, or no Owner choice is available, Orca:

- changes no registry or configuration file;
- processes eligible memory only under the fixed Unassigned scope; and
- may offer the workflow again on later explicit request.

It never treats an unknown project as General Memory.

## Recovery and idempotency

### Local mapping intent

Before `project.md` or `config/host.yaml` changes, the workflow writes one
private `orca-project-mapping-intent/0.1` under:

```text
.runtime/project-mappings/<operation-id>/intent.json
```

The intent contains:

- operation ID and `register`, `relink`, or `worktree-reuse` action;
- normalized root and applicable Git common directory;
- fixed `project_id` and Project Alias;
- target `project.md` path plus before/after hash;
- host configuration before/after hash and staged post-image; and
- creation time and fixed schema/policy versions.

It contains no memory content or credentials. The path and Git values remain
local and are never copied into the vault or a Run Manifest.

The workflow uses one local Project Mapping lock. It must finish or resolve one
existing intent before starting another mapping change.

### Recovery rules

| State | Required action |
|---|---|
| Intent exists and neither final change exists | Publish the fixed `project.md` when required, then the host mapping |
| `project.md` matches the intent but mapping is absent | Add the fixed mapping; do not assign another `project_id` |
| Mapping matches the intent and `project.md` is valid | Verify and remove the intent |
| Exact mapping already existed before the request | Return `mapped`; make no write |
| Target or host config matches neither before-image nor after-image | Stop; preserve the intent; require Owner repair |
| Intent is missing but an unlinked `project.md` is found | Do not link, delete, or create a duplicate automatically; require Owner repair |
| Mapping points to a missing or different project record | Stop; do not process as project-scoped memory |

No retry may allocate another Project Identity while a valid registration intent
already owns the root. Cleanup happens only after both final states verify.

## User-visible behavior

For a known root, the workflow is silent.

For an exact local Git worktree, Orca may add the mapping automatically and show
one short confirmation after success: project alias and short project ID only.

For every other unknown root, Orca shows one bounded choice: create, link, or
keep Unassigned. It does not ask several small questions when one confirmation
can carry the alias and action together.

## Data changes

- New project records use `orca-project/0.1`.
- Local mapping changes use `orca-project-mapping-intent/0.1` during recovery.
- `config/host.yaml` remains the host-local mapping authority.
- Project Root paths and Git evidence never enter the vault.

## Interface changes

- Governance gains a deterministic project-resolution result.
- Storage gains Project Identity allocation and `project.md` publication.
- Configuration gains atomic add/relink mapping updates under one lock.
- The future project setup skill or operator command presents the bounded Owner
  choice and calls the same deterministic workflow.
- Processing consumes only a completed Project Identity or the fixed Unassigned
  scope; it does not perform registration itself.

## Security and privacy

- Paths, Git common directories, and mapping intents remain local and ignored.
- The vault contains Project Identity and Alias, not host topology.
- No model decides project ownership or writes a mapping.
- Ambiguity, collision, missing registry state, or conflicting evidence fails
  closed.
- Project setup grants no canonical-write authority.

## Failure behavior

- Missing configuration, inaccessible paths, or invalid registry records stop
  the workflow before a write.
- Alias collision returns to Owner choice without allocating an identity.
- Failed `project.md` publication leaves host mapping unchanged.
- Failed host mapping after `project.md` publication reuses the same intent and
  `project_id` on retry.
- An invalid or lost intent cannot authorize automatic repair.
- Project-scoped processing cannot begin until registry and mapping agree.

## Compatibility

Existing valid `project.md` records and root mappings remain unchanged. Adoption
must validate them against the promoted schema before they can support automatic
resolution. Missing fields require explicit migration; Orca must not invent an
Owner confirmation.

## Migration

After acceptance:

1. readers validate existing Project Registry records and local mappings;
2. valid records remain in place with the same `project_id` and alias;
3. incomplete records are reported for Owner repair, not silently rewritten;
4. new registrations use `orca-project/0.1`; and
5. new mapping writes use the recovery intent and atomic config replacement.

## Operational impact

Phase 1 gains one explicit project setup surface and one private local mapping
intent directory. No background scan may create or relink a project.

## Drawbacks

- A new project normally needs one Owner confirmation.
- Registration spans the vault and local host configuration, so it needs a small
  recovery protocol.
- Old missing root mappings remain until the Owner confirms cleanup.
- Exact worktree detection depends on local Git metadata being available.

## Alternatives

### Always create a new project for an unknown root

Rejected because a moved folder or clone would split one real project into
several Project Identities.

### Relink automatically by Git remote URL

Rejected because a remote is a useful hint, not proof of project ownership or
intended memory sharing.

### Store roots and remotes in `project.md`

Rejected because machine-specific topology must remain local and
unsynchronized.

### Use one central Project Registry file

Rejected because the accepted design uses the collection of `project.md`
records and a rebuildable index.

### Ask the semantic provider to classify the project

Rejected because semantic similarity cannot grant project identity or scope.

## Unresolved questions

None.

## Promotion result

The accepted design was promoted into:

- [Glossary](../01-foundation/glossary.md);
- [Memory Model](../03-specifications/memory-model.md);
- [Configuration](../03-specifications/configuration.md);
- [Runtime Architecture](../02-architecture/runtime.md);
- [Data Architecture](../02-architecture/data-architecture.md);
- [Acceptance Plan](../07-quality/acceptance.md);
- [Test Strategy](../07-quality/test-strategy.md);
- [Phase 1 Local Runbook](../08-operations/runbook.md); and
- [Phase 1 Implementation Plan](../06-plans/completed/phase-1-implementation.md).

Implementation verification must cover:

- exact existing mapping with no write;
- new project registration with one fixed identity;
- explicit relink to an existing identity;
- exact Git worktree reuse;
- remote, clone, move, non-Git, collision, and ambiguous cases requiring Owner
  choice;
- Keep Unassigned with no project write;
- retry after `project.md` but before host mapping;
- config and record before/after mismatch;
- lost or invalid intent and unlinked project record;
- case-insensitive alias and slug uniqueness; and
- proof that host paths and Git evidence never enter the vault.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Roadmap:** [Phase 1](../ROADMAP.md#phase-1)
- **Terms:** [Glossary](../01-foundation/glossary.md)
- **Affected accepted owners:** [Memory Model](../03-specifications/memory-model.md) and [Configuration](../03-specifications/configuration.md)
- **Runtime:** [Runtime Architecture](../02-architecture/runtime.md)
- **Quality:** [Acceptance Plan](../07-quality/acceptance.md) and [Test Strategy](../07-quality/test-strategy.md)
- **Implementation sequence:** [Phase 1 Implementation Plan](../06-plans/completed/phase-1-implementation.md)
