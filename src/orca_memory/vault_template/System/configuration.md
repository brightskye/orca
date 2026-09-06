# Configuration

This starter keeps host and vault settings separate. The selected installation
owns `config/host.yaml` on the host that runs Orca; the vault owns
`Orca Memory/orca-memory.yaml` under `System/`.

The host file binds this vault to its selected `vault_path`, disposable
`runtime_path`, and Codex source location. A host may move the vault by
changing that binding and validating the new location. Keep host settings,
credentials, and runtime state outside this vault.

The vault policy owns provider, privacy, processing, recall, and interaction
settings. This starter keeps `lifecycle.enabled: false`: automatic capture is
off, and Phase 1 has no automatic canonical apply. Conversation artifacts and
other generated runtime records remain noncanonical until a separate human
curation step.

For operator steps, see the versioned [setup guide](https://github.com/brightskye/orca/blob/v0.1.0/docs/operations/setup.md).
For implementation status and boundaries, see [current status](https://github.com/brightskye/orca/blob/v0.1.0/docs/project-record/current.md).
