---
status: accepted
date: 2026-08-25
supersedes: 0001-separate-local-and-synchronized-system-state.md
---

# Separate the Orca project workspace from the Orca vault

Orca Memory code, tests, technical documentation, deployment assets, and
historical engineering evidence live in a standalone project checkout such as
`/workspace/projects/orca`.

The configured Orca vault contains knowledge and synchronized operational data,
including future `System/Orca Memory/` artifacts. It does not contain the
service source checkout. Each host keeps its vault path and rebuildable runtime
location in a local, unversioned `config/host.yaml`.

This keeps executable project lifecycle and Git history independent from the
Obsidian knowledge library while preserving Orca as the authoritative memory
store.
