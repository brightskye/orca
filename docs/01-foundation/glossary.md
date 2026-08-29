---
id: GLOSSARY-ORCA
title: Orca Glossary
document_type: glossary
status: accepted
authority: normative
implementation_status: not-applicable
applies_to:
  - phase-1
owners:
  - project-owner
last_reviewed: 2026-08-29
---

# Orca glossary

## Purpose

This document defines Orca's canonical project-specific terminology and avoided
synonyms.

## This document owns

- Names and concise definitions for Orca domain concepts.

## This document does not own

- Exact behavior, schemas, lifecycle transitions, or implementation status.

# Orca Memory

Orca Memory turns supported Codex conversations into governed local context
without confusing provisional evidence with accepted durable knowledge.

## Authority

**Owner**:
The human final authority for Orca memory and automation scope.
_Avoid_: administrator, agent

**Orca**:
The Owner's governed memory system, including canonical notes, noncanonical
memory artifacts, governance, and the executable memory layer.
_Avoid_: retrieval backend, memory cache

**Canonical Memory**:
Owner-accepted durable knowledge in Orca's canonical vault folders.
_Avoid_: conversation evidence, shallow memory

**Conversation Evidence**:
A transient normalized selection of positively identified source conversation
records presented to the Processor. It is not a separate raw archive or
accepted knowledge.
_Avoid_: transcript memory, canonical record

**Secret Containment**:
The boundary that prevents credential values already present in an agent-owned
conversation from propagating into another provider, durable memory, retrieval
indexes, synchronized vaults, or other agents.
_Avoid_: secret prevention, undoing disclosure

**Knowledge Candidate**:
An atomic proposed fact, decision, preference, lesson, or project state awaiting
human or Curator disposition.
_Avoid_: knowledge, canonical candidate

## Working memory

**Shallow Memory**:
Compact provisional context derived from conversation evidence for bounded
near-term recall.
_Avoid_: canonical memory, conversation evidence

**Conversation Continuation Summary**:
An evolving structural Shallow Memory summary for continuing one source
conversation, identified by its Conversation Identity and retained separately
from project-wide memory.
_Avoid_: conversation handoff, project summary, transcript

**Typed Memory Record**:
A living atomic Shallow Memory document whose current state has one controlled
kind: workstream summary, decision, knowledge, entity, identity, goal,
constraint, open question, lesson, or topic. Conversation Continuation Summary
and Project Summary are separate structural derived views without their own
Memory Identities. A Typed Memory Record retains compact lineage but is not an
immutable history log.
_Avoid_: untyped memory, canonical fact

**Conversation Identity**:
The stable source-agent identifier for one conversation and its evolving
Continuation Summary, independent of summary content or filename.
_Avoid_: memory identity, project identity

**Memory Identity**:
The permanent opaque identifier of one logical Typed Memory Record, unchanged
when its content, provenance, status, or physical location changes.
_Avoid_: content hash, filename, subject

**Memory Subject**:
A stable, kind-appropriate identifying phrase for a Typed Memory Record: for
example a Goal's desired outcome or a Decision's issue. It supports matching and
human-readable naming without granting identity or authority.
_Avoid_: memory ID, topic tag

**Project Memory**:
The project-scoped collection of typed memory records supported by one or more
conversations; it is not one merged transcript or one monolithic summary.
_Avoid_: conversation memory, canonical project knowledge

**Project Summary**:
The single evolving, bounded, and rebuildable overview of a Project Memory,
supported by referenced current Typed Memory Records rather than raw transcripts.
_Avoid_: project memory, canonical project record

**Workstream Summary**:
An optional Typed Memory Record summarizing records that share one Workstream
Label while remaining inside the containing Project Memory scope.
_Avoid_: workstream scope, project summary

**Project Identity**:
The permanent opaque identifier of one Orca Project, independent of its folder
paths, Git remotes, display name, and Project Alias.
_Avoid_: project root, repository URL, project alias

**Project Alias**:
An Owner-selected, human-readable, unique name for a Project Identity used in
recall requests and displays; changing it does not change project membership.
_Avoid_: project ID, folder name

**Project Registry**:
The logical collection that relates each Project Identity to its current Project
Alias and identity metadata. It is durable and rebuildable without requiring one
central registry document.
_Avoid_: project root mapping, retrieval index

**Project Root Mapping**:
A host-local association between one normalized project root and a Project
Identity; several roots may map to the same project.
_Avoid_: project identity, synchronized path

**Workstream Label**:
A relationship label connecting related records within Project Memory, such as
B1, B2, or B3 under Project B; it is not a separate memory scope.
_Avoid_: workstream scope, subproject authority

**Memory Conflict**:
Two or more contradictory variants of the same Typed Memory Record for which no
later trusted Owner turn clearly establishes an applicable replacement; none is
current.
_Avoid_: source revision, duplicate

