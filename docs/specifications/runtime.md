# Orca runtime coordination

This specification owns lifecycle coordination, worker scheduling, catch-up,
Attention Items, and reminder delivery for Phase 1. It consolidates the runtime
rules formerly embedded in Architecture. It does not change product behavior
or establish implementation readiness; see [Current](../project-record/current.md).

## Contract boundaries

| Subject | Owner |
|---|---|
| Source eligibility, scope resolution, source cursors, secure retry handoff | [Capture](capture.md) |
| Configuration fields, lifecycle setting, project discovery and mapping | [Configuration](configuration.md) |
| Semantic input, budgets, proposal validation | [Processing](processing.md) |
| Publication, replay, checkpoints, intent recovery | [Provenance](provenance.md) |
| Candidate and conflict disposition | [Knowledge Candidates](knowledge-candidates.md), [Memory](memory.md) |
| Startup presentation guidance | [Interaction Guidance](interaction-guidance.md) |
| Explicit memory retrieval | [Retrieval](retrieval.md) |
| Encrypted recovery copies and staging | [Backup](backup.md) |
| Commands and operator procedures | [Runbook](../operations/runbook.md) |

## Lifecycle coordination

Lifecycle hooks MUST load validated configuration before automatic work.
The Configuration and Capture specifications define the disabled boundary:
disabled hooks do not read transcripts, and automatic workers recheck before
each queued unit. Disabling cannot cancel a provider request in progress.

Enabled events MUST resolve their working directory and conversation scope
through the Capture and Configuration contracts before loading guidance or
queueing work. A model MUST NOT infer project identity or General scope.

Session start MUST:

1. Resolve the applicable scope from local governance evidence.
2. Select active interaction entries and compile bounded fixed-template guidance
   according to the Interaction specifications.
3. Deliver that noncanonical guidance, the attention reminder below, and a
   locally executable recall command bound to the resolved project or confirmed
   General scope. Unassigned startup MUST NOT advertise a guessed scope.
4. Read no conversation content and perform no memory search or semantic
   processing in the startup hook. Codex may later use the provided command for
   active or passive recall as defined by Retrieval. Agent-initiated use is
   instruction-guided, not a guarantee of a tool call on every relevant turn.

Recall instructions must tell Codex to use a continuation reference as the
entire query when requesting the full handoff. When continuing recalled work,
the final answer should retain the prior decision and reason, tentative ideas,
saved next step, and open question when available, before suggesting new work.
It should cite an exact returned source reference, including for passive recall.
These instructions require behavioral testing; their presence alone does not
prove that the agent followed them.

The SessionStart matcher MUST cover Codex `startup`, `resume`, `clear`, and
`compact` sources. The SessionEnd command MUST use a timeout no greater than
three seconds. SessionEnd performs the bounded local handoff synchronously and
starts the worker separately; the configured timeout is not evidence of an
observed wall-time result.

`PreCompact`, `SessionEnd`, explicit save, and catch-up use the same queue and
worker path. Capture owns whether the handoff carries a source pointer or a
permitted retry payload. The runtime MUST NOT introduce an alternate unredacted
handoff path.

## Worker and queue

Phase 1 uses one authorized local processor and a local OS lock. Lock contention
MUST leave the competing worker inactive while the current worker continues.
No permanent daemon is required.

A one-shot invocation drains at most 20 queued units by default. Before each
automatic unit it reloads the lifecycle setting; disabled work remains pending
without an attempt. Transient failures retry after one and two seconds, with
at most three attempts by default. Terminal failures are recorded while later
independent units continue. Work left by a drain limit or an exhausted current
retry cycle MUST report `pending`, never completion.

New terminal failure receipts include a content-free `failure_code`:
`output-budget`, `input-budget`, `validation`, `filesystem`, `processing`, or
`unobserved`. The last value means exhaustion was found without an observed
exception, including after an interrupted attempt; it must not be described as
a confirmed provider failure. Existing receipts without a code remain readable.
Never persist arbitrary exception messages, source text, or model output in
these receipts.

Each unit uses the owning pipeline contracts in this order:

1. Read permitted evidence after the durable handoff cursor and processing
   checkpoint, applying Capture identity and privacy rules.
2. Consult durable Run Manifests for replay or source-revision disposition.
3. Build bounded chronological input and invoke the replaceable provider.
4. Validate proposals before Storage prepares a fixed publication intent.
5. Publish artifacts and a Run Manifest, advance the checkpoint last, then
   remove successful spool and publication-intent material as their contracts
   require.
6. Reconcile disposable projections for later explicit Recall.

Invalid proposal output MUST NOT publish affected derived artifacts or advance
processing progress. Derived-view refresh failure MUST leave the valid source
record intact and exclude the stale view until rebuilt. Exact replay and
publication-recovery rules remain owned by Provenance.

## Catch-up

Automatic catch-up MUST check lifecycle enablement before rollout discovery.
It considers only mapped Project or explicitly confirmed General sources and
skips Unassigned history without provider access. It queues only source bytes
after the private handoff cursor.

Every discovered source MUST be resolved and contained inside the configured
rollout store before metadata is read. Invalid discovery produces only a
content-free Attention Item and MUST NOT prevent later valid sources from being
considered. No eligible new work means no model call. Catch-up reuses the worker
limits and privacy boundaries; external scheduling is an Operations concern.

## Human attention

Attention is a rebuildable projection, never an independent source of truth.
It MUST collect unresolved conditions deterministically from failed operations
and intents, configuration errors, stale blocking views, Unassigned records,
Memory Conflicts, and pending candidates.

Each item MUST have a stable ID, an owning-workflow route, and one severity:
`urgent`, `action-required`, or `review`. Duplicate observations of the same
source condition MUST NOT create independent issues. IDs and summaries MUST
remain content-free; status MUST NOT expose private memory or conversation
payloads.

Explicit Status MUST return counts by class and severity, safe IDs, and routes
without a model call or mutation of the underlying source state. Resolution
occurs only through the owning workflow. If resolution cannot be proved, the
item remains visible. Rebuilding a local projection cannot resolve an item.

After session start or resume, unresolved attention MUST produce at most one
counts-only reminder per session. The reminder cursor suppresses repeat
delivery; it cannot mark source conditions resolved. Reminder delivery makes no
model call or memory recall. There is no background notification or public
status endpoint in Phase 1.

## Recovery routing

Publication, project-mapping, and Owner-review operations have separate fixed
intents. Recovery MUST use the appropriate Provenance, Configuration, Memory,
or Candidate contract. A valid matching plan can complete without another
semantic call. Identity, path, or before/after hash mismatch MUST remain visible
for Owner repair. Missing or corrupt intents do not authorize orphan cleanup.

Interrupted conflict-candidate cleanup MUST respect committed resolution
lineage so stale leftovers cannot become current or reviewable again.

Commands for invoking these workflows belong to the
[Runbook](../operations/runbook.md#recovery).

## Verification routes

[Test Strategy](../quality/test-strategy.md) owns runtime, attention, hook,
configuration, and recovery verification. [Acceptance](../quality/acceptance.md)
owns the expected Phase 1 demonstrations. Recorded outcomes and known
implementation gaps belong to [Current](../project-record/current.md).
