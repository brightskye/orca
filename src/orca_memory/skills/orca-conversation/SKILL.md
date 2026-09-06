---
name: orca-conversation
description: "Use for governed Orca conversation continuity: recall or resume a saved discussion, or explicitly save the current conversation when a verified source binding is available. Do not use for wiki/source intake, canonical note writing, or runtime administration."
---

# Orca conversation continuity

Use this skill when the Owner asks to remember or retain a discussion for later,
or when earlier discussion context is needed to resume current work. Orca
conversation memory is distilled, scoped, and noncanonical. It may preserve
decisions, reasons, tentative ideas, progress, open questions, and next steps;
it does not make those items accepted wiki knowledge.

## Authority and boundaries

- Current Owner instructions take precedence over recalled context.
- Treat every recalled result as past context and keep its `authority`, `scope`,
  `status`, and exact source reference visible. Do not turn a noncanonical
  result into an asserted fact without current evidence.
- Never manually create, edit, move, or delete generated files under
  `System/Orca Memory/`. Storage owns record identity, paths, schemas, hashes,
  manifests, and checkpoints.
- Do not copy full transcripts into the vault or expose secrets, credentials,
  private keys, recovery codes, or other sensitive values. The agent-owned
  rollout store remains the source; the vault receives governed distilled
  artifacts.
- Do not activate lifecycle processing, run catch-up, enable a provider, repair
  runtime state, or perform backup/restore as a side effect of ordinary recall
  or save. Those are separate operator workflows.

If “remember this” could mean either conversation continuity or accepting a
fact/source into the wiki, ask which outcome the Owner wants before writing.
Requests to save an article, source, note, or accepted knowledge belong to the
companion `orca-wiki` skill when it is available; otherwise ask the Owner to
provide that workflow. Do not silently use conversation memory as a wiki intake
route.

## Establish the binding before operating

Use the installed `orca` command when its launcher already selects the host
configuration. In a checkout-based development environment, use the
task-supplied `uv run orca --host-config <known-host-config>` binding. Do not
hard-code a checkout, vault, runtime, rollout-store, or personal path in this
skill.

Before inspecting or writing vault state, resolve the configured vault from the
known host configuration or the documented `ORCA_VAULT_PATH` binding, then read
the vault's `AGENTS.md`, `System/rules.md`, and `System/configuration.md`, plus
any delegated rules those files name. Before any write, all required policy
files and delegated rules must be present, readable, and mutually consistent.
If `AGENTS.md`, `System/rules.md`, or a required delegated rule is missing,
unreadable, or conflicting, stop before writing and ask the Owner for the
missing policy; do not silently skip it or infer a replacement. `ORCA_VAULT_PATH`
identifies the vault only; it does not replace a required host configuration or
prove a conversation/project identity.

Before live processing, follow the readiness and activation constraints in the
operator guidance linked by the configuration map. Installing this skill or
successfully recalling a record does not qualify a deployment for private capture.

Never guess any of these values:

- the host configuration or vault;
- the current conversation ID or rollout source path;
- the source byte offset/cursor;
- the project ID or alias; or
- whether a conversation belongs to General or Unassigned.

If the selected installation or current hook does not provide a required
binding, report the missing binding and ask only for that binding. Do not search
other vaults, projects, rollout histories, or agent stores to find a substitute.

## Recall or resume

Recall is a read-only command. Use a specific question and preserve one exact
scope selector:

```bash
# Installed launcher already bound to its host configuration:
orca recall "<specific question>" --project-alias "<known-project-alias>"

# Or select an explicitly known project identity:
orca recall "<specific question>" --project-id "<known-project-id>"

# For projectless or unresolved conversations:
orca recall "<specific question>" --scope general
orca recall "<specific question>" --scope unassigned
```

From a mapped current workspace, the CLI can resolve the exact project when
that mapping has been verified. Omit a selector only when the binding proves
that mapping; never use an unscoped query to search all projects. If the
workspace is unmapped, ask for a known project selector or an explicit General
or Unassigned scope.

When a result supplies a `conv:<purpose>--<id>` reference, use that complete
reference as the entire next recall question, without surrounding text. This
requests the exact continuation first. A normal question may return several
bounded results; respect the returned scope, authority, status, omitted items,
and refinement indicator.

The command may exit successfully with no results. Empty results, an ambiguous
result, a missing index, or an unavailable binding means recall was not
confirmed. Say so rather than filling the gap from memory or broadening scope.
Include the exact returned Markdown path or structural ID when reporting what
was recalled. `orca start` only supplies deterministic guidance and a
counts-only reminder; it does not perform Recall.

## Explicitly save a discussion

Only save when the Owner explicitly asks to remember, retain, or save the
conversation, or when an already-authorized current hook is carrying out its
documented lifecycle operation. An ordinary conversation, a suggestion to save,
or a vague “this may matter” does not authorize a write.

The current CLI's explicit-save path requires a verified, absolute rollout
source inside the configured Codex rollout store and a known connector,
conversation ID, and source offset:

```bash
orca queue-pointer \
  --trigger explicit-save \
  --connector-id codex-local \
  --conversation-id "<known-conversation-id>" \
  --source "<known-absolute-rollout-jsonl>" \
  --start-offset <known-source-offset> \
  --scope general
```

Use `--scope unassigned` only when that scope is explicitly confirmed. The
current `queue-pointer` command accepts only `general` and `unassigned`; it
cannot safely invent a project scope. If the Owner requests project-scoped
explicit saving and no already-bound interface supplies that exact project
identity, report that limitation and ask for a supported binding. Do not use an
automatic hook or enable lifecycle processing to work around it.

The command's `{"queued": true, "work_id": ...}` output proves only that work
was queued. It does not prove that a memory artifact was published. Record the
work ID, then inspect `orca status` before starting a worker. Status enumerates
unresolved `runtime-worker` items with their pending work IDs as locators; use
those locators to check that the explicit work ID is present and is the only
pending work item. The other unresolved status items (for example review or
recovery items) do not belong to the worker queue and must not be counted as
queued work. If the explicit work ID is absent, or another `runtime-worker`
locator is present, stop: the current worker has no single-work-item selector
and must not process unrelated histories by default. Ask the Owner whether to
process the broader queue or wait for its owning workflow.

When the explicit work item is the only pending item, run the approved worker
binding with its required reasoning effort (the current runbook examples use
`xhigh`):

```bash
orca worker --reasoning-effort xhigh
```

Interpret the worker result exactly:

- `success` means queued work completed at the worker boundary;
- `idle` means there was no work to process;
- `pending` means work remains and is not complete;
- `retry` means processing needs another bounded attempt;
- `failed` means a terminal failure was recorded;
- `disabled` applies to automatic work when lifecycle is off; and
- `locked` means another worker owns the runtime lock.

After `success`, verify the requested discussion with a scoped `orca recall`
question and confirm a returned source reference and noncanonical authority.
If the recall is empty, do not claim the save succeeded merely because the
worker exited zero. Preserve any pending or failure state and report the
unconfirmed outcome.

## Completion response

For a recall, state whether relevant context was found, its exact source
reference, and its authority/scope/status. For an explicit save, state the
queued work ID, worker result, and whether scoped recall confirmed a published
noncanonical artifact. Keep the saved next step and open question distinct from
new suggestions. If any required identity, binding, scope, or verification is
missing, say what is unknown and ask only for that item.
