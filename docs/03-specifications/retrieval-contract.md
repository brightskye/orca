---
id: SPEC-RETRIEVAL-CONTRACT
title: Orca Retrieval Contract
document_type: specification
status: accepted
authority: normative
implementation_status: planned
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-29
last_verified_against_code: 2026-08-29
supersedes: []
projection-policy: orca-retrieval-projection/0.1
---

# Orca Retrieval Contract

## Purpose

Define the Recall module interface for explicit, bounded, authority-labelled
memory retrieval. The Module hides projection, eligibility, ranking-adapter
coordination, deduplication, and excerpt selection from requesting agents.

## Scope

This specification owns Recall Requests, Retrieval Projections, hard filters,
ranking order, result budgets, exact-conversation behavior, failures, and result
shape. It does not own source memory schemas, interaction-guidance loading, or
the retrieval Adapter's internal ranking implementation.

## Inputs

A Recall Request contains:

- an explicit memory question;
- optional project, memory-kind, topic, or time filters;
- requester identity and visibility context; and
- only the immediately relevant conversation context required to resolve a
  direct reference.

The request MUST NOT derive semantic intent from a guessed hidden motive or an
Adaptive Interaction Profile. A supplied Project Alias is convenience input;
Recall MUST resolve and enforce scope through the permanent `project_id`.

## Retrieval Projections

Recall MUST build a deterministic projection before any document reaches the
replaceable retrieval Adapter:

- a current record contributes only applicable current meaning;
- an unresolved Memory Conflict contributes clearly labelled active variants
  without a selected winner;
- resolved lineage is excluded from ordinary search and included only for an
  explicit historical request; and
- a structural summary marked stale contributes no projection.

Every projection MUST bind:

- source `memory_id` when the source owns one;
- authority;
- scope and permanent scope identity;
- lifecycle status;
- source-file content hash; and
- projection-policy version.

A projection with a mismatched source hash or stale marker MUST be excluded
until reconciliation replaces it. Reconciliation MUST replace the prior source
identity rather than add a duplicate projection.

## Required behavior

### Eligibility and ranking

1. Semantic memory recall MUST occur only after an explicit recall invocation.
2. Recall MUST apply authority, visibility, project, and status filters before
   ranking.
3. Ordinary Recall includes `current`, MAY include visibly labelled `conflict`,
   and MUST exclude `closed` unless the request explicitly asks for historical,
   completed, resolved, or closed memory.
4. Candidates, Run Manifests, `Raw/`, `Inbox/`, `Archive/`, and transient
   Conversation Evidence MUST remain outside ordinary Recall.
5. The Adapter ranks only permitted projections against the explicit requested
   meaning. It cannot broaden scope, change meaning, select a conflict winner,
   or grant authority.
6. Relevance determines eligibility and selection. Weakly relevant Canonical
   Memory MUST NOT displace strongly relevant Shallow Memory solely because it
   is canonical.
7. Among comparably relevant selected results, Canonical Memory MUST be
   presented before Shallow Memory. Every result remains authority-labelled.
8. Duplicate identities and strongly overlapping results MUST collapse before
   consuming result positions.
9. Recall returns at most six results. It MUST return fewer or request
   refinement rather than fill positions with weak or ambiguous matches.

### Result budget and excerpts

The complete Recall Result set, including labels and provenance, MUST fit within
4,000 tokens. No ordinary source document contributes more than 1,500 tokens.
Higher-ranked results receive space first.

An explicit exact-conversation request using stable
`conv:<purpose>--<short-id>` syntax is the sole exception. It MAY return:

- up to 2,000 tokens from the exact Conversation Continuation Summary;
- up to 1,000 tokens from its Project Summary when applicable; and
- relevant Typed Memory Record excerpts within the remaining 4,000-token total.

Recall MUST select directly responsive passages rather than blindly returning a
file prefix. It MUST visibly mark omitted content and MUST NOT make another LLM
call merely to summarize results.

