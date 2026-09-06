# Orca current state

Last reviewed: 2026-09-06

This document owns the current implementation, limitation, and verification
snapshot. Architecture and Specifications own intended design; the Roadmap owns
future direction.

## Current phase

The Phase 1 baseline was accepted by the Owner on 2026-08-31. Orca provides
the governed local capture, processing, provisional-memory, interaction,
scoped Recall, provenance, recovery, attention, and backup boundaries defined
for that phase, subject to the unresolved readiness findings below. Automatic
canonical apply remains disabled and absent.

Orca structurally follows the PLS 0.3 working model by Owner direction dated
2026-09-04. The adoption changed project organization and navigation without
changing product behavior, phase scope, or capability claims.

The installed `src/orca_memory/` package contains only supported product and
runtime modules. Maintained evaluation cases and evaluation-only runners live
under `tests/evals/` and are not part of the installed package.

The documentation ownership cleanup on 2026-09-05 applies PLS 0.3 throughout
the active architecture routes. Architecture owns system views; the Runtime and
Backup specifications own exact coordination and recovery-copy behavior.
Operations owns executable procedures. Stale implementation claims were removed
from design documents. This documentation change does not resolve RFC-0004.
Runtime and security architecture are consolidated into the architecture
overview for readability; their standalone architecture files were removed.
On 2026-09-06, Operations was split into a short navigation index, a setup
guide, and the runbook titled "Using and maintaining Orca." Setup owns
installation and first tests; the runbook owns daily use and recovery.

## Pending readiness review

A read-only review on 2026-09-05 identified potential privacy, scope,
provenance, composition, and deployment defects that were not exercised by the
earlier acceptance evidence. The findings and suggested remediations are
preserved in draft [RFC-0004](proposals/0004-close-phase-1-codex-readiness-gaps.md).

The Owner authorized the remaining implementation repairs and controlled-test
preparation on 2026-09-05. The original RFC remains the historical review;
implementation disposition is recorded below. The Owner authorized the
non-sensitive CLI trial on 2026-09-06. Its initial failures and subsequent
repairs and retests are recorded below;
the working tree is not approved for routine private capture.
The existing private lifecycle configuration remains disabled.

## Capability status

The Owner clarified the Phase 1 goal on 2026-09-05: preserve useful distilled
conversation history in the Orca vault and recall it across Codex sessions.
The existing capture → processing → Markdown → retrieval structure is retained.
No new vault format, retrieval backend, or wiki workflow is introduced.

Working-tree adjustments now preserve cumulative continuation context in the
provider instructions, send only selected source segments, and reject an
oversized serialized request before invoking the provider. Exact conversation
recall returns the bounded continuation before related search hits. The CLI
uses the mapped project or requires an explicit scope; the service rejects
unscoped broad searches and contradictory scope selections.

SessionStart now supplies a scoped recall command for mapped projects and
confirmed General conversations. The Owner can request recall, or Codex can
invoke the command when earlier context is needed. This is instruction-guided
agent behavior, not a startup search or automatic memory injection. Actual
usefulness and agent-initiated recall were exercised in the controlled CLI
trial below. The initial passive-recall failure was followed by a passing
retest after the recall instructions were tightened.

