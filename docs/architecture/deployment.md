# Orca deployment architecture

This view describes the intended Phase 1 host, process, storage, and network
boundaries. [Current](../project-record/current.md) owns deployment status;
[Setup](../operations/setup.md) owns installation and activation.

## Topology

```text
Windows host
  Codex Desktop
      |
      | local invocation
      v
  WSL runtime
      |-- Orca project checkout
      |-- private host configuration and runtime state
      `-- configured Orca vault, separate from the checkout
```

Phase 1 connects one Codex agent, one authorized local processor, and one vault.
Hooks hand work to a one-shot worker; no permanent daemon or public service is
part of this topology.

## Location boundaries

| Location | Responsibility |
|---|---|
| Project checkout | Public source, tests, documentation, and safe configuration examples |
| Configured vault | Owner-governed canonical knowledge and permitted noncanonical artifacts |
| Host configuration | Machine-specific paths and identity mappings, outside Git and synchronization |
| Local runtime | Private queues, locks, cursors, recovery intents, and disposable indexes |
| Agent-owned rollout store | Original conversation history, read through the Connector |

The checkout and vault have separate ownership and publication boundaries.
Runtime recovery material stays local even when it supports a vault artifact.
The [Configuration specification](../specifications/configuration.md) owns exact
path and validation rules; [Data Architecture](data.md) maps artifact ownership.

## Network and provider boundary

Phase 1 exposes no public memory or administration service. The supported
invocation shape is local CLI and hooks. A future MCP or remote transport
requires an explicit design; this view does not describe an installed MCP
endpoint.

A semantic provider sits across a trust boundary. Local capture and validation
must contain what may cross it. [Security Architecture](README.md#security-and-trust) describes
that boundary, and [Processing](../specifications/processing.md) owns permitted
provider input and output behavior.

## Risks and future direction

Windows/WSL path identity and permissions may differ. Incorrect placement can
expose private vault or runtime material through the public checkout. Provider
access can extend beyond the intended request unless the boundary is enforced.

The [Roadmap](../project-record/roadmap.md) owns candidate multi-agent and
synchronized-host directions. Their topology and authorization require later
design work; neither changes the Phase 1 local boundary.

## Related documents

- [Architecture](README.md)
- [Integrations](integrations.md)
- [Installation and activation](../operations/setup.md)
- [Operating and recovery procedures](../operations/runbook.md)
- [Checkout/vault decision](../project-record/decisions/0004-separate-project-workspace-from-vault.md)
