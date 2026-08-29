---
id: WORK-2026-08-29-PDS-MANIFEST
title: PDS Documentation Migration Manifest
document_type: working-note
status: draft
authority: working
implementation_status: not-applicable
created: 2026-08-29
---

# Documentation migration manifest

> [!WARNING]
> This is non-authoritative working material.
> Do not treat it as accepted project design or roadmap direction.

Statuses describe migration readiness only. `ready` does not authorize the
migration.

## M-001 — Establish documentation control plane

- **Source:** `docs/system-design.md#Document-responsibilities`; this audit.
- **Classification:** documentation index and authority map.
- **Target:** `docs/README.md`.
- **Preserve:** existing responsibility links; add PDS version/profile, routes,
  registry, non-authority warnings, and `tbd/` exception.
- **Conflicts:** None; PDS-0.2 Core and tracked root custody are approved.
- **Cross-links:** root README, AGENTS, STATUS, ROADMAP, charter, overview.
- **Validation:** every current canonical document registered; one owner per
  subject; no working/archive file listed as normative.
- **Status:** **ready**.

## M-002 — Create current project status

- **Source:** `README.md#Current-status`;
  `docs/architecture.md#Retrieval-implementation`;
  `docs/operations.md#Current-status`; `SECURITY.md#Supported-state`; code/tests.
- **Classification:** project status.
- **Target:** `docs/STATUS.md`.
- **Preserve:** implemented/partial/planned distinctions and exact verification
  limits; do not convert design prose into implementation claims.
- **Conflicts:** C-002 and D-001 through D-010.
- **Cross-links:** roadmap phase, active plan, acceptance/test strategy.
- **Validation:** capability table agrees with source/tests and names every known
  divergence.
- **Status:** **ready**; approved public wording is now in `SECURITY.md`.

## M-003 — Extract project charter

- **Source:** `README.md#Goal`, `#Current-philosophy`;
  `docs/system-design.md#Purpose`, `#Design-goals`, `#Non-goals`;
  `docs/architecture.md#Goal`, `#Non-goals`.
- **Classification:** project charter.
- **Target:** `docs/01-foundation/project-charter.md`.
- **Preserve:** Owner authority, local-first governed memory, provisional versus
  canonical boundary, phase topology constraint, and no automatic apply.
- **Conflicts:** none requiring semantic resolution; phase detail moves to roadmap.
- **Cross-links:** requirements, roadmap, overview, security.
- **Validation:** root README contains only a concise summary; no unique goal or
  non-goal is lost.
- **Status:** **ready**.

## M-004 — Build requirements set

- **Source:** `README.md#Phase-1-scope`; governance contract invariants;
  architecture completion criteria; system-design goals.
- **Classification:** functional, quality, security, data, and operational requirements.
- **Target:** `docs/01-foundation/requirements.md`.
- **Preserve:** wording strength and explicit exclusions; assign stable IDs only
  after Owner review without changing meaning.
- **Conflicts:** C-001 and C-008 are resolved; implementation gaps D-001–D-009
  are not requirement changes.
- **Cross-links:** roadmap phase, exact specs, acceptance IDs.
- **Validation:** each normative obligation has one owner and at least a planned
  verification route.
- **Status:** **ready**.

## M-005 — Migrate active glossary

- **Source:** `CONTEXT.md` complete file.
- **Classification:** glossary.
- **Target:** `docs/01-foundation/glossary.md`.
- **Preserve:** every active term and `_Avoid_` synonym.
- **Conflicts:** behavioral wording for conflict replacement must follow H-002;
  later terms in `tbd/future/CONTEXT-all-phases.md` stay out.
- **Cross-links:** memory, interaction, recall, data, and architecture docs.
- **Validation:** term set is complete; exact behavior is linked rather than
  independently specified.
- **Status:** **ready**.

## M-006 — Create roadmap

- **Source:** `README.md#Delivery-phases`;
  `docs/system-design.md#Delivery-topology`; reviewed sections of
  `tbd/future/delivery-plan.md`.
