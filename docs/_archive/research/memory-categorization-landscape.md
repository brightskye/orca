---
type: research
status: informational
updated: 2026-08-27
---

# Memory categorization landscape

> [!WARNING]
> Archived research evidence. Current categorization and scope behavior is owned
> by the [Memory Model Specification](../../03-specifications/memory-model.md).

This note compares a small set of first-party agent-memory implementations to
answer two questions for Orca:

1. How do existing systems organize memories across conversations, users, and
   projects?
2. Does Orca need a knowledge graph to combine related conversations?

Sources were limited to the projects' own repositories and documentation. The
descriptions below state documented behavior unless marked **Inference**.

## Short answer

Existing systems usually separate four ideas that are easy to accidentally
blend together:

- **Memory kind:** what the item is, such as a handoff, fact, decision,
  preference, or procedure.
- **Scope:** where it may be used, such as one conversation, one project, one
  user, or general memory.
- **Lifecycle:** whether it is proposed, current, superseded, expired, or in
  conflict.
- **Relationships and provenance:** what source produced it and what other
  items it relates to.

This is the useful pattern for Orca. A category is not a scope, and a graph is
not an authority system.

A knowledge graph can help answer relationship-heavy questions (for example,
“which decisions about Project B depend on B1?”), but it is not required to
merge conversations that share a project root. A project namespace plus typed
Markdown records, source references, and bounded retrieval is sufficient for
Phase 1.

## Comparison

