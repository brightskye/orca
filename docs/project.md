---
id: CHARTER-ORCA
title: Orca Project Details
document_type: project-details
status: accepted
authority: normative
implementation_status: not-applicable
applies_to:
  - all-phases
owners:
  - project-owner
last_reviewed: 2026-08-29
---

# Orca project details

## Purpose

This document defines why Orca exists, who it serves, its stable boundaries, and
the conditions that constitute success.

## This document owns

- The project problem, purpose, stakeholders, scope, non-goals, and constraints.
- Stable phase boundaries and project-level success criteria.

## This document does not own

- Exact behavior, component design, implementation progress, or task sequence.

## Problem

The Owner discusses projects and subjects, explores ideas, builds systems, and
delegates chores to AI agents. Useful context is difficult to carry into a new
session or another agent. Re-explaining the discussion loses decisions, reasons,
unfinished questions, and progress. Orca should preserve enough distilled
history to continue that work when needed.

## Purpose

Orca has two connected functions:

- **Orca LLM Wiki:** the Owner's source of truth for durable knowledge and a
  second brain. It holds useful material distilled from conversations, websites,
  videos, images, screenshots, and other sources through its own workflows.
- **Orca Agent Memory:** conversation continuity, so a later session or agent
  can recover the relevant discussion, decisions, ideas, progress, and next steps.

This repository's three phases describe Orca Agent Memory. Distilled
conversation history is stored in its designated area of the Orca LLM wiki
vault; useful material can later become accepted wiki knowledge through the
wiki's workflow. The existing wiki rules and workflows need a separate later
review. Privacy, provenance, review, and recovery support these user outcomes.

## Stakeholders

- **Owner:** final authority for memory, privacy, automation scope, and durable
  acceptance.
- **Supported agents:** consumers and sources of bounded governed context; never
  memory authorities.
- **Maintainers/operators:** responsible for implementation, validation, local
  configuration, recovery, and safe deployment.

## Goals

- Preserve useful supported conversation context with exact provenance.
- Let the Owner resume a discussion or task without explaining its history again.
- Preserve tentative ideas as ideas for later discussion or development, without
  requiring them to become accepted facts or projects.
- Keep provisional memory visibly separate from accepted durable knowledge.
- Provide small, relevant, authority-labelled recall results.
- Improve presentation through inspectable scoped feedback without inferring
  personality, sensitive traits, or hidden motives.
- Keep private memory and machine-local runtime state in permitted locations.
- Make capture, processing, storage, and retrieval safe to retry and recover.
- Keep retrieval and synchronization implementations replaceable.

## Scope and phase boundaries

- **Phase 1:** continuity across sessions in one agent harness, Codex, using one
  WSL runtime and one local vault. It supports many Codex conversations.
- **Phase 2 candidate:** continuity across different agents sharing the local vault.
- **Phase 3 candidate:** continuity across devices using synchronized vault replicas.

The phases vary participating agents and hosts. They do not defer the core
memory capabilities established for Phase 1. Phase commitment and exit criteria
belong to the [Roadmap](project-record/roadmap.md).

## Non-goals

- Treating model output, Conversation Evidence, Shallow Memory, candidates,
  profiles, manifests, or retrieval results as accepted knowledge.
- Automatically modifying Canonical Memory.
- Redesigning the LLM wiki or implementing its general document-ingestion
  workflows as part of these agent-memory phases.
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

- After discussing a project, subject, idea, or chore in one Codex session, the
  Owner can use its saved distilled context in another Codex session and resume
  with the relevant outcomes, open questions, and next steps.
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

- **Project entry point:** [README](../README.md)
- **Documentation map:** [Orca documentation](README.md)
- **Requirements:** [Requirements](specifications/requirements.md)
- **Roadmap:** [Roadmap](project-record/roadmap.md)
- **Current implementation state:** [Current](project-record/current.md)
- **Current architecture:** [Architecture](architecture/README.md)
