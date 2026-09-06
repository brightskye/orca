---
id: SPEC-PROVENANCE-LEDGER
title: Orca Provenance Ledger Specification
document_type: specification
status: accepted
authority: normative
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-31
supersedes: []
manifest-schema: orca-run-manifest/0.2
checkpoint-schema: orca-checkpoint/0.2
publication-intent-schema: orca-publication-intent/0.1
owner-review-intent-schema: orca-owner-review-intent/0.1
candidate-disposition-schema: orca-knowledge-candidate-disposition/0.1
conflict-review-receipt-schema: orca-conflict-review-receipt/0.1
---

# Orca Provenance Ledger Specification

## Purpose

Define the accepted Run Manifest, checkpoint, deduplication, publication, and
recovery interface for Phase 1.

## This document owns

- Run Manifest, checkpoint, and local publication-intent schemas.
- The boundary between content-minimized Owner-review receipts and their local
  recoverable intents.
- Processed-source identity and deduplication meaning.
- Operation-to-source and operation-to-output audit joins.
- Artifact/Manifest/checkpoint publication order and progress repair.
- Compatibility with immutable `orca-run-manifest/0.1` receipts.

## This document does not own

- Memory meaning, semantic operation meaning, artifact schemas, identity
  assignment policy, operator procedures, or implementation progress.

## Boundary

Run Manifests are immutable, noncanonical operational receipts. They retain the
complete processed-source, logical-operation, and physical-output mapping needed
for deduplication, audit, and rebuilding disposable indexes. They contain no raw
conversation text.

Checkpoints are local disposable progress hints. Losing one may cause Orca to
scan Manifests again but must not cause repeated semantic work. A checkpoint is
never synchronized and carries no memory authority.

Publication intents are private local recovery records. They permit Storage to
finish or reconcile an interrupted publication without another semantic call.
They are neither memory authority nor durable audit authority.

Owner-review intents are a separate private local recovery mechanism for
explicit candidate and conflict decisions. They do not represent a semantic
processing run and therefore do not invent source references or a Run Manifest.
The corresponding content-minimized Owner-review receipt is durable vault
provenance for the explicit decision; it contains identities, the selected
outcome, timestamps, and before/after hashes, not proposal text or raw source.

## Run Manifest 0.2

One successful processing chunk creates one JSON Manifest under:

```text
System/Orca Memory/manifests/YYYY/MM/DD/<run-id>.json
```

`orca-run-manifest/0.2` requires:

- permanent unique `run_id`, controlled `status`, and UTC `processed_at`;
- connector and conversation identities;
- resolved scope type and scope identity;
- semantic provider and Processor policy version;
- a bounded `sources` array for the current processing chunk;
- a bounded `operations` array for accepted logical results; and
- a bounded `outputs` array for physical vault changes.

The arrays use run-local references:

```text
sources -> operations -> outputs
```

`source_ref`, `operation_id`, and `output_ref` are unique only inside one
Manifest. Storage assigns and validates them. A semantic provider cannot assign
them.

### Source segment receipts

Every selected turn uses one or more uniform segment receipts. An unsegmented
turn is one segment:

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

Rules:

- `source_ref` is assigned in chronological input order.
- `start_byte` is inclusive and `end_byte` is exclusive in the UTF-8 encoding
  of the normalized redacted turn.
- Segment boundaries must fall on valid UTF-8 boundaries.
- `index` starts at `1`; `count` is the total deterministic segment count.
- An unsegmented turn uses index `1`, count `1`, start byte `0`, and the full
  redacted byte length as `end_byte`.
- `parameters_sha256` hashes the canonical parameters that affect segmentation,
  including the applicable size limit and tokenizer/version where used.
- The segment hash covers exactly the bytes in the declared half-open range.
- The whole-turn hash and redaction policy remain identical across every segment
  of the same processed representation.

### Operation receipts

Each accepted logical operation produces one receipt:

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

`operation` is one of:

- `add`
- `support`
- `update`
- `supersede`
- `conflict`
- `candidate`
- `observation`
- `summary-refresh`
- `summary-stale`

`outcome` is one of:

- `created`
- `supported`
- `updated`
- `conflict-recorded`
- `observed`
- `stale`
- `no-change`

Allowed operation/outcome pairs are:

| `operation` | Allowed `outcome` |
|---|---|
| `add` | `created` |
| `support` | `supported` |
| `update` | `updated`, `no-change` |
| `supersede` | `updated` |
| `conflict` | `conflict-recorded` |
| `candidate` | `created`, `updated`, `no-change` |
| `observation` | `observed` |
| `summary-refresh` | `created`, `updated`, `no-change` |
| `summary-stale` | `stale` |

