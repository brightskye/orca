---
type: orca-candidate
authority: candidate
orca_state: new
intent: explicit
candidate_id: fixture-correction-k7
captured_at: 2026-08-22T16:00:00+08:00
generated:
  by: orca-capture/0.1
  at: 2026-08-22T16:00:00+08:00
sources:
  - id: fixture-source-s1
    resource: Raw/sources/source-s1.md
  - id: human-correction-k7
    resource: memory://fixture/k7-correction
    author: human:owner
candidate_type: preference
applicability:
  scope: owner-global
retention:
  class: durable
relations:
  - type: supersedes
    target: Projects/Example/historical.md
---

# Candidate correction

## Candidate content

Architecture reviews should be detailed.

## Authority

Explicit capture intent and human correction evidence are preserved. The proposition remains noncanonical until Curator apply.
