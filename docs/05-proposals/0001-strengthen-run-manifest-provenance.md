---
id: RFC-0001
title: Strengthen Run Manifest provenance and recovery
document_type: proposal
status: accepted
authority: informative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
---

# RFC-0001: Strengthen Run Manifest provenance and recovery

## Summary

This accepted record proposed `orca-run-manifest/0.2` and
`orca-checkpoint/0.2`.

The accepted formats:

- identify every processed segment of an oversized turn;
- connect each accepted operation to its exact source segments;
- connect logical artifact IDs to physical file writes;
- record support and no-change outcomes even when no file changes; and
- recover safely when artifact publication starts but the Run Manifest is not
  published.

The Owner accepted this RFC on 2026-08-30. Its conclusions were promoted into
the owning specifications, architecture, quality documents, and implementation
plan. Those current documents now own exact behavior; this RFC remains the
informative decision and design record.

## Motivation

The accepted design has two ordinary-path gaps.

First, the Processor may split one oversized turn across several runs, but the
current processed-source key contains only connector ID, conversation ID, and
turn ID. A later segment can therefore look like a changed copy of an already
processed turn.

Second, a Typed Memory Record uses `memory_id` to join the record to its audit
history, but a current Manifest output contains only artifact kind, path, and
hash. It does not say which logical record changed or which source segments
supported that operation.

There is also a recovery gap. Artifacts publish before the immutable Manifest.
If Manifest publication fails, files may exist without the durable receipt
needed to explain or safely complete the run.

## Roadmap context

This change supports Phase 1 Milestones 2 and 3. During review, Milestone 1
capture work could continue, but Typed Memory Record and full processing
publication could not freeze a permanent Manifest schema. Acceptance resolved
that design block; implementation remains pending.

## Goals

- Make each processed source segment independently identifiable and replay-safe.
- Make one Manifest sufficient to audit what logical operation occurred, which
  sources supported it, and which physical files changed.
- Keep semantic providers unable to assign identity, paths, hashes, or
  publication order.
- Keep Manifests immutable and checkpoints disposable.
- Recover an interrupted publication without another semantic call when the
  required local recovery data remains valid.
- Fail closed and request human repair when automatic reconciliation is unsafe.

## Non-goals

- Changing memory meaning, matching, conflict, candidate, or interaction rules.
- Adding a database, public service, dashboard, or canonical-write path.
- Copying conversation text into a Manifest.
- Rewriting or deleting existing `orca-run-manifest/0.1` files.
- Defining the general human-attention interface; that is a separate design
  decision.

## Current behavior

At proposal time, the accepted [Provenance
Ledger](../03-specifications/provenance-ledger.md) owned
`orca-run-manifest/0.1` and `orca-checkpoint/0.1`. The promoted version now owns
the `0.2` formats and retains `0.1` read compatibility. The [Processing
Pipeline](../03-specifications/processing-pipeline.md) owns oversized-turn
segmentation and semantic operation meaning. The [Memory
Model](../03-specifications/memory-model.md) makes `memory_id` the Typed Memory
Record audit join.

Current code implements the initial `0.1` Conversation Continuation Summary
slice only. It does not yet implement oversized-turn segmentation, Typed Memory
Records, Knowledge Candidates, or the complete operation set.

## Proposed design

### One simple audit model

The Manifest would contain three linked arrays:

```text
sources -> operations -> outputs
```

- `sources` say exactly which redacted source segments were processed.
- `operations` say what logical result was accepted and which sources support
  it.
- `outputs` say which physical files were created, replaced, or deleted.

Local references such as `src-001`, `op-001`, and `out-001` are unique only
inside one Manifest. Stable artifact identity remains owned by the artifact's
specification.

### Source segment receipt

Every source receipt would use the same structure, including an unsegmented
turn:

```json
{
  "source_ref": "src-001",
  "turn_id": "turn-17",
  "source_uri": "codex://session/example/event/turn-17",
  "occurred_at": "2026-08-30T10:00:00Z",
  "turn_content_sha256": "<whole-redacted-turn-hash>",
  "redaction_policy": "orca-redaction/0.1",
  "segment": {
    "policy_version": "orca-segmentation/0.1",
    "parameters_sha256": "<canonical-segmentation-parameters-hash>",
    "index": 1,
    "count": 2,
    "start_byte": 0,
    "end_byte": 24000,
    "content_sha256": "<redacted-segment-hash>"
  }
}
```

`start_byte` is inclusive and `end_byte` is exclusive in the UTF-8 encoding of
the normalized redacted turn. Segment boundaries must fall on valid UTF-8
boundaries. An unsegmented turn uses index `1`, count `1`, start byte `0`, and
the full redacted byte length as its end.

The proposed processed-source key is:

```text
connector_id
+ conversation_id
+ turn_id
+ redaction_policy
+ segment.policy_version
+ segment.parameters_sha256
+ segment.index
```

The whole-turn hash, segment count, byte range, and segment hash establish the
processed representation. A matching key with different representation fields
fails closed. A changed redaction or segmentation policy requires governed
reprocessing and is not silently treated as a new segment.

### Operation receipt