The [Processing Pipeline](processing.md) owns operation meaning. This
specification owns how the accepted result is recorded.

Every operation must:

- carry the stable logical artifact identity defined by its owning
  specification;
- cite at least one `source_ref` from the same Manifest; and
- cite only `output_ref` values for the same artifact identity.

`embedded_artifact` is normally null. It is required only when the owning
specification stores the complete artifact inside the Manifest. In Phase 1 this
applies to an Interaction Observation, whose embedded value must validate
against `orca-interaction-observation/1`. An embedded artifact cannot contain
raw conversation text or replace exact `source_refs`.

Known artifact identity mappings are:

| Artifact kind | Recorded `artifact_id` |
|---|---|
| Typed Memory Record | `memory_id` |
| Knowledge Candidate | `candidate_id` |
| Conflict Overflow Candidate | `<memory_id>:<variant_id>` |
| Interaction Observation | `observation_id` |
| Conversation Continuation Summary | Conversation Identity |
| Project Summary | `project_id` |

`support`, `observation`, `summary-stale`, and `no-change` may record no physical
output. An `observation` operation instead carries its validated
`embedded_artifact`. A valid full abstention is represented by run-level
`no_memory`, not by an operation receipt.

### Physical output receipts

Every changed vault artifact produces one output receipt:

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

`effect` is `created`, `replaced`, or `deleted`:

- `created` requires null `before_sha256` and present `after_sha256`;
- `replaced` requires both hashes; and
- `deleted` requires present `before_sha256` and null `after_sha256`.

The path is vault-relative and must pass the owning Storage path policy. The
Manifest does not list itself as an output. A support-only or no-change result
does not invent an output receipt.

### Run status

`status` is:

- `success` when at least one validated operation is recorded, including a
  support-only or no-change operation with no physical output; or
- `no_memory` when the complete valid run produces no accepted semantic
  operation, including a valid full abstention.

`no_memory` requires empty `operations` and `outputs`. Both statuses prove that
the listed source segments were processed. Failed provider, validation, or
unrecoverable publication attempts create no successful Manifest.

The date directories shard publication and inspection; conversation duration
does not select the shard. A conversation spanning months may appear in many
Manifest shards while retaining one Conversation Identity and one evolving
Continuation Summary.

## Deduplication

The `orca-run-manifest/0.2` processed-source key is:

```text
connector_id
+ conversation_id
+ turn_id
+ redaction_policy
+ segment.policy_version
+ segment.parameters_sha256
+ segment.index
```

The corresponding whole-turn hash, segment count, byte range, and segment hash
establish the processed representation.

- An identical key and representation is an exact replay and makes no semantic
  call.
- An identical key with different representation fields fails closed as a
  source or segmentation conflict.
- A changed redaction or segmentation policy requires explicitly governed
  reprocessing. It must not silently appear as a new segment.
- All segments for one turn representation must agree on the whole-turn hash,
  policy fields, parameters hash, and segment count.
- Missing, duplicated, overlapping, or out-of-order segment receipts fail
  closed during reconciliation.

Filesystem Manifest scan is the correctness baseline. An optional SQLite
projection may accelerate it but must rebuild to the same answer from
Manifests.

## Checkpoint 0.2

`orca-checkpoint/0.2` records the last successfully processed segment:

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

Storage writes or replaces it under local `.runtime/checkpoints/` after each
successful segment run. A later run resumes at the next unprocessed segment.
The checkpoint's `manifest_path` must name the Manifest that proves the cursor.

When a checkpoint is missing, stale, or lost, Manifest scan reconstructs the
last complete chronological segment and repairs the checkpoint without another
semantic call. An incomplete or conflicting segment sequence cannot advance the
checkpoint automatically.

## Publication intent 0.1

Before changing any final artifact or publishing a no-output Manifest, Storage
must atomically publish a complete private local
`orca-publication-intent/0.1` record under:

```text
.runtime/publications/<run-id>/intent.json
```

The run directory also holds staged post-image files. Directories use owner-only
permissions and files use owner read/write permissions.

The intent contains:

- the fixed `run_id` and final Manifest location;
- the exact source, operation, and output plan;
- target paths and before/after hashes;
- staged-file paths and hashes;
- the hash of the final Manifest payload; and
- the target checkpoint payload.

It contains no raw conversation text. Staged derived content remains private,
outside Git, and outside the configured vault until publication. The complete
intent must be durable before the first final target mutation.

## Publication and recovery

Publication order is:

1. validate all proposed operations, identities, paths, hashes, and secret
   exclusion;