- **Classification:** roadmap.
- **Target:** `docs/ROADMAP.md`.
- **Preserve:** three-phase topology axis, independent phase usability, deferred
  canonical apply, outcomes, dependencies, and exit criteria.
- **Conflicts:** C-003 and C-006; do not import exact future architecture.
- **Cross-links:** status, active plan, proposals, acceptance.
- **Validation:** each phase has PDS status/outcome/dependencies/exit criteria;
  no task checklist or exact specification remains.
- **Status:** **ready**; Phase 2 and Phase 3 are candidate directions.

## M-007 — Create primary architecture overview

- **Source:** `docs/system-design.md#System-context`, module-responsibility
  summaries, and `docs/architecture.md#System-shape`, `#Modules`.
- **Classification:** architecture overview.
- **Target:** `docs/02-architecture/overview.md`.
- **Preserve:** semantic/deterministic seam, components, ownership, boundaries,
  architecture principles, and detailed-design routes.
- **Conflicts:** remove C-001 exact behavior from overview; status must not be
  implied from component descriptions.
- **Cross-links:** charter, requirements, all architecture children, specs,
  ADRs, quality, runbook.
- **Validation:** primary entry point answers PDS design questions without
  repeating schemas/budgets/state machines.
- **Status:** **ready** after M-004 owner boundaries are settled.

## M-008 — Extract runtime architecture

- **Source:** `docs/system-design.md#Normal-operating-flow`;
  `docs/operations.md#Normal-operation`, scheduling and failure behavior;
  `docs/architecture.md` hook/job flow.
- **Classification:** runtime architecture.
- **Target:** `docs/02-architecture/runtime.md`.
- **Preserve:** direct-source path, hook handoff, one-shot worker, checkpoint-last
  sequence, replay, recall separation, and failure boundaries.
- **Conflicts:** D-002/D-006 and deferred scheduler model C-003.
- **Cross-links:** capture, processing, provenance, recall specs and runbook.
- **Validation:** current intended runtime is separate from implemented status
  and future topology.
- **Status:** **ready** with divergence labels.

## M-009 — Extract deployment architecture

- **Source:** system-design data locations/topology; Phase 1 architecture system
  shape/storage; operations configuration/scheduling; roadmap-approved later summaries.
- **Classification:** deployment architecture.
- **Target:** `docs/02-architecture/deployment.md`.
- **Preserve:** Codex Desktop/WSL/vault/project separation, local-only runtime
  state, no public interface, and clearly labelled future replicas.
- **Conflicts:** C-003/C-006 and absent deployment D-007.
- **Cross-links:** roadmap, data/security/integration architecture, runbook.
- **Validation:** current and future diagrams are unmistakably labelled; no
  installation procedure is embedded.
- **Status:** **ready**; later-phase deployment is candidate future state.

## M-010 — Build data architecture

- **Source:** system-design authority/data locations; architecture storage;
  governance; memory-record layout/provenance; run contract; relevant future data risks.
- **Classification:** data architecture.
- **Target:** `docs/02-architecture/data-architecture.md`.
- **Preserve:** canonical/noncanonical/derived classes, owners, rebuildability,
  lifecycle, retention/deletion state, provenance, backup/recovery and later sync boundary.
- **Conflicts:** active no-retention state versus future proposed periods (C-003).
- **Cross-links:** memory/provenance specs, security, deployment, ADRs.
- **Validation:** every data class has canonical owner, retention/deletion and
  recovery statement; future proposals are labelled.
- **Status:** **ready** for Phase 1; future retention section remains proposed.

## M-011 — Build security and trust architecture

- **Source:** `SECURITY.md#Deployment-boundary`, `#Secret-containment`;
  governance Authority/Capture/Local data; architecture; operations failure behavior.
- **Classification:** security and trust.
- **Target:** `docs/02-architecture/security-and-trust.md`.
- **Preserve:** protected private memory, Owner/agent/provider trust boundaries,
  explicit-private exclusion, local redaction, output rejection, no public interface.