Each validated semantic operation would produce one receipt:

```json
{
  "operation_id": "op-001",
  "operation": "update",
  "outcome": "updated",
  "artifact_kind": "typed-memory-record",
  "artifact_id": "mem_example",
  "source_refs": ["src-001"],
  "output_refs": ["out-001"],
  "embedded_artifact": null
}
```

Storage assigns `operation_id` and validates every reference. The semantic
provider cannot assign it.

The proposed controlled operation values are:

- `add`
- `support`
- `update`
- `supersede`
- `conflict`
- `candidate`
- `observation`
- `summary-refresh`
- `summary-stale`

The proposed controlled outcomes are:

- `created`
- `supported`
- `updated`
- `conflict-recorded`
- `observed`
- `stale`
- `no-change`

The accepted pairings are `add/created`, `support/supported`,
`update/(updated or no-change)`, `supersede/updated`,
`conflict/conflict-recorded`, `candidate/(created, updated, or no-change)`,
`observation/observed`, `summary-refresh/(created, updated, or no-change)`, and
`summary-stale/stale`.

The operation records the accepted logical result, not merely the provider's
request. `support`, `observation`, `summary-stale`, and `no-change` may have no
physical output. Every operation must carry the stable identity defined by its
owning specification.

Examples of stable artifact identity are:

| Artifact kind | `artifact_id` source |
|---|---|
| Typed Memory Record | `memory_id` |
| Knowledge Candidate | `candidate_id` |
| Conflict Overflow Candidate | `<memory_id>:<variant_id>` |
| Interaction Observation | `observation_id` |
| Conversation Continuation Summary | Conversation Identity |
| Project Summary | `project_id` |

Every operation must cite at least one source from the current run. An
`output_ref` must point to an output for the same artifact identity.
`embedded_artifact` is normally null; it carries the complete validated
artifact only when the owning specification places that artifact inside the
Manifest. In Phase 1 this applies to an Interaction Observation.

### Physical output receipt

Each changed file would use this structure:

```json
{
  "output_ref": "out-001",
  "artifact_kind": "typed-memory-record",
  "artifact_id": "mem_example",
  "effect": "replaced",
  "path": "System/Orca Memory/shallow/projects/orca/decisions/example.md",
  "before_sha256": "<old-hash>",
  "after_sha256": "<new-hash>"
}
```

`effect` is `created`, `replaced`, or `deleted`.

- `created` requires a null `before_sha256` and a present `after_sha256`.
- `replaced` requires both hashes.
- `deleted` requires a present `before_sha256` and a null `after_sha256`.

Support-only and no-change operations create no output entry. The Manifest file
does not list itself as an output.

### Run status

`status: success` means at least one validated operation was recorded, even if
the result was support-only and no artifact file changed.

`status: no_memory` means the complete valid run produced no accepted semantic
operation, including a valid full abstention. Its `operations` and `outputs`
arrays are empty. Both statuses mark the listed source segments as processed.

### Checkpoint 0.2

The checkpoint would identify the last processed segment, not only the last
turn:

```json
{
  "schema_version": "orca-checkpoint/0.2",
  "connector_id": "codex-local",
  "conversation_id": "conversation-123",
  "processed_through": {
    "turn_id": "turn-17",
    "redaction_policy": "orca-redaction/0.1",
    "turn_content_sha256": "<whole-redacted-turn-hash>",
    "segment_policy_version": "orca-segmentation/0.1",
    "segment_parameters_sha256": "<parameters-hash>",
    "segment_index": 1,
    "segment_count": 2,
    "segment_content_sha256": "<segment-hash>"
  },
  "manifest_path": "System/Orca Memory/manifests/2026/08/30/run_example.json"
}
```

The checkpoint advances after each successful segment run. A later run resumes
at the next unprocessed segment. Manifest scan remains the correctness source
when a checkpoint is missing or stale.

## Publication recovery

### Local publication intent

Before changing any final artifact, Storage would write a private local
`orca-publication-intent/0.1` record under:

```text
.runtime/publications/<run-id>/intent.json
```

The same directory holds staged post-image files. The intent contains:

- the fixed `run_id`;
- the exact source, operation, and output plan;
- target paths and before/after hashes;
- staged-file paths and hashes;
- the hash of the final Manifest payload; and
- the target checkpoint payload.

It contains no raw conversation text. Staged derived content is private and
must use restrictive local permissions. The intent is recovery material, not
memory authority or audit authority.

### Recovery rules

| State found under the processing lock | Required action |
|---|---|
| Intent exists, Manifest absent, target matches its before-image | Publish the staged after-image, then the fixed Manifest and checkpoint without another semantic call |
| Intent exists, Manifest absent, target already matches its after-image | Treat that output as already applied; finish the remaining outputs, Manifest, and checkpoint |
| Intent and Manifest both exist | Verify all after-images, repair the checkpoint if needed, then remove the intent and staged files |
| Target matches neither the recorded before-image nor after-image | Stop; do not overwrite; require human repair |
| Intent is missing or invalid but an unreceipted artifact is detected | Do not guess, delete, or overwrite; report an orphan for human repair |
| Manifest exists but an output does not match its receipt | Stop and report integrity failure |

