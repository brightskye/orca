---
id: WORK-2026-08-29-PDS-CURRENT-STATE
title: PDS Audit Current-State Summary
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Current-state summary

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

## Conclusion

Orca has adopted **PDS-0.2 Core** and is ready to begin the documentation
migration described by this working set. The repository already contains strong
Phase 1 domain, governance, record, interaction, and run-receipt contracts. Its
principal remaining problem is information architecture: the same active files
mix charter, roadmap, architecture, specification, decision rationale, plan,
status, acceptance, and operations responsibilities. PDS entry points and
explicit canonical ownership are still absent and are migration work, not
unresolved design choices.

The Owner resolved every decision in
[`09-human-decisions-required.md`](09-human-decisions-required.md) on 2026-08-29.
The migration may proceed through the manifest and validation gates. No source
document is authorized for archival or deletion before parity validation and
Owner acceptance of its replacement.

## Current documentation structure

```text
/
├── README.md                 mixed orientation, charter, roadmap, architecture, status
├── AGENTS.md                 current agent protocol
├── CONTEXT.md                active domain glossary
├── SECURITY.md               vulnerability policy plus security architecture/status
├── PDS.md                    supplied PDS v0.2.0 standard (draft, untracked)
├── config/*.yaml             local host configuration contract/example
├── docs/
│   ├── architecture.md       Phase 1 architecture plus status and acceptance
│   ├── system-design.md      project-wide mixed system design and decisions
│   ├── operations.md         runbook, runtime specification, status, readiness
│   ├── governance/           normative Phase 1 governance contract
│   ├── *-contract.md         detailed normative specifications
│   └── research/             informative design research
├── tbd/
│   ├── future/               deferred all-phase design and accepted-labelled ADRs
│   └── reference/legacy/     preserved prototype docs, schemas, fixtures, and code
└── local ignored records
    ├── .agent-notes/         continuity notes
    ├── evidence/             frozen reports and machine evidence
    └── index.md              pre-reorganization historical project hub
```

The working tree also shows pre-existing deletion of the former `docs/adr/`,
`docs/system-overview.md`, `docs/prototype-migration-notes.md`, `prototype/`, and
legacy test paths, with corresponding material currently present under `tbd/`.
Most moved documentation and schemas are byte-identical to their `HEAD`
versions; `tbd/future/system-overview.md` and
`tbd/reference/legacy/prototype/README.md` contain boundary/path adjustments.

## PDS profile assessment

**Adopted profile: Core.** The project is maintained, multi-session, data-centric,
agentic, security-sensitive, and explicitly spans three delivery phases. A
Minimal profile would not provide adequate ownership for its contracts,
provenance, trust boundaries, active implementation work, or phase direction.
There is not yet evidence that the complete Extended profile is necessary.

The Owner accepted `PDS-0.2` and `core` on 2026-08-29. The migration must record
that declaration in `docs/README.md`.

## Trigger evaluation

| Trigger | Result | Evidence | Required target |
|---|---|---|---|
| Roadmap | **Triggered** | Three intended phases and deferred capabilities appear in `README.md` and `docs/system-design.md`. | `docs/ROADMAP.md` |
| Data architecture | **Triggered** | Canonical, noncanonical, operational, and rebuildable data; provenance; deletion; retention; and later synchronization are central. | `docs/02-architecture/data-architecture.md` |
| Security and trust | **Triggered** | Personal memory, secrets, external semantic providers, untrusted model output, local tool execution, and later synchronization are in scope. | `docs/02-architecture/security-and-trust.md` |
| Runtime architecture | **Triggered** | Hooks, direct-source reading, one-shot workers, checkpoints, retries, indexing, and recall form substantial runtime flows. | `docs/02-architecture/runtime.md` |
| Deployment architecture | **Triggered** | Codex Desktop, WSL, vault separation, local configuration, and materially different later-host topologies require a deployment view separate from operation steps. | `docs/02-architecture/deployment.md` |
| Integration architecture | **Triggered** | Codex rollout parsing, MCP, semantic-provider and AgentCairn seams, and later connectors have distinct boundaries and failure assumptions. | `docs/02-architecture/integration-architecture.md` |
| User documentation | **Not yet triggered** | No deployed supported user workflow exists; current material serves developers/operators. Reassess when Phase 1 is routinely usable. | None now; runbook and root quick start suffice. |
| Changelog | **Not proven triggered** | `pyproject.toml` says `0.1.0`, but the repository has no tags and only one committed baseline. | Human confirmation if `0.1.0` is a released version. |

