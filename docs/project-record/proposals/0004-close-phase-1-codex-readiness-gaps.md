---
id: RFC-0004
title: Close Phase 1 Codex readiness gaps
document_type: proposal
status: draft
authority: informative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-09-05
---

# RFC-0004: Close Phase 1 Codex readiness gaps

## Summary

A read-only Phase 1 review on 2026-09-05 found that Orca is substantially
implemented and suitable for continued deterministic testing, but should not
yet be enabled for routine Codex capture of private or valued memory.

The accepted architecture is coherent. The findings concern implementation
composition, provider isolation, default Recall scope, and deployment
procedures rather than a need to redesign Orca.

This RFC preserves the review for later Owner disposition. It is unaccepted,
does not authorize implementation, and does not by itself change the accepted
Phase 1 architecture, specifications, roadmap, or completion status. The
configured lifecycle remains disabled.

## Repair disposition — 2026-09-05

The Owner subsequently authorized fixing the remaining blockers and preparing
controlled testing. The working-tree repairs address provider isolation,
private paths, production summary IDs, existing-memory composition, exact
operation references, and hook setup. Optional-context fitting complements the
prior selected-segment and recall-scope fixes; configuration-independent recovery
was already repaired. [Current](../current.md) owns the evidence and remaining
live-trial limits. The original findings below are retained as review history,
not assertions that every described defect still exists.

## Review boundary

This RFC preserves the original review below. Later implementation status is
recorded in [Current](../current.md). On 2026-09-05, the Owner's separate request
to align Phase 1 with conversation continuity authorized focused adjustments:
F-03 gained service/CLI scope enforcement; F-02 gained selected-segment
serialization and a local prompt/schema ceiling. The active suite passed 236
tests. Other findings are not resolved by those changes. The active Retrieval
specification now permits agent-initiated scoped recall; the original
automatic-Recall non-goal below does not prohibit that later instruction-guided
behavior.

- Scope was one Codex agent, one WSL runtime, and one configured local vault.
- The exact active regression command passed 228 tests.
- `uv lock --check`, package build, CLI validation, health, and content-free
  configuration checks passed.
- The configured lifecycle was disabled, the Orca root was mapped, and the
  configured vault was outside the checkout.
- No private vault content was inspected and no lifecycle hook was enabled.
- Ordinary edge cases were not treated as blockers. Only catastrophe-class
  safety risks and missing core happy-path behavior affect the readiness
  verdict.

## Motivation

Current project documents say Phase 1 is complete, but several important paths
are not exercised by the existing acceptance evidence. Some component tests
use mocked providers, manually supplied related records, or predictable test
identities that conceal production composition failures.

The findings need explicit Owner review before the earlier completion claim is
used to authorize routine private deployment.

## Roadmap context

The review does not broaden Phase 1. It evaluates the existing Phase 1 outcome:
one Codex agent using a governed local memory loop without automatic Canonical
Memory mutation or a public service.

## Goals

- Close catastrophe-class provider, scope, and private-path risks.
- Make the existing project-memory happy path work with production identities.
- Wire bounded existing-memory context into the real processing composition.
- Make provenance as exact as the accepted specification requires.
- Make a fresh Codex deployment and canary reproducible.
- Reconcile project status only after findings are dispositioned and verified.

## Non-goals

- Multi-agent or remote-host operation.
- Automatic or agent-initiated Canonical Memory mutation.
- Automatic semantic Recall.
- A daemon, scheduler, public MCP service, dashboard, or general ingestion
  system.
- Blocking Phase 1 on harmless or safely failing edge cases.
- Removing the replaceable AgentCairn retrieval library merely because its
  separate Codex plugin and skills were removed.

## Findings requiring Owner disposition

### F-01 — Semantic-provider isolation is prompt-only

`src/orca_memory/codex_provider.py` invokes a full `codex exec` agent with a
read-only sandbox and a prompt instruction not to inspect files. It supplies no
sanitized environment and does not establish a no-tools process boundary.
Current Codex documentation states that a read-only agent may inspect files.
An injected conversation could therefore cause unrelated local data to enter
provider output.

Suggested remediation:

- use a non-agentic structured-output invocation with no tools; or
- prove an empty tool, MCP, browser, plugin, and subagent surface and place the
  subprocess inside an OS boundary that exposes only the request, schema,
  output, and required authentication;
- pass an explicit minimal environment; and
- add harmless file and environment sentinel tests that must remain
  inaccessible even under an adversarial semantic request.

This is a catastrophe-class privacy blocker for routine private use.

### F-02 — Provider serialization bypasses segmentation and budgets