**Conflict Variant**:
One incompatible alternative within a Memory Conflict, identified permanently
within its containing Memory Identity but never treated as a separate memory.
_Avoid_: Typed Memory Record, source turn

**Conflict Overflow Candidate**:
A redacted noncanonical provisional artifact holding one fourth-or-later
Conflict Variant outside the three-variant living-record bound until explicit
Owner resolution.
_Avoid_: Knowledge Candidate, ordinary memory, raw conversation archive

**Variant Support Weight**:
The count of distinct qualifying Owner source turns that support one Conflict
Variant. It helps the Owner assess repeated support but does not grant authority
or override a newer trusted Owner position.
_Avoid_: confidence score, vote, truth

**Variant Position Timestamp**:
The actual source-turn time at which a Conflict Variant's distinct position was
introduced or materially changed. It helps the Owner order positions during
conflict review.
_Avoid_: processing time, file-write time, support count

**Conflict Review Threshold**:
The point at which a reviewable Memory Conflict becomes urgent: the appearance
of a third simultaneously unresolved Conflict Variant.
_Avoid_: variant storage limit, automatic resolution

**Conflict Review**:
An explicit Owner-invoked workflow for inspecting and resolving any Memory
Conflict, whether or not it crossed the Conflict Review Threshold.
_Avoid_: automatic recall, startup notification

**Review State**:
The urgency and acknowledgement state of Owner conflict review: none, required,
acknowledged, or overflow. It does not determine review eligibility and remains
independent of Memory Status.
_Avoid_: memory status, authority

**Conflict Resolution**:
An explicit Owner disposition that selects one Conflict Variant or supplies the
applicable current position. Choosing to keep a conflict unresolved is a review
outcome, not a resolution.
_Avoid_: automatic winner, support-weight vote

**Memory Status**:
The resolution state of a Typed Memory Record: current, conflict, or closed. It
does not express canonical authority or the domain-specific state inside the
memory.
_Avoid_: authority, approval

**Memory Relationship**:
A controlled association established by scope, exact provenance, Workstream
Label, summary support, or in-record lineage and represented by stable identity
or label. Similar subject matter alone does not establish one.
_Avoid_: related-to guess, file link

**Retrieval Index**:
A local rebuildable projection of configured canonical and shallow Markdown.
It carries no memory authority.
_Avoid_: memory store, source of truth

**Retrieval Projection**:
The deterministic, authority-labelled, indexable representation of one memory
document. It includes current meaning or labelled unresolved variants and omits
resolved lineage from ordinary recall.
_Avoid_: memory record, full-file embedding

**Recall Request**:
The asker's explicit memory question, optional scope or kind filters, and only
the immediately relevant conversation context needed to resolve a direct
reference. It does not include a guessed hidden motive or Interaction Profile.
_Avoid_: inferred intent, search keywords alone

**Recall Result**:
An authority-labelled memory document that passes hard visibility and scope
rules plus the relevance threshold for one Recall Request.
_Avoid_: retrieval candidate, automatic context

## Interaction

**Interaction Context**:
One controlled presentation situation used to keep feedback comparable: general,
status update, explanation, design discussion, implementation, or review.
_Avoid_: project topic, inferred hidden task type

**Interaction Observation Proposal**:
An untrusted controlled classification proposed from contextual conversation
evidence and requiring deterministic validation before it may become evidence.
_Avoid_: Interaction Observation, accepted preference

**Interaction Observation**:
Immutable contextual evidence inside a Run Manifest about how the Owner
responded to an agent's presentation, constrained to its observed scope and
carrying no durable preference authority.
_Avoid_: personality inference, confirmed preference

**Adaptive Interaction Profile**:
A living, rebuildable, scoped view containing only active or conflicting
presentation guidance derived from Interaction Observations.
_Avoid_: personality profile, canonical preference

**Interaction Guidance**:
The bounded noncanonical presentation instructions compiled exactly from active
Adaptive Interaction Profile entries through versioned fixed templates.
_Avoid_: semantic recall, free-form profile prompt

**Confirmed Interaction Preference**:
An Owner-confirmed durable presentation preference governed as Canonical
Memory.
_Avoid_: inferred preference, adaptive profile

## Operation

**Codex Connector**:
The Phase 1 adapter that positively identifies and normalizes supported Codex
events.
_Avoid_: processor, Codex agent

**Processor**:
The single local WSL runtime authorized to derive provisional memory from
conversation evidence.
_Avoid_: connector, retrieval backend

**Run Manifest**:
An immutable record binding one processing run to its inputs, outputs,
configuration, provider, status, and failures.
_Avoid_: summary, log

## Related documents

- **Documentation map:** [Documentation Index](../README.md)
- **Requirements:** [Requirements](requirements.md)
- **Exact behavior:** [Memory System Contract](../governance/memory-system-contract.md)
- **Current implementation state:** [Current Status](../STATUS.md)
