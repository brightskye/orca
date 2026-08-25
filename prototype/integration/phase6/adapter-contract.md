# Phase 6 Cairn delta/checkpoint adapter contract v0.1.2

## Scope

This is deterministic transport and operational checkpoint state. It does not
perform semantic consolidation, Curator judgment, canonical writes, production
wiring, scheduling, migration, or transitional-pipeline retirement.

```text
Cairn Markdown
  -> complete scanner
  -> permalink/content snapshot
  -> checkpoint comparison
  -> added/changed/deleted result
  -> atomic observed-checkpoint advancement
```

## Identity and revision

- Logical identity: exact Cairn `permalink` frontmatter scalar.
- Revision: `(permalink, content_sha256)`.
- `content_sha256`: lowercase SHA-256 of the exact UTF-8 bytes of the candidate
  content returned by Cairn-style observation parsing. The parser mirrors
  AgentCairn 0.25.2 observation rules: for ordinary memories, exactly one
  `[context]` observation; for `kind: session-summary`, exactly one `[verbatim]`
  observation. An ordinary memory may also retain `[verbatim]` source evidence,
  but it is not candidate content. Cairn tags and trailing observation context
  are not content.
- No whitespace/newline/Unicode normalization is applied after Cairn parsing.
- Filename, relative path, frontmatter serialization, frontmatter metadata,
  mtime, DuckDB, and vector state are excluded from revision identity.

Explicit A5 decision: the frozen implementation contract defines the hash over
`content`; it defines no revision-bearing frontmatter metadata in v0.1. A
frontmatter-only edit is therefore not a changed candidate revision. The
checkpoint still refreshes the latest source reference and available provenance
for future deletion evidence. A future contract that makes metadata
revision-bearing would require a versioned identity change; Phase 6 does not
invent one. The A5 development/held-out case verifies this exclusion rather
than contradicting the current authority by emitting a same-hash revision.

## Complete-scan safety

Every `*.md` below the configured source root must be valid UTF-8 Cairn
Markdown with frontmatter, one non-empty permalink, and one unambiguous content
observation. Missing/duplicate permalinks, malformed frontmatter, unreadable
files, ambiguous content, or unterminated fences invalidate the whole scan.
An invalid scan produces no result replacement and no checkpoint advancement.

Duplicate permalinks are collisions even when their content matches. Filename
rename with stable permalink/content is not an addition or content revision.

## Configuration and source-store identity

The manual CLI requires explicit values:

```text
--source-root <Cairn Markdown directory>
--checkpoint <checkpoint.json>
--output <delta-result.json>
--store-id <stable deployment/configuration identity>
--harness <configured collection harness>
--default-intent <explicit|implicit>
```

No runtime path is hard-coded. `store-id` plus `harness`, not the absolute
filesystem path, is the checkpoint namespace. Configured default intent is
also bound to the checkpoint. It supplies the required explicit/implicit
candidate intent only when Markdown omits that field; any `entry_mode` such as
`source` or `reflection` is preserved separately. A mismatch fails closed
before scanning or writing.

## Checkpoint v1

The checkpoint records schema/adapter version, source-store identity, a
deterministic checkpoint ID, successful completion time, and sorted permalink
entries containing content hash, relative source reference, source session,
last-seen time, and bounded provenance. It stores no full candidate body and is
not canonical Orca knowledge.

Corrupt JSON, duplicate JSON keys, missing/extra schema fields, invalid hashes
or checkpoint IDs, malformed entry provenance, and schema/adapter version
mismatches fail closed. Recovery is manual: restore the valid checkpoint or
explicitly choose a separately reviewed checkpoint path. The adapter never
silently resets or deletes corrupt state.

## Result and advancement

First scan emits every valid memory as `added`. Later scans count unchanged
entries and emit only `added`, `changed`, and `deleted`, ordered by permalink.
A changed delta preserves previous and current hashes. A deleted tombstone
preserves the last hash, previous source reference, and prior provenance.

The sequence is:

```text
complete scan -> validate -> atomically replace result -> atomically replace checkpoint
```

Each replacement writes a temporary sibling, flushes and `fsync`s it, then
uses `os.replace`. Result files are immutable: a retry may reuse an existing
path only when its stable result identity is identical. Stable identity excludes
only the top-level generation timestamp and per-delta generation timestamps;
the first durable result remains authoritative and its original timestamps are
retained. A different result requires a new output path. This prevents a later
no-op scan from erasing an earlier unconsumed delta. If result materialization
fails, the checkpoint is not attempted. If checkpoint replacement fails, the
prior checkpoint remains and a retry reproduces the same change identities and
checkpoint ID even when its wall clock is later. Phase 6 treats the
durable immutable result file as the handoff acceptance boundary and implements
an observed checkpoint only; a future consumer-acknowledged checkpoint is not
invented.

## Deletion and Curator boundary

> Cairn deletion emits source-candidate removal evidence only and does not
> delete canonical Orca knowledge.

A deletion is not a truth judgment, correction, rejection, deprecation, or
supersession. Every event has `authority: candidate` and `orca_state: new`.
Added/changed events include current content and provenance; deleted events
include the prior revision evidence. Phase 4 Curator may inspect these fields
but Phase 6 never invokes Curator or applies a disposition.
