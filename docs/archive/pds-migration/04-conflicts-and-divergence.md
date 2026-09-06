---
id: WORK-2026-08-29-PDS-CONFLICTS
title: PDS Audit Conflicts and Divergence
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Conflicts and divergence

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

Claims are preserved as found. This report does not choose a winner based on
date, filename, length, or current placement.

## Document-to-document contradictions

### C-001 — Conflict supersession rule

- **Claim A:** `docs/system-design.md`, Processor module, says that for otherwise
  matching project records the source turn with the latest trusted timestamp is
  made current and the older record is retained as superseded (lines 205–209).
- **Claim B:** `docs/governance/memory-system-contract.md`, Processing, says a
  later trusted Owner turn becomes current only when it clearly states or
  confirms the applicable replacement (lines 173–184).
- **Claim C:** `docs/memory-record-contract.md`, Conflict variant identity,
  repeats that chronology alone does not establish supersession and requires a
  clear replacement (lines 306–315).
- **Implementation evidence:** typed-record conflict handling is not implemented.
- **Authority:** all three files present themselves as current normative design;
  no PDS registry establishes precedence.
- **Impact:** choosing by timestamp alone can silently erase a still-applicable
  Owner position.
- **Required decision:** Owner selects the accepted rule; every non-owning
  summary must then link to the memory-model specification.
- **Resolution (2026-08-29):** A trusted timestamp establishes chronology only.
  A later trusted Owner turn becomes current only when it clearly states or
  confirms the applicable replacement. `docs/system-design.md` was reconciled
  with the governance and Memory Record contracts.

### C-002 — Project supported state

- **Claim A:** `SECURITY.md#Supported-state` says Orca is currently architecture
  and a manual prototype.
- **Claim B:** `README.md#Current-status` says the Phase 1 local Codex
  implementation is in progress and identifies migrated/tested source slices.
- **Implementation evidence:** `src/orca_memory/` and three active test modules
  implement an initial capture/processing/storage slice.
- **Authority:** `SECURITY.md` owns public security policy, not project status;
  `README.md` is informative and no `STATUS.md` exists.
- **Required decision:** approve accurate public support wording; the factual
  status owner should be `docs/STATUS.md`.
- **Resolution (2026-08-29):** Public wording now states that an active but
  incomplete Phase 1 local implementation exists, is not deployed or publicly
  supported, and keeps canonical automatic apply disabled. `docs/STATUS.md`
  remains the migration target for detailed implementation state.

## Documentation-to-code divergence

### D-001 — Visible assistant-response capture is not implemented

- **Documented intent:** `README.md#Phase-1-scope`,
  `docs/architecture.md#Completion-criteria`, and operations describe selecting
  Owner messages plus visible/final assistant responses.
- **Implementation:** `conversation.py::_owner_message` accepts only
  `event_msg/item_completed/UserMessage`; no assistant event is normalized.
- **Status:** partial/diverged depending on whether the statements are treated as
  accepted requirements or current capability.

### D-002 — Partial trailing JSONL does not wait

- **Documented intent:** `docs/operations.md#Failure-behavior` says a partial
  trailing JSONL line waits for a later run.
- **Implementation:** `conversation.py::_read_jsonl` raises `ValueError` on every
  JSON decode error, including a partial trailing line.
- **Status:** diverged.

### D-003 — Bounded Processor context and complete semantic proposal set are absent

- **Documented intent:** system design, governance, and operations define token
  budgets, chronological chunking, overlap, current summaries, related records,
  typed-record/candidate/profile proposals, and deterministic validation.
- **Implementation:** `processor.py` passes the whole supplied `ConversationBatch`,
  previous continuation text, and optional project ID to one provider call. It
  validates only a `ContinuationSummary` or `no_memory`.
- **Status:** partial; only the provider seam and continuation validation exist.

### D-004 — Recall is not implemented

- **Documented intent:** explicit MCP/skill recall, hard filters, retrieval
  projections, hash checks, result/budget limits, and exact-conversation recall.
- **Implementation:** no active Recall module, MCP server, skill, or retrieval
  projection exists under `src/orca_memory/`.
- **Status:** planned.

### D-005 — Interaction learning and guidance are not implemented