Storage deletes the local intent only after the Manifest and checkpoint are
durable and verified. Cleanup failure does not repeat semantic work because the
Manifest remains authoritative.

## User-visible behavior

There is no new automatic recall or notification behavior in this RFC.

When automatic recovery is safe, Orca completes it without another model call.
When hashes or identities disagree, Orca stops and exposes a content-free repair
item containing the run ID, affected artifact ID, path, and failure class.

## Data changes

- New successful runs would use `orca-run-manifest/0.2`.
- New checkpoints would use `orca-checkpoint/0.2`.
- Interrupted publication would use local
  `orca-publication-intent/0.1` recovery data.
- Existing `0.1` Manifests remain immutable and valid historical receipts.

## Interface changes

- Processor must return exact source-segment bindings for every validated
  operation.
- Storage must assign run-local operation/output references and stable artifact
  identity where the owning specification gives it that responsibility.
- Storage must prepare the complete publication intent before mutating final
  artifacts.
- Manifest scanners must understand both `0.1` and `0.2` during Phase 1.
- Checkpoint repair must retain the available Manifest path and segment cursor.

## Security and privacy

- Manifests contain hashes, identities, paths, and references but no conversation
  text.
- Publication intents and staged content remain local, private, outside Git, and
  outside the configured vault.
- Recovery never bypasses output secret scanning or scope/path validation.
- A hash, path, identity, or schema mismatch fails closed.

## Failure behavior

- Invalid source, operation, artifact, or output references publish nothing.
- A failed provider or validation call creates no publication intent.
- A prepared intent prevents another semantic call while safe recovery is
  possible.
- A missing or corrupt intent cannot authorize automatic orphan cleanup.
- Checkpoint failure after Manifest publication remains repairable from the
  Manifest.

## Compatibility

Readers must accept both Manifest versions during Phase 1. New code must not add
segment or operation meaning to an old `0.1` receipt by inference.

A `0.1` Manifest continues to prove only the source and output facts its schema
actually contains. It cannot prove per-operation source support or segmented
processing.

## Migration

No existing Manifest is rewritten or backfilled. After accepted contract and
implementation changes land:

1. readers support `0.1` and `0.2`;
2. new writers switch to `0.2`;
3. new checkpoints switch to `0.2` after the first successful `0.2` run; and
4. `0.1` writer support is removed only after tests prove all active writers use
   `0.2`.

## Operational impact

The runtime gains one bounded private publication-intent directory. Recovery and
status inspection must distinguish pending, completed-but-not-cleaned, orphaned,
and integrity-failed publication states.

## Drawbacks

- The Manifest is larger and has more controlled fields.
- Storage publication becomes more complex.
- Readers must support two Manifest versions during migration.
- Safe recovery depends on retaining valid local publication intent; otherwise
  human repair is required.

## Alternatives

### Add only a segment number

Rejected as incomplete. It prevents one deduplication collision but does not
provide logical artifact provenance or interrupted-publication recovery.

### Keep only the current `outputs` array

Rejected because support, observation, stale-summary, and no-change outcomes may
have no physical file write.

### Use SQLite as the transaction authority

Rejected for Phase 1. The vault and immutable Manifests must remain sufficient
for durable audit; a database may be a disposable projection only.

### Rewrite old Manifests into the new schema

Rejected because old receipts are immutable and do not contain enough facts to
reconstruct the missing operation links honestly.

## Unresolved questions

- None.

## Promotion result

The accepted design was promoted into:

- [Provenance Ledger](../03-specifications/provenance-ledger.md);
- [Processing Pipeline](../03-specifications/processing-pipeline.md);
- [Memory Model](../03-specifications/memory-model.md);
- [Runtime Architecture](../02-architecture/runtime.md);
- [Data Architecture](../02-architecture/data-architecture.md);
- [Acceptance Plan](../07-quality/acceptance.md);
- [Test Strategy](../07-quality/test-strategy.md); and
- [Phase 1 Implementation Plan](../06-plans/completed/phase-1-implementation.md).

Required deterministic tests must cover:

- two or more segments of one turn without false source revision;
- exact replay of each segment;
- per-operation source and artifact joins;
- support and no-change outcomes with no file rewrite;
- interruption before each artifact, Manifest, checkpoint, and intent cleanup;
- before/after hash reconciliation;
- orphan and integrity mismatch fail-closed behavior;
- checkpoint repair with the correct Manifest locator and segment cursor; and
- mixed `0.1` and `0.2` Manifest scanning without rewriting old receipts.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Roadmap:** [Phase 1](../ROADMAP.md#phase-1)
- **Affected accepted owners:** [Provenance Ledger](../03-specifications/provenance-ledger.md), [Processing Pipeline](../03-specifications/processing-pipeline.md), and [Memory Model](../03-specifications/memory-model.md)
- **Quality:** [Acceptance Plan](../07-quality/acceptance.md) and [Test Strategy](../07-quality/test-strategy.md)
- **Implementation sequence:** [Phase 1 Implementation Plan](../06-plans/completed/phase-1-implementation.md)