## Major organizational problems

1. Required PDS entry points are missing: `docs/README.md`, `docs/STATUS.md`,
   `docs/ROADMAP.md`, the foundation package, and the primary architecture
   overview.
2. Root `README.md`, `docs/system-design.md`, `docs/architecture.md`, and
   `docs/operations.md` repeat phase, architecture, status, runtime, and
   acceptance claims.
3. No canonical ownership registry tells readers whether the governance
   contract, system design, architecture, or operations prose owns a repeated
   rule.
4. Current metadata uses uncontrolled values such as `active`,
   `phase-1-current`, `informational`, and `accepted-baseline`, and generally
   omits authority and implementation status.
5. The active system design describes a complete Phase 1 system while the code
   implements a bounded initial slice. That distinction exists only in scattered
   status prose.
6. Significant accepted choices are embedded in `docs/system-design.md` rather
   than maintained as ADRs. The only ADR files are under a directory explicitly
   declared noncurrent.
7. Informative research contains pre-decision candidate schemas and terminology
   that conflict with later contracts but lacks a prominent historical/non-
   normative warning.
8. Current quality claims and phase exit criteria are scattered across
   architecture, operations, tests, CI, and historical evidence, with no quality
   owner or traceability map.
9. `tbd/` successfully separates later and legacy material, but files inside it
   still say `accepted` or `accepted-baseline`; their local metadata conflicts
   with the parent directory's noncurrent boundary.
10. Local ignored `index.md` and `.agent-notes/issues.md` are stale. They are not
    public authority, but ordinary filesystem search can still surface them.

## Current strengths

- `CONTEXT.md` provides disciplined, explicit domain language.
- The governance, memory-record, run-manifest, interaction-preference, and
  interaction-guidance contracts are precise enough to decompose into PDS
  specifications without redesigning the system.
- Authority boundaries are repeatedly explicit: Owner authority, noncanonical
  derived artifacts, replaceable retrieval, and disabled canonical apply.
- The direct-source, no-second-raw-archive approach is reflected in active code,
  tests, and current documentation.
- Failure behavior, idempotency, provenance, replay, secret containment, and
  bounded recall receive unusually strong coverage for a project at this stage.
- `tbd/README.md` and `AGENTS.md` already enforce a current-versus-deferred
  boundary.
- Tests provide direct evidence for the implemented capture, redaction,
  continuation-summary, manifest, checkpoint/replay, no-memory, source-revision,
  and AgentCairn-wrapper slices.

## Resolved blockers and remaining migration gaps

1. Conflict supersession now requires a clear applicable Owner replacement;
   trusted timestamps establish chronology only.
2. Phase 2 and Phase 3 are candidate directions. Their exact future designs
   remain unaccepted proposal evidence.
3. Deferred documents and ADRs still contain accepted-looking metadata, but the
   approved `tbd/` exception and ADR classifications now determine how migration
   must route them.
4. `SECURITY.md` now acknowledges the active but incomplete Phase 1 local
   implementation without implying deployment or public support.
5. Ordinary Knowledge Candidates remain in Phase 1. Their complete active
   contract is required migration work and must not be inferred from legacy
   Curator or Conflict Overflow Candidate behavior.
6. The repository-root `PDS.md` is the adopted tracked standard; it remains
   untracked in the working tree until included in the migration change set.
7. No changelog is required because `0.1.0` is not a proven release.

## Pre-existing Git working-tree state

The initial `git status --short` was recorded before audit writes. It contained:

- modified: `.github/workflows/ci.yml`, `.gitignore`, `AGENTS.md`, `CONTEXT.md`,
  `README.md`, `SECURITY.md`, `docs/architecture.md`,
  `docs/governance/memory-system-contract.md`, and `docs/operations.md`;
- deleted: the four former `docs/adr/` files,
  `docs/prototype-migration-notes.md`, `docs/system-overview.md`, the legacy
  `prototype/` implementation/contracts/schemas, and corresponding legacy test
  files;
- untracked: `PDS.md`, the new active contracts and research files,
  `docs/system-design.md`, `pyproject.toml`, `src/`, `tbd/`, the active tests,
  and `uv.lock`.

These changes pre-date the audit and were not reset, reformatted, or modified.
The exact final status is reported in the task handoff and can be compared with
this baseline; only `docs/_working/pds-migration/` should be newly added by this
audit.