- **Conflicts:** partial implementation D-001/D-006/D-007 and future secret rule C-003.
- **Cross-links:** root SECURITY, data architecture, capture/config specs, tests.
- **Validation:** assets, identities, external services, invariants, mitigations,
  residual risk, retention, backup, and incident routing are covered.
- **Status:** **ready** with partial implementation labels.

## M-012 — Build integration architecture

- **Source:** system-design semantic seam/adapters/AgentCairn; architecture
  interfaces/backend; README AgentCairn section; capture connector material.
- **Classification:** integration architecture.
- **Target:** `docs/02-architecture/integration-architecture.md`.
- **Preserve:** Codex event-source assumptions, MCP boundary, provider proposal
  seam, AgentCairn replaceability and non-authority.
- **Conflicts:** adapter is tested but not wired (D-010); future connectors noncurrent.
- **Cross-links:** capture/processing/retrieval specs and retrieval ADR.
- **Validation:** no vendor capability is mistaken for Orca authority.
- **Status:** **ready**.

## M-013 — Create architecture diagrams

- **Source:** ASCII and Mermaid flows in README, system design, architecture, operations.
- **Classification:** architecture diagram sources.
- **Target:** `docs/02-architecture/diagrams/system-context.mmd` and
  `processing-flow.mmd`.
- **Preserve:** actors, components, stores, trust/failure boundaries.
- **Conflicts:** use only current accepted flow; future diagrams stay proposals.
- **Cross-links:** overview/runtime/deployment/security.
- **Validation:** diagrams match the associated text and carry title/scope.
- **Status:** **blocked** until M-007–M-011 content is reviewed.

## M-014 — Create specification registry

- **Source:** current contract set and this ownership map.
- **Classification:** specification index.
- **Target:** `docs/03-specifications/README.md`.
- **Preserve:** contract version identifiers and boundaries.
- **Conflicts:** Candidate behavior remains a specification gap, but its Phase 1
  owner and target are resolved.
- **Cross-links:** requirements, architecture, ADRs, quality.
- **Validation:** every exact behavior has one registered specification.
- **Status:** **ready**.

## M-015 — Migrate capture contract

- **Source:** governance `#Capture`; system-design Conversation module;
  architecture/operations capture flow; `conversation.py` and capture tests as status evidence.
- **Classification:** specification.
- **Target:** `docs/03-specifications/capture-pipeline.md`.
- **Preserve:** eligible events, exclusions, privacy/redaction, source identity,
  spool boundary, partial input, assistant-context rules.
- **Conflicts:** D-001, D-002, D-006.
- **Cross-links:** requirements, runtime, security, processing, acceptance.
- **Validation:** intended contract remains explicit and each divergence is in STATUS.
- **Status:** **ready**.

## M-016 — Migrate processing contract

- **Source:** system-design Processor/seam; governance Processing; operations
  steps 8–18; context-budget research as rationale only.
- **Classification:** specification.
- **Target:** `docs/03-specifications/processing-pipeline.md`.
- **Preserve:** context categories/budgets, chunking, semantic proposal boundary,
  deterministic validation, errors and `no_memory`.
- **Conflicts:** C-001 belongs to memory spec; D-003/D-009 record partial status.
- **Cross-links:** capture, memory, candidates, provenance, interaction, quality.
- **Validation:** no data schema is duplicated; research is only evidence.
- **Status:** **ready** excluding conflict rule.

## M-017 — Migrate memory model

- **Source:** `docs/memory-record-contract.md` complete; accepted matching,
  identity, conflict, relationship rules in governance and system design.
- **Classification:** specification.
- **Target:** `docs/03-specifications/memory-model.md`.
- **Preserve:** all version identifiers, examples, state tables, structural
  summary schemas, layout, naming, lineage, overflow, and relationship rules.
- **Conflicts:** C-001 and research C-005.
- **Cross-links:** requirements, data architecture, processing, provenance,
  retrieval, ADRs, acceptance.
