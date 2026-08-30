---
id: RFC-0003
title: Define human attention and common-use quality gate
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

# RFC-0003: Define human attention and common-use quality gate

## Summary

This draft proposes two small Phase 1 controls:

1. one content-free **Orca Status** view and one quiet session reminder when
   unresolved work needs a person; and
2. a frozen 100-case common-use evaluation that must pass at least 95 cases,
   without hiding a weak area or allowing any critical safety failure.

The status view does not become a new authority, dashboard, notification
service, or memory store. The quality score does not excuse unsafe edge cases.

The Owner accepted this RFC on 2026-08-30. Its conclusions are promoted into
the current requirements, architecture, specifications, quality, operations,
and implementation-plan documents. This file remains the informative review
record.

## Motivation

Orca already fails closed when identity, provenance, recovery, privacy, or
meaning is unsafe. It also creates normal review work such as pending Knowledge
Candidates, Unassigned records, and Memory Conflicts. The accepted design does
not yet give a person one simple place to see these items.

The Phase 1 gate also lists required tests, but it does not state the requested
goal that the system should work well for about 95% of normal use while making
unusual or unsafe cases visible to a person.

## Roadmap context

This change supports the Phase 1 quality, operations, and routine-use exit
criteria. It does not broaden Phase 1 scope or add a public service.

## Goals

- Make unresolved human work visible without exposing memory content.
- Keep reminders quiet, bounded, and deterministic.
- Route repair and review to the workflow that owns the state.
- Define a measurable common-use target before implementation is judged ready.
- Require safe refusal or visible human attention for unusual cases.

## Non-goals

- A dashboard, background notification service, email, or public endpoint.
- Automatic repair, candidate approval, conflict resolution, or canonical apply.
- Showing private memory at startup.
- Claiming that one score proves universal model quality.
- Exhaustively testing every possible edge case.

## Current behavior

The [Runtime Architecture](../02-architecture/runtime.md) already requires
content-free repair items for some failures. The [Acceptance Plan](../07-quality/acceptance.md)
defines direct Phase 1 evidence, and the [Runbook](../08-operations/runbook.md)
defines safe operator boundaries. No accepted document yet defines one complete
attention interface or the 95% common-use gate.

Current code implements neither control.

## Proposed design

### One attention interface

`Orca Status` is the single explicit view of unresolved human work. It is built
deterministically from accepted source states and makes no model call.

It includes these classes:

| Class | Examples |
|---|---|
| Failed operation | Terminal retry failure or blocked runtime operation |
| Integrity or recovery | Orphan output, hash mismatch, stuck Publication Intent, or stuck Project Mapping Intent |
| Configuration | Invalid configuration or runtime setup that blocks safe work |
| Stale derived state | A stale summary, projection, or index that blocks recall or processing |
| Unassigned | Records waiting for an Owner project decision |
| Memory review | Unresolved Memory Conflict or Conflict Overflow Candidate |
| Knowledge review | Pending Knowledge Candidate |

Each item has one severity:

- `urgent`: privacy, secret, cross-scope, identity, integrity, orphan, or blocked
  configuration state;
- `action-required`: recoverable state that cannot continue safely, including a
  stuck intent, blocking stale view, or overflow; or
- `review`: normal Unassigned, conflict, and Knowledge Candidate review work.

Each content-free item contains only:

- deterministic `attention_id`;
- class, severity, and unresolved/resolved state;
- `first_seen_at`, `last_seen_at`, and occurrence count;
- safe owning-workflow name; and
- safe identity or locator needed to open that workflow.

The default view reports counts by severity and class plus safe IDs. It shows no
memory text, source text, credentials, or synchronized host path. Explicitly
opening an item is a separate authority-aware action in its owning workflow.

### Quiet session reminder

At most once per session start or resume, Orca shows this kind of line when any
unresolved item exists:

```text
Orca needs attention: 1 urgent, 3 review items. Run Orca Status.
```

The reminder contains counts only. It makes no model call, performs no recall,
and does not repeat during the same session. A local rebuildable reminder cursor
suppresses duplicates. Changes become eligible for one reminder in the next
session. `Orca Status` remains available at any time.

### Authority and resolution

The status projection is local and rebuildable. Manifests, records, candidates,
configuration validation, and runtime intents remain the owning sources. Status
does not change their state.

Resolving an item uses the existing owning workflow: retry or repair,
configuration correction, project mapping, conflict resolution, candidate
review, or index rebuild. If Orca cannot prove the item is resolved, it remains
visible.

### Common-use evaluation

Before running the gate, the Owner approves a frozen representative corpus of
at least 100 cases and the expected result for each case. The minimum category
distribution is:

| Category | Minimum cases |
|---|---:|
| Capture and privacy | 15 |
| Processing and provenance | 20 |
| Project and memory behavior | 20 |
| Interaction behavior | 10 |
| Recall | 20 |
| Runtime and recovery | 15 |

Each case has a binary pass or fail under a fixed rubric. Invalid output,
unsupported claims, or missing required behavior fail; there is no partial
credit.

The common-use gate passes only when:

