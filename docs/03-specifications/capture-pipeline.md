---
id: SPEC-CAPTURE-PIPELINE
title: Orca Capture Pipeline Specification
document_type: specification
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-29
last_verified_against_code: 2026-08-29
supersedes: []
redaction-policy: orca-secret-containment/0.1
---

# Orca Capture Pipeline Specification

## Purpose

Define the Conversation module interface that converts positively identified
agent-owned events into permitted, redacted, transient Conversation Evidence.
The Module hides connector-specific records and privacy mechanics from the
Processor without creating a second raw conversation archive.

## Scope

This specification owns event eligibility, exclusion, privacy filtering,
credential redaction, normalized source identity and ordering, source hashes,
partial-input behavior, and the secure retry handoff.

It does not own semantic interpretation, source deduplication disposition,
memory schemas, publication, or checkpoint fields. Those behaviors belong to
the [Processing Pipeline](processing-pipeline.md),
[Memory Model](memory-model.md), and
[Provenance Ledger](provenance-ledger.md).

## Definitions

- **Conversation module:** the deep Module that hides one connector's source
  format behind the Conversation Evidence interface.
- **Supported event:** a connector record whose envelope, role, event kind, and
  identity are positively recognized by a versioned adapter.
- **Permitted assistant context:** a visible final assistant response or an
  assistant passage directly referenced by a qualifying Owner turn.
- **Content-free receipt:** local evidence that a record was excluded or a
  retry ended, containing no source text or credential value.

The canonical definitions of Conversation Evidence and Secret Containment are
in the [Glossary](../01-foundation/glossary.md).

## Inputs

The interface accepts:

- an authorized connector identity;
- a pointer to an agent-owned source or a previously prepared secure retry
  spool;
- an optional processed-through source position; and
- the active privacy and redaction-policy versions.

The connector adapter MUST read only the bounded source range required for the
handoff. It MUST NOT copy the complete source into the project, vault, or retry
area.

## Outputs

One normalized batch contains one connector identity, one conversation identity,
and zero or more chronological turns. Each admitted turn exposes:

| Field | Required meaning |
|---|---|
| `connector_id` | Stable identifier for the authorized connector |
| `conversation_id` | Stable source conversation identity |
| `turn_id` | Stable source event identity within the conversation |
| `occurred_at` | Trusted source timestamp when present, otherwise unknown |
| `source_uri` | Stable locator back to the agent-owned source record |
| `text` | Permitted normalized text after local redaction |
| `content_sha256` | SHA-256 of the exact permitted redacted representation |
| `redaction_policy` | Policy version used to produce the representation |

The batch and turns are transient Processor inputs. They are not durable memory
records and grant no authority.

## Required behavior

### Event eligibility

1. The adapter MUST admit genuine Owner prompts and steering only after the
   connector positively identifies the supported event envelope and role.
2. Visible final assistant responses MAY be included as context. A non-final
   assistant passage MAY be included only when a qualifying Owner turn directly
   references it.
3. Injected envelopes, system instructions, hidden reasoning, tool protocol,
   raw tool output, subagent sessions, private-session content, unsupported
   record shapes, and ambiguous events MUST NOT enter Conversation Evidence.
4. The adapter MUST preserve source order. It MUST reject duplicate admitted
   `turn_id` values within one normalized batch.
5. A non-Owner source thread MUST yield an empty excluded batch rather than be
   reclassified as Owner evidence.

### Privacy and redaction

1. Explicit private-session or private-turn controls MUST be applied before
   content enters a retry spool or semantic-provider input.
2. Excluded content MAY create only a content-free local receipt.
3. Versioned credential patterns MUST replace obvious credential values locally
   while preserving permitted surrounding context.
4. The redacted representation and its policy version MUST bind the normalized
   content hash.
5. A later policy version producing a different hash is a policy revision. It
   MUST NOT be reported as source tampering under the old policy.
6. Secret Containment prevents further propagation; it does not claim to remove
   a secret already stored in the agent-owned source.

