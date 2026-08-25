---
type: migration-notes
status: current
created: 2026-08-25
updated: 2026-08-25
tags:
  - orca
  - agent-memory
  - migration
  - provenance
---

# Prototype migration notes

These notes constrain later structural migration. The manual prototype has now been relocated intact to `prototype/`; this does not authorize changing its behavior or rewriting historical evidence.

## Responsibility map

| Current responsibility | Structural destination |
|---|---|
| Codex normalization | connector adapter for Codex |
| Hermes normalization | connector adapter for Remote Agent |
| Source event identity and persistence | conversation module |
| Semantic provider execution and validation | distillation module |
| Cairn parsing and reconciliation | replaceable backend/storage adapter |
| Checkpoint lineage and deduplication | storage module |
| Atomic publication and locking | storage module |
| Delta validation and Curator intake | Curator intake module |
| Semantic proposal recording | Curator planning module |
| Guarded canonical mutation | internal Curator apply module |
| Authorization and policy loading | governance module |

The new implementation preserves proven normalization, positive identification, hashing, complete-scan, checkpoint, locking, precondition, atomic-write, and lineage behavior. It does not preserve the Phase 6/7 workflow shape, loose-file imports, path insertion, or phase identifiers.

## Current-source provenance cautions

### Integration adapter

The current manual adapter at `prototype/integration/integration_adapter.py` reports `orca-cairn-integration/0.2.0`. Its current source is:

- SHA-256: `842baf7b6e9823017764e370772a5b225d4b49074582f7fcd9a75e0cce0b91ac`
- byte length: `26561`

Retained smoke and canary artifacts record the adapter version but do not preserve a freeze manifest that content-binds this exact Python revision. Archive it as the current manual source without claiming that the retained executions cryptographically prove this revision.

### Phase 7 intake

The current relocated Phase 7 source is `prototype/integration/phase7/curator_delta_intake.py`:

- SHA-256: `537a5720904a91bc4254aa9a8a94e3485d7195adc275ec6fd7e9726c655d43c7`
- byte length: `73640`

The frozen v0.1.4 manifest records:

- SHA-256: `af5e8acd21ddaeb050eba440afbd36d8e680a03ed8f2abfd90821b24faddd8e5`

The contract and schemas match their frozen manifest, but the Python source does not. The reason is unproven because the archive does not retain the old source copy. Preserve the current source as a relocated revision with this ambiguity; do not repair historical manifests or call the source identical to the frozen implementation.

### Semantic provider rules

The current semantic rules hash is `832b9e49096064ce2554a46f859f5162bfc36c61d6f5747e62fe8cae8128c62c`. It matches the final provider smoke and real-use canary artifacts. Earlier smoke evidence retains an older rules hash and remains valid historical evidence.

The current rules document contains a stale relative contract link. Structural migration replaces filesystem-relative coupling with configured governance lookup and recorded content hashes; historical artifacts remain untouched.

## Path and artifact rules

- Package tests use installed imports rather than calculating the vault root or modifying `sys.path`.
- Synchronized provenance uses stable source IDs, URIs, replica IDs, writer IDs, and hashes. Absolute machine paths remain local-only.
- Existing evidence, freeze manifests, reports, IDs, and embedded historical paths remain unchanged.
- The relocated manual source remains clearly labelled under `prototype/` until replacement cutover succeeds; its operational retirement is a separate decision.
- Generated `__pycache__` and `.pyc` files are removed rather than migrated.
