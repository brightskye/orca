---
id: ADR-0004
title: Separate the Orca project workspace from the Orca vault
document_type: decision
status: accepted
authority: historical
implementation_status: verified
applies_to:
  - phase-1
  - phase-2-candidate
  - phase-3-candidate
owners:
  - project-owner
date: 2026-08-25
last_reviewed: 2026-08-30
supersedes:
  - ADR-0001
migration_classification: promoted-to-active-decision-registry
---

# ADR-0004: Separate the Orca project workspace from the Orca vault

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
