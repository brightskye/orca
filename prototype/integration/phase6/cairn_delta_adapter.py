"""Deterministic Cairn Markdown snapshot/delta adapter for Orca Phase 6.

The adapter is intentionally transport-only. It reads a complete Markdown
store, derives candidate revisions from Cairn permalinks and exact parsed
candidate content, emits replayable added/changed/deleted records, and advances
an operational checkpoint only after the delta result is durably materialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote

ADAPTER_NAME = "orca-cairn-delta"
ADAPTER_VERSION = "0.1.2"
CHECKPOINT_SCHEMA = "orca-cairn-checkpoint"
CHECKPOINT_SCHEMA_VERSION = 1
DELTA_SCHEMA = "orca-cairn-delta-result"
DELTA_SCHEMA_VERSION = 1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$")
_OBSERVATION_RE = re.compile(r"^\s*[-*]\s+\[(?!\[)([^\]]+)\]\s*(.*)$")
_TAG_RE = re.compile(r"(?:^|\s)#([\w\-/]+)")
_CONTEXT_RE = re.compile(r"\(([^)]*)\)\s*$")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")


class AdapterError(RuntimeError):
    """Base class for expected, fail-closed adapter failures."""


class ScanError(AdapterError):
    """The source store could not produce one complete valid snapshot."""


class CheckpointError(AdapterError):
    """The checkpoint is corrupt, incompatible, or otherwise unsafe."""


class SourceStoreMismatch(CheckpointError):
    """The checkpoint belongs to a different configured source store."""


@dataclass(frozen=True)
class CandidateSnapshot:
    permalink: str
    content: str
    content_sha256: str
    source_reference: str
    provenance: Mapping[str, str]

    def checkpoint_entry(self, observed_at: str) -> dict[str, Any]:
        return {
            "content_sha256": self.content_sha256,
            "source_reference": self.source_reference,
            "source_session": self.provenance.get("source_session"),
            "last_seen_at": observed_at,
            "provenance": dict(sorted(self.provenance.items())),
        }


@dataclass(frozen=True)
class ScanSnapshot:
    source_root: Path
    entries: Mapping[str, CandidateSnapshot]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_sha256(content: str) -> str:
    """Hash exact UTF-8 bytes of Cairn-parsed candidate content."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def scan_store(source_root: Path) -> ScanSnapshot:
    """Read every Markdown file or fail without returning a partial snapshot."""

    root = source_root.resolve()
    if not root.is_dir():
        raise ScanError(f"source root is not a directory: {source_root}")

    paths = sorted(
        (path for path in root.rglob("*.md") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    entries: dict[str, CandidateSnapshot] = {}
    owners: dict[str, str] = {}
    errors: list[str] = []

    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            candidate = parse_candidate_file(path, relative)
        except (OSError, UnicodeError, ScanError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        if candidate.permalink in entries:
            errors.append(
                "duplicate permalink "
                f"{candidate.permalink!r}: {owners[candidate.permalink]} and {relative}"
            )
            continue
        entries[candidate.permalink] = candidate
        owners[candidate.permalink] = relative

    if errors:
        raise ScanError("invalid Cairn snapshot; checkpoint not advanced:\n- " + "\n- ".join(errors))

    return ScanSnapshot(root, dict(sorted(entries.items())))


def parse_candidate_file(path: Path, source_reference: str) -> CandidateSnapshot:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ScanError("not valid UTF-8") from exc

    metadata, body = _parse_frontmatter(text)
    permalink = metadata.get("permalink")
    if not isinstance(permalink, str) or not permalink.strip():
        raise ScanError("missing or invalid permalink")
    if permalink != permalink.strip():
        raise ScanError("permalink has leading or trailing whitespace")

    observations = _parse_observations(body)
    kind = metadata.get("kind")
    if kind == "session-summary":
        candidates = [content for category, content in observations if category == "verbatim"]
    else:
        candidates = [content for category, content in observations if category == "context"]
    if len(candidates) != 1 or not candidates[0]:
        raise ScanError(
            "expected exactly one non-empty Cairn candidate content observation "
            f"but found {len(candidates)}"
        )

    content = candidates[0]
    provenance: dict[str, str] = {}
    source = metadata.get("source")
    if isinstance(source, str) and source:
        provenance["source"] = source
        if source.startswith("memory://session/") and len(source) > len("memory://session/"):
            provenance["source_session"] = source
    for field in (
        "harness",
        "project",
        "observed_project",
        "intent",
        "entry_mode",
        "captured_at",
        "created",
        "authority",
        "candidate_type",
        "memory_type",
        "semantic_contract",
    ):
        value = metadata.get(field)
        if isinstance(value, str) and value:
            provenance[field] = value

    intent = provenance.get("intent")
    if intent is not None and intent not in {"explicit", "implicit"}:
        raise ScanError(f"invalid intent {intent!r}; expected explicit or implicit")
    entry_mode = provenance.get("entry_mode")
    if entry_mode is not None and entry_mode not in {
        "explicit",
        "implicit",
        "conversational",
        "source",
        "reflection",
    }:
        raise ScanError(f"invalid entry_mode {entry_mode!r}")

    return CandidateSnapshot(
        permalink=permalink,
        content=content,
        content_sha256=content_sha256(content),
        source_reference=source_reference,
        provenance=dict(sorted(provenance.items())),
    )


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ScanError("missing opening frontmatter delimiter")
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\r\n") == "---"),
        None,
    )
    if closing is None:
        raise ScanError("missing closing frontmatter delimiter")

    metadata: dict[str, Any] = {}
    active_container = False
    for number, raw in enumerate(lines[1:closing], start=2):
        line = raw.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[: len(line) - len(line.lstrip("\t "))]:
            raise ScanError(f"frontmatter line {number} uses tab indentation")
        if line[0].isspace() or line.startswith("-"):
            if not active_container:
                raise ScanError(f"unexpected nested frontmatter line {number}")
            _validate_nested_yaml_line(line.lstrip(), number)
            continue
        match = _TOP_LEVEL_KEY_RE.fullmatch(line)
        if not match:
            raise ScanError(f"malformed top-level frontmatter line {number}")
        key, raw_value = match.group(1), match.group(2) or ""
        if key in metadata:
            raise ScanError(f"duplicate frontmatter key {key!r}")
        value = _parse_yaml_scalar(raw_value.strip(), number)
        metadata[key] = value
        active_container = value is None

    body = "".join(lines[closing + 1 :])
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return metadata, body


def _parse_yaml_scalar(value: str, line_number: int) -> Any:
    if value == "":
        return None
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise ScanError(f"unterminated single-quoted scalar on line {line_number}")
        return value[1:-1].replace("''", "'")
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ScanError(f"invalid double-quoted scalar on line {line_number}") from exc
        if not isinstance(parsed, str):
            raise ScanError(f"invalid scalar on line {line_number}")
        return parsed
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.startswith(("[", "{")):
        if not (
            (value.startswith("[") and value.endswith("]"))
            or (value.startswith("{") and value.endswith("}"))
        ):
            raise ScanError(f"unterminated flow collection on line {line_number}")
        return value
    return value


def _validate_nested_yaml_line(value: str, line_number: int) -> None:
    if value.startswith("-"):
        item = value[1:].strip()
        if not item:
            return
        if ":" not in item:
            return
        if not _TOP_LEVEL_KEY_RE.fullmatch(item):
            raise ScanError(f"malformed nested frontmatter line {line_number}")
        return
    if not _TOP_LEVEL_KEY_RE.fullmatch(value):
        raise ScanError(f"malformed nested frontmatter line {line_number}")


def _parse_observations(body: str) -> list[tuple[str, str]]:
    observations: list[tuple[str, str]] = []
    in_fence = False
    for raw_line in body.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = _INLINE_CODE_RE.sub("", raw_line)
        match = _OBSERVATION_RE.match(line)
        if not match:
            continue
        category = match.group(1).strip()
        if not category or category in {"x", "X"}:
            continue
        remainder = match.group(2).strip()
        context_match = _CONTEXT_RE.search(remainder)
        if context_match:
            remainder = remainder[: context_match.start()].strip()
        content = _TAG_RE.sub("", remainder).strip()
        observations.append((category.casefold(), content))
    if in_fence:
        raise ScanError("unterminated fenced code block")
    return observations


def load_checkpoint(
    checkpoint_path: Path, *, store_id: str, harness: str, default_intent: str
) -> dict[str, Any] | None:
    if not checkpoint_path.exists():
        return None
    try:
        text = checkpoint_path.read_text(encoding="utf-8")
        data = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise CheckpointError(
            f"checkpoint is corrupt; restore or explicitly replace it after review: {checkpoint_path}"
        ) from exc
    _validate_checkpoint(data)
    source_store = data["source_store"]
    if (
        source_store["id"] != store_id
        or source_store["harness"] != harness
        or source_store["default_intent"] != default_intent
    ):
        raise SourceStoreMismatch(
            "checkpoint source-store mismatch; use the matching --store-id/--harness "
            "or an explicitly separate checkpoint"
        )
    return data


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_checkpoint(data: Any) -> None:
    if not isinstance(data, dict):
        raise CheckpointError("checkpoint root must be an object")
    expected_root = {
        "schema",
        "schema_version",
        "adapter",
        "source_store",
        "checkpoint_id",
        "completed_at",
        "entries",
    }
    if set(data) != expected_root:
        raise CheckpointError("checkpoint root fields do not match schema v1")
    if data.get("schema") != CHECKPOINT_SCHEMA:
        raise CheckpointError(f"unsupported checkpoint schema: {data.get('schema')!r}")
    if data.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise CheckpointError(
            f"unsupported checkpoint schema version: {data.get('schema_version')!r}"
        )
    adapter = data.get("adapter")
    if (
        not isinstance(adapter, dict)
        or set(adapter) != {"name", "version"}
        or adapter.get("name") != ADAPTER_NAME
    ):
        raise CheckpointError("checkpoint adapter identity is invalid")
    if adapter.get("version") != ADAPTER_VERSION:
        raise CheckpointError(
            f"checkpoint adapter version mismatch: {adapter.get('version')!r}"
        )
    source_store = data.get("source_store")
    if not isinstance(source_store, dict) or set(source_store) != {
        "id",
        "harness",
        "default_intent",
    }:
        raise CheckpointError("checkpoint source_store is invalid")
    if not all(
        isinstance(source_store.get(key), str) and source_store[key]
        for key in ("id", "harness")
    ):
        raise CheckpointError("checkpoint source_store id/harness is invalid")
    if source_store.get("default_intent") not in {"explicit", "implicit"}:
        raise CheckpointError("checkpoint source_store default_intent is invalid")
    checkpoint_id = data.get("checkpoint_id")
    if (
        not isinstance(checkpoint_id, str)
        or not re.fullmatch(r"phase6:[0-9a-f]{64}", checkpoint_id)
    ):
        raise CheckpointError("checkpoint_id is invalid")
    if not isinstance(data.get("completed_at"), str) or not data["completed_at"]:
        raise CheckpointError("checkpoint completed_at is invalid")
    entries = data.get("entries")
    if not isinstance(entries, dict):
        raise CheckpointError("checkpoint entries must be an object")
    for permalink, entry in entries.items():
        if not isinstance(permalink, str) or not permalink or not isinstance(entry, dict):
            raise CheckpointError("checkpoint entry identity is invalid")
        if set(entry) != {
            "content_sha256",
            "source_reference",
            "source_session",
            "last_seen_at",
            "provenance",
        }:
            raise CheckpointError(f"checkpoint fields are invalid for {permalink!r}")
        digest = entry.get("content_sha256")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise CheckpointError(f"checkpoint hash is invalid for {permalink!r}")
        if not isinstance(entry.get("source_reference"), str) or not entry["source_reference"]:
            raise CheckpointError(f"checkpoint source reference is invalid for {permalink!r}")
        source_session = entry.get("source_session")
        if source_session is not None and (
            not isinstance(source_session, str) or not source_session
        ):
            raise CheckpointError(f"checkpoint source session is invalid for {permalink!r}")
        if not isinstance(entry.get("last_seen_at"), str) or not entry["last_seen_at"]:
            raise CheckpointError(f"checkpoint last_seen_at is invalid for {permalink!r}")
        provenance = entry.get("provenance")
        if not isinstance(provenance, dict) or not all(
            isinstance(key, str)
            and key
            and isinstance(value, str)
            and value
            for key, value in provenance.items()
        ):
            raise CheckpointError(f"checkpoint provenance is invalid for {permalink!r}")


def compare_snapshot(
    snapshot: ScanSnapshot,
    previous: Mapping[str, Any] | None,
    *,
    store_id: str,
    harness: str,
    default_intent: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    previous_entries: Mapping[str, Any] = previous["entries"] if previous else {}
    previous_id = previous["checkpoint_id"] if previous else None
    current_entries = snapshot.entries
    checkpoint_id = _checkpoint_id(
        store_id=store_id,
        harness=harness,
        default_intent=default_intent,
        previous_id=previous_id,
        current_entries=current_entries,
    )

    deltas: list[dict[str, Any]] = []
    counts = {"added": 0, "changed": 0, "deleted": 0, "unchanged": 0}
    for permalink in sorted(set(previous_entries) | set(current_entries)):
        prior = previous_entries.get(permalink)
        current = current_entries.get(permalink)
        if prior is None and current is not None:
            counts["added"] += 1
            deltas.append(
                _current_delta(
                    "added",
                    current,
                    None,
                    checkpoint_id,
                    store_id,
                    harness,
                    default_intent,
                    generated_at,
                )
            )
        elif prior is not None and current is None:
            counts["deleted"] += 1
            deltas.append(
                _deleted_delta(
                    permalink,
                    prior,
                    checkpoint_id,
                    store_id,
                    harness,
                    default_intent,
                    generated_at,
                )
            )
        elif prior["content_sha256"] != current.content_sha256:
            counts["changed"] += 1
            deltas.append(
                _current_delta(
                    "changed",
                    current,
                    prior,
                    checkpoint_id,
                    store_id,
                    harness,
                    default_intent,
                    generated_at,
                )
            )
        else:
            counts["unchanged"] += 1

    result = {
        "schema": DELTA_SCHEMA,
        "schema_version": DELTA_SCHEMA_VERSION,
        "adapter": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        "source_store": {
            "id": store_id,
            "harness": harness,
            "default_intent": default_intent,
        },
        "generated_at": generated_at,
        "checkpoint": {
            "previous_id": previous_id,
            "current_id": checkpoint_id,
            "initial_discovery": previous is None,
        },
        "summary": counts,
        "deltas": deltas,
    }
    checkpoint = {
        "schema": CHECKPOINT_SCHEMA,
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "adapter": {"name": ADAPTER_NAME, "version": ADAPTER_VERSION},
        "source_store": {
            "id": store_id,
            "harness": harness,
            "default_intent": default_intent,
        },
        "checkpoint_id": checkpoint_id,
        "completed_at": generated_at,
        "entries": {
            permalink: current_entries[permalink].checkpoint_entry(generated_at)
            for permalink in sorted(current_entries)
        },
    }
    return result, checkpoint


def _checkpoint_id(
    *,
    store_id: str,
    harness: str,
    default_intent: str,
    previous_id: str | None,
    current_entries: Mapping[str, CandidateSnapshot],
) -> str:
    material = {
        "adapter_version": ADAPTER_VERSION,
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "store_id": store_id,
        "harness": harness,
        "default_intent": default_intent,
        "previous_id": previous_id,
        "entries": [
            {
                "permalink": permalink,
                "content_sha256": current_entries[permalink].content_sha256,
                "source_reference": current_entries[permalink].source_reference,
                "source_session": current_entries[permalink].provenance.get("source_session"),
            }
            for permalink in sorted(current_entries)
        ],
    }
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return f"phase6:{digest}"


def _current_delta(
    change: str,
    current: CandidateSnapshot,
    prior: Mapping[str, Any] | None,
    checkpoint_id: str,
    store_id: str,
    harness: str,
    default_intent: str,
    generated_at: str,
) -> dict[str, Any]:
    sources = [
        {
            "id": "cairn-permalink",
            "resource": f"cairn://{quote(store_id, safe='')}/{quote(current.permalink, safe='')}",
        }
    ]
    source_session = current.provenance.get("source_session")
    if source_session:
        sources.append({"id": "source-session", "resource": source_session})
    intent = current.provenance.get("intent", default_intent)
    entry_mode = current.provenance.get("entry_mode", intent)
    return {
        "change": change,
        "permalink": current.permalink,
        "previous_sha256": prior["content_sha256"] if prior else None,
        "current_sha256": current.content_sha256,
        "content_sha256": current.content_sha256,
        "content": current.content,
        "source_reference": current.source_reference,
        "previous_source_reference": prior.get("source_reference") if prior else None,
        "adapter_version": ADAPTER_VERSION,
        "checkpoint_id": checkpoint_id,
        "harness": harness,
        "intent": intent,
        "entry_mode": entry_mode,
        "authority": "candidate",
        "orca_state": "new",
        "generated": {
            "by": f"process:{ADAPTER_NAME}/{ADAPTER_VERSION}",
            "at": generated_at,
        },
        "sources": sources,
        "provenance": dict(current.provenance),
    }


def _deleted_delta(
    permalink: str,
    prior: Mapping[str, Any],
    checkpoint_id: str,
    store_id: str,
    harness: str,
    default_intent: str,
    generated_at: str,
) -> dict[str, Any]:
    source_session = prior.get("source_session")
    sources = [
        {
            "id": "cairn-permalink",
            "resource": f"cairn://{quote(store_id, safe='')}/{quote(permalink, safe='')}",
        }
    ]
    if isinstance(source_session, str) and source_session:
        sources.append({"id": "source-session", "resource": source_session})
    prior_provenance = dict(prior.get("provenance") or {})
    intent = prior_provenance.get("intent", default_intent)
    entry_mode = prior_provenance.get("entry_mode", intent)
    return {
        "change": "deleted",
        "permalink": permalink,
        "previous_sha256": prior["content_sha256"],
        "current_sha256": None,
        "content_sha256": prior["content_sha256"],
        "source_reference": None,
        "previous_source_reference": prior["source_reference"],
        "adapter_version": ADAPTER_VERSION,
        "checkpoint_id": checkpoint_id,
        "harness": harness,
        "intent": intent,
        "entry_mode": entry_mode,
        "authority": "candidate",
        "orca_state": "new",
        "generated": {
            "by": f"process:{ADAPTER_NAME}/{ADAPTER_VERSION}",
            "at": generated_at,
        },
        "sources": sources,
        "provenance": prior_provenance,
        "semantics": "source-candidate-removed; no canonical deletion or truth judgment",
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def run_adapter(
    *,
    source_root: Path,
    checkpoint_path: Path,
    output_path: Path,
    store_id: str,
    harness: str,
    default_intent: str,
    generated_at: str | None = None,
    before_checkpoint_replace: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    if not store_id.strip() or not harness.strip():
        raise AdapterError("store_id and harness must be non-empty")
    if default_intent not in {"explicit", "implicit"}:
        raise AdapterError("default_intent must be explicit or implicit")
    if checkpoint_path.resolve() == output_path.resolve():
        raise AdapterError("checkpoint and output paths must be different")
    if checkpoint_path.suffix.casefold() != ".json" or output_path.suffix.casefold() != ".json":
        raise AdapterError("checkpoint and output paths must use .json")

    observed_at = generated_at or utc_now()
    previous = load_checkpoint(
        checkpoint_path,
        store_id=store_id,
        harness=harness,
        default_intent=default_intent,
    )
    snapshot = scan_store(source_root)
    result, checkpoint = compare_snapshot(
        snapshot,
        previous,
        store_id=store_id,
        harness=harness,
        default_intent=default_intent,
        generated_at=observed_at,
    )

    # Result materialization is the Phase 6 durable handoff boundary. No
    # consumer acknowledgement protocol is invented in this phase.
    materialized_result = _materialize_result(output_path, result)
    if materialized_result is not result:
        materialized_at = materialized_result["generated_at"]
        checkpoint["completed_at"] = materialized_at
        for entry in checkpoint["entries"].values():
            entry["last_seen_at"] = materialized_at
    _atomic_write_json(
        checkpoint_path,
        checkpoint,
        before_replace=before_checkpoint_replace,
    )
    return materialized_result


def _atomic_write_json(
    path: Path,
    value: Any,
    *,
    before_replace: Callable[[Path], None] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if before_replace is not None:
            before_replace(temporary)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _materialize_result(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        try:
            existing = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise AdapterError(
                f"output already exists but is unreadable; preserve it and choose a new path: {path}"
            ) from exc
        if _stable_result_identity(existing) == _stable_result_identity(result):
            return existing
        raise AdapterError(
            f"output already contains a different materialized result; choose a unique path: {path}"
        )
    _atomic_write_json(path, result)
    return result


def _stable_result_identity(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    normalized = json.loads(json.dumps(result))
    normalized.pop("generated_at", None)
    deltas = normalized.get("deltas")
    if isinstance(deltas, list):
        for delta in deltas:
            if isinstance(delta, dict) and isinstance(delta.get("generated"), dict):
                delta["generated"].pop("at", None)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--store-id", required=True)
    parser.add_argument("--harness", required=True)
    parser.add_argument(
        "--default-intent",
        required=True,
        choices=("explicit", "implicit"),
        help="Configured fallback when Cairn Markdown has no explicit/implicit intent field.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_adapter(
            source_root=args.source_root,
            checkpoint_path=args.checkpoint,
            output_path=args.output,
            store_id=args.store_id,
            harness=args.harness,
            default_intent=args.default_intent,
        )
    except AdapterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