## Outputs

Each Recall Result exposes:

| Field | Rule |
|---|---|
| `path` | Current source path in the configured vault |
| `memory_id` | Permanent identity when the source owns one; otherwise absent with the structural identity supplied |
| `authority` | Visible authority label |
| `scope` | Enforced scope and permanent identity |
| `status` | Current lifecycle status |
| `excerpt` | Directly responsive bounded source text with omissions marked |
| `source_sha256` | Hash used to verify projection freshness |
| `projection_policy` | Policy version used to build the projection |

The complete response also reports applied filters and whether results were
omitted because of relevance, ambiguity, or the token ceiling. It MUST NOT
expose filtered candidate paths or private content as omission details.

## Invariants

- Markdown artifacts remain authoritative; the retrieval index is local,
  derived, disposable, rebuildable, and non-authoritative.
- Every ranked item has already passed deterministic eligibility filters.
- A rendered link or similarity score never grants identity, scope, visibility,
  status, or authority.
- Interaction guidance uses a separate presentation-context interface and is
  never blended into semantic Recall Results.
- Ordinary Recall never selects a conflict winner or returns resolved lineage.

## Error behavior and idempotency

| Condition | Required result |
|---|---|
| Missing or corrupt index | Semantic recall unavailable until rebuild; do not silently scan the vault |
| Unknown or ambiguous Project Alias | Request clarification; do not guess scope |
| Stale hash or stale summary | Exclude until reconciliation |
| Missing or stale projection/index blocks safe Recall | Exclude it and expose a content-free action-required Attention Item until rebuild succeeds |
| No result passes relevance | Return an empty result or refinement request |
| Result set exceeds budget | Remove or shorten lower-ranked results while preserving whole labels and provenance |
| Adapter returns an ineligible or unknown projection | Reject it before presentation |

The same request against the same projection set, policy version, filters, and
Adapter version SHOULD produce the same eligibility and bounded result shape.
Index reconciliation MUST be safe to repeat and MUST NOT modify source Markdown.

## Security and privacy

Recall runs locally and exposes no public Phase 1 interface. Requester
visibility is a hard filter. Paths and snippets from excluded sources MUST NOT
be leaked in results or diagnostic text. The configured retrieval Adapter MUST
receive only permitted deterministic projections.

## Compatibility and current divergence

This interface preserves the current accepted Recall rules in the
[Memory System Contract](../governance/memory-system-contract.md),
[Architecture Overview](../02-architecture/overview.md), and
[Runtime Architecture](../02-architecture/runtime.md). The canonical-first rule applies only
among comparably relevant selected results; older unconditional canonical-first
material is not current behavior.

Recall, projection reconciliation, the explicit skill, and the MCP surface are
not implemented. See [Current Status](../STATUS.md).

## Acceptance criteria

- Filter tests prove that authority, visibility, project, and status are applied
  before Adapter ranking.
- Projection tests cover current meaning, unresolved variants, resolved-lineage
  exclusion, stale summaries, and hash mismatch.
- Relevance tests prevent weak canonical displacement, order comparable
  canonical results first, collapse duplicates, and abstain on ambiguity.
- Result tests enforce six results, 4,000 total tokens, 1,500 per ordinary
  document, and the exact-conversation exception.
- Failure tests prove that a missing index never triggers a broad vault scan.
- Every returned result exposes its authority, path, scope, status, and identity
  where available without an additional summarization call.

## Related documents

- **Requirements:** [Recall and retrieval](../01-foundation/requirements.md#recall-and-retrieval)
- **Memory semantics:** [Memory Model](memory-model.md)
- **Candidate exclusion:** [Knowledge Candidates](knowledge-candidates.md)
- **Integration Seam:** [Integration Architecture](../02-architecture/integration-architecture.md)
- **Historical budget rationale:** [Recall Context Budget](../_archive/research/recall-context-budget.md)
