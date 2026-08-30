"""Run Manifest 0.2 source receipts, replay lookup, and checkpoint cursors."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from orca_memory.conversation import NormalizedTurn


MANIFEST_SCHEMA = "orca-run-manifest/0.2"
LEGACY_MANIFEST_SCHEMA = "orca-run-manifest/0.1"
CHECKPOINT_SCHEMA = "orca-checkpoint/0.2"
SEGMENTATION_POLICY = "orca-segmentation/0.1"
SEGMENTATION_PARAMETERS = {"mode": "unsegmented", "version": SEGMENTATION_POLICY}
SEGMENTATION_PARAMETERS_SHA256 = hashlib.sha256(
    json.dumps(SEGMENTATION_PARAMETERS, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
).hexdigest()


@dataclass(frozen=True)
class ProcessedReceipt:
    representation: tuple[object, ...]
    manifest_path: Path
    source: dict[str, Any]


def unsegmented_source(turn: NormalizedTurn, *, source_ref: str) -> dict[str, Any]:
    payload = turn.text.encode("utf-8")
    return {
        "source_ref": source_ref,
        "turn_id": turn.turn_id,
        "source_role": turn.source_role,
        "source_uri": turn.source_uri,
        "occurred_at": turn.occurred_at,
        "turn_content_sha256": turn.content_sha256,
        "redaction_policy": turn.redaction_policy,
        "segment": {
            "policy_version": SEGMENTATION_POLICY,
            "parameters_sha256": SEGMENTATION_PARAMETERS_SHA256,
            "index": 1,
            "count": 1,
            "start_byte": 0,
            "end_byte": len(payload),
            "content_sha256": hashlib.sha256(payload).hexdigest(),
        },
    }


def processed_sources(vault_root: Path) -> dict[tuple[str, str, str], ProcessedReceipt]:
    """Scan immutable 0.1 and 0.2 Manifests without inventing old semantics."""

    manifest_root = vault_root / "System" / "Orca Memory" / "manifests"
    result: dict[tuple[str, str, str], ProcessedReceipt] = {}
    if not manifest_root.exists():
        return result
    for path in sorted(manifest_root.glob("**/*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        schema = value.get("schema") or value.get("schema_version")
        if schema not in {MANIFEST_SCHEMA, LEGACY_MANIFEST_SCHEMA}:
            continue
        if value.get("status") not in {"success", "no_memory"}:
            continue
        connector_id = value.get("connector_id")
        conversation_id = value.get("conversation_id")
        if not isinstance(connector_id, str) or not isinstance(conversation_id, str):
            raise ValueError(f"invalid Manifest source identity: {path}")
        sources = value.get("sources")
        if not isinstance(sources, list):
            raise ValueError(f"invalid Manifest sources: {path}")
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("turn_id"), str):
                raise ValueError(f"invalid Manifest source receipt: {path}")
            key = (connector_id, conversation_id, source["turn_id"])
            if schema == LEGACY_MANIFEST_SCHEMA:
                representation = (
                    source.get("content_sha256"),
                    source.get("redaction_policy"),
                    "legacy-0.1",
                )
            else:
                segment = source.get("segment")
                if not isinstance(segment, dict):
                    raise ValueError(f"invalid Manifest segment receipt: {path}")
                representation = (
                    source.get("turn_content_sha256"),
                    source.get("redaction_policy"),
                    segment.get("policy_version"),
                    segment.get("parameters_sha256"),
                    segment.get("index"),
                    segment.get("count"),
                    segment.get("start_byte"),
                    segment.get("end_byte"),
                    segment.get("content_sha256"),
                )
            if any(item is None for item in representation):
                raise ValueError(f"incomplete Manifest source receipt: {path}")
            known = result.get(key)
            receipt = ProcessedReceipt(representation, path, source)
            if known is not None and known.representation != representation:
                known_legacy = known.representation[-1] == "legacy-0.1"
                current_legacy = representation[-1] == "legacy-0.1"
                if (
                    known_legacy != current_legacy
                    and known.representation[:2] == representation[:2]
                ):
                    if known_legacy:
                        result[key] = receipt
                    continue
                raise ValueError(f"conflicting Manifest receipts for {key}")
            result[key] = receipt
    return result


def current_representation(turn: NormalizedTurn) -> tuple[object, ...]:
    source = unsegmented_source(turn, source_ref="src-001")
    segment = source["segment"]
    return (
        source["turn_content_sha256"],
        source["redaction_policy"],
        segment["policy_version"],
        segment["parameters_sha256"],
        segment["index"],
        segment["count"],
        segment["start_byte"],
        segment["end_byte"],
        segment["content_sha256"],
    )


def is_exact_replay(turn: NormalizedTurn, receipt: ProcessedReceipt) -> bool:
    if receipt.representation[-1] == "legacy-0.1":
        return receipt.representation[:2] == (
            turn.content_sha256,
            turn.redaction_policy,
        )
    return receipt.representation == current_representation(turn)


def checkpoint_payload(
    *,
    connector_id: str,
    conversation_id: str,
    source: dict[str, Any],
    manifest_path: str,
) -> bytes:
    segment = source["segment"]
    value = {
        "schema_version": CHECKPOINT_SCHEMA,
        "connector_id": connector_id,
        "conversation_id": conversation_id,
        "processed_through": {
            "turn_id": source["turn_id"],
            "redaction_policy": source["redaction_policy"],
            "turn_content_sha256": source["turn_content_sha256"],
            "segment_policy_version": segment["policy_version"],
            "segment_parameters_sha256": segment["parameters_sha256"],
            "segment_index": segment["index"],
            "segment_count": segment["count"],
            "segment_content_sha256": segment["content_sha256"],
        },
        "manifest_path": manifest_path,
    }
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
