# Orca data architecture

This view owns data categories, responsibility, authority, storage boundaries,
and rebuildability. Exact schemas, paths, state transitions, and retention
rules belong to the linked specifications.

## Data ownership

| Data class | Owner and authority | Storage boundary | Recovery or derivation | Contract |
|---|---|---|---|---|
| Canonical Memory | Owner-governed canonical knowledge | Configured vault | Requires an Owner-governed recovery copy | [Memory System Contract](../specifications/memory-system-contract.md) |
| Conversation history | External agent-owned source | Agent store | No second Orca raw archive | [Capture](../specifications/capture.md) |
| Conversation Evidence | Transient noncanonical input | Processing memory | Re-readable while permitted source remains | [Capture](../specifications/capture.md) |
| Retry spool | Private operational recovery input | Local runtime | Bounded recovery from permitted evidence | [Capture](../specifications/capture.md) |
| Typed Memory Records | Noncanonical working memory | Vault shallow scopes | Durable records with governed lineage | [Memory](../specifications/memory.md) |
| Continuation, Project, and Workstream Summaries | Noncanonical derived views | Vault shallow scopes | Derived from permitted evidence or records while available | [Memory](../specifications/memory.md) |
| Ordinary and overflow candidates | Noncanonical proposals | Vault candidate scopes | Durable proposals with explicit disposition | [Knowledge Candidates](../specifications/knowledge-candidates.md), [Memory](../specifications/memory.md) |
| Interaction observations and profiles | Noncanonical evidence and working context | Manifests and vault profiles | Profiles derive from observations | [Interaction Preferences](../specifications/interaction-preferences.md) |
| Run Manifests | Durable processing receipts, noncanonical | Vault provenance | Source for audit and processing projections | [Provenance](../specifications/provenance.md) |
| Publication intents and staged post-images | Private operational recovery plans | Local runtime | Finish a fixed publication or require repair | [Provenance](../specifications/provenance.md) |
| Owner-review receipts and intents | Explicit decision provenance and recovery | Vault receipts; local intents | Recover a fixed Owner disposition | [Memory](../specifications/memory.md), [Knowledge Candidates](../specifications/knowledge-candidates.md) |
| Project registry, mapping, and mapping intents | Governed identity and local operational mapping | Vault registry; host-local paths and intents | Rebuild lookup or recover a fixed mapping | [Configuration](../specifications/configuration.md), [Memory](../specifications/memory.md) |
| Checkpoints, cursors, and scope choices | Local progress and explicit scope evidence | Local runtime | Recover only from their permitted sources | [Provenance](../specifications/provenance.md), [Capture](../specifications/capture.md), [Runtime](../specifications/runtime.md) |
| Attention projection and reminder cursor | Derived content-free status | Local runtime | Rebuild from owning source states | [Runtime](../specifications/runtime.md) |
| Retrieval indexes and optional lookup caches | Disposable, non-authoritative projections | Local runtime | Rebuild from permitted artifacts | [Retrieval](../specifications/retrieval.md) |
| Host and vault configuration | Owner-selected operating policy | Host-local configuration and vault | Owner-managed | [Configuration](../specifications/configuration.md) |
| Credentials | External secrets | Separately authorized local mechanism | Owner-managed, outside vault and Git | [Memory System Contract](../specifications/memory-system-contract.md) |
| Encrypted backup | Recovery copy without independent authority | Private destination | Verify before exposing separate staging | [Backup](../specifications/backup.md) |

## Authority and derived views

Canonical authority comes from the Owner-governed canonical store. Neither a
Manifest, candidate, profile, index, synchronized copy, nor ranked result can
grant it.

Manifests are durable processing receipts. Summaries, profiles, attention
projections, and indexes derive from their respective sources. A derived view
cannot override the record from which it was built. Missing source can limit
reconstruction even when provenance remains.

## Lifecycle and consistency

The Connector selects evidence; Processor proposes meaning; Storage publishes
validated artifacts and provenance; local progress follows durable publication.
Project mapping and Owner disposition use their own recoverable operations.
[Runtime Architecture](README.md#runtime) shows the interactions.

Retention and deletion belong to each artifact's specification. The
[Roadmap](../project-record/roadmap.md#intentionally-deferred) owns general
retention work that remains deferred.

## Host and recovery boundaries

Phase 1 uses one local vault. Host configuration, credentials, queues, spools,
locks, checkpoints, indexes, and recovery intents remain host-local.
Synchronization requires later accepted design.

The repository preserves public source and documentation. Vault backup protects
private memory, while disposable indexes can be rebuilt. Exact backup membership,
validation, and staging rules belong to [Backup](../specifications/backup.md);
execution belongs to the [Runbook](../operations/runbook.md).

Implementation and verification limits belong to [Current](../project-record/current.md).
