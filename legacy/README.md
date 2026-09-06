# Legacy implementation

This directory is a project-specific PDS exception for the retained Orca manual
prototype. PDS governs project documentation but does not prescribe a storage
location for historical source code and tests. Keeping the package here avoids
misclassifying executable material under `docs/archive/` or active Phase 1
material under `src/` and `tests/`.

## Contents and authority

- `manual-prototype/prototype/`: historical source, schemas, runtime rules, and
  code-adjacent contracts.
- `manual-prototype/tests/`: historical tests and fixtures for that source.

The package is noncurrent implementation evidence. It does not define accepted
behavior, current status, or future direction. Current project truth is indexed
in [`docs/README.md`](../docs/README.md); former all-phase design snapshots and
migration notes are in the [Documentation Archive](../docs/archive/README.md).

Consult this directory only for explicit historical comparison, prototype
behavior, or legacy migration work.

The package remains runnable from its own root when its pinned dependencies are
available:

```bash
cd legacy/manual-prototype
UV_CACHE_DIR=/tmp/orca-uv-cache \
CAIRN_LOCK_DIR=/tmp/orca-locks \
uv run --with agentcairn==0.25.2 python -m unittest \
  tests/integration/test_integration_adapter.py \
  tests/phase6/test_cairn_delta_adapter.py \
  tests/phase7/test_curator_delta_intake.py
```

Files here may retain historical terminology and former paths. Preserve their
content and provenance unless a task explicitly authorizes a correction.

## Owner and review trigger

The project Owner owns this exception. Review removal only after the active
Phase 1 replacement passes its accepted cutover and recovery evidence; retirement
must preserve necessary provenance in Git history before deleting the package.
