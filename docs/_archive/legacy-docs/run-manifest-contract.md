---
type: contract
status: phase-1-current
updated: 2026-08-29
manifest-schema: orca-run-manifest/0.1
checkpoint-schema: orca-checkpoint/0.1
---

# Run Manifest and Checkpoint Contract

> [!WARNING]
> Archived compatibility source. Current behavior is owned by the
> [Provenance Ledger Specification](../../03-specifications/provenance-ledger.md).

> [!NOTE]
> This document is a compatibility mirror. The normative owner is the
> [Provenance Ledger Specification](../../03-specifications/provenance-ledger.md). Do
> not edit this mirror independently.

## Boundary

Run Manifests are immutable, noncanonical operational receipts. They retain the
complete processed-source and output mapping needed for deduplication, audit,
and rebuilding disposable indexes. They contain no raw conversation text.

Checkpoints are local disposable progress hints. Losing one may cause Orca to
scan Manifests again but must not cause repeated semantic work. A checkpoint is
never synchronized and carries no memory authority.

## Run Manifest

One successful processing chunk creates one JSON Manifest under:

```text
System/Orca Memory/manifests/YYYY/MM/DD/<run-id>.json
```

`orca-run-manifest/0.1` requires:

- permanent unique `run_id`, `status`, and UTC `processed_at`;
- connector and conversation identities;
- resolved scope type and scope identity;
- semantic provider and Processor policy version;
- a bounded `sources` array containing turn ID, source URI, source-turn time,
  redacted-content hash, and redaction-policy version;
- a bounded `outputs` array containing artifact kind, vault-relative path, and
  published-content hash.

`status` is `success` when at least one derived artifact was published and
`no_memory` when processing validly produced none. Both statuses prove that the
listed source turns were processed and therefore prevent replay. Failed runs do
not create a successful Manifest.

The date directories shard publication and inspection; conversation duration
does not select the shard. A conversation spanning months may therefore appear
in many Manifest shards while retaining one Conversation Identity and one
evolving Continuation Summary.

## Deduplication

The baseline processed-source key is connector ID, conversation ID, and turn ID.
The corresponding redacted-content hash and redaction-policy version establish
the processed representation.

- An identical key, hash, and policy is an exact replay and makes no semantic
  call.
- An identical key and policy with a different hash fails closed as a source
  revision.
- A changed redaction policy is a policy revision and requires explicitly
  governed reprocessing rather than being treated as a hash-integrity failure.

Filesystem Manifest scan is the correctness baseline. A future optional SQLite
projection may accelerate it but must rebuild to the same answer from Manifests.

## Checkpoint

`orca-checkpoint/0.1` records connector ID, conversation ID, processed-through
turn ID, its hash and redaction policy, and the latest Manifest locator when
available. Storage writes or replaces it under local `.runtime/checkpoints/`.

Publication order is recoverable rather than transactionally atomic:

1. validate and publish derived artifacts;
2. publish the immutable Run Manifest;
3. advance the local checkpoint last.

If step 3 fails, a later Manifest scan recognizes the replay and repairs the
checkpoint without repeating semantic work. If publication fails before the
Manifest, the checkpoint remains unchanged and the run may retry.