| Implementation | Memory units and categorization | Scope and update model | Provenance, conflicts, and retrieval | Graph and operating cost |
|---|---|---|---|---|
| [AgentCairn](https://github.com/ccf/agentcairn) | Inspectable Markdown memory notes with frontmatter such as `type`, tags, importance, validity, and source. Its Obsidian companion recognizes `type: memory` and exposes project, harness, session, and related-note metadata. | Recall is project-aware by default; cross-project recall is an explicit opt-in. The repository also documents import records that remain inspectable when a source is superseded or disappears. | Hybrid BM25 + vector retrieval, with recency/importance and project boosting. The Markdown vault is the source of truth; DuckDB is a rebuildable cache. | Uses deterministic `[[wikilinks]]` and optional neighbor links; it does not require an LLM to invent graph entities. Local embeddings are the default; cloud embedding/judge options add egress, latency, and provider cost. The project notes that graph boost is ineffective when the corpus has no native links. |
| [Mem0](https://github.com/mem0ai/mem0) ([memory types](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-types.mdx)) | Ordinary memories are extracted from messages. In the current OSS documentation, `procedural_memory` is implemented; semantic and episodic enum values are not wired into the OSS pipeline. Platform custom categories add classifier-selected labels, but labels are separate from scope. | `user_id`, `agent_id`, `run_id`, and Platform `app_id` scope writes and queries; multiple identifiers narrow the scope. `run_id` is suitable for a session/task, while `user_id` persists across sessions. | With inference enabled, Mem0 gathers context, retrieves same-scope candidates, and makes one LLM decision to add, update, delete, or leave facts. Categories are applied asynchronously at ingestion and changing the category catalog does not retag old memories. IDs and metadata provide scoping/audit context, but the cited docs do not define Orca-style content hashes or an authority model. | Platform Graph Memory extracts entities and connects memories that share them; current docs say this improves ranking and multi-hop recall, but does not create typed entity-to-entity relations. Extraction, embeddings, and hosted service operation add cost and dependency compared with local files. |
| [Letta / MemGPT](https://github.com/letta-ai/letta) ([MemFS docs](https://github.com/letta-ai/letta-docs-md/blob/main/concepts/memfs/index.md)) | Core memory is divided into labelled, editable blocks such as `persona` and `human`; archival memory is external and searched on demand; conversation recall is another external source. MemFS organizes durable memory as Markdown files with YAML frontmatter and paths. | Blocks attached to an agent are always in context. Files under `system/` are loaded every turn; other paths remain outside context until needed. The file tree and path act as the categorization/indexing surface. | Git-backed MemFS supplies version history and inspectable edits. The cited docs do not specify an automatic semantic conflict policy or source-hash manifest. On-demand file search keeps the active prompt smaller, while core blocks have character limits and therefore a continuing per-turn token cost. | No knowledge graph is central to the documented design, and semantic/vector search is not included by default. Optional search extensions add retrieval capability. This is a useful example of path-and-scope organization without a graph database. |
| [LangGraph](https://docs.langchain.com/oss/python/concepts/memory) + [LangMem](https://github.com/langchain-ai/langmem/blob/main/docs/docs/concepts/conceptual_guide.md) | LangGraph distinguishes short-term thread state from long-term memories. LangMem describes semantic facts/knowledge, episodic experiences or summaries, and procedural rules. Semantic memory can be a structured **profile** or an unbounded **collection** of records. | Short-term state is thread-scoped. Long-term records use custom namespaces and keys, which can represent user, organization, application, or project scopes. A profile is updated as current state; a collection accumulates searchable records. | LangMem's core operation accepts conversations plus current memory state, then asks an LLM to expand or consolidate it. Collection memory must reconcile new beliefs by updating, invalidating, deleting, or consolidating records. The docs explicitly warn that over-extraction hurts precision and under-extraction hurts recall. Background processing avoids user-path latency but is asynchronous work. | No graph database is part of the core memory contract. JSON documents, namespace filters, and optional embeddings are the basic organization/retrieval model. LLM extraction/consolidation and indexing consume compute; background scheduling trades freshness for lower interactive latency. |
| [Graphiti](https://github.com/getzep/graphiti) (the open-source engine behind Zep) | An **episode** is an ingestion event and provenance node. Extracted entities are nodes; facts/relationships are edges with validity windows. Custom entity and edge types provide a domain ontology. | `group_id` creates isolated graph namespaces; it can represent tenants, teams, or domains. Episodes can be added incrementally and queried by namespace. The docs caution that too many namespaces fragment data and too few reduce isolation. | Episodes retain source/time context; facts can be resolved and invalidated as new temporal information arrives. Hybrid semantic + BM25 search can be enhanced with node-distance and community retrieval. Bulk ingestion is faster but the documented bulk path does not perform edge invalidation. | A graph is the primary data model, useful for temporal and multi-hop questions. It requires a graph database around the open-source engine and LLM extraction of entities/edges, so it has materially higher Phase 1 operational and processing cost than Markdown plus a local index. |
| [Microsoft GraphRAG](https://microsoft.github.io/graphrag/index/overview/) | Its indexing pipeline extracts entities, relationships, claims, communities, embeddings, and multi-level community reports from unstructured text. This is a corpus-indexing/RAG pipeline rather than a conversation-memory lifecycle. | Its query engine operates over completed indexes; the cited docs do not define conversation/user/project memory namespaces or a durable memory authority model. | Local search combines graph-derived data with raw text chunks. Global search searches community reports with map-reduce; the docs call it resource-intensive. Index outputs are Parquet tables plus a configured vector store. | The graph and community hierarchy are valuable for corpus-wide themes and entity-centered retrieval, but indexing and global query require substantial LLM/compute work. This is a strong reference for later large-corpus retrieval, not a Phase 1 memory contract. |

## Patterns worth adopting in Orca

### 1. Use multiple views, not one giant “memory” category

The user's desired outputs map cleanly to patterns already used elsewhere:

| Orca output | Useful analogue | Phase 1 identity |
|---|---|---|
| Conversation Handoff | Episodic summary/experience | One evolving record per `conversation_id`; it can be revised as the conversation continues. |
| Project memory across B, B1, B2, B3 | Semantic collection | Multiple typed records sharing `project_id`; each record retains all contributing conversation/turn sources. |
| Topics, entities, knowledge, decisions, constraints, goals, open questions, lessons | Collection records with controlled labels | A record can have one primary `kind` and optional topic/entity tags. It is not a canonical fact merely because it was categorized. |
| Interaction observations and combined profile | Semantic profile | Keep separate from project facts and from ordinary semantic search; applicability and authority remain governed by Orca. |

This lets B1, B2, and B3 contribute to B without forcing every detail into one
summary. A new run can update a handoff, add or revise project records, and
retain a traceable source list.

### 2. Keep scope independent from category

Recommended Phase 1 fields for a Shallow Memory record are conceptually:

```yaml
memory_id: shallow-...
kind: decision              # handoff | knowledge | topic | entity | ...
scope: project              # conversation | project | general | unassigned
scope_id: project-orca
status: proposed            # proposed | current | superseded | conflict | expired
content: ...
sources:
  - conversation_id: ...
    turn_ids: [...]
    source_hash: ...
provenance:
  processor: ...
  redaction_policy: ...
```

The exact on-disk schema remains an Orca design decision. The important part is
the separation:

- `kind` says what the memory means.
- `scope` says where it belongs.
- `status` says how much trust or currentness it has.
- `sources` make merging and later correction possible.

For projectless conversations, use `general` only when ownership is known to
be general. Keep `unassigned` separate when Orca cannot determine ownership;
this avoids leaking project-specific material into global memory.

### 3. Merge by stable identity and evidence, not by category name alone

The strongest common pattern is “retrieve related existing records, then
update/consolidate.” Mem0 and LangMem document this explicitly; Graphiti does
it for entities and temporal edges. For Orca, the deterministic boundary should
remain local:

1. Deduplicate source turns using the existing source identity and hash.
2. Match a handoff by `conversation_id`.
3. Match project records using `scope_id`, `kind`, normalized subject/entity,
   and related source references.
4. Let the Processor propose add/update/supersede/conflict operations.
5. Validate, secret-scan, attach provenance, and publish noncanonical Shallow
   Memory.

**Inference:** A newer observation should not automatically erase an older
   project decision. Preserve both and mark a conflict unless the evidence
   clearly says the earlier decision was replaced, or the Owner explicitly
   corrects it. This is safer for Orca than relying on recency alone.

### 4. Treat links as a useful first graph

AgentCairn demonstrates a low-cost middle ground: ordinary Markdown records
can contain deterministic links and remain browsable in Obsidian, while the
retrieval index remains disposable. Orca can record relationships such as:

```text
Project B
  ├─ contains → B1
  ├─ contains → B2
  ├─ informed-by → conversation-123
  └─ superseded-by → decision-456
```

These links are useful for provenance and navigation without introducing a
graph database or model-generated ontology. They should not be treated as a
replacement for hard scope filters or source hashes.

## What a knowledge graph would add

A graph becomes worthwhile when Orca needs one or more of these capabilities:

- multi-hop retrieval across entities and decisions;
- temporal fact validity and explicit invalidation;
- browsing relationships among projects, conversations, entities, and memory
  records;
- community-level summaries over a large, interlinked corpus.

Graphiti is the clearest fit for temporal multi-hop memory; GraphRAG is the
clearest fit for corpus-wide community summaries. Mem0 shows a lighter graph
role where entities merely connect memories and boost ranking. AgentCairn
shows that deterministic Markdown links can provide a useful graph surface at
much lower complexity.

However, a graph does not solve these Orca requirements by itself:

- whether a conversation is in Project B or is unassigned;
- whether a source is private or secret-contaminated;
- whether a proposal is canonical or merely shallow;
- whether two similarly named entities are actually the same;
- which agent is authorized to write or recall a record.

Those remain scope, privacy, authority, and governance decisions. A graph can
also amplify a mistaken entity merge or cross-scope link, so graph retrieval
would need hard namespace and authority filters before it could be trusted.

## Recommendation for Orca

### Phase 1: implement a typed, scoped collection with handoff records

Use the existing local Markdown-vault model and rebuildable retrieval index.
Add the following conceptual structure to the Shallow Memory design:

- one evolving Conversation Handoff per conversation ID;
- project-scoped typed records shared by conversations with the same normalized
  project root;
- separate General and Unassigned scopes;
- controlled `kind` labels for handoff, topic, entity, knowledge, decision,
  constraint, goal, open question, lesson, and similar records;
- source conversation/turn identities, hashes, policy version, status, and
  supersession/conflict links on every derived record;
- bounded retrieval that searches the active project first and only includes
  relevant General records when explicitly permitted;
- deterministic Markdown links for obvious relationships, with no requirement
  for a graph database.

This directly supports the B/B1/B2/B3 use case and keeps conversation handoffs
separate from the merged project view.

### Defer

Defer full entity-resolution graphs, typed relationship extraction, temporal
edge invalidation, graph databases, and community detection until a measured
Phase 2/3 need exists. If later retrieval tests show that keyword/vector search
plus deterministic links cannot answer multi-hop questions, Graphiti is the
most relevant implementation to evaluate. If the vault becomes a large
corpus requiring whole-collection thematic search, GraphRAG's community-report
pattern is a possible later reference.

AgentCairn can remain the replaceable Phase 1 retrieval implementation because
its documented project-aware recall, provenance-bearing Markdown, disposable
index, and deterministic link graph align with this lower-complexity design.
Orca should continue to own the category vocabulary, scope routing, source
hashes, privacy gate, authority labels, and canonical boundary.

## Primary sources

- [AgentCairn repository](https://github.com/ccf/agentcairn) and [Obsidian
  companion frontmatter/graph contract](https://github.com/ccf/agentcairn-obsidian)
- [Mem0 memory types and update pipeline](https://github.com/mem0ai/mem0/blob/main/docs/core-concepts/memory-types.mdx), [entity-scoped memory](https://docs.mem0.ai/platform/features/entity-scoped-memory), [custom categories](https://docs.mem0.ai/platform/features/custom-categories), and [Graph Memory](https://docs.mem0.ai/platform/features/graph-memory)
- [Letta MemFS](https://github.com/letta-ai/letta-docs-md/blob/main/concepts/memfs/index.md) and [memory blocks API](https://docs.letta.com/api/typescript/resources/agents/subresources/blocks)
- [LangGraph memory concepts](https://docs.langchain.com/oss/python/concepts/memory) and [LangMem conceptual guide](https://github.com/langchain-ai/langmem/blob/main/docs/docs/concepts/conceptual_guide.md)
- [Graphiti repository](https://github.com/getzep/graphiti), [episodes](https://help.getzep.com/graphiti/core-concepts/adding-episodes), [namespacing](https://help.getzep.com/graphiti/core-concepts/graph-namespacing), and [search](https://help.getzep.com/graphiti/working-with-data/searching)
- [Microsoft GraphRAG indexing overview](https://microsoft.github.io/graphrag/index/overview/) and [query overview](https://microsoft.github.io/graphrag/query/overview/)
