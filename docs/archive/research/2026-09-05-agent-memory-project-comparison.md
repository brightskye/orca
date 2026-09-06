---
title: Four agent memory projects compared with Orca
document_type: research
status: completed
authority: informative
last_reviewed: 2026-09-05
---

# Four agent memory projects compared with Orca

This completed research snapshot is evidence only. It does not change Orca's
design or authorize an integration, migration, or new roadmap commitment.

## Recommendation

Keep Orca's trust rules and vault storage. Borrow selected ideas, especially
better search if real recall questions show a need. None of the four projects
is a direct replacement under Orca's current requirements.

| Project | Main purpose | Best fit for Orca |
|---|---|---|
| Atlas | Desktop workspace for coding agents and their history | Handoff experience, capture-health display, local search ideas |
| TencentDB Agent Memory | Memory and knowledge server for teams and agents | Shared-asset permissions, versioned procedures, generation logs |
| agentmemory | Persistent context for coding agents | Optional meaning-based search alongside keyword search |
| RAGFlow | Document processing, search, and agent workflows, including memory | Search diagnostics and later PDF/Office-document retrieval |

## Evidence and limits

Official documentation and selected source files were inspected. No external
software was installed, run, benchmarked, or security-tested. Integration and
replacement judgments are inferences from that inspection, not runtime results.