`SourceSegment` contains both bounded `segment.text` and its complete
`NormalizedTurn`. `CodexCliSemanticProvider.distill` recursively serializes the
whole `ProcessingInput` with `asdict`, so each provider call includes the
selected segment and the entire original turn. Processor budget measurement
counts only the selected segment.

Suggested remediation:

- define a provider-specific DTO containing necessary metadata and only the
  selected bounded segment text;
- measure the full fixed instructions plus serialized DTO before invocation;
  and
- add a multi-segment regression proving that one call cannot see a marker from
  another segment and remains within its configured input ceiling.

This is a privacy, bounded-processing, and provenance blocker.

### F-03 — Unscoped Recall permits cross-project results

`RecallRequest` permits no project or scope. In that state, the eligibility
filter accepts Project, General, and Unassigned projections. The CLI creates
that request when the user runs plain `orca recall`.

Suggested remediation:

- enforce exact scope at the Recall service boundary;
- resolve the current working directory only through an exact configured
  project mapping;
- otherwise require explicit General or Unassigned scope and fail closed; and
- test two projects plus General and Unassigned data through both service and
  CLI default paths.

This is a catastrophe-class cross-project confidentiality blocker.

### F-04 — Private checkout separation is not enforced

Configuration validates that runtime and rollout paths are outside the vault,
but does not reject a vault inside a project checkout. Backup restore likewise
permits plaintext staging inside a checkout. The current configured vault is
outside the Orca checkout, so this is a validator gap rather than a known
current-path violation.

Suggested remediation:

- reject a vault, plaintext staging destination, or other private state inside
  any configured project root or detected Git worktree;
- normalize symlinks before comparison; and
- cover nested and symlinked paths in configuration and backup tests.

The consequence of misconfiguration is catastrophe-class private publication.

### F-05 — Project-memory creation cannot satisfy summary identity

The provider must not assign a `memory_id`. Storage assigns an unpredictable ID
after receiving the proposal, but then requires the same provider response's
Project Summary to already contain that ID. The current passing unit test
predicts a deterministic injected test ID, which a production provider cannot
do.

Suggested remediation:

- let summary proposals reference operation-local keys that Storage resolves;
  or
- let Storage deterministically insert newly allocated IDs after validating
  the summary content.

Add a production-schema integration test in which the provider cannot know the
future ID. This is a core happy-path blocker, not an edge case.

### F-06 — Existing memory context is not wired into the real pipeline

Processor accepts bounded same-scope related records, but `Step3Pipeline` never
loads or passes them. The provider therefore cannot reliably choose an
existing target for support, update, supersession, conflict, or candidate
support.

Suggested remediation:

- deterministically select bounded current same-scope records and candidate
  targets before processing;
- pass only their required identity and bounded meaning; and
- test two sequential composed runs: create, then support, update, or conflict
  without creating a duplicate.

This blocks the intended living-memory loop but does not require a new
architecture.

### F-07 — Operation provenance is not exact

Storage assigns every Owner segment in a processing chunk to every operation.
Proposal types cannot identify the exact segment or segments supporting one
specific memory change, and semantic timestamps are not derived from those
exact cited sources.

Suggested remediation:

- add operation-local source-segment references to untrusted proposals;
- validate a nonempty subset of current-run Owner evidence; and
- derive trusted source timestamps deterministically from the cited segments.

This must be resolved before claiming the accepted exact-provenance contract.

## Deployment and operational gaps

### Codex hooks and setup

- `SessionEnd` is configured for 10 seconds even though current Codex supports
  at most 3 seconds.
- `SessionStart` omits the supported `clear` source.
- Operations does not tell a fresh operator to review and trust the project
  hooks through `/hooks`.
- The initial configuration begins with no project mapping, but the canary
  procedure does not require project registration.
- The canary does not define an exact compaction, session-end, content-safe
  verification, version, or revision sequence.
- The project-local hook command is sufficient for an Orca-only pilot. If
  Phase 1 must cover other mapped repositories, it needs a stable installed
  Orca entry point from an appropriate Codex hook layer rather than treating
  every active repository as the Orca uv project.

Suggested remediation is to correct the hook values and tests, document trust
and registration, and define one exact non-sensitive canary. A small
content-free `orca canary-check` command is optional convenience.

### Backup recovery

Follow-up on 2026-09-05: the Owner authorized this repair. CLI verification now
runs before configuration loading; explicit `backup stage --standalone` exposes
a verified new recovery copy without configuration. Normal staging retains
configured live-root protections. [Current](../current.md) records the synthetic
real-GPG drill and remaining deployment limitations. The paragraph below
preserves the original finding.

The CLI loads live host configuration before dispatching `backup verify` or
`backup stage`. Loss of that configuration can therefore prevent use of the
recovery command intended for that situation.

