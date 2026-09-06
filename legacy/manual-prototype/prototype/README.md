# Orca Agent Memory — Current Manual Prototype

This directory contains the Orca-owned code and rules used by the current
manual/local shared-memory prototype. It remains relevant until verified
cutover, but its planning-phase layout is not the accepted target architecture.

Use the archived [all-phase system overview](../../../docs/archive/legacy-design/system-overview.md)
for historical design context.

```text
integration/integration_adapter.py
  Codex/Hermes normalization, one-pass provider binding, and locked Cairn ingest

workflows/semantic-provider-rules.md
  current semantic selection rules

integration/phase6/
  deterministic Cairn delta/checkpoint adapter, contract, and schemas

integration/phase7/
  deterministic delta-to-Curator intake, contract, and schemas
```

Tests and fixtures live under `tests/`. Completed reports and run artifacts live
under `evidence/`; superseded phase work lives under `archive/`.

These components do not install production hooks, change Cairn source, enable
automatic canonical apply, or define a permanent runtime-state location. All
runtime roots, checkpoints, and processing-state paths remain explicit inputs.

This tree has been relocated intact from the vault and remains the current
manual prototype until replacement client and processor deployments pass
cutover. At that point it can be retired as historical source. Existing
evidence, contracts, hashes, and historical paths remain unchanged; generated
bytecode is not preserved.