| Repository | Reviewed commit |
|---|---|
| [Atlas](https://github.com/pacifio/atlas) | `7abe155908f66efc05851f9f0fb9d30f91fcfe8a` |
| [TencentDB Agent Memory](https://github.com/TencentCloud/tencentdb-agent-memory) | `2ee22397f6091b8cd3ea847bc1edb04d3bec0c94` |
| [agentmemory](https://github.com/rohitg00/agentmemory) | `e04ba88819c365c9acf9d6661ea802143e728bd6` |
| [RAGFlow](https://github.com/infiniflow/ragflow) | `0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b` |

Orca was inspected in `/workspace/projects/orca`, on `main`, at HEAD
`497fc5f046d770e6350bfcba7967f2dde6143dea`, with existing uncommitted changes.
This comparison uses the current working-tree documents; it does not imply
that all those documents belong to that commit. Existing work was preserved.

## What a replacement must preserve

Orca separates agent-generated notes from knowledge the Owner has accepted.
It keeps durable memory in the configured Markdown vault. Search indexes can
be rebuilt and do not determine trust. Models suggest content; deterministic
code controls scope, validation, identity, placement, and publication. Normal
memory recall is explicit. Orca keeps no second raw transcript archive, and
Phase 1 cannot apply canonical changes automatically. See the
[architecture](../../architecture/README.md),
[memory system contract](../../specifications/memory-system-contract.md), and
[retrieval contract](../../specifications/retrieval.md).

Orca also creates provisional memory automatically. The replacement concern
is therefore not simply that another tool writes memory. It is whether it
preserves Orca's validation, review, source evidence, and accepted-knowledge
rules along the relevant paths.

Orca's [current record](../../project-record/current.md) says the Phase 1
baseline was accepted, but later privacy, scope, provenance, composition, and
deployment findings remain unresolved. Routine private capture is disabled.
This comparison does not clear those findings or prove Orca's runtime meets
every intended safeguard.

## Atlas

**What it offers — documented.** A desktop workspace for coding agents, notes,
session history, and code changes. Its supported platform is macOS; Windows and
Linux builds are described as untested. The repository is MIT licensed.
[README](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/README.md).

**Useful ideas — documented and source-inspected.** Compact session handoff,
visible capture-health states, content-hash indexing, and local retrieval
combining embedding and graph results. Orca could improve how it presents its
existing continuation summaries and Attention Items using these ideas.
[Memory implementation](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/crates/atlas-memory/README.md),
[retrieval](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/crates/atlas-memory/src/retrieve.rs).

**Replacement gaps — source-inspected.** Memory sharing defaults to enabled,
and the send path adds memory and handoff context before the agent receives
the message. An extraction path can automatically promote repeated,
high-confidence preferences and constraints across projects. Orca requires
stronger control over where inferred preferences apply and whether they have
been accepted. For example, a coding-project preference should not silently
become a general rule for unrelated work.
[Sharing defaults](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/src-tauri/src/commands/memory_sharing.rs),
[send path](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/src-tauri/src/commands/agents.rs),
[global promotion](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/crates/atlas-memory/src/global.rs).

These features have controls: capture is separately enabled, native extraction
is optional, and disabling memory sharing bypasses normal memory injection.
Atlas could be explored as an agent host with explicit Orca recall, but that
connection is untested. Disabling capture alone is not enough to disable its
other memory paths.
[Capture controls](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/src-tauri/src/commands/capture.rs),
[extraction gate](https://github.com/pacifio/atlas/blob/7abe155908f66efc05851f9f0fb9d30f91fcfe8a/crates/atlas-memory/src/extract.rs).

**Verdict:** borrow experience and search ideas. Replacing Orca with Atlas
would also mean adopting a different agent workspace and memory policy.

## TencentDB Agent Memory

**What it offers — documented and source-inspected.** This repository contains
server implementations, not just a client for a hosted database. It includes
memory, knowledge, proxy, and panel components. The Core supports Node.js,
SQLite, and local files with an LLM for extraction. Its layers cover raw
conversations, individual facts, scenario summaries, and core/profile context.
Documentation describes beta status; the Core documents MIT licensing.
[Core README](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/README.md),
[project status](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/README.md),
[knowledge server](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryKnowledge/src/server.ts).

**Useful ideas — source-inspected.** Assets have owners and permissions; calls
identify team, user, and agent. Skills have version checks. Generation logs
record model, input/output references, timing, and errors. A later shared Orca
vault could benefit from a clear view of which agents may use each asset and
a reviewable history of suggested procedures.
[Permissions API](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/v3-api-memorycore-doc.md),
[skill versions](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/src/core/skill/skill-core.ts),
[generation log](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/src/core/memory-generation-log/types.ts).

**Replacement gaps — source-inspected.** The Core records raw conversations
and lets extraction store, update, and merge memories. Skill “review” can be
an LLM workflow with write tools, which is different from human acceptance.
Some Core operations rely on the panel/metadata layer for user authorization.
Those paths do not provide Orca's full distinction between provisional memory
and Owner-accepted knowledge.
[Raw recorder](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/src/core/conversation/l0-recorder.ts),
[extractor](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/src/core/record/l1-extractor.ts),
[skill review prompt](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/src/core/skill/prompts/skill-review-prompt.ts),
[Core authorization boundary](https://github.com/TencentCloud/tencentdb-agent-memory/blob/2ee22397f6091b8cd3ea847bc1edb04d3bec0c94/MemoryCore/src/gateway/chat-memory-handlers.ts).

**Verdict:** revisit its permissions and versioned procedure ideas when
multi-agent sharing becomes an accepted need. Orca already separates summaries,
typed records, and profiles; copying another layered taxonomy would add little.
Its raw-conversation layer should not be imported into the current design.

## agentmemory

**What it offers — documented and source-inspected.** Coding-agent hooks, an
MCP interface, keyword search, optional embeddings, and context selection. Basic
search can work without an LLM. The inspected package declares version 0.9.29,
Node 20 or later, Apache-2.0 licensing, and an `iii-sdk` dependency.
[README](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/README.md),
[package](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/package.json),
[configuration](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/config.ts).

**Most useful idea: combine word matching with meaning matching.** Orca's
current default adapter uses AgentCairn BM25 keyword ranking. A question such
as “How did we limit spending?” might need a note saying “cap monthly API
costs.” Optional embedding search is worth comparing on real Orca questions;
this is an illustrative example, not a measured failure.
[agentmemory search](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/functions/search.ts),
[Orca adapter](../../../src/orca_memory/retrieval.py),
[default wiring](../../../src/orca_memory/application.py).

**Replacement gaps — source-inspected.** Saves and consolidation write to
its own key-value store. Automatic forgetting can mark older high-overlap
items as superseded and delete expired content. Selected search paths allow
records with missing project identity through as unscoped content. Those
behaviors differ from Orca's uncertain-scope, conflict, vault, and retention
rules.
[Remember](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/functions/remember.ts),
[forgetting](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/functions/auto-forget.ts),
[search filtering](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/functions/search.ts).

Compression and context injection are off by default in the inspected
configuration. Installing hooks still introduces observation capture. The
explicit save path also does not call the capture privacy filter. A retrieval
trial therefore needs a narrow Orca-controlled interface, not general access
to its save/delete tools. This is a source finding, not a full security audit.
[Hooks](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/plugin/hooks/hooks.codex.json),
[MCP server](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/mcp/server.ts),
[privacy filter](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/src/functions/privacy.ts).

Its benchmark documents describe retrieval-only testing and warn that the
comparison table mixes setups. Advertised scores do not establish better
answers on Orca's notes or preservation of Orca's safeguards.
[Benchmark method](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/benchmark/LONGMEMEVAL.md),
[comparison caveats](https://github.com/rohitg00/agentmemory/blob/e04ba88819c365c9acf9d6661ea802143e728bd6/benchmark/COMPARISON.md).

**Verdict:** the closest alternative for simpler coding-agent memory; the
best current idea to test is hybrid search behind Orca's existing adapter.
Budgeting and lineage are useful shared concepts that Orca already requires.
Provider fallback should not be copied without approving each data destination.

## RAGFlow

**What it offers — documented.** Document parsing, searchable chunks, source
citations, keyword/vector retrieval, and agent workflows. It also has agent
memory. Its self-hosting minimum is four CPU cores, 16 GB RAM, and 50 GB disk,
with several supporting services. The repository license is Apache-2.0.
[README](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/README.md),
[service stack](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/docker/docker-compose-base.yml),
[license](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/LICENSE).

**Useful idea — documented.** Its retrieval-test view checks whether the right
passage was found before judging the final answer. This separates missing
content, poor document splitting, incorrect filters, weak ranking, and poor
answer generation. Orca can borrow that diagnostic sequence without deploying
a service or building a dashboard.
[Retrieval testing](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/docs/guides/dataset/retrieval_testing.md).

**Replacement gaps — documented and source-inspected.** Memory types include
raw conversations, facts, events, and procedures. Raw storage is required by
the documented configuration, and capacity management can remove older content.
Inspected Python code stores user/agent exchanges, links extracted records
through source IDs, and performs FIFO deletion. Those source links do not
replace Orca's exact provenance and review rules.
[Memory configuration](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/docs/guides/memory/configure_memory.md),
[write and capacity handling](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/api/db/joint_services/memory_message_service.py).

The message UI can disable retrieval of a record while keeping it stored.
Owner/team access checks also exist. These are useful controls, but they do
not establish Orca's separate Owner-accepted knowledge classification.
[Message controls](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/docs/guides/memory/message_page.md),
[access checks](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/api/apps/services/memory_api_service.py).

**Verdict:** a possible later companion for large PDF, Office, and scanned
document collections. Its document retrieval API could return passages from
permitted copies without adopting its conversation-memory flow. General
document ingestion is deferred in Orca's [roadmap](../../project-record/roadmap.md).
[Chunk retrieval API](https://github.com/infiniflow/ragflow/blob/0c28d59ea1d362d9b6aa7481eed48c7fd9a95f0b/api/apps/restful_apis/chunk_api.py).

## Suggested next steps

1. Resolve Orca's current readiness findings before routine private capture.
2. If recall needs improvement, compare the existing keyword search with one
   hybrid approach using identical permitted notes and questions. Check correct
   results, project separation, conflicts, stale sources, response size, speed,
   and model cost. This review did not perform that experiment.
3. Preserve the boundary: Orca selects eligible content; the search component
   ranks only that content; Orca validates and labels the results. Filtering
   only after a broad search is insufficient for the current contract.
4. Revisit Tencent for accepted multi-agent needs, RAGFlow for accepted document
   ingestion needs, and Atlas's presentation ideas for handoff or health issues.

Several shared ideas already exist in Orca: typed records, summaries, bounded
recall, provenance, redaction, rebuildable indexes, and attention reporting.
The benefit must be a concrete improvement, not another taxonomy or service.

## When replacement could make sense

If the goal changes to “help my coding agent remember useful context
automatically,” agentmemory is the closest product to evaluate. If it becomes
“run agents and inspect their work in one desktop app,” Atlas is more relevant.
For a team memory service, evaluate Tencent; for document-heavy question
answering, evaluate RAGFlow.

Keeping Orca's current requirements while replacing its implementation would
still require privacy filtering, scope validation, source mapping, conflict
rules, review, authority-preserving storage, recovery, and migration work.
This review found no evidence that replacement would be less work than
improving Orca's existing replaceable components.
