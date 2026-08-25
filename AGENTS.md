# Orca project instructions

## Scope

This repository owns the Orca Memory System implementation, tests, technical
documentation, deployment assets, and engineering history. The configured Orca
vault owns memory data. Keep project source and vault content separate.

## Authority

- Read `CONTEXT.md` when changing domain language or module boundaries.
- Read `docs/architecture.md` for system structure and deployment topology.
- Read `docs/governance/memory-system-contract.md` before changing authority,
  lifecycle, curation, privacy, or canonical-apply behavior.
- Treat `evidence/` and `index.md` as local historical records. Preserve their
  content, IDs, and hashes unless a task explicitly authorizes a historical
  correction. They must remain outside the public Git repository.

## Working rules

- Implement the smallest structural change that satisfies the current task.
- Keep AgentCairn replaceable and Orca authoritative.
- Keep candidates, shallow memory, and source evidence noncanonical.
- Keep canonical apply disabled unless a task explicitly grants the required
  scope and the governance gates pass.
- Load the vault path from local `config/host.yaml` or `ORCA_VAULT_PATH`; never
  hard-code a personal vault path in tracked source.
- Keep `config/host.yaml`, `.runtime/`, credentials, secrets, private memory,
  and generated dependency caches out of Git.
- Preserve the current manual prototype under `prototype/` until
  a separately verified cutover retires it.

## Verification

Run the focused prototype suite after changing the prototype or its
tests:

```bash
UV_CACHE_DIR=/tmp/orca-uv-cache \
CAIRN_LOCK_DIR=/tmp/orca-locks \
uv run --with agentcairn==0.25.2 python -m unittest \
  tests/integration/test_integration_adapter.py \
  tests/phase6/test_cairn_delta_adapter.py \
  tests/phase7/test_curator_delta_intake.py
```

Run `tests/skills/test_phase4_skills.py` only where the configured vault
contains the transitional Orca skills.
