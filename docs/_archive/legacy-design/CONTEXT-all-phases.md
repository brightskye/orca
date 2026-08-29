# Orca Memory

> [!WARNING]
> Archived all-phase vocabulary snapshot. Current terminology is owned by the
> [Glossary](../../01-foundation/glossary.md).

Orca Memory is the domain that turns agent conversations and supplied sources into governed, shared context without confusing provisional evidence with accepted durable knowledge.

## Authority

**Owner**:
The human final authority for Orca memory, governance, and automation scope.
_Avoid_: administrator, named individual

**Orca**:
The Owner's complete governed memory system, including canonical notes, source evidence, synchronized memory-system data, governance, and the executable memory layer.
_Avoid_: memory gateway, retrieval backend

**Canonical Memory**:
Accepted durable knowledge in Orca's canonical folders. Owner remains its final authority.
_Avoid_: source of truth, live memory

**Source Evidence**:
An external artifact or preserved source record used to support later extraction and review. It is evidence, not accepted knowledge.
_Avoid_: canonical source, memory

**Conversation Evidence**:
A normalized, immutable record of an owner-agent interaction captured from an authorized connector. It is transient evidence, not shallow memory.
_Avoid_: transcript memory, raw memory

**Knowledge Candidate**:
An atomic proposed fact, decision, preference, lesson, or project state awaiting Curator disposition.
_Avoid_: knowledge, canonical candidate

**Curator**:
The agent-independent governed role that inspects evidence and candidates, prepares dispositions, and applies authorized canonical changes.
_Avoid_: Remote Agent, processor

**Curator Plan**:
A hash-bound proposal describing an exact canonical change and its preconditions. A plan grants no authority by itself.
_Avoid_: apply, approval

**Disposition**:
The durable outcome of Curator review, such as reject, promote, merge, correct, update, or supersede.
_Avoid_: decision result

## Working Memory

**Shallow Memory**:
Compact provisional context produced by distillation for bounded near-term recall. It is derived only after conversation processing.
_Avoid_: conversation evidence, canonical memory

**Agent Shallow Memory**:
Shallow memory routed to its originating logical agent and hidden from other agents by default.
_Avoid_: private canonical memory

**Shared Shallow Memory**:
Shallow memory explicitly scoped to a project, topic, or interaction pattern useful across agents.
_Avoid_: aggregated memory, global context

**Interaction Observation**:
Evidence about how the Owner responded to an agent interaction, constrained to presentation behavior and its observed scope.
_Avoid_: personality inference, preference

**Adaptive Interaction Profile**:
A rebuildable weighted view derived from interaction observations and used as a contextual presentation baseline.
_Avoid_: canonical preference, personality profile

**Confirmed Interaction Preference**:
An Owner-confirmed durable preference governed as canonical assistant operating context.
_Avoid_: inferred preference, adaptive profile

## Operation

**Remote Agent**:
A logical agent whose connector and runtime operate on a private remote host.
_Avoid_: named agent identity, processor

**Connector**:
A versioned adapter that positively identifies and normalizes conversation events from one configured agent surface.
_Avoid_: agent, processor

**Client Deployment**:
An Orca Memory Service installation that is not authorized to perform semantic processing. It captures and recalls but cannot derive or apply memory.
_Avoid_: local service

**Processor Deployment**:
The single Orca Memory Service installation authorized to perform semantic derivation. It is the local WSL runtime in Phases 1 and 2 and the governed processor host in Phase 3.
_Avoid_: server, VPS service

**Replica**:
One local filesystem copy of the Orca vault synchronized with another copy through Syncthing under eventual consistency.
_Avoid_: cache, deployment

**Run Manifest**:
An immutable operational record binding a processing run to its inputs, outputs, configuration, provider, status, and failures.
_Avoid_: summary, log
