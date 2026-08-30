"""Run Manifest 0.2 source receipts, replay lookup, and checkpoint cursors."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from orca_memory.conversation import NormalizedTurn
from orca_memory.segmentation import SourceSegment


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

_OPERATION_OUTCOMES = {
    "add": {"created"},
    "support": {"supported"},
    "update": {"updated", "no-change"},
    "supersede": {"updated"},
    "conflict": {"conflict-recorded"},
    "candidate": {"created", "updated", "no-change"},
    "observation": {"observed"},
    "summary-refresh": {"created", "updated", "no-change"},
    "summary-stale": {"stale"},
}


@dataclass(frozen=True)
class ProcessedReceipt:
    representation: tuple[object, ...]
    manifest_path: Path
    source: dict[str, Any]


SegmentKey = tuple[str, str, str, str, str, int]


def segment_key(
    connector_id: str, conversation_id: str, source: dict[str, Any]
) -> SegmentKey:
    segment = source.get("segment")
    if not isinstance(segment, dict):
        raise ValueError("source receipt lacks segment identity")
    values = (
        connector_id,
        conversation_id,
        source.get("turn_id"),
        segment.get("policy_version"),
        segment.get("parameters_sha256"),
        segment.get("index"),
    )
    if not all(isinstance(item, str) for item in values[:5]) or not isinstance(
        values[5], int
    ):
        raise ValueError("source receipt has invalid segment identity")
    return values  # type: ignore[return-value]


def segmented_source(segment: SourceSegment, *, source_ref: str) -> dict[str, Any]:
    """Return the uniform Manifest receipt for a prepared segment."""

    return segment.as_manifest_source(source_ref)


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
    """Compatibility view returning the last proven receipt for each turn."""

    segments, legacy = processed_segment_receipts(vault_root)
    result = dict(legacy)
    for key, receipt in sorted(segments.items(), key=lambda item: item[0][-1]):
        result[key[:3]] = receipt
    return result


def processed_segment_receipts(
    vault_root: Path,
) -> tuple[dict[SegmentKey, ProcessedReceipt], dict[tuple[str, str, str], ProcessedReceipt]]:
    """Scan and validate immutable segmented and legacy source receipts."""

    manifest_root = vault_root / "System" / "Orca Memory" / "manifests"
    result: dict[SegmentKey, ProcessedReceipt] = {}
    legacy: dict[tuple[str, str, str], ProcessedReceipt] = {}
    if not manifest_root.exists():
        return result, legacy
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
        if schema == MANIFEST_SCHEMA:
            validate_manifest(value, path=path)
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("turn_id"), str):
                raise ValueError(f"invalid Manifest source receipt: {path}")
            turn_key = (connector_id, conversation_id, source["turn_id"])
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
            receipt = ProcessedReceipt(representation, path, source)
            if schema == LEGACY_MANIFEST_SCHEMA:
                known = legacy.get(turn_key)
                if known is not None and known.representation != representation:
                    raise ValueError(f"conflicting legacy Manifest receipts for {turn_key}")
                legacy[turn_key] = receipt
                continue
            key = segment_key(connector_id, conversation_id, source)
            known = result.get(key)
            if known is not None and known.representation != representation:
                raise ValueError(f"conflicting Manifest receipts for {key}")
            result[key] = receipt

    grouped: dict[tuple[str, str, str, str, str], list[ProcessedReceipt]] = {}
    for key, receipt in result.items():
        grouped.setdefault(key[:5], []).append(receipt)
    for group_key, receipts in grouped.items():
        ordered = sorted(receipts, key=lambda item: int(item.source["segment"]["index"]))
        segments = [item.source["segment"] for item in ordered]
        counts = {item["count"] for item in segments}
        turn_hashes = {item.source["turn_content_sha256"] for item in ordered}
        redactions = {item.source["redaction_policy"] for item in ordered}
        if len(counts) != 1 or len(turn_hashes) != 1 or len(redactions) != 1:
            raise ValueError(f"inconsistent segment sequence for {group_key[:3]}")
        indexes = [item["index"] for item in segments]
        if indexes != list(range(1, max(indexes) + 1)):
            raise ValueError(f"missing or out-of-order segment receipt for {group_key[:3]}")
        previous_end = 0
        for item in segments:
            if item["start_byte"] != previous_end or item["end_byte"] <= item["start_byte"]:
                raise ValueError(f"overlapping or invalid segment receipt for {group_key[:3]}")
            previous_end = item["end_byte"]
    policies_by_turn: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    for key in result:
        policies_by_turn.setdefault(key[:3], set()).add((key[3], key[4]))
    for turn_key, policies in policies_by_turn.items():
        if len(policies) > 1:
            raise ValueError(
                f"conflicting redaction or segmentation policies for {turn_key}"
            )
    return result, legacy


def validate_manifest(value: dict[str, Any], *, path: Path | None = None) -> None:
    """Validate Manifest 0.2 reference joins and controlled outcomes."""

    label = str(path) if path is not None else "Manifest"
    if not isinstance(value, dict) or value.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"invalid Manifest schema: {label}")
    sources = value.get("sources")
    operations = value.get("operations")
    outputs = value.get("outputs")
    if not all(isinstance(group, list) for group in (sources, operations, outputs)):
        raise ValueError(f"invalid Manifest receipt arrays: {label}")
    source_refs = [item.get("source_ref") for item in sources if isinstance(item, dict)]
    output_refs = [item.get("output_ref") for item in outputs if isinstance(item, dict)]
    operation_ids = [item.get("operation_id") for item in operations if isinstance(item, dict)]
    if (
        len(source_refs) != len(sources)
        or len(set(source_refs)) != len(source_refs)
        or not all(isinstance(item, str) and item for item in source_refs)
    ):
        raise ValueError(f"invalid or duplicate Manifest source_ref: {label}")
    for source in sources:
        segment = source.get("segment")
        if (
            source.get("source_role") not in {"owner", "assistant"}
            or not isinstance(source.get("turn_id"), str)
            or not isinstance(source.get("source_uri"), str)
            or not _hash_shape(source.get("turn_content_sha256"))
            or not isinstance(segment, dict)
            or not _hash_shape(segment.get("parameters_sha256"))
            or not _hash_shape(segment.get("content_sha256"))
            or not isinstance(segment.get("index"), int)
            or not isinstance(segment.get("count"), int)
            or not 1 <= segment["index"] <= segment["count"]
            or not isinstance(segment.get("start_byte"), int)
            or not isinstance(segment.get("end_byte"), int)
            or not 0 <= segment["start_byte"] < segment["end_byte"]
        ):
            raise ValueError(f"invalid Manifest source segment: {label}")
    if (
        len(output_refs) != len(outputs)
        or len(set(output_refs)) != len(output_refs)
        or not all(isinstance(item, str) and item for item in output_refs)
    ):
        raise ValueError(f"invalid or duplicate Manifest output_ref: {label}")
    if (
        len(operation_ids) != len(operations)
        or len(set(operation_ids)) != len(operation_ids)
        or not all(isinstance(item, str) and item for item in operation_ids)
    ):
        raise ValueError(f"invalid or duplicate Manifest operation_id: {label}")
    output_by_ref = {item["output_ref"]: item for item in outputs}
    for output in outputs:
        before = output.get("before_sha256")
        after = output.get("after_sha256")
        effect = output.get("effect")
        if effect == "created":
            valid_effect = before is None and _hash_shape(after)
        elif effect == "replaced":
            valid_effect = _hash_shape(before) and _hash_shape(after)
        elif effect == "deleted":
            valid_effect = _hash_shape(before) and after is None
        else:
            valid_effect = False
        if not valid_effect or not isinstance(output.get("artifact_id"), str):
            raise ValueError(f"invalid Manifest output receipt: {label}")
    for operation in operations:
        pair = _OPERATION_OUTCOMES.get(operation.get("operation"))
        if pair is None or operation.get("outcome") not in pair:
            raise ValueError(f"invalid Manifest operation outcome: {label}")
        cited_sources = operation.get("source_refs")
        cited_outputs = operation.get("output_refs")
        if (
            not isinstance(cited_sources, list)
            or not cited_sources
            or not set(cited_sources).issubset(source_refs)
            or not isinstance(cited_outputs, list)
            or not set(cited_outputs).issubset(output_refs)
        ):
            raise ValueError(f"invalid Manifest operation joins: {label}")
        if any(
            output_by_ref[ref].get("artifact_id") != operation.get("artifact_id")
            for ref in cited_outputs
        ):
            raise ValueError(f"Manifest operation/output identity mismatch: {label}")
        embedded = operation.get("embedded_artifact")
        if operation.get("operation") == "observation":
            if not isinstance(embedded, dict):
                raise ValueError(f"observation lacks embedded artifact: {label}")
        elif embedded is not None:
            raise ValueError(f"unexpected embedded Manifest artifact: {label}")
    status = value.get("status")
    if status == "no_memory" and (operations or outputs):
        raise ValueError(f"no_memory Manifest contains outcomes: {label}")
    if status == "success" and not operations:
        raise ValueError(f"success Manifest contains no operation: {label}")


def _hash_shape(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdef" for char in value
    )


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


def segment_representation(segment: SourceSegment) -> tuple[object, ...]:
    source = segmented_source(segment, source_ref="src-001")
    value = source["segment"]
    return (
        source["turn_content_sha256"],
        source["redaction_policy"],
        value["policy_version"],
        value["parameters_sha256"],
        value["index"],
        value["count"],
        value["start_byte"],
        value["end_byte"],
        value["content_sha256"],
    )


def is_exact_segment_replay(segment: SourceSegment, receipt: ProcessedReceipt) -> bool:
    return receipt.representation == segment_representation(segment)


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
