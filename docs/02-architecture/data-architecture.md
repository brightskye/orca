---
id: ARCH-DATA
title: Orca Data Architecture
document_type: data-architecture
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-29
related:
  - ARCH-OVERVIEW
  - REQ-ORCA
---

# Orca data architecture

## Purpose

This document defines the accepted ownership, authority, lifecycle,
rebuildability, retention, synchronization, and security classification of Orca
data classes.

## This document owns

- Data-category ownership and lifecycle boundaries.
- Canonical, noncanonical, operational, and derived classifications.

## This document does not own

- Exact schemas, filenames, state machines, or processing algorithms.

## Data categories

| Data class | Owner/source | Authority | Primary location | Lifecycle and retention | Rebuildability | Phase 1 synchronization | Security |
|---|---|---|---|---|---|---|---|
| Canonical Memory | Owner | Canonical | Configured vault canonical folders | Governed human lifecycle; no automatic apply | No | None | Private |
| Agent conversation history | Agent/Codex | External source | Agent-owned rollout store | Agent-owned | No Orca copy | None | Private, may contain secrets |
| Conversation Evidence | Connector selection | Noncanonical transient evidence | Memory only during processing | Discard after processing; no raw archive | Re-readable when source remains | None | Private, minimized/redacted |
| Retry spool | Connector/runtime | Noncanonical operational recovery | Local `.runtime/` | Delete after success; at most three automatic attempts; default 72-hour terminal retention then content-free receipt | Re-created only from available source | Never | Highly sensitive |
| Conversation Continuation Summary | Storage from validated proposal | Noncanonical derived view | Vault shallow scope | Living replacement view | Rebuildable from permitted evidence only while available; provenance in Manifests | None | Private |
| Typed Memory Record | Storage from validated proposal | Noncanonical working memory | Vault shallow project/general/unassigned scope | Living current-state record with retained bounded lineage; no general automated Phase 1 retention | Current state may be reconstructed from governed records and Manifests only where semantics permit | None | Private |
| Project/Workstream Summary | Storage from validated proposal | Noncanonical derived view | Vault shallow project scope | Refresh on material record change; stale views excluded | Rebuildable from current typed records | None | Private |
| Knowledge Candidate | Storage from validated proposal | Noncanonical proposal | Vault `candidates/knowledge/` project/general/unassigned scope | `pending` until explicit review; terminal `approved-for-manual-apply` or `rejected`; no age-based retention or Phase 1 cleanup interface | Not generally rebuildable; Manifests retain exact provenance but not candidate content | None | Private, redacted |
| Conflict Overflow Candidate | Storage | Noncanonical proposal | Vault `candidates/conflicts/` scope | No age-based Phase 1 retention; remove only after committed explicit resolution dispositions | Provenance and disposition recoverable from Manifests | None | Private, redacted |
| Interaction Observation | Validated semantic proposal | Noncanonical evidence | Embedded by reference in immutable Run Manifest | Immutable audit evidence; no separate observation file | Read from Manifests | None | Private, no copied conversation text |
| Adaptive Interaction Profile | Deterministic consolidation | Noncanonical working context | Vault interaction profiles | Living active/conflicting state; inferred entries expire under the accepted policy | Rebuildable from observations | None | Private |
| Run Manifest | Storage | Noncanonical operational audit record | Vault date-sharded manifests | Immutable durable receipt; no accepted automatic deletion policy | Authoritative source for processed/audit projections | None | Private metadata and references |
| Checkpoint | Storage/runtime | Noncanonical operational progress | Local runtime | Advance last after successful durable publication | Repairable from Manifests where specified | Never | Local private |
| Retrieval projection/index | Deterministic projection/retrieval adapter | Derived and non-authoritative | Local `.runtime/` | Replace on source hash/policy change; discard when stale | Fully rebuildable from permitted current Markdown | Never | Private |
| Project Root Mapping | Governance/Owner confirmation | Local operational identity mapping | Local configuration/runtime | Update only through deterministic mapping or Owner-confirmed relink | Not inferred from synchronized paths | Never | Host-private |
| Host configuration | Owner/operator | Operational | Local ignored `config/host.yaml` plus optional `ORCA_VAULT_PATH` | Owner-managed; validated before operation | No | Never | Host-private paths and identities; no credentials |
| Vault configuration | Owner/operator | Operational | Vault `System/Orca Memory/orca-memory.yaml` | Owner-managed accepted policy and budget selection | No | None | Private |
| Credentials | Owner/operator and configured Adapter | External secret | Separately authorized local mechanism outside vault and Git | Owner-managed | No | Never | Secret |

