---
status: superseded
superseded_by: 0004-separate-project-workspace-from-vault.md
---

# Separate local and synchronized system state

Orca Memory originally assigned `.orca/` to local implementation and rebuildable runtime state, while synchronized noncanonical artifacts and governance lived under `System/Orca Memory/`. A partially synchronized hidden runtime tree was rejected because it made deployment, Syncthing ignores, authority, and recovery difficult to reason about.

ADR 0004 supersedes the local implementation location with a standalone project workspace while retaining the separation from synchronized vault data.
