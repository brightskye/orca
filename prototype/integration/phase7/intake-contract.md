# Phase 7 Cairn delta to Orca Curator intake contract v0.1.4

## Scope and authority

Phase 7 is a manual/local bridge from immutable Phase 6 v0.1.2 delta results
to the agent-independent Orca Curator workflow. It is not a scheduler,
production consumer, semantic rules engine, or automatic promotion path.

```text
Phase 6 immutable delta batch
  -> structural and lineage validation
  -> deterministic event identity
  -> Phase 6 scanner freshness check
  -> persistent operational idempotency lookup
  -> Curator intake
  -> inspect -> plan -> explicit-authority apply
  -> Markdown disposition and optional canonical effect
```

The deterministic layer may validate, identify, check freshness, assemble
evidence, persist operational state, and apply an exact already-governed plan.
It does not decide semantic duplication, truth, correction, contradiction,
merge meaning, promotion, rejection, supersession, or canonical destination.

## Phase 6 reuse

Supported input is exactly:

- result schema `orca-cairn-delta-result`, schema version `1`;
- adapter `orca-cairn-delta/0.1.2`;
- top-level `source_store`, `checkpoint`, `summary`, and `deltas`;
- event `change`, `permalink`, `previous_sha256`, `current_sha256`,
  `content_sha256`, current/previous source references, `checkpoint_id`,
  `harness`, `intent`, `entry_mode`, candidate authority/state, generation,
  `sources`, and `provenance`.

Freshness imports and uses the Phase 6 `scan_store` and exact parsed-content
hash contract. Phase 6 code and schemas are not amended.

## Identity contracts

These identities are distinct:

```text
candidate identity: Cairn permalink
candidate revision: (permalink, content_sha256)
delta event: one observed add/change/delete transition in one checkpoint lineage
Curator disposition: governance result for one exact delta event and plan
```

Canonical JSON means UTF-8 JSON with sorted keys, no insignificant whitespace,
and preserved Unicode.

`phase7-batch:<sha256>` hashes the complete Phase 6 result after removing only
top-level `generated_at` and each delta's `generated.at`, matching the Phase 6
stable immutable-result identity treatment.

`phase7-event:<sha256>` hashes canonical JSON of:

```json
{
  "identity_contract": "phase7-delta-event-v1",
  "phase6_adapter": {"name": "orca-cairn-delta", "version": "0.1.2"},
  "phase6_delta_schema_version": 1,
  "source_store": {"id": "...", "harness": "...", "default_intent": "..."},
  "checkpoint_lineage": {"previous_id": "... or null", "current_id": "phase6:..."},
  "transition": {
    "change": "added|changed|deleted",
    "permalink": "...",
    "previous_sha256": "... or null",
    "current_sha256": "... or null"
  }
}
```

`phase7-plan:<sha256>` hashes the exact recorded plan excluding only
`generated_at`. `phase7-disposition:<sha256>` hashes the identity contract,
event ID, plan ID, and proposed terminal disposition. Filesystem mtimes,
temporary filenames, random values, and process counters are excluded.

## Batch validation

Before any intake or state write, Phase 7 validates:

- supported schema and adapter versions;
- exact configured source-store ID, harness, and default intent;
- checkpoint ID shapes, initial-discovery consistency, and the
  operator-supplied expected previous checkpoint ID;
- event checkpoint IDs equal the batch current checkpoint ID;
- summary counts equal actual actionable records;
- one event per permalink and unique derived event IDs;
- trimmed non-empty permalinks, hash shapes, source references, provenance,
  change kinds, intent, entry mode, and candidate authority/state;
- exact added/changed/deleted hash/content/source-reference semantics.

Any structural failure rejects the whole batch. It creates no intake and does
not create or advance processing state. An unchanged-only batch creates no
Curator work.

The Phase 6 result intentionally omits unchanged entry records, so Phase 7
cannot independently recompute `checkpoint.current_id` or reconstruct the
entire prior checkpoint. It validates the supplied lineage and per-event
transition exactly, relies on the unchanged Phase 6 adapter for checkpoint
construction, and then verifies current source state per event. Recomputing a
partial checkpoint in Phase 7 would be a competing and incorrect transport
contract; a complete prior-checkpoint audit remains a Phase 6 concern.