Suggested remediation is to make verification configuration-independent, let
staging target an explicit new protected destination, add missing-config CLI
tests, and run one real GPG create, verify, and stage drill before entrusting
valued memory to Orca.

### Release and documentation state

The current PLS migration is a large uncommitted working-tree change. The tree
tests and builds, but it is not yet a reproducible release artifact. Current
documentation also contains contradictory status, hook, backup, and test-count
claims.

Suggested remediation is to finish findings on the working tree, reconcile the
owning documents, commit one coherent revision, run the complete suite and
build against that exact revision, and perform the lifecycle canary from it.

## Codex usability follow-up

A small explicitly invoked Orca Codex skill or governed `orca save` command
would make status, scoped Recall, explicit save, and Owner review discoverable.
It should be added after the scope and provider boundaries are corrected. It is
not a Phase 1 safety blocker, and it should not introduce automatic Recall.

Removing the AgentCairn Codex plugin and skills does not remove Orca's separate
optional `agentcairn==0.25.2` Python retrieval dependency. If the Owner later
chooses to remove AgentCairn entirely, an Orca-native adapter must replace it
before Recall can be considered complete.

## Existing positive evidence

- The exact active deterministic suite passed 228 tests.
- Source and wheel distributions built successfully and kept evaluation-only
  runners outside the installed package.
- Configuration, health, CLI, authentication, and dependency checks passed.
- Capture, retry, recoverable publication, conflict/candidate handling,
  interaction profiles, attention, backup boundaries, and the absence of
  public or Canonical-apply surfaces have meaningful implementation and tests.
- Lifecycle defaults off and was confirmed disabled during the review.

This evidence supports continued development and synthetic testing. It does
not override findings in untested production composition seams.

## Suggested remediation order

1. Close F-01 through F-04 before routine use of private data.
2. Close F-05 through F-07 before renewing the Phase 1 completeness claim.
3. Correct hooks, trust, mapping, backup recovery, and the deterministic
   canary procedure.
4. Add focused regressions, then run the complete suite and package build.
5. Reconcile Current, Roadmap, Architecture, Acceptance, Operations, and the
   root README after the Owner dispositions are known.
6. Commit a clean revision, run an exact-revision non-sensitive Codex canary,
   and complete one real encrypted-backup staging drill.

## Failure behavior during review

Until the findings are dispositioned, keep `lifecycle.enabled: false`. Static
inspection, deterministic tests, package builds, and a completely disposable
non-sensitive environment remain permitted. The earlier completion record
should not be treated as authorization for routine private capture.

## Compatibility

The suggested changes retain Orca's current authority model, noncanonical
Shallow Memory, explicit Recall, replaceable retrieval backend, checkpoint-last
publication, and prohibition on automatic Canonical Memory mutation. No vault
format migration is proposed unless later implementation review proves one is
necessary.

## Unresolved questions

- Whether to retain `codex exec` behind stronger isolation or move semantic
  proposal generation to a non-agentic structured-output interface.
- Whether Storage should resolve proposal-local summary references or inject
  changed record IDs deterministically.
- Whether Phase 1 hooks are intentionally Orca-repository-only or must operate
  in every configured project root.
- Whether the Owner wants to keep AgentCairn as the initial replaceable
  retrieval backend.

## Acceptance conditions

- The Owner dispositions F-01 through F-07.
- Accepted fixes have regression coverage at their real composition boundary.
- The complete deterministic suite and package build pass from one clean
  revision.
- A non-sensitive exact-revision Codex lifecycle canary passes with hooks
  reviewed and trusted.
- A real encrypted backup verifies and stages into a new safe directory.
- Current project documents accurately describe the resulting state and do not
  overstate the meaning of deterministic or semantic evaluation evidence.

## Related documents

- **Documentation map:** [Documentation Index](../../README.md)
- **Current state:** [Current](../current.md)
- **Roadmap:** [Phase 1](../roadmap.md#phase-1)
- **Architecture:** [Architecture Overview](../../architecture/README.md)
- **Security boundary:** [Security and Trust](../../architecture/README.md#security-and-trust)
- **Required behavior:** [Requirements](../../specifications/requirements.md)
- **Processing:** [Processing](../../specifications/processing.md)
- **Retrieval:** [Retrieval](../../specifications/retrieval.md)
- **Configuration:** [Configuration](../../specifications/configuration.md)
- **Acceptance:** [Acceptance](../../quality/acceptance.md)
- **Test strategy:** [Test Strategy](../../quality/test-strategy.md)
- **Deployment:** [Setup](../../operations/setup.md)
- **Runbook:** [Runbook](../../operations/runbook.md)
- **Official Codex hooks:** <https://learn.chatgpt.com/docs/hooks>
- **Official Codex sandboxing:** <https://learn.chatgpt.com/docs/sandboxing>
