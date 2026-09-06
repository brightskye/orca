# Orca integration architecture

This view owns responsibilities, dependencies, and trust assumptions at external
and replaceable component boundaries. Exact interfaces belong to the linked
specifications. [Current](../project-record/current.md) records which surfaces
are implemented and their limitations.

## Integration map

| Integration | Direction | Responsibility and boundary | Exact behavior |
|---|---|---|---|
| Codex rollout | Source → Connector | Supply agent-owned evidence; Connector controls eligibility and normalization | [Capture](../specifications/capture.md) |
| Codex hooks and local CLI | Codex/operator → runtime | Trigger bounded handoff or explicit workflows; worker owns semantic execution | [Runtime](../specifications/runtime.md) |
| Semantic provider | Processor ↔ provider | Propose meaning from permitted input; deterministic Orca validation owns admission | [Processing](../specifications/processing.md) |
| Configured vault | Storage ↔ filesystem | Store governed artifacts through recoverable publication | [Memory](../specifications/memory.md), [Provenance](../specifications/provenance.md) |
| AgentCairn | Orca ↔ replaceable adapter | Distil prevalidated input or retrieve permitted projections without gaining authority | [Processing](../specifications/processing.md), [Retrieval](../specifications/retrieval.md) |
| Host configuration | Operator → Governance | Supply machine-local configuration and confirmed mappings | [Configuration](../specifications/configuration.md) |
| Encrypted backup | Vault/runtime ↔ GPG | Produce a private recovery copy; verified staging remains separate from live storage | [Backup](../specifications/backup.md) |

## Replaceable components

Codex owns its source format. Connector changes must preserve the Orca evidence
interface as the upstream format evolves. Unsupported source cannot be treated
as valid simply because a new format resembles an old one.

Semantic providers supply proposals, while Orca owns identity, scope,
validation, publication, and provenance. Replacing a provider cannot expand its
authority or bypass the capture boundary.

AgentCairn remains behind Orca-owned interfaces. Its native capture or canonical
pipeline is outside the accepted integration. Retrieval ranking supplies
candidates to Orca's Recall filters; it cannot determine memory authority.
The [AgentCairn decision](../project-record/decisions/0012-use-agentcairn-behind-retrieval-interface.md)
owns the selection rationale.

Filesystem and optional cache backends provide persistence and acceleration.
Storage owns physical placement; disposable projections cannot become the
correctness baseline.

## Invocation and future integrations

Local CLI and lifecycle hooks are the Phase 1 integration shape. SessionStart
supplies a scoped executable recall command for Owner-requested or agent-initiated
continuity; it does not inject previously saved conversation content. Commands and
setup belong in [Setup](../operations/setup.md) and the
[Runbook](../operations/runbook.md). A skill or MCP adapter would be an additional
invocation adapter subject to the same governance boundary; its mention here
does not establish availability.

The [Roadmap](../project-record/roadmap.md) owns later connectors and hosts.
Synchronization, if accepted later, would transport eligible artifacts without
granting authority or resolving their meaning.

## Failure assumptions

Source formats can drift; providers can timeout or return unsafe proposals;
retrieval can return stale or cross-scope candidates; filesystem writes can stop
between steps. Each failure belongs to an Orca enforcement or recovery boundary.

See [Runtime Architecture](README.md#runtime) for component flow and
[Security Architecture](README.md#security-and-trust) for trust and threat assumptions.