2. prepare all post-images and the fixed Manifest/checkpoint payloads;
3. publish the complete local intent;
4. publish or delete final vault artifacts according to their output receipts;
5. publish the immutable Run Manifest;
6. advance the local checkpoint; and
7. verify success, then remove the intent and staged files.

Recovery runs under the same processing lock:

| State | Required action |
|---|---|
| Intent exists, Manifest absent, target matches its before-image | Publish the staged after-image, then the fixed Manifest and checkpoint without another semantic call |
| Intent exists, Manifest absent, target already matches its after-image | Treat that output as applied; finish the remaining outputs, Manifest, and checkpoint |
| Intent and Manifest both exist | Verify all after-images, repair the checkpoint if needed, then remove the intent and staged files |
| Target matches neither recorded before-image nor after-image | Stop; do not overwrite; require human repair |
| Intent is missing or invalid but an unreceipted artifact is detected | Do not guess, delete, or overwrite; expose an orphan repair item |
| Manifest exists but an output does not match its receipt | Stop and expose an integrity-failure repair item |

A repair item is content-free and contains only the failure class, run ID when
known, artifact identity, and a safe local locator. The accepted Orca Status
interface owns how it is grouped and displayed without changing this state.

Storage deletes the local intent only after the Manifest and checkpoint are
durable and verified. Cleanup failure cannot repeat semantic work because the
Manifest remains authoritative.

### Owner-review publication and recovery

The separate candidate and conflict review commands publish a fixed private
Owner-review intent before changing a candidate or Typed Memory Record. The
intent contains the receipt payload, target paths, and exact before/after
hashes. Publication order is:

1. validate the explicit Owner outcome and all target identities and paths;
2. write the private intent and staged post-images;
3. publish the immutable content-minimized Owner-review receipt;
4. publish or delete the fixed target artifacts; and
5. verify every post-image, then remove the intent and staged files.

The receipt is stored under:

```text
System/Orca Memory/provenance/owner-reviews/<operation-id>.json
```

The private intent is stored under:

```text
.runtime/owner-reviews/<operation-id>/intent.json
```

Recovery uses `orca recovery owner-review <operation-id>`. It never makes a
semantic call or chooses an outcome. A missing, malformed, or hash-mismatched
intent or target fails closed and remains a content-free attention item for
Owner repair. On conflict resolution, overflow-candidate deletion occurs only
after the resolved record and receipt are committed; a leftover is not
reviewable once the committed lineage proves the resolution.

## Compatibility and migration

Existing `orca-run-manifest/0.1` files remain immutable valid historical
receipts. They prove only the source and output facts their schema contains;
they do not prove segmented processing or per-operation source support.

The Phase 1 reader and writer contract is:

1. readers must support `0.1` and `0.2`;
2. new writers must use `0.2`;
3. new checkpoints switch to `0.2` after the first successful `0.2` run; and
4. active writers must not create new `0.1` receipts.

No old Manifest is rewritten, deleted, or backfilled. New code must not infer
missing segment or operation meaning from `0.1` receipts.

## Security and privacy

- Manifests contain hashes, identities, paths, and references but no
  conversation text.
- Publication intents and staged content remain private, local, and outside Git
  and the configured vault.
- Owner-review intents and staged review post-images remain private and local;
  Owner-review receipts contain no proposal or conversation text.
- Recovery never bypasses output secret scanning, scope validation, or path
  validation.
- A hash, path, identity, schema, or source-sequence mismatch fails closed.

## Acceptance criteria

- Two or more segments of one turn process without false source revision.
- Exact replay of each segment makes no semantic call.
- Every operation joins to exact current-run sources and the correct logical
  artifact identity.
- Every physical change joins to the operation and records before/after hashes.
- Support and no-change outcomes create a successful Manifest without rewriting
  an artifact.
- Fault injection before every artifact, Manifest, checkpoint, and intent
  cleanup step produces the specified recoverable or human-repair state.
- Checkpoint repair retains the correct Manifest locator and segment cursor.
- Mixed `0.1` and `0.2` scans preserve old receipts without inventing missing
  meaning.

## Related documents

- **Requirements:** [Processing and provenance](requirements.md#processing-and-provenance)
- **Processing:** [Processing Pipeline](processing.md)
- **Memory identities:** [Memory Model](memory.md)
- **Runtime coordination:** [Runtime](runtime.md)
- **Quality:** [Acceptance Plan](../quality/acceptance.md) and [Test Strategy](../quality/test-strategy.md)
- **Accepted proposal record:** [RFC-0001](../project-record/proposals/0001-strengthen-run-manifest-provenance.md)
- **Current state:** [Current Status](../project-record/current.md)
