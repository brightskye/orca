# Security policy

## Supported state

Orca targets local Phase 1 use and is not offered as a publicly supported
service. [Current](docs/project-record/current.md) owns support limitations,
deployment state, and unresolved readiness findings.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability
reporting for `brightskye/orca`. Do not open a public issue containing secrets,
personal memory, vault contents, connector records, host paths, or exploit
details that expose a deployed system.

## Security and privacy boundaries

Accepted assets, trust boundaries, threats, deployment restrictions, secret
containment, logging, and residual risks are defined by [Security and
Trust](docs/architecture/README.md#security-and-trust). Exact privacy and authority
behavior remains governed by the [Memory System
Contract](docs/specifications/memory-system-contract.md). See [Current](docs/project-record/current.md)
for implementation limits; documented design is not proof of deployed
protection.
