---
type: orca-curator-disposition
authority: candidate
orca_state: merged
candidate_id: fixture-correction-k7
comparison: correction
canonical_target: Projects/Example/current.md
curated:
  by: process:phase4-fixture
  at: 2026-08-22T16:05:00+08:00
  skill: orca-curator/0.1
  reason: Explicit human correction supersedes the prior preference in this isolated fixture.
relations:
  - type: supersedes
    target: Projects/Example/historical.md
human_correction:
  explicit: true
  source: memory://fixture/k7-correction
sources:
  - id: candidate-k7
    resource: Inbox/candidate-correction.md
  - id: fixture-source-s1
    resource: Raw/sources/source-s1.md
---

# Curator disposition fixture

The old evidence, explicit correction, disposition, current target, and supersession relation remain linked.