## Canonical sources

Canonical Memory is authoritative only in the Owner-governed canonical vault
folders. Neither a Run Manifest, candidate, profile, retrieval index, synchronized
copy, nor high-ranked result can grant canonical authority.

Agent-owned conversation history is the source for capture provenance but is not
Orca memory. Run Manifests are the durable source for processing receipts,
deduplication, memory audit joins, and rebuildable operational projections.

## Derived representations

Project and Workstream Summaries, Adaptive Interaction Profiles, processed-source
indexes, retrieval projections, and retrieval indexes are derived views. A stale
or missing view must be excluded or rebuilt; it must not override its source
records.

## Data lifecycle

1. The Connector selects and redacts permitted source records.
2. Transient Conversation Evidence enters bounded processing or a secure retry
   spool when necessary.
3. Validated logical proposals become controlled vault artifacts.
4. A durable Run Manifest records the processing result.
5. The local checkpoint advances last.
6. Disposable projections reconcile from current permitted Markdown and
   Manifests.

Exact formats and transitions remain owned by the active contracts.

## Retention and deletion

Phase 1 has no general automated retention policy for Shallow Memory or Run
Manifests. Ordinary Knowledge Candidates have no age-based retention and expose
no Phase 1 cleanup interface. Conflict Overflow Candidates also have no
age-based retention and are removed only through their accepted resolution
flow. Retry-spool content follows the bounded recovery policy above. A deletion
or retention policy must not be inferred from archived or legacy material.

Deletion must preserve authority and provenance boundaries. An interrupted
candidate cleanup cannot make a resolved position current or reviewable again.

## Consistency and recovery

Phase 1 uses local filesystem state. Publication is recoverable through durable
artifacts, Manifest-last receipt semantics, and checkpoint-last progress rather
than claimed transactional atomicity. Optional SQLite and retrieval indexes are
disposable accelerators.

## Synchronization

Phase 1 synchronizes nothing. Phase 3 synchronization is a candidate direction;
only accepted permitted vault artifacts may eventually be eligible. Host paths,
credentials, runtime state, checkpoints, locks, spools, queues, and indexes
remain host-local.

## Schema evolution and migration

Artifact schemas and policy versions are explicit. A redaction-policy change is
a policy revision rather than a source-integrity error. Migration must preserve
stable memory, project, variant, conversation, and run identities and must not
derive identity from filenames or content hashes.

## Backup and recovery

The configured vault requires Owner-managed backup appropriate to private
memory. The project repository backs up only public source and documentation.
Disposable indexes are rebuilt, not backed up as authority. The current runbook
migration must define only verified operational procedures.

## Known risks

- Ordinary Knowledge Candidate behavior is accepted but remains unimplemented.
- General Shallow Memory and Manifest retention is intentionally unspecified in
  Phase 1 and requires an explicit later decision.
- Backup and filesystem semantics have not yet been verified in a routine
  deployment.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Memory format:** [Memory Model](../03-specifications/memory-model.md)
- **Knowledge Candidates:** [Knowledge Candidates](../03-specifications/knowledge-candidates.md)
- **Provenance:** [Provenance Ledger](../03-specifications/provenance-ledger.md)
- **Configuration:** [Configuration](../03-specifications/configuration.md)
- **Checkout/vault rationale:** [ADR-0004](../04-decisions/0004-separate-project-workspace-from-vault.md)
- **Security classification:** [Security and Trust](security-and-trust.md)
- **Current state:** [Current Status](../STATUS.md)