| Capability | Status | Important boundary |
|---|---|---|
| Conversation capture and privacy filtering | Implemented | Only positively identified permitted records cross the privacy boundary; partial input and secrets fail closed. |
| Bounded semantic processing | Implemented | Providers propose meaning but cannot grant identity, authority, placement, or publication. |
| Typed Memory Records and Project Summaries | Implemented | Validated noncanonical records, stable identities, support/update, conflict handling, and summary refresh are tested. |
| Knowledge Candidates and Owner review | Implemented | Candidates remain noncanonical; candidate and conflict outcomes require explicit Owner workflows. |
| Provenance and recoverable publication | Implemented | Manifest/checkpoint joins, replay, intent-first publication, and repair are tested. |
| Interaction observations, profiles, and guidance | Implemented | Evidence is inspectable, scoped, bounded, rebuildable, and noncanonical. |
| Scoped Recall and retrieval projections | Implemented | Scope enforcement, exact continuation priority, budgets, authority labels, stale-index failure, and rebuild are tested. |
| AgentCairn adapters | Implemented | AgentCairn receives only prevalidated projections and remains replaceable and non-authoritative. |
| Configuration and project mapping | Implemented | Strict local configuration, exact-root mapping, registration, relink, and recovery are tested. |
| Lifecycle hooks and catch-up | Implemented and installed; currently disabled | One-shot workers use deterministic scope, private cursors, bounded retries, and fail-closed source handling. |
| Status and Attention Items | Implemented | Content-free stable items expose pending or repairable work without leaking private payloads. |
| Encrypted backup and staging restore | Implemented; synthetic real-GPG drill passed | Verification and explicit standalone staging work without host configuration; normal staging still protects configured live roots. No private-vault backup was run. |
| Canonical automatic apply | Deliberately absent | It is disabled and unexposed in Phase 1. |

## Readiness findings and remaining trial checks

| Finding | Current disposition |
|---|---|
| F-01 provider isolation | Fixed for qualified static Codex CLI 0.153.4 on the tested Linux/bubblewrap boundary. Forced tool execution is blocked; an external file read fails before a model request. The minimal environment excludes host sentinel values. Missing prerequisites or CLI drift fail closed. |
| F-02 selected input and budgets | Selected segment serialization replaces whole-turn recursion. Processor drops optional related context/overlap to fit the exact local prompt, instructions, and schema. Mandatory overflow fails before a provider call without dropping evidence. Codex's own protocol wrappers are outside this local byte-conservative measure; this is not a claim to count every token of the remote model request. |
| F-03 recall scope | Service and CLI enforce mapped/explicit scope; exact continuation takes priority over related mentions. |
| F-04 private paths | Vault and rollout paths reject configured projects and detected Git worktrees. Normal staging also protects configured project roots; all staging and temporary plaintext workspaces reject detected Git worktrees. Symlinks are normalized; partial markers fail closed. |
| F-05 summary identity | Storage inserts allocated changed-record IDs into a proposed Project Summary before validation; the provider does not need to guess them. |
| F-06 existing memory context | The real pipeline loads same-scope current records and pending candidate targets within shared bounded context, enabling subsequent support/update. |
| F-07 operation provenance | Semantic operations require exact supporting Owner segment locators. Processor validates them and derives source timestamps; Storage maps them to Manifest source references. |
| Recovery configuration dependency | Verification and explicit standalone staging work without the original configuration. Real GPG recovery, rebuilt search, and recalled source hashes passed on synthetic data. |
| Hook setup | Actual project hook and reviewed templates include `clear`, avoid dependency synchronization during a hook, and use the three-second SessionEnd limit. A separate template supports other mapped repositories. |