- **Documented intent:** observation validation, Manifest storage, profile
  consolidation, expiry/conflict, exact template compilation, and session-start
  delivery.
- **Implementation:** no interaction module, schema implementation, compiler, or
  tests exist in active source.
- **Status:** planned.

### D-006 — Lifecycle hooks, job queue, retry spool, scheduler, and `$orca-save` are absent

- **Documented intent:** architecture and operations specify `PreCompact`,
  `SessionEnd`, a one-shot worker, periodic catch-up, a secure retry spool, MCP,
  and `$orca-save`.
- **Implementation:** active source exposes only Python classes/functions for a
  directly supplied rollout and batch.
- **Status:** planned.

### D-007 — Configuration/deployment behavior is absent

- **Documented intent:** load and validate `config/host.yaml` or
  `ORCA_VAULT_PATH`, enforce budget configuration, operate a WSL runtime, and
  connect Codex Desktop.
- **Implementation:** `config/host.example.yaml` exists, but active code has no
  loader, validator, CLI, launcher, or deployment integration.
- **Status:** planned.

### D-008 — Replay checkpoint repair does not retain an available Manifest locator

- **Documented intent:** `docs/run-manifest-contract.md#Checkpoint` says the
  checkpoint records the latest Manifest locator when available; replay repair
  follows a Manifest scan.
- **Implementation:** `Storage.record_replay` calls `_write_checkpoint` with
  `manifest_path=None`, even though the processed turn was found in a Manifest.
- **Status:** diverged, narrowly scoped.

### D-009 — Typed memory, Project Summary, project registry, and ordinary candidates are absent

- **Documented intent:** memory record/governance/system-design contracts define
  these as Phase 1 behavior.
- **Implementation:** Storage publishes only Conversation Continuation Summary,
  Run Manifest, and checkpoint artifacts.
- **Status:** planned.

### D-010 — AgentCairn adapter exists but is not wired

- **Documented intent/status:** README and architecture explicitly call the
  custom Distiller migrated and tested but not wired.
- **Implementation:** `agentcairn.py` and its focused tests exist; the Step 3
  pipeline does not import or call it.
- **Status:** accurately documented as partial.

## Accepted-versus-proposed ambiguity

### C-003 — Deferred all-phase documents contradict current design

The parent `tbd/README.md` says `tbd/` does not define current behavior, yet its
future documents carry `status: accepted-baseline` and assert former rules:

| Subject | Deferred claim | Current active claim |
|---|---|---|
| Conversation Evidence | Immutable evidence is published in the vault (`delivery-plan.md`, `memory-system-contract.md`). | Evidence is transient; no second raw archive (`CONTEXT.md`, governance contract, code). |
| Phase 1 interaction profiles | Excluded from Phase 1 (`delivery-plan.md#Phase-1`). | Required Phase 1 capability (README, system design, interaction contracts). |
| Recall ordering | Canonical-first regardless of relevance (`delivery-plan.md`, future contract). | Relevance gates selection; canonical first only among comparable results (active contracts). |
| Secret handling | Hard-secret cases publish no content/reject (`delivery-plan.md`). | Locally redact obvious credentials where safe; reject affected generated outputs (active security/governance). |
| Scheduling/capture | Separate capture ticks and MCP startup capture (`future/operations.md`). | Lifecycle-hook handoff plus one-shot worker and catch-up (`docs/operations.md`). |
| Retention | Shallow memory is time-limited with proposed day counts (`future` files). | Automated retention is outside Phase 1; active conflict overflow has no age retention. |

The parent boundary prevents these from automatically controlling current
behavior, but their metadata and accepted wording create high search/context
risk. They must remain visibly historical/proposed until selectively promoted.

### C-004 — Deferred ADR applicability

- ADR 0004 describes the currently implemented checkout/vault separation but is
  located under noncurrent `tbd/future/`.
- ADRs 0002 and 0003 say `accepted`, but they concern future multi-host processor
  authority and follow-on canonical apply.
- No active decision registry states whether these are accepted current
  rationale, accepted future direction, or merely a retained baseline.
- **Required decision:** confirm each ADR's lifecycle/applicability without
  rewriting or reusing its number.

