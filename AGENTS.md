# Orca project instructions

## Scope

This repository owns the active Phase 1 Orca Memory implementation and its
supporting documentation. The configured Orca vault owns memory data. Historical
prototype source and tests live under `legacy/`.

Orca follows the PLS 0.3 working model. Its [project map](README.md#project-map)
and [documentation map](docs/README.md) own local placement and navigation.
The PLS standard is maintained as an independent project; ordinary Orca work
follows the mapped local routes without loading or modifying that sibling
project. The preserved `docs/archive/standards/PDS-0.2.md` is historical and no
longer governs Orca.

## Authority

- When `.local/agent-note/README.md` exists, read its index before resuming
  ongoing work. Read only relevant `pending/` notes by default; consult
  `reviewed/` or `retired/` only when the task explicitly needs that history.
- Treat `.local/agent-note/` as temporary, ignored, non-authoritative context.
  Promote durable outcomes to the Project Record or the owning document before
  a pending note leaves that state.
- Read `docs/project-record/README.md` when current work, next work, proposals,
  decisions, or history must be located together.
- Read `docs/README.md` when locating the document that owns a rule or lifecycle.
- Read `docs/project-record/current.md` before claiming a capability is implemented, verified,
  deployed, or ready.
- Read `docs/project-record/roadmap.md` when changing phase scope, entry conditions, or exit
  criteria.
- Read `docs/specifications/glossary.md` when changing domain language or module
  boundaries.
- Read `docs/architecture/README.md` for the active Phase 1 system structure.
- Read `docs/specifications/runtime.md` before changing worker coordination,
  catch-up, attention, or session reminders.
- Read `docs/specifications/backup.md` before changing backup membership,
  validation, or staging behavior.
- Read `docs/specifications/memory-system-contract.md` before changing authority,
  privacy, capture, processing, recall, or canonical behavior.
- Read `docs/specifications/memory.md` before changing memory kinds,
  subjects, filenames, record placement, lifecycle, or Storage naming behavior.
- Read `docs/specifications/knowledge-candidates.md` before changing ordinary
  candidate schema, placement, review, retention, or disposition behavior.
- Read `docs/specifications/configuration.md` before changing host or vault
  configuration fields, defaults, validation, or precedence.
- Read `docs/quality/test-strategy.md` before changing tests, fixtures, CI,
  or verification commands. Read `docs/quality/acceptance.md` before making
  a Phase 1 acceptance claim.
- Read `docs/operations/runbook.md` before executing or documenting an
  operator procedure.
- Read `docs/operations/setup.md` for installation, hook configuration, or the
  first controlled test. `docs/operations/README.md` is the navigation index.
- Read `legacy/README.md` only when a task explicitly targets prototype
  behavior, historical comparison, or legacy migration.
- Treat `.local/evidence/` and `.local/index.md` as local historical records.
  Preserve their content, IDs, and hashes unless a task explicitly authorizes a
  historical correction. They must remain outside the public Git repository.

## Working rules

- Implement the smallest structural change that satisfies the current task.
- Prefer readable sections in an existing document. Split out a separate
  document only when the amount of content makes the combined document hard
  to use; a distinct topic alone does not justify another file.
- Use PLS 0.3 placement and content ownership. Do not retain old layout rules
  or introduce a placement exception without explicit Owner confirmation.
- Follow the root README's [Source boundary](README.md#source-boundary). Do not
  place test-only runners, development automation, or temporary helpers in the
  installed `src/orca_memory/` package.
- Keep the retrieval backend replaceable and Orca authoritative.
- Keep conversation evidence, candidates, and shallow memory noncanonical.
- Keep canonical apply disabled and unexposed in Phase 1.
- Load the vault path from local `config/host.yaml` or `ORCA_VAULT_PATH`; never
  hard-code a personal vault path in tracked source.
- Keep `config/host.yaml`, `.runtime/`, credentials, secrets, private memory,
  and generated dependency caches out of Git.
- Do not save conversations automatically. When the Owner asks to retain a
  temporary conversation note, use `.local/agent-note/`, keep its index and
  state current, and record a concise summary rather than mirroring a
  transcript. Exclude private vault content, credentials, hidden reasoning,
  and unnecessary tool output.
- Preserve the historical package under `legacy/`; it does not define active
  Phase 1 behavior.

## Verification

Run the active Phase 1 suite after changing implementation or tests:

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
  tests/interaction/test_interaction.py \
  tests/interaction/test_pipeline.py \
  tests/retrieval/test_retrieval.py \
  tests/config/test_configuration.py \
  tests/runtime/test_runtime.py \
  tests/runtime/test_attention.py \
  tests/runtime/test_application.py \
  tests/runtime/test_owner_review.py \
  tests/runtime/test_backup.py \
  tests/runtime/test_codex_provider.py \
  tests/runtime/test_codex_hook.py \
  tests/acceptance/test_readiness_boundaries.py \
  tests/acceptance/test_semantic_evaluation.py \
  tests/agentcairn/test_distiller.py
```
