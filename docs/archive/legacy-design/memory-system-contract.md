---
type: governance-contract
status: accepted-baseline
created: 2026-08-25
updated: 2026-08-25
tags:
  - orca
  - agent-memory
  - governance
---

# Orca Memory System Contract

> [!WARNING]
> Archived all-phase governance snapshot. Current authority and privacy behavior
> is owned by the [Memory System Contract](../../specifications/memory-system-contract.md).

## Status

This contract is the accepted target architecture baseline. It governs design and implementation of the replacement Orca Memory system. It does not declare the replacement deployed, disable the current transitional workflow, enable canonical apply, or authorize migration by itself.

Operational agents remain governed by `AGENTS.md` until Owner separately approves operating-rule and cutover changes.

## Delivery applicability

The [three-phase delivery plan](delivery-plan.md) introduces capabilities
progressively. Core authority, capture, derivation, recall, and privacy
invariants apply from Phase 1. Multi-agent visibility invariants become active
in Phase 2. Replica, synchronization, processor-transfer, and host-authority
invariants become active in Phase 3. Automated retention and
automatic canonical apply are separate follow-on capabilities and are not
enabled by completing any delivery phase.

## Authority invariants

- Owner is final authority.
- Canonical Orca is authoritative durable memory.
- Source evidence, conversation evidence, shallow memory, interaction observations, adaptive profiles, knowledge candidates, Curator plans, and run manifests are noncanonical.
- A semantic model proposes meaning; it does not assign canonical authority.
- Curator owns reject, promote, merge, correct, update, supersede, destination, and scope decisions.
- A Curator plan grants no apply authority by itself.
- The retrieval index is derived, local, rebuildable, and replaceable.
- Repetition and semantic similarity are discovery signals, not independent evidence.
- Historical evidence is immutable and retains its contemporaneous terminology.

## Replica and writer invariants

- Phases 1 and 2 have one local vault. Phase 3 has one local and one VPS replica
  synchronized through Syncthing under eventual consistency.
- Project-local `config/host.yaml`, `.runtime/`, credentials, caches, locks, and
  recovery material remain local-only and ignored by vault synchronization.
- `System/Orca Memory/` is local in Phases 1 and 2, synchronized in Phase 3,
  and explicitly noncanonical in every phase.
- Each connector writes immutable evidence only inside its configured namespace.
- Only the authorized processor writes derived shallow memory, observations, profiles, processing manifests, and retention dispositions.
- Mutable automated writes require the expected previous content hash.
- In Phase 3, a Syncthing conflict blocks the affected artifact and every
  dependent operation.
- No Phase 3 process treats Syncthing as a transaction manager or semantic merger.

## Processor invariants

- In Phases 1 and 2, the single WSL runtime is the only authorized processor.
- In Phase 3, synchronized configuration names exactly one authorized processor
  host and processor generation.
- In Phase 3, a host may process only when its local `host_id` matches
  synchronized processor authority; processor-only commands fail closed on all
  other hosts.
- One local OS lock protects each processor run; synchronized lock files are invalid.
- A deterministic window ID and durable checkpoint prevent duplicate semantic processing.
- Phase 3 processor reassignment increments processor generation.
- Missing, malformed, conflicted, or incompatible applicable governance blocks
  affected processing and apply operations.

## Capture invariants

- A connector positively identifies supported owner and user-visible agent events; ambiguous events fail closed.
- Connector identity and source namespace are configured, then verified against observed metadata.
- Conversation evidence is published as sealed immutable segments.
- Overlapping capture is deduplicated by immutable event identity and content hash.
- Hidden reasoning, system/developer envelopes, raw tool protocol, and unselected tool output are excluded.
- Subagent sessions are not independent owner-conversation evidence.
- Attachments are referenced by identity and hash; full content requires source ingestion.
- An explicit private-session instruction disables content capture and leaves only a non-content exclusion marker.
- Owner may force evidence deletion; forced deletion records the unresolved lineage rather than claiming successful processing.

## Derivation invariants

- Conversation evidence becomes shallow memory only after semantic processing.
- The processor reads evidence directly and creates no persistent merged transcript.
- One source revision receives at most one accepted semantic disposition per processing configuration.
- Provider input is minimized; deterministic code binds connector provenance and hashes after semantic output.
- Provider results are schema-validated proposals, never direct writes.
- A failed chunk commits none of its semantic outputs and retains its evidence.
- Derived artifacts reference source and run IDs instead of copying full provenance.
- Deleted conversation content leaves a compact source tombstone and archived evidence reference.

## Recall invariants

- Recall is canonical-first and authority-labelled.
- Default recall includes canonical, visible shared shallow, and the requesting agent's shallow memory.
- Cross-agent private shallow recall requires an explicit filter.
- Candidates and Curator plans are excluded from ordinary recall.
- Lower-authority context cannot silently override canonical memory.
- Automatic result injection has one total result/token budget.
- Cache freshness, replica, observation time, configuration hash, authority, and conflict status remain available as compact metadata.
- Missing or corrupt semantic cache makes semantic recall unavailable until deterministic rebuild; broad vault scanning is not a silent fallback.

## Interaction invariants

- Ordinary turn/session instructions do not become persistent evidence automatically.
- Persistent feedback requires explicit owner intent such as reinforce, confirm, correct, or an equivalent skill/tool call.
- Automatic adaptation is limited to presentation behavior.
- Silence contributes no evidence.
- Confirmed preferences require canonical governance.
- Adaptive profiles are deterministic, inspectable, scoped, weighted, decayed, contradiction-aware, and rebuildable.

## Curator and apply invariants

- Curator intake and planning may run periodically as processor stages.
- Canonical apply begins disabled and unexposed.
- Apply requires exact plan, source, policy, and destination preconditions plus atomic publication and durable disposition evidence.
- The VPS processor is the sole automated canonical writer initially.
- Automatic authority graduates per disposition category, never globally.
- Owner alone expands a category's automation level.
- Every new automatic category passes manual adjudication, shadow, and bounded canary evidence before activation.
- Safety or authority violations suspend the affected category; resumption requires Owner.
- Sensitive, contradictory, destructive, structural, governance-changing, or unconfirmed high-impact changes remain review-only or prohibited.
- Rollback is a new governed transaction; it never erases apply history or overwrites newer human edits.

## Retention invariants

These invariants apply only after automated retention receives separate scope
and approval.

- Processed conversation segments are deleted only after every eligible event has durable outputs, summary, manifests, checkpoints, and dispositions, unless Owner explicitly forces deletion.
- Agent-private shallow memory has a 14-day expiry policy.
- Shared shallow memory has a 30-day expiry policy beginning in Phase 2.
- Expired shallow memory leaves default recall before physical deletion.
- Shallow deletion waits for successful Curator inspection.
- Interaction observations retain 90 days.
- Knowledge candidates and Curator artifacts remain until disposition or governed archive.
- Apply before-images remain local to the processor for 14 days and longer while referenced by an unresolved failure, correction, or rollback.
- Compact apply manifests remain after before-images expire.
- The three delivery phases may mark expiry but do not delete content
  automatically.

## Privacy invariants

- Credentials, tokens, passwords, private keys, recovery codes, authentication cookies, and raw secrets never enter synchronized memory.
- Obvious secrets are rejected or minimally redacted only when useful non-sensitive meaning remains.
- Synchronized memory is private, not public, but VPS-synchronized content must be treated as potentially exposed if the VPS is compromised.
- Broader sensitivity classification and redaction are deferred; this deferral never weakens the hard secret prohibition.
