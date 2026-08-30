# Orca project instructions

## Scope

This repository owns the active Phase 1 Orca Memory implementation and its
supporting documentation. The configured Orca vault owns memory data. Historical
prototype source and tests live under `legacy/`.

## Authority

- When `.agent-notes/` exists, read `.agent-notes/current.md` before resuming
  ongoing work and update the relevant note when project state materially changes.
- Read `docs/README.md` when locating the document that owns a rule or lifecycle.
- Read `docs/STATUS.md` before claiming a capability is implemented, verified,
  deployed, or ready.
- Read `docs/ROADMAP.md` when changing phase scope, entry conditions, or exit
  criteria.
- Read `docs/01-foundation/glossary.md` when changing domain language or module
  boundaries.
- Read `docs/02-architecture/overview.md` for the active Phase 1 system structure.
- Read `docs/governance/memory-system-contract.md` before changing authority,
  privacy, capture, processing, recall, or canonical behavior.
- Read `docs/03-specifications/memory-model.md` before changing memory kinds,
  subjects, filenames, record placement, lifecycle, or Storage naming behavior.
- Read `docs/03-specifications/knowledge-candidates.md` before changing ordinary
  candidate schema, placement, review, retention, or disposition behavior.
- Read `docs/03-specifications/configuration.md` before changing host or vault
  configuration fields, defaults, validation, or precedence.
- Read `docs/07-quality/test-strategy.md` before changing tests, fixtures, CI,
  or verification commands. Read `docs/07-quality/acceptance.md` before making
  a Phase 1 acceptance claim.
- Read `docs/08-operations/runbook.md` before executing or documenting an
  operator procedure.
- Read `legacy/README.md` only when a task explicitly targets prototype
  behavior, historical comparison, or legacy migration.
- Treat `evidence/` and `index.md` as local historical records. Preserve their
  content, IDs, and hashes unless a task explicitly authorizes a historical
  correction. They must remain outside the public Git repository.

## Working rules

- Implement the smallest structural change that satisfies the current task.
- Keep the retrieval backend replaceable and Orca authoritative.
- Keep conversation evidence, candidates, and shallow memory noncanonical.
- Keep canonical apply disabled and unexposed in Phase 1.
- Load the vault path from local `config/host.yaml` or `ORCA_VAULT_PATH`; never
  hard-code a personal vault path in tracked source.
- Keep `config/host.yaml`, `.runtime/`, credentials, secrets, private memory,
  and generated dependency caches out of Git.
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
  tests/agentcairn/test_distiller.py
```