- at least 95 of 100 cases pass overall;
- every category passes at least 90% of its cases; and
- there are zero critical violations of authority, privacy, secret containment,
  project scope, canonical-write prohibition, identity integrity, or silent
  unrecoverable failure.

If the corpus contains more than 100 cases, the same 95% overall and 90%
per-category thresholds apply.

### Edge-case safety set

A separate frozen adversarial set covers unusual, ambiguous, malformed, and
unsupported inputs. It is not counted in the 95% score. Every case must either
succeed safely, abstain or reject clearly, or create a visible attention item.
Any unsafe output or silent unsafe failure fails the gate.

The model, provider, policy versions, repository revision, corpus version, and
rubric version are recorded. A material change reruns the gate. Human review is
required to approve the corpus, rubric, and final verdict, not each automated
run.

## User-visible behavior

Normal successful sessions stay quiet. A session with unresolved work shows at
most one short content-free reminder. The Owner can explicitly run `Orca Status`
to see grouped items and enter the correct repair or review workflow.

## Data changes

One local rebuildable attention projection and reminder cursor are added under
`.runtime/`. They contain safe metadata only and never become memory authority.
No new vault artifact is proposed.

Frozen quality fixtures and expected outcomes may be tracked only when they are
synthetic or explicitly permitted and contain no private conversation or vault
content.

## Interface changes

- Governance/runtime gains deterministic attention collection.
- The future local operator or skill surface gains explicit `Orca Status`.
- Session start/resume gains one bounded content-free reminder check.
- Quality gains one common-use evaluation and one separate edge-safety set.

## Security and privacy

- Startup and default status output contain no memory or source text.
- Credentials and secret-like values are never status fields.
- Host paths stay local and appear only in a later explicit repair workflow when
  necessary.
- Status cannot approve, repair, apply, recall, or change scope.
- Critical safety failures cannot be averaged into a passing percentage.

## Failure behavior

- Missing or stale attention projection triggers a deterministic rebuild; it
  does not clear source items.
- An unreadable source state produces an urgent content-free item when safe to
  do so, or fails the status operation explicitly.
- Reminder failure does not block safe Orca operation, but it is itself visible
  in explicit status or diagnostics.
- A quality case with missing evidence is a failure, not an assumed pass.

## Compatibility

Existing Manifests, records, candidates, intents, and indexes remain unchanged.
The proposal adds a derived view over their accepted states. Existing Phase 1
acceptance scenarios remain required; the common-use gate adds a higher-level
readiness measure and cannot replace them.

## Migration

After acceptance, implementation rebuilds attention state from current accepted
sources. It must not invent resolved history from filenames or timestamps.
Existing test fixtures may be reused only when their permission and expected
outcome are clear.

## Operational impact

Phase 1 gains one local read-only status command or skill and one bounded
session reminder. No daemon, public listener, external notification, or separate
administration application is required.

## Drawbacks

- One reminder may mention ordinary review work the Owner plans to defer.
- A representative 100-case corpus needs an initial Owner review.
- Binary scoring is simple and clear but loses some nuance.

## Alternatives

### Show reminders only for urgent failures

Not recommended because normal conflicts, candidates, and Unassigned records
could remain invisible indefinitely. Once-per-session counts keep the broader
reminder quiet.

### Add a dashboard or notification service

Rejected for Phase 1 because it adds operation, privacy, and maintenance cost
without being needed for one local Owner.

### Use only the overall 95% score

Rejected because a strong area could hide a weak but common subsystem.

### Count edge cases in the 95% score

Rejected because rare unsafe failures must not be averaged away. The separate
edge set requires safe handling in every case.

## Unresolved questions

None.

## Promotion result

The accepted design was promoted into:

- [Glossary](../01-foundation/glossary.md);
- [Requirements](../01-foundation/requirements.md);
- [Runtime Architecture](../02-architecture/runtime.md);
- [Data Architecture](../02-architecture/data-architecture.md);
- affected specifications for candidates, memory, provenance, retrieval, and
  configuration;
- [Acceptance Plan](../07-quality/acceptance.md);
- [Test Strategy](../07-quality/test-strategy.md);
- [Phase 1 Local Runbook](../08-operations/runbook.md); and
- [Phase 1 Implementation Plan](../06-plans/completed/phase-1-implementation.md).

Implementation verification must cover attention classification, severity,
deduplication, rebuild, privacy, once-per-session reminder behavior, resolution
visibility, and owning-workflow routing. Evaluation evidence must preserve the
frozen corpus, expected outcomes, rubric, versions, scores, critical-failure
count, and Owner verdict.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Roadmap:** [Phase 1](../ROADMAP.md#phase-1)
- **Affected accepted owners:** [Runtime Architecture](../02-architecture/runtime.md), [Acceptance Plan](../07-quality/acceptance.md), and [Test Strategy](../07-quality/test-strategy.md)
- **Operations:** [Phase 1 Local Runbook](../08-operations/runbook.md)
- **Implementation sequence:** [Phase 1 Implementation Plan](../06-plans/completed/phase-1-implementation.md)
