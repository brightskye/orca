# Security policy

## Supported state

Orca Memory has an active but incomplete Phase 1 local implementation. It is not
deployed or offered as a publicly supported service, and canonical automatic
apply remains disabled.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability
reporting for `brightskye/orca`. Do not open a public issue containing secrets,
personal memory, vault contents, connector records, host paths, or exploit
details that expose a deployed system.

## Security and privacy boundaries

Accepted assets, trust boundaries, threats, deployment restrictions, secret
containment, logging, and residual risks are defined by [Security and
Trust](docs/02-architecture/security-and-trust.md). Exact privacy and authority
behavior remains governed by the [Memory System
Contract](docs/governance/memory-system-contract.md). See [Current
Status](docs/STATUS.md) for implementation gaps; documented design is not proof
of deployed protection.