### C-005 — Informative research contains superseded design recommendations

`docs/research/memory-categorization-landscape.md` proposes `proposed` and
`expired` record states, source arrays/provenance in each record, a Conversation
Handoff name, and broad deterministic links. The active Memory Record Contract
instead uses `current|conflict|closed`, keeps provenance in Run Manifests, uses a
Conversation Continuation Summary, and prohibits general semantic links.

The research says its exact schema remains a design decision, so it is evidence,
not a current contradiction. Its current location and weak `informational`
metadata still make accidental promotion possible. Archive it as historical
research and link it only as decision evidence.

## Roadmap-versus-plan ambiguity

### C-006 — Phase 2 and Phase 3 commitment is unknown

- Root README labels Phase 2 and Phase 3 `Planned`.
- Active system design describes them as delivered future phases but does not use
  PDS commitment states.
- `tbd/future/delivery-plan.md` is labelled accepted baseline but is explicitly
  noncurrent and mixes roadmap, architecture, plan, and acceptance detail.
- No evidence safely establishes whether each later phase is `committed`,
  `candidate`, `exploratory`, or `deferred` under PDS.
- **Required decision:** assign roadmap status and retain exact designs as
  proposals unless separately accepted.
- **Resolution (2026-08-29):** Phase 2 and Phase 3 are candidate directions.
  Their exact future designs remain noncurrent proposal evidence unless
  separately accepted.

## Unknown or stale implementation status

### C-007 — Local working/history files are stale but non-authoritative

- `.agent-notes/issues.md` says processing resource limits are not explicit;
  active docs now specify limits, although code does not enforce them.
- ignored `index.md` points to moved paths and reports former Phase 3–8 work that
  is unrelated to the current three-phase delivery model.
- These records are local working/historical material and must not be silently
  corrected or promoted during PDS migration.

### C-008 — Ordinary Knowledge Candidate behavior is underspecified

Current design includes Knowledge Candidates among Phase 1 outputs, but no
active document owns their complete schema, placement, lifecycle, review,
retention, or retrieval exclusion at the same precision as Typed Memory Records
and Conflict Overflow Candidates. Legacy Phase 7 candidate/Curator material
cannot fill this gap automatically.

**Resolution (2026-08-29):** Ordinary Knowledge Candidates remain in Phase 1.
The migration must create a complete active specification without generalizing
the legacy Curator contract or the narrower Conflict Overflow Candidate rules.

### C-009 — Quality and agent verification routes disagree

- `AGENTS.md` instructs only the conversation capture suite.
- CI runs conversation capture plus AgentCairn tests.
- The active Step 3 pipeline suite is not in either command.
- Architecture and README use tested/implemented status without a centralized
  test-strategy or acceptance traceability document.

### C-010 — PDS standard custody is unknown

The supplied `PDS.md` is a 6,128-line, untracked, draft house standard. PDS itself
recommends maintaining the standard separately and having projects declare only
the adopted version/profile. The repository does not state whether this copy is
vendored project material, temporary migration input, or the authoritative
standard intended to be committed here.

**Resolution (2026-08-29):** The root `PDS.md` is the tracked authoritative copy
for this repository and must be included in the migration change set.

### C-011 — Nonportable research link

`docs/research/recall-context-budget.md` links to an absolute personal skill path.
The external finding can be preserved, but a migrated public historical report
must not rely on that path as a resolvable project link.

## Overall implementation status

| Capability | Status from repository evidence |
|---|---|
| Owner-turn Codex normalization and secret-pattern redaction | implemented and covered by focused tests |
| Visible assistant-response normalization | not implemented |
| Continuation Summary proposal/validation/publication | implemented initial slice |
| Immutable Run Manifest, scan-based dedupe, checkpoint-last, no-memory, source revision | implemented initial slice |
| AgentCairn prevalidated Distiller seam | implemented/tested, not integrated |
| Typed records, Project Summary, project registry, candidates | planned |
| Interaction observations/profiles/guidance | planned |
| Recall/MCP/skills/index projections | planned |
| Hooks, queue, spool, periodic catch-up, deployment | planned |
| Full privacy gate and assistant-context policy | partial |
| Canonical automatic apply | deliberately disabled and absent |
