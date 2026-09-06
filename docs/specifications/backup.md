# Orca encrypted backup

This specification owns Phase 1 backup membership, creation preconditions,
verification, and staging behavior previously described in Architecture and
Operations. [Runbook](../operations/runbook.md) owns commands and execution.
[Current](../project-record/current.md) records verification limits and known
recovery gaps.

## Authority and interface

A backup is a private recovery copy. It MUST NOT establish canonical authority
or authorize merging into live memory. The supported operations are create,
verify, and decrypt to new staging. Live overwrite or automatic restore is
outside this interface.

The caller supplies the encryption recipient and absolute output path.
Encryption and decryption use a locally installed GPG executable; Orca does
not store or manage private keys or infer a recipient.

## Creation

Backup creation MUST require lifecycle handling to be disabled and no pending
queue, retry-spool, publication, project-mapping, or Owner-review work. An
unsettled runtime blocks creation rather than being silently copied.

The vault and runtime roots MUST be separate directories. The encrypted output
MUST be a new path outside both. Existing output MUST NOT be overwritten.
Private memory and plaintext recovery material MUST remain outside the public
checkout under the project/vault separation contract.
[Current](../project-record/current.md) records enforcement and verification limits.

## Membership

| Included | Excluded |
|---|---|
| Full configured vault, including vault-local Run Manifests | Agent-owned raw rollout store |
| Validated, content-minimized runtime `source-cursors/` JSON | Host configuration and credentials outside the vault |
| Validated, content-minimized runtime `scope-choices/` JSON | Queues, retry spools, pending intents, runtime checkpoints, indexes, locks, and other disposable runtime state |

The full-vault copy is not a content-redaction operation. The configuration and
privacy contracts require credentials and raw rollouts to remain outside the
vault before backup.

The archive uses schema `orca-backup/0.1` and a `manifest.json` binding member
paths, sizes, and hashes. Verification MUST reject unsafe paths, unsupported
member types, duplicate or inconsistent membership, and content-hash mismatch.

## Verification

The source MUST be a private regular encrypted backup file. Verification
decrypts into a private temporary workspace and checks the manifest and every
member hash before declaring success. A decryption, path, type, permission, or
hash failure MUST fail closed without modifying live vault or runtime state.
Temporary plaintext is cleaned up when verification ends.

CLI verification MUST NOT load host configuration, vault policies, the Project
Registry, or provider configuration. It requires only the archive, installed
GPG, and access to the decryption key.

## Staging

Staging MUST verify the archive before exposing decrypted contents. The
destination is a new private directory outside the live vault and runtime;
it MUST NOT overwrite or merge into an existing directory. An explicit
destination MUST be absolute. Plaintext remains private during validation.

Successful staging exposes a recovery copy for a separate Owner-controlled
recovery procedure. It does not redirect configuration, register a project,
rebuild indexes, or write live memory. Failure MUST expose no staging contents
and MUST NOT alter live state.

Normal CLI staging loads configuration and protects the configured live vault
and runtime roots, configured project roots, and detected containing Git
worktrees. Temporary plaintext workspaces also reject detected Git worktrees.
Explicit `--standalone` staging bypasses configuration for
recovery after installation loss. It retains archive verification, private
staging, and refusal to reuse an existing destination. In this mode the caller
MUST select a new destination outside live data and project checkouts: absent
configuration cannot identify the former live roots or non-Git project mappings.
Detected Git worktrees are still rejected in standalone mode. This is an explicit
recovery mode, not a fallback after configuration validation fails.

## Verification routes and limits

[Test Strategy](../quality/test-strategy.md) owns deterministic backup testing.
A fake-GPG test establishes archive handling at that boundary; actual encryption
and recovery of a deployed vault require the operator procedure in
[Using and maintaining Orca](../operations/runbook.md#backup).
The CLI has separate missing/invalid-configuration regression coverage and an
opt-in real GPG drill covering installation loss, restored hashes, rebuilt
retrieval, and recalled sources. [Current](../project-record/current.md) records
the latest evidence and distinguishes a synthetic drill from a deployed-vault
backup.