The controlled CLI trial established real provider authentication, useful
distillation for one synthetic sample, active recall, and a shutdown-time bound.
The initial passive-recall answer missed required final-answer details; the
repaired instructions passed the later synthetic retest. Desktop behavior and
reliable routine usefulness remain unverified.
The [controlled trial procedure](../operations/setup.md#controlled-two-session-continuity-test)
requires a separate test vault/runtime/configuration and a project-local hook
in the disposable workspace. The CLI's hook browser was used to review and trust
only the three test project hooks, without a trust bypass. Only synthetic
conversations were captured; no private history or private vault content was used.

A frozen wheel and lock-file-pinned environment were prepared locally with an
empty test vault, mapped `orca-control` workspace, no pending work, and lifecycle
disabled. The local preparation sheet contains its exact paths, build identity,
activation steps, synthetic messages, and pass/fail conditions. It is not a
release or Owner acceptance of routine use. The subsequent CLI trial added
separate Codex state, rollout storage, and temporary directories to avoid
inheriting the Desktop database and shared sandbox-lock locations.

## Controlled CLI trial — 2026-09-06

**Verdict: partial; the full controlled-test gate did not pass.**

The frozen installed wheel was exercised with Codex CLI 0.153.4,
`gpt-5.6-luna` (`high` for the conversation agent, `xhigh` for the isolated
processor), existing file-backed authentication, and the separate test vault.
The synthetic Paper Lantern discussion was followed by two fresh CLI sessions.
Their first Recall results matched the stored capture snapshot's scope and
source hashes; no prior answers were supplied in their prompts.

| Check | Observed result |
|---|---|
| Real capture and distillation | **pass** for this sample: Markdown choice/reason, tentative JSON idea, comparison next step, and timestamp question were retained. |
| Active recall | **pass**: the fresh agent invoked scoped Recall and returned all five details with source links. |
| Passive recall | **fail** against the full rubric: the fresh agent independently invoked Recall and continued from the saved context, but its final answer omitted the Markdown rationale and source links. |
| CLI shutdown and end hook | **pass** for the measured sample: 1.260 seconds from `turn.completed` to process exit, including SessionEnd, with a durable queue handoff. This is an upper bound on shutdown including the hook, not an isolated hook-duration measurement. |
| Additional timing-session distillation | **fail**: the queued capture exhausted three processing attempts, including the explicit queue-drain recovery. The failure receipt identifies retry exhaustion but not the underlying cause. |
| Desktop lifecycle | **not-run**; CLI evidence does not establish Desktop behavior. |

Background processing used retries and took minutes. The reason for the
retries was not retained by the content-free worker diagnostics.
A separate provider-only diagnostic timed out after 45 seconds; subsequent
real processing succeeded without changing provider isolation or authentication.
Immediate availability after ending a discussion is therefore not established.
The timing-only capture session inspected the local test instructions, so it
does not count as an independent recall-quality sample.

The local test sheet and results retain the installed wheel hash, source
revision/dirty-tree label, session identities, source hashes, and timing evidence.
The tool sandbox runner reached its time limit with background work still
queued; the remaining item was resumed using the explicit bounded worker
command, which reported `worker: failed` after retry exhaustion. The CLI process
exit code was zero, so the worker result and status must be checked explicitly.
That recovery step is separate from uninterrupted Desktop operation.
At trial closure, test capture and the existing private lifecycle were both
disabled, the test queue was empty, and one action-required runtime-retry item
was retained. All test vault writes stayed within Orca's policy and noncanonical
system areas; no canonical wiki content was created.
This trial is not a replacement for Owner usefulness review or routine-use
acceptance.

### Repairs and targeted retests

Replaying the retained synthetic failed capture reproduced a size-limit
rejection after a successful model response. The response was 3,994 UTF-8
bytes; Orca's parsed representation expanded to 4,988 bytes because it included
the locally rendered Project Summary a second time and JSON spacing. Processor
now measures compact supplied fields, excluding that duplicate rendering and
fixed local authority. The 4,000-unit byte-conservative ceiling is unchanged;
genuinely oversized content remains rejected.

The same frozen model response then exposed a second rejection: it proposed a
Project Summary refresh while only supporting existing records. Storage now
keeps the existing Project Summary unchanged and publishes the independently
valid continuation and operations. Provider instructions also ask for no
Project Summary refresh in that case. The frozen-response replay now succeeds.
Regression tests reproduce both failures and verify the corrected behavior,
including continued oversized-output rejection and unchanged summary bytes.

A subsequent installed-worker replay still failed with `validation`. A bounded
diagnostic replay identified a support proposal that reworded an existing
record. The adapter had supplied only its rendered Markdown body, requiring
the model to reconstruct the exact fields checked by Storage. It now supplies
the exact semantic fields, including nulls, and instructs the model to copy
them unchanged for support. The strict meaning check remains in place. A new
regression verifies that the serialized fields can produce a valid support
proposal without reconstructing Markdown.

The final separately installed wheel passed a normal worker replay of that
same retained synthetic capture with `codex-cli/gpt-5.6-luna/xhigh`. The worker
reported `success` after 85.456 seconds, published a Continuation Summary and
three support operations, and left no queued work or failure receipts. A fresh
process rebuilt eight retrieval projections and recalled the saved summary in
the correct project, including the decision, reason, tentative idea, open
question, and next step. All preexisting test-vault files remained byte-identical.
Test lifecycle was restored to disabled. The final wheel SHA-256 is
`7bd2fb9b91df40aa053b007059c78adbb8093586cabea28c919f6768e57b9eb5`.
Local results are retained under `/tmp/orca-final-worker-7q8j4_h_`; earlier
failed replays are preserved. This single successful sample does not guarantee
that future model proposals will always pass validation.

New terminal failure receipts retain fixed, content-free categories such as
`output-budget` and `validation`. An interrupted/unobserved exhausted attempt
is labelled `unobserved`; arbitrary exception or conversation text is not saved.
The original failure receipt is preserved. Its three attempts did not retain
enough detail to prove that every original attempt failed for the same reason.

The SessionStart guidance now requests the saved decision/reason, tentative
idea, next step, open question, and an exact source reference before new plans.
A first wording revision still missed the saved next step. The final revision
passed all those checks in a fresh CLI session using the same passive prompt,
with no answers supplied in that prompt. The agent invoked scoped Recall and
cited an exact returned reference. This was a recall-only SessionStart test;
its capture remained off and it does not retest Desktop or SessionEnd behavior.

Other limits retained from the existing design:

- Codex rollout format remains non-public; unsupported drift fails closed.
- Standalone recovery cannot infer former live roots or non-Git project
  mappings from missing configuration; the caller selects a separate private
  destination. Detected Git checkout protection still applies.
- The real GPG drill uses generated test keys and a synthetic vault. It does not
  verify the Owner's backup-key safekeeping or recovery of the deployed private
  vault. Automatic capture resumption after recovery remains untested.
- Automatic Canonical Markdown discovery remains deferred; automatic canonical
  apply remains disabled and unexposed.
- Mandatory oversized processing input may require smaller configured chunks;
  no automatic repacking of mandatory history is introduced for this trial.

## Verification

- The Owner-approved frozen common-use set passed 100/100 and the separate
  edge-safety set passed 12/12 with zero critical failures.
- The accepted Phase 1 evidence and Owner verdict remain retained locally under
  ignored `.local/evidence/`.
- After the continuity adjustments on 2026-09-05, the active deterministic
  regression command passed 236/236 tests. The [Test Strategy](../quality/test-strategy.md)
  owns the command and its limits. These tests used synthetic data and provider
  substitutes; no live semantic-provider or two-session Codex canary was run.
- After the backup-recovery fix on the same date, the full active suite with
  `ORCA_RUN_GPG_DRILL=1` passed 239/239 tests, including the real encryption and
  recovery drill. `git diff --check` passed. This is working-tree evidence,
  not an exact-revision release or deployment acceptance claim.
- After the remaining repairs on the same date, the full active suite with
  both `ORCA_RUN_GPG_DRILL=1` and `ORCA_RUN_CODEX_ISOLATION_DRILL=1` passed
  255/255 tests. The application, provider, and backup suites also passed
  39/39 checks against the frozen installed wheel with lock-file-pinned
  dependencies. These include real GPG recovery and actual Codex executable
  isolation probes using a local synthetic Responses server, without a real
  model call. The installed CLI passed configuration, health, rebuild, and
  empty-status checks; its isolated Codex version preflight also passed.

## Related material

- [Roadmap](roadmap.md)
- [Project details](../project.md)
- [Architecture](../architecture/README.md)
- [Specifications](../specifications/README.md)
- [Quality](../quality/README.md)
- [Operations](../operations/README.md)
- [Historical pre-migration status snapshot](../archive/orca-status-before-pls-structure.md)
- [PDS-to-PLS history](../archive/standards/README.md)
