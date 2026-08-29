---
id: ARCH-SECURITY
title: Orca Security and Trust Architecture
document_type: security
status: accepted
authority: normative
implementation_status: partial
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-30
last_verified_against_code: 2026-08-29
related:
  - ARCH-OVERVIEW
  - REQ-ORCA
---

# Orca security and trust architecture

## Purpose

This document defines the proposed security assets, actors, trust boundaries,
threats, invariants, mitigations, and residual risks for Phase 1.

## This document owns

- Security and trust boundaries for conversation, processing, storage, provider,
  retrieval, and deployment behavior.
- Security classification and architectural mitigation strategy.

## This document does not own

- Vulnerability-reporting procedure, exact privacy schemas, or operational tasks.

## Protected assets

- Canonical and noncanonical personal memory.
- Agent-owned conversation content and references to it.
- Credentials, tokens, private-session content, and host paths.
- Project and conversation identity mappings.
- Run Manifests, checkpoints, retry spools, and audit metadata.
- The integrity of authority, scope, provenance, lifecycle, and conflict state.

## Actors and trust

| Actor or component | Trust position |
|---|---|
| Owner | Final authority for memory, privacy, scope, and acceptance |
| Codex/agent | Supported source and consumer; not authority for durable memory |
| Connector | Deterministic boundary trusted only for positively identified and validated normalization |
| Semantic provider | Untrusted proposer of meaning; receives minimized redacted input |
| Governance and Storage | Deterministic enforcement boundary for permitted scope, identity, authority, and publication |
| Retrieval adapter/AgentCairn | Untrusted for authority; may rank only permitted projections |
| Local operator/host | Trusted to protect filesystem, credentials, configuration, and process boundary |
| Future synchronized host | Not trusted by Phase 1; requires separate accepted authorization and threat model |

## Trust boundaries

1. Agent-owned source → Connector: source format and event identity must be
   positively recognized; injected/system/tool/reasoning content is hostile or
   ineligible by default.
2. Connector → semantic provider: explicit privacy exclusion and credential
   redaction occur locally before data crosses the provider boundary.
3. Provider → Processor/Governance: all semantic output is untrusted structured
   proposal data.
4. Storage → vault: only complete validated artifacts may enter approved
   locations; no caller controls arbitrary paths or canonical authority.
5. Vault → retrieval adapter: only permitted deterministic projections are
   indexed; ranking cannot bypass hard filters.
6. Project checkout ↔ vault/runtime: public source, private memory, host state,
   and credentials remain in separate locations.

## Security invariants

- Explicitly private content publishes no memory content and reaches no semantic
  provider.
- Orca must not treat redaction as prevention of the original disclosure; it is
  containment against further propagation.
- Generated output containing credential-like material is rejected before
  storage, embedding, indexing, synchronization, recall, or agent exposure.
- Ambiguous event identity, scope, source revision, or cross-scope target fails
  closed.
- No public administration or canonical-apply interface exists in Phase 1.
- Canonical Memory changes require separate governed human acceptance.
- Machine-local configuration, mappings, recovery state, and credentials never
  enter Git or synchronization.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Prompt or envelope injection masquerades as Owner evidence | Positive event classification; exclude injected/system/tool/reasoning records |
| Private or secret content propagates to a provider or vault | Explicit privacy gate, local versioned redaction, secure retry boundary, generated-output scan |
| Model output grants itself authority or changes scope | Deterministic controlled schemas, Governance resolution, Storage-owned identity/path/authority |
| Cross-project memory leakage | Hard scope filters, host-local confirmed mappings, no semantic project guessing |
| Replay or source mutation creates duplicate/inconsistent memory | Stable source identity, policy-bound hashes, durable Manifest lookup, fail-closed revisions |
| Path traversal or writes outside approved stores | Storage maps logical artifacts to allowlisted locations; callers do not supply final paths |
| Retrieval exposes impermissible or stale content | Pre-ranking filters, source-hash-bound projections, stale exclusion, bounded labelled results |
| Runtime or cache publication leaks private state | Git ignores, local permissions, no public service, no synchronization of host-local state |
| Future replica grants authority by arrival order | Phase 3 remains candidate; synchronization is not authority or semantic merge |

## Authentication and authorization

Phase 1 relies on the local Owner/operator and host boundary. MCP uses local
stdio or another explicitly authenticated private transport. There is no public
user or service authentication surface. Future remote host authorization is not
defined by Phase 1 and must be accepted before Phase 3 commitment.

## Logging and audit

Run Manifests provide immutable processing receipts and reference-based
provenance without copying raw conversation text into each memory record.
Content-free receipts record privacy exclusions or terminal spool failure where
required. Logs and diagnostics must not emit credentials or private memory.

## Retention, backup, and incident handling

Retry-spool content is bounded and deleted after success or terminal expiry;
general memory retention remains an explicit gap rather than an inferred policy.
Ordinary Knowledge Candidates follow their accepted indefinite Phase 1
retention and expose no cleanup interface.
The Owner is responsible for private vault backup and host protection. Suspected
vulnerabilities follow the root [Security Policy](../../SECURITY.md); public
issues must not contain personal memory, secrets, host paths, or exploit detail.

## Implementation state and residual risk

Basic local redaction and Owner-turn filtering exist. Complete private-session
handling, assistant classification, secure spooling, hook wiring, output secret
scanning across every artifact, deployed permissions, and retrieval enforcement
remain partial or planned.

Residual risks include upstream source-format drift, incomplete credential
pattern coverage, original disclosures already present in agent history,
operator misconfiguration, filesystem/backup weaknesses, and probabilistic
semantic misinterpretation that deterministic validation cannot fully eliminate.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Architecture overview:** [Architecture Overview](overview.md)
- **Security reporting:** [Security Policy](../../SECURITY.md)
- **Required behavior:** [Requirements](../01-foundation/requirements.md)
- **Exact governance:** [Memory System Contract](../governance/memory-system-contract.md)
- **Knowledge Candidates:** [Knowledge Candidates](../03-specifications/knowledge-candidates.md)
- **Configuration:** [Configuration](../03-specifications/configuration.md)
- **Checkout/vault rationale:** [ADR-0004](../04-decisions/0004-separate-project-workspace-from-vault.md)
- **Current state:** [Current Status](../STATUS.md)