- **Validation:** section-by-section semantic comparison; C-001 explicitly resolved;
  no old source deleted before parity review.
- **Status:** **ready**; C-001 is resolved.

## M-018 — Decide/create Knowledge Candidate specification

- **Source:** candidate mentions across README/system design/governance;
  conflict-overflow contract; legacy Phase 7 material only as historical evidence.
- **Classification:** specification gap.
- **Target:** `docs/03-specifications/knowledge-candidates.md`.
- **Preserve:** noncanonical authority and exclusion from ordinary recall; do not
  invent schema/lifecycle.
- **Conflicts:** C-008.
- **Cross-links:** processing, memory model, data/security architecture, future Curator proposal.
- **Validation:** either a complete accepted contract exists or all unsupported
  Phase 1 candidate claims are narrowed; no legacy contract is silently adopted.
- **Status:** **ready**; authoring requires semantic review because no complete
  source contract exists.

## M-019 — Migrate provenance ledger

- **Source:** `docs/run-manifest-contract.md`; corresponding governance/operations;
  `storage.py` and Step 3 tests as implementation evidence.
- **Classification:** specification.
- **Target:** `docs/03-specifications/provenance-ledger.md`.
- **Preserve:** schemas/versions, fields, dedupe key, status meanings, date
  sharding, recoverable publication order, checkpoint semantics.
- **Conflicts:** D-008.
- **Cross-links:** data architecture, capture/processing, memory, acceptance.
- **Validation:** contract/code comparison lists D-008; no claim of transactional atomicity.
- **Status:** **ready**.

## M-020 — Migrate retrieval contract

- **Source:** governance `#Recall`; system-design Recall; operations recall
  behavior; architecture completion; budget research as rationale.
- **Classification:** specification.
- **Target:** `docs/03-specifications/retrieval-contract.md`.
- **Preserve:** request semantics, filters, statuses, projections, relevance/
  authority ordering, dedupe, budgets, exact-conversation exception, errors.
- **Conflicts:** deferred canonical-first claim C-003; implementation absent D-004.
- **Cross-links:** requirements, data/security/integration, memory, acceptance.
- **Validation:** current rule is singular and future rule remains historical.
- **Status:** **ready**.

## M-021 — Migrate interaction preference contract

- **Source:** `docs/interaction-preference-contract.md`; accepted matching
  governance/system-design sections; research as historical rationale.
- **Classification:** specification.
- **Target:** `docs/03-specifications/interaction-preferences.md`.
- **Preserve:** all schema/policy IDs, controlled values, abstentions, profile
  paths/state, activation/expiry/conflict/precedence, deterministic boundary.
- **Conflicts:** C-005 historical precursor; D-005 implementation absence.
- **Cross-links:** requirements, security, processing, guidance, quality, ADR.
- **Validation:** exact contract parity and no psychometric claim.
- **Status:** **ready**.

## M-022 — Migrate interaction guidance contract

- **Source:** `docs/interaction-guidance-contract.md` complete file.
- **Classification:** specification.
- **Target:** `docs/03-specifications/interaction-guidance.md`.
- **Preserve:** exact strings, keys, policy version and compiler rules byte-for-byte
  unless separately versioned.
- **Conflicts:** D-005 implementation absence.
- **Cross-links:** interaction preferences, quality tests.
- **Validation:** exact-output fixture comparison and template-key completeness.
- **Status:** **ready**.

## M-023 — Create configuration specification

- **Source:** operations Configuration; architecture data locations;
  `config/host.example.yaml`; AGENTS environment/path rule.
- **Classification:** specification.
- **Target:** `docs/03-specifications/configuration.md`.
- **Preserve:** local versus vault fields, environment override, budget defaults,
  path privacy, deterministic validation expectations.
- **Conflicts:** D-007; actual `config/host.yaml` must not be copied.
- **Cross-links:** deployment, security, data, runbook.
- **Validation:** example fields match spec; private values absent.
- **Status:** **ready**.

