---
id: ADR-0005
title: Read agent history without creating a raw archive
document_type: decision
status: accepted
authority: historical
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
supersedes: []
---

# ADR-0005: Read agent history without creating a raw archive

## Context

Orca needs retryable, provenance-bearing capture, but copying complete agent
transcripts would create another sensitive store with independent retention and
privacy risk.

## Decision

The Conversation Module reads bounded records directly from agent-owned history
and exposes only permitted redacted Conversation Evidence through its Interface.
Only a bounded secure retry spool may temporarily preserve evidence when the
source may disappear. Orca creates no second raw or merged transcript archive.

## Consequences

Source identities, hashes, Run Manifests, and checkpoint-last publication carry
audit and replay state without duplicating private transcripts. Recovery of
unpublished semantic meaning is limited once both the agent source and eligible
retry material are gone.

## Related documents

- **Capture behavior:** [Capture Pipeline](../03-specifications/capture-pipeline.md)
- **Security:** [Security and Trust](../02-architecture/security-and-trust.md)
