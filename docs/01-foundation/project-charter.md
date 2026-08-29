---
id: CHARTER-ORCA
title: Orca Project Charter
document_type: project-charter
status: accepted
authority: normative
implementation_status: not-applicable
applies_to:
  - all-phases
owners:
  - project-owner
last_reviewed: 2026-08-29
---

# Orca project charter

## Purpose

This charter defines why Orca exists, who it serves, its stable boundaries, and
the conditions that constitute success.

## This document owns

- The project problem, purpose, stakeholders, scope, non-goals, and constraints.
- Stable phase boundaries and project-level success criteria.

## This document does not own

- Exact behavior, component design, implementation progress, or task sequence.

## Problem

AI-agent conversations contain useful decisions, knowledge, goals, lessons, and
interaction preferences, but raw conversation history is noisy, private, hard to
reuse, and not equivalent to accepted durable knowledge. Retrieval systems and
models can help derive context, but neither should become the authority for what
the Owner knows or accepts.

## Purpose

Orca is a governed, local-first memory system for AI agents. It preserves
durable knowledge in the Owner's configured vault, keeps provisional artifacts
separate from Canonical Memory, and gives authorized agents bounded recall
without making an agent, model, synchronization tool, or retrieval backend
authoritative.

## Stakeholders

- **Owner:** final authority for memory, privacy, automation scope, and durable
  acceptance.
- **Supported agents:** consumers and sources of bounded governed context; never
  memory authorities.
- **Maintainers/operators:** responsible for implementation, validation, local
  configuration, recovery, and safe deployment.

## Goals

- Preserve useful supported conversation context with exact provenance.
- Keep provisional memory visibly separate from accepted durable knowledge.
- Provide small, relevant, authority-labelled recall results.
- Improve presentation through inspectable scoped feedback without inferring
  personality, sensitive traits, or hidden motives.
- Keep private memory and machine-local runtime state in permitted locations.
- Make capture, processing, storage, and retrieval safe to retry and recover.
- Keep retrieval and synchronization implementations replaceable.

## Scope and phase boundaries

- **Phase 1:** one Codex Desktop agent, one WSL runtime, and one local vault.
- **Phase 2 candidate:** multiple local agents sharing the local vault.
- **Phase 3 candidate:** local and remote agents using synchronized vault
  replicas.

The phases vary participating agents and hosts. They do not defer the core
memory capabilities established for Phase 1. Phase commitment and exit criteria
belong to the [Roadmap](../ROADMAP.md).

## Non-goals

- Treating model output, Conversation Evidence, Shallow Memory, candidates,
  profiles, manifests, or retrieval results as accepted knowledge.
- Automatically modifying Canonical Memory.
- Providing a general document-ingestion system in the three delivery phases.
- Providing a public memory or administration interface.
- Inferring personality, emotion, motives, mental health, sensitive traits, or
  unsupported intent from interaction behavior.
- Requiring a particular retrieval backend or synchronization product as part of
  Orca's authority model.

## Constraints

- The Owner remains final authority.
- The project checkout and configured vault have different ownership,
  publication, and backup boundaries and remain separate.
- Personal vault paths, credentials, private memory, runtime state, and generated
  caches must remain outside tracked source.
- Canonical apply remains disabled and unexposed unless separately governed and
  accepted.
- Ambiguous authority, scope, provenance, privacy, or replacement intent fails
  closed or remains explicitly unresolved.

## Success criteria

- An Owner can use a complete local Codex memory loop without automatic
  canonical mutation or a public network service.
- Every derived artifact remains visibly classified and traceable through
  durable provenance.
- Exact replay produces no duplicate semantic result, and durable artifacts can
  rebuild disposable indexes and progress state.
- Recall returns bounded, relevant, authority-labelled context without guessing
  scope or intent.
- Project documentation clearly separates accepted design, implementation
  status, future direction, working evidence, and history.

## Assumptions requiring validation

- Codex's agent-owned rollout remains readable enough for a positively
  identified versioned Connector.
- A replaceable local retrieval backend can satisfy bounded recall without
  becoming authoritative.
- The configured local vault and host provide adequate privacy, backup, and
  filesystem semantics for the accepted Phase 1 contracts.

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Requirements:** [Requirements](requirements.md)
- **Roadmap:** [Roadmap](../ROADMAP.md)
- **Current implementation state:** [Current Status](../STATUS.md)
- **Current architecture:** [Architecture Overview](../02-architecture/overview.md)