## M-024 — Establish decision registry and templates

- **Source:** former/current ADRs; system-design key decisions; PDS templates.
- **Classification:** decision index/template.
- **Target:** `docs/04-decisions/README.md`, `template.md`.
- **Preserve:** existing ADR numbers and supersession history; never reuse 0001–0004.
- **Conflicts:** C-004.
- **Cross-links:** architecture/specs/roadmap/proposals.
- **Validation:** every significant current decision has either an ADR or an
  explicit pending-decision entry.
- **Status:** **ready**.

## M-025 — Promote or retain existing ADRs 0001–0004

- **Source:** `tbd/future/adr/*.md` and their deleted former `docs/adr/` paths.
- **Classification:** historical decisions.
- **Target:** keep ADR 0001 through ADR 0004 under `docs/04-decisions/` with
  explicit superseded, proposed-future, or accepted lifecycle metadata.
- **Preserve:** exact numbers, text, status, supersedes/superseded-by links.
- **Conflicts:** C-004.
- **Cross-links:** roadmap/deployment/data/security as applicable.
- **Validation:** no history rewrite; target status accurately states phase/applicability.
- **Status:** **complete**; the initial `tbd/` custody exception was corrected
  by Owner direction on 2026-08-30 so every ADR record follows the PDS decision
  path.

## M-026 — Convert embedded current decisions to ADRs

- **Source:** `docs/system-design.md#Key-design-decisions`, AgentCairn sections,
  direct-source rationale and semantic/deterministic seam.
- **Classification:** accepted-looking decisions lacking ADRs.
- **Target:** new sequential ADRs beginning after reserved 0001–0004.
- **Preserve:** exact existing rationale and consequences; do not invent alternatives.
- **Conflicts:** acceptance is inferred from current normative use but not formally recorded.
- **Cross-links:** affected architecture/specifications/research evidence.
- **Validation:** Owner confirms decision status; ADR does not become sole current behavior owner.
- **Status:** **ready for ADR drafting**; each extracted decision still requires
  Owner review before acceptance.

## M-027 — Establish proposals package

- **Source:** selected unresolved future material under `tbd/future/`.
- **Classification:** proposal index/template and later proposal candidates.
- **Target:** `docs/05-proposals/README.md`, `template.md`, approved RFCs.
- **Preserve:** original `tbd` source until extraction validation.
- **Conflicts:** C-003/C-004/C-006; accepted labels cannot be copied blindly.
- **Cross-links:** roadmap phases, requirements, affected architecture, ADRs.
- **Validation:** every proposal visibly unaccepted; no current architecture
  depends on it.
- **Status:** **ready** for the index and template; promote no exact future design
  without separate Owner approval.

## M-028 — Create Phase 1 implementation plan

- **Source:** current implementation gaps in README/architecture/code/tests and
  accepted Phase 1 completion criteria; local notes as evidence only.
- **Classification:** active implementation plan.
- **Target:** `docs/06-plans/active/phase-1-implementation.md`.
- **Preserve:** current implemented slice and remaining capability order only
  where supported; do not import obsolete future plan tasks.
- **Conflicts:** C-008/C-009 and all D-series gaps.
- **Cross-links:** roadmap Phase 1, requirements/specs/ADRs, acceptance.
- **Validation:** milestones have measurable exit criteria and do not redefine design.
- **Status:** **ready for plan drafting**; Owner review is required before the
  plan becomes accepted execution authority.

## M-029 — Create acceptance plan

- **Source:** architecture completion criteria; operations readiness; tests; CI;
  local evidence reports as historical evidence.
- **Classification:** quality/acceptance.
- **Target:** `docs/07-quality/acceptance.md`.
- **Preserve:** every readiness case, evidence labels such as `PASS — SMALL
  SAMPLE`, and distinction between deterministic tests and semantic evaluation.