## Freshness and event handling

The configured source root must scan completely through Phase 6. A failed
complete scan stops the attempt because no event freshness can be established
safely.

- `added` or `changed` is fresh only when the permalink exists and its current
  Phase 6 revision equals the delta `current_sha256`.
- `deleted` is fresh only while the permalink remains absent.
- a moved file with the same permalink/revision stays unchanged under Phase 6
  and produces no Phase 7 event.

A stale event gets a deterministic freshness-attempt artifact containing its
event ID, expected state/revision, observed state/revision, reason, check time,
and integration/scanner version. It receives operational status `stale`, no
Curator-ready intake, no disposition, and no canonical effect. It is eligible
for a later manual retry but is not marked consumed or rejected.

Within a structurally valid batch, independent events are handled visibly per
event: fresh events receive intake, stale events are recorded stale, and
already handled events return `already_processed`. State is atomically written
after each event so partial progress is visible and replayable.

If a planned event became stale during apply and its original source
precondition later matches again, batch replay returns
`stale_plan_ready_for_replan`. It preserves the coherent `stale` record and
historical plan reference; it does not regress the record to `received` or
silently apply the old plan. The operator must re-run Curator planning, which
revalidates both source and current canonical preconditions.

## Change-kind intake semantics

Added intake preserves the new permalink/revision, current candidate content,
source/session/harness/project provenance when present, entry mode, batch, and
checkpoint lineage. It makes no distinct/duplicate/promotion judgment.

Changed intake preserves the same permalink, previous/current revisions,
current content, previous source reference, and any prior disposition links.
A changed revision is new review work and never overwrites the earlier
revision's disposition.

Deleted intake preserves the permalink, previous revision/reference,
provenance, explicit source-removal semantics, and prior dispositions. It has
no current content/revision. A deletion is not falsehood, rejection,
correction, deprecation, supersession, or canonical deletion.

> Cairn deletion does not delete canonical Orca knowledge.

The apply engine has no delete action. A Curator may explicitly author an
authorized `write_markdown` plan to update a provenance note after source
removal, but source removal itself never selects that action or target.

## Curator intake and planning

Fresh intake schema v1 includes event/batch identity, exact Phase 6 source
store and checkpoint evidence, candidate revisions/content/references,
provenance, entry mode, prior dispositions, current freshness, and the
`orca-curator/0.2` inspect-plan-apply contract.

Semantic planning remains external. The `plan` command accepts an explicit
Curator proposal containing comparison class, proposed lifecycle disposition,
Curator-selected canonical target, exact proposed action, evidence references,
rationale, and `curator` or `human` authority requirement. Phase 7 records:

- deterministic plan/disposition IDs;
- delta event and intake references;
- candidate identity and previous/current revision;
- semantic proposal unchanged;
- source precondition;
- current canonical SHA-256 or expected absence;
- exact planned canonical SHA-256;
- Curator skill/version.

Only `none` and atomic whole-file `write_markdown` are supported. This is an
optimistic local fixture/manual patch boundary, not a general transaction
engine. A different active plan for the same event fails closed and must be
handled by explicit re-inspection/replanning outside v0.1.

## Apply and retry safety

Apply requires a separate authorization JSON bound to the exact plan ID,
affirmative approval, actor, authority class, and local Phase 7 scope. A plan
marked `human` cannot be applied with Curator-only authority.

Immediately before mutation, apply rescans the source and verifies the exact
source precondition. It then verifies the canonical target still has the
planned prior hash (or remains absent). A changed source or canonical target
marks the operational record stale and aborts; the plan must be re-inspected
and replanned.

All intake, plan, and apply operations for one configured state path hold one
exclusive local single-writer lock across state loading, precondition checks,
artifact/canonical writes, and state persistence. A concurrent invocation or
crash-left lock fails closed and reports the exact lock path; the lock is never
automatically broken. The configured state path is therefore the local
coordination key and must not be forked for the same integration stream.

