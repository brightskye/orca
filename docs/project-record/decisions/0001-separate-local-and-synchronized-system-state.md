---
id: ADR-0001
title: Separate local and synchronized system state
document_type: decision
status: superseded
authority: historical
implementation_status: not-applicable
applies_to: []
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
superseded_by:
  - ADR-0004
migration_classification: superseded-historical-rationale
---

# ADR-0001: Separate local and synchronized system state

Orca Memory originally assigned `.orca/` to local implementation and rebuildable runtime state, while synchronized noncanonical artifacts and governance lived under `System/Orca Memory/`. A partially synchronized hidden runtime tree was rejected because it made deployment, Syncthing ignores, authority, and recovery difficult to reason about.

ADR 0004 supersedes the local implementation location with a standalone project workspace while retaining the separation from synchronized vault data.