- **Conflicts:** implementation incomplete; no traceability IDs.
- **Cross-links:** requirements/specs/roadmap/plan/tests.
- **Validation:** no historical canary is upgraded into Phase 1 end-to-end proof.
- **Status:** **complete**; the Owner accepted the scenario IDs and normative
  quality gate on 2026-08-30.

## M-030 — Create test strategy

- **Source:** AGENTS Verification; CI; active tests; system-design deterministic
  boundary; research/evidence limitations.
- **Classification:** quality/test strategy.
- **Target:** `docs/07-quality/test-strategy.md`.
- **Preserve:** actual suite commands, deterministic versus semantic evaluation,
  fixture privacy and phase gates.
- **Conflicts:** C-009.
- **Cross-links:** acceptance, requirements/specs, AGENTS, CI.
- **Validation:** documented commands cover intended active suites or explicitly
  state exclusions.
- **Status:** **complete**; the Owner accepted the canonical active-suite route
  and evidence boundaries on 2026-08-30.

## M-031 — Decompose operations into runbook

- **Source:** `docs/operations.md` installation/configuration procedures,
  scheduling, recovery, troubleshooting/failure behavior.
- **Classification:** runbook.
- **Target:** `docs/08-operations/runbook.md`.
- **Preserve:** only executable or clearly labelled planned procedures; exact
  safety/failure statements and expected outcomes.
- **Conflicts:** D-002/D-006/D-007; current file has no install/start/health commands.
- **Cross-links:** runtime/deployment/data/security architecture and specs.
- **Validation:** copied commands are tested and labelled; unimplemented flow is
  linked as design, not represented as procedure.
- **Status:** **complete**; the Owner accepted the truthful limited runbook on
  2026-08-30. Deployment/start/health procedures remain unavailable until a
  runnable Phase 1 interface exists.

## M-032 — Keep root security policy narrow

- **Source:** `SECURITY.md`.
- **Classification:** vulnerability reporting policy.
- **Target:** root `SECURITY.md`.
- **Preserve:** private advisory route and sensitive-content prohibition.
- **Conflicts:** C-002 supported state; architecture detail moves to security-and-trust.
- **Cross-links:** STATUS and security-and-trust.
- **Validation:** reporting path remains correct; no duplicated trust model.
- **Status:** **complete**; reporting guidance is preserved and architecture
  detail routes to its current owners.

## M-033 — Update root README

- **Source:** current `README.md` after M-003/M-006/M-007/M-002 extraction.
- **Classification:** orientation.
- **Target:** root `README.md`.
- **Preserve:** concise project description, actual status, AgentCairn summary,
  locations, future links, quick start when verified.
- **Conflicts:** none after owners exist.
- **Cross-links:** docs index, status, roadmap, charter, overview, runbook.
- **Validation:** no detailed roadmap, specification, or plan remains.
- **Status:** **complete**; the control documents now exist and the root README
  is limited to orientation and current-status routing.

## M-034 — Update AGENTS protocol

- **Source:** current `AGENTS.md` and PDS agent protocol.
- **Classification:** agent instructions.
- **Target:** root `AGENTS.md`.
- **Preserve:** current safety, local notes, tbd/evidence boundaries, configuration
  constraints and narrow verification commands.
- **Conflicts:** C-009; no current PDS entry points.
- **Cross-links:** docs index, status, roadmap, architecture, governance specs,
  quality strategy.
- **Validation:** no architecture/roadmap duplication; correct commands and
  authority rules.
- **Status:** **complete**; AGENTS routes to current authority and uses the
  accepted canonical active-suite command.

## M-035 — Archive completed research

- **Source:** `docs/research/*.md`.
- **Classification:** historical research/evidence.
- **Target:** `docs/_archive/research/`.
- **Preserve:** full text, sources, inference labels, dates, and original report
  statuses; repair nonportable link without losing source description.
- **Conflicts:** C-005/C-011.
- **Cross-links:** relevant ADRs/specs as evidence, never normative authority.
- **Validation:** every adopted conclusion has a canonical owner; reports carry
  historical warning and replacement/evidence links.