Canonical writes use a temporary sibling, flush, `fsync`, and `os.replace`.
After writing, the exact planned SHA-256 is verified. If a process fails after
the canonical replacement but before disposition/state persistence, a retry
detects the already-present planned hash, records one deterministic
disposition, and does not rewrite the target. Unexpected outcomes are exposed
as `indeterminate`; they are never hidden or treated as success.

Disposition Markdown is separate from the immutable Phase 6 batch, intake,
and plan. It records event, plan, candidate revision, governance lifecycle,
canonical target/effect hashes, actor/time, rationale, and Curator version.

## Processing state

Processing state is configurable with `--state`, uses
`orca-phase7-processing-state` schema version `2`, and is operational evidence,
not canonical knowledge or Orca lifecycle. It binds one source-store namespace
and stores event status plus artifact references. Writes are atomic temporary
sibling + flush + `fsync` + replace.

Each event record binds its event ID, batch ID, permalink, and change kind with
a deterministic `record_sha256`. Presented batch/intake/plan evidence must
match those bound fields before any idempotent short-circuit. `applied` records
remain applied on repeated planning, while `indeterminate` and `failed`
records remain visibly blocked for manual recovery rather than silently
regressing to `received`.

Malformed JSON, duplicate keys, unknown/incompatible version, invalid or
internally incoherent event shape, unsafe artifact reference, or source-store
mismatch fails closed. Before plan/apply, the helper fully revalidates the
intake's Phase 6/event identity and binds intake/plan paths and event metadata
back to the state record. It is never treated as empty or automatically
reset/deleted. Recovery is manual: restore the last valid state, or reconstruct
a separately reviewed state path from preserved freshness, intake, plan,
disposition, and canonical-effect evidence.

Artifact references are normalized POSIX-relative paths only: leading slash,
backslash, drive-prefixed, empty/dot, parent-traversal, and backslash-containing
forms fail closed on every host.

Applied retries revalidate authorization and the preserved plan/disposition
evidence before returning `already_applied`. They report whether the recorded
canonical effect is still current but never replay an old patch over a later
human edit. An applied event remains applied even when Cairn later changes;
that later source revision belongs to a new Phase 6 event. `failed` and
`indeterminate` records cannot be replanned or applied until explicit manual
recovery.

Operational statuses are `received`, `stale`, `planned`, `applied`, `failed`,
and `indeterminate`. Governance lifecycle remains `new`, `consumed`,
`rejected`, `merged`, `promoted`, and `superseded`; Phase 7 does not merge the
two state systems.

## Manual invocation

Use explicit local paths. For initial discovery, pass literal `null`; otherwise
pass the exact Phase 6 `checkpoint.previous_id` expected by the operator.

```powershell
python -B curator_delta_intake.py intake `
  --batch <phase6-delta.json> --source-root <cairn-markdown> `
  --state <processing-state.json> --artifact-root <curator-artifacts> `
  --store-id <stable-id> --harness <harness> --default-intent implicit `
  --expected-previous-checkpoint-id <phase6:id|null>

python -B curator_delta_intake.py plan `
  --intake <intake.json> --proposal <curator-proposal.json> `
  --source-root <cairn-markdown> --canonical-root <fixture-or-authorized-vault> `
  --state <processing-state.json> --artifact-root <curator-artifacts>

python -B curator_delta_intake.py apply `
  --plan <plan.json> --authorization <authorization.json> `
  --source-root <cairn-markdown> --canonical-root <fixture-or-authorized-vault> `
  --state <processing-state.json> --artifact-root <curator-artifacts>
```

No path is hard-coded. Test apply is isolated under `tests/fixtures/` and
disposable test roots; production canonical knowledge is not a test target.

## Phase boundaries

```text
production Curator automation: NOT IMPLEMENTED
production Cairn synchronization: NOT IMPLEMENTED
production hooks: UNCHANGED
production schedulers: UNCHANGED
transitional nightly distillation/review pipeline: UNCHANGED
Phase 8 shadow validation: NOT IMPLEMENTED
automatic self-improvement/fine-tuning: NOT IMPLEMENTED
```
