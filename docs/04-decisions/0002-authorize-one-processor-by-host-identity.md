---
id: ADR-0002
title: Authorize one processor by host identity
document_type: decision
status: proposed
authority: working
implementation_status: planned
applies_to:
  - phase-3-candidate
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
source_status: accepted
migration_classification: future-only-proposal-evidence
---

# ADR-0002: Authorize one processor by host identity

Many connectors may publish immutable evidence, but synchronized governance names exactly one processor `host_id` and generation. This preserves two writable replicas and portable deployments without allowing duplicate distillation, profile calculation, retention, or automated canonical apply.