- **Status:** **complete**; the Owner approved relocation and all three reports
  retain source context, historical warnings, and current-owner routes.

## M-036 — Preserve former active documents during migration

- **Source:** root/design/contract/operations documents superseded by targets.
- **Classification:** legacy mixed documentation.
- **Target:** `docs/_archive/legacy-docs/` only after target parity review.
- **Preserve:** complete original files, metadata, links where practical, and a
  manifest mapping every section.
- **Conflicts:** all C/D records remain visible in migration history.
- **Cross-links:** each archived file points to current replacements; current
  docs must not depend on archive.
- **Validation:** unique-information diff, link scan, ownership map, human review.
- **Status:** **complete**; the Owner approved relocation after target parity,
  current-link independence, archive-link, and ownership-map validation.

## M-037 — Retain legacy implementation as a declared exception

- **Source:** former `tbd/reference/legacy/**` package.
- **Classification:** noncurrent historical implementation package.
- **Target:** `legacy/manual-prototype/`; declare exception in `docs/README.md`.
- **Preserve:** source, tests, schemas, fixtures, runtime rules, code-adjacent
  contracts, provenance, runnable package, and exact history.
- **Conflicts:** internal accepted labels C-003/C-004.
- **Cross-links:** docs index warning; roadmap/proposals may cite exact sources.
- **Validation:** excluded from normal routes; no current document uses it as
  normative authority; no source/test relocation is attempted.
- **Status:** **complete**; Owner direction moved the intact package from the
  ambiguous `tbd/` path to the explicit top-level `legacy/` boundary.

## M-038 — Preserve local ignored records outside migration

- **Source:** `.agent-notes/`, `evidence/`, `index.md`, `config/host.yaml`.
- **Classification:** working/historical/local configuration.
- **Target:** unchanged ignored locations.
- **Preserve:** content, IDs, hashes, privacy and local-only status.
- **Conflicts:** C-007; no migration may correct them incidentally.
- **Cross-links:** public docs may mention the boundary, not private contents.
- **Validation:** `git check-ignore` still covers each root; no file appears in
  migration diff.
- **Status:** **complete** (retain-only action); ignore and tracked-file checks
  pass.

## M-039 — Resolve PDS standard custody

- **Source:** root `PDS.md`.
- **Classification:** external/internal standard reference.
- **Target:** retain and track the root copy as the repository's authoritative
  PDS-0.2 standard.
- **Preserve:** exact v0.2.0 text used for this audit and draft status.
- **Conflicts:** C-010.
- **Cross-links:** docs index declaration by version/profile.
- **Validation:** project has an accessible authoritative PDS source and no
  ambiguous duplicate standard.
- **Status:** **prepared**; the exact root copy is present with verified hash and
  will become tracked when the migration diff is committed.

## M-040 — Decide changelog trigger

- **Source:** `pyproject.toml` version, Git tags/log.
- **Classification:** conditional changelog.
- **Target:** none until an actual release exists.
- **Preserve:** no release history may be invented from working-tree changes.
- **Conflicts:** no tags; version alone is insufficient evidence.
- **Cross-links:** status/roadmap/release docs if created.
- **Validation:** entries correspond to actual releases and dates.
- **Status:** **complete** as an intentional no-op; no release evidence exists,
  so this migration does not create `CHANGELOG.md`.

## M-041 — Add documentation validation after structure stabilizes

- **Source:** PDS v0.2 validation requirements and this validation plan.
- **Classification:** quality tooling/CI plan.
- **Target:** future validator and CI integration; exact path decided during implementation.
- **Preserve:** required-document, metadata, ID, links, ownership, trigger,
  warning, and orphan checks.
- **Conflicts:** none; implementation not part of this audit.
- **Cross-links:** docs index, test strategy, AGENTS, CI.
- **Validation:** validator detects structural problems without asserting semantic correctness.
- **Status:** **excluded** from this migration-only task as later implementation
  and CI work.