When automatic lifecycle handling is disabled, the hook MUST stop before
transcript access, capture, redaction, retry-spool creation, queueing, or
provider invocation. This does not create an unredacted path: enabling the
lifecycle retains every exclusion and redaction rule in this section, while a
redaction failure sends nothing.

### Source completion and handoff

1. A partial trailing JSONL record MUST remain unprocessed and wait for a later
   run. Complete preceding records MAY proceed.
2. `PreCompact` MAY hand the worker a pointer to the still-available agent-owned
   source.
3. Before a `SessionEnd` hook returns, only unprocessed permitted normalized
   evidence MAY be written to a private local retry spool when the original
   source may disappear.
4. A retry spool MUST be outside the vault and Git, use fixed secure permissions,
   and contain only the redacted representation.
5. The same Conversation interface and privacy policy MUST apply whether the
   worker reads the original source or a retry spool.
6. The retry spool MUST be deleted only after successful output publication,
   Run Manifest publication, and checkpoint advancement. It receives at most
   three automatic attempts. Its configurable retention defaults to 72 hours;
   terminal expiry deletes its content and retains only a content-free receipt.

## Invariants

- The connector adapter is an Adapter at the agent-format Seam. Replacing it
  MUST NOT change Conversation Evidence semantics.
- No admitted turn lacks a stable connector, conversation, and turn identity.
- No durable second raw or merged transcript is created.
- Excluded text and unredacted credential values never cross the Conversation
  interface.
- Source identity, source order, redacted content hash, and redaction policy
  remain available to the Provenance Ledger.

## Error behavior

| Condition | Required result |
|---|---|
| Missing or unsafe connector/conversation identity | Reject the batch; publish nothing |
| Duplicate admitted turn identity | Reject the batch; publish nothing |
| Unsupported or ambiguous event | Exclude it; do not guess |
| Partial trailing record | Defer only the incomplete record |
| Malformed complete record or schema drift | Fail closed with the checkpoint unchanged |
| Retry-spool creation failure at `SessionEnd` | Return a visible handoff failure; do not claim capture |
| Lock contention downstream | Leave source or eligible spool available for a later attempt |

## Idempotency

Normalization of the same complete source range under the same connector and
redaction-policy version MUST produce the same ordered identities, redacted
text, and hashes. Durable replay disposition belongs to the Provenance Ledger;
capture itself writes no memory artifact.

## Security and privacy

The Conversation module runs in the authorized local WSL runtime. It MUST NOT
send content to a semantic provider before exclusion and redaction complete.
Raw agent source, retry material, content-free receipts, credentials, and locks
MUST remain outside the vault and tracked source. No capture interface is
publicly network-accessible in Phase 1.

## Compatibility and current divergence

The interface preserves the accepted Phase 1 behavior migrated from the
[Memory System Contract](../governance/memory-system-contract.md),
[Architecture Overview](../02-architecture/overview.md), and
[Runtime Architecture](../02-architecture/runtime.md).

Current code positively normalizes Owner `UserMessage` completion events,
redacts credentials, preserves source identity, and creates no raw copy. It does
not yet admit permitted assistant context, defer partial trailing JSONL, apply
the full private-session policy, or implement the retry spool. The authoritative
implementation snapshot is [Current Status](../STATUS.md).

## Acceptance criteria

- Supported Owner, assistant-context, injected, tool, reasoning, private,
  subagent, ambiguous, schema-drift, and non-Owner fixtures produce the required
  inclusion or exclusion result.
- Repeated normalization is byte-stable for the same policy version.
- Redaction occurs before any spool or provider handoff.
- A partial trailing record does not prevent later completion and does not
  advance its checkpoint.
- No capture path creates a second raw transcript.
- Retry success, retry exhaustion, and retention expiry preserve the defined
  content and receipt boundaries.

## Related documents

- **Requirements:** [REQ-CAP-001 through REQ-CAP-003](../01-foundation/requirements.md#capture-and-privacy)
- **Runtime:** [Runtime Architecture](../02-architecture/runtime.md)
- **Security:** [Security and Trust](../02-architecture/security-and-trust.md)
- **Next interface:** [Processing Pipeline](processing-pipeline.md)
- **Receipts:** [Provenance Ledger](provenance-ledger.md)
