# Security policy

## Supported state

Orca Memory is currently an architecture and manual prototype. It is not a
publicly supported network service, and canonical automatic apply remains
disabled.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's private vulnerability
reporting for `brightskye/orca`. Do not open a public issue containing secrets,
personal memory, vault contents, connector records, host paths, or exploit
details that expose a deployed system.

## Deployment boundary

- Keep MCP access local through stdio or another explicitly authenticated,
  private transport.
- Do not expose administrative, curation, ingestion, scheduler, or canonical
  apply interfaces directly to the public Internet.
- Keep credentials and machine-local configuration outside Git.
- Treat conversation evidence, shallow memory, candidates, and runtime state as
  private data even when they are noncanonical.
