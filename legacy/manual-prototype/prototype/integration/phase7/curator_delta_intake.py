"""Manual Phase 7 bridge from immutable Phase 6 deltas to Orca Curator.

This module validates deterministic transport evidence, checks the current
Cairn source with the Phase 6 scanner, persists operational idempotency state,
and applies an explicitly authorized Curator-authored plan.  It never chooses
semantic comparisons, dispositions, canonical targets, or supersession.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

PHASE6_DIR = Path(__file__).resolve().parents[1] / "phase6"
if str(PHASE6_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE6_DIR))

from cairn_delta_adapter import (  # noqa: E402
    ADAPTER_NAME as PHASE6_ADAPTER_NAME,
    ADAPTER_VERSION as PHASE6_ADAPTER_VERSION,
    DELTA_SCHEMA as PHASE6_DELTA_SCHEMA,
    DELTA_SCHEMA_VERSION as PHASE6_DELTA_SCHEMA_VERSION,
    ScanError as Phase6ScanError,
    content_sha256,
    scan_store,
)


INTEGRATION_NAME = "orca-cairn-curator-intake"
INTEGRATION_VERSION = "0.1.4"
STATE_SCHEMA = "orca-phase7-processing-state"
STATE_SCHEMA_VERSION = 2
INTAKE_SCHEMA = "orca-phase7-curator-intake"
INTAKE_SCHEMA_VERSION = 1
PLAN_SCHEMA = "orca-phase7-curator-plan"
PLAN_SCHEMA_VERSION = 1
PROPOSAL_SCHEMA = "orca-phase7-curator-proposal"
PROPOSAL_SCHEMA_VERSION = 1
AUTHORIZATION_SCHEMA = "orca-phase7-apply-authorization"
AUTHORIZATION_SCHEMA_VERSION = 1
DISPOSITION_SCHEMA = "orca-phase7-curator-disposition"
DISPOSITION_SCHEMA_VERSION = 1

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PHASE6_ID_RE = re.compile(r"^phase6:[0-9a-f]{64}$")
_EVENT_ID_RE = re.compile(r"^phase7-event:[0-9a-f]{64}$")
_BATCH_ID_RE = re.compile(r"^phase7-batch:[0-9a-f]{64}$")
_PLAN_ID_RE = re.compile(r"^phase7-plan:[0-9a-f]{64}$")
_DISPOSITION_ID_RE = re.compile(r"^phase7-disposition:[0-9a-f]{64}$")
_TERMINAL_DISPOSITIONS = {"consumed", "rejected", "merged", "promoted", "superseded"}
_OPERATIONAL_STATUSES = {"received", "stale", "planned", "applied", "failed", "indeterminate"}


class Phase7Error(RuntimeError):
    """Base class for expected fail-closed Phase 7 errors."""


class BatchValidationError(Phase7Error):
    """The immutable Phase 6 batch is structurally invalid or mismatched."""


class ProcessingStateError(Phase7Error):
    """Operational state is corrupt, incompatible, or mismatched."""


class IntakeError(Phase7Error):
    """A Curator intake artifact is invalid or cannot be created safely."""


class PlanError(Phase7Error):
    """A semantic Curator proposal or recorded plan is invalid or stale."""


class AuthorizationError(Phase7Error):
    """Apply authority is missing or does not satisfy the plan."""


@dataclass(frozen=True)
class ValidatedEvent:
    event_id: str
    delta: Mapping[str, Any]


@dataclass(frozen=True)
class ValidatedBatch:
    batch_id: str
    batch: Mapping[str, Any]
    events: tuple[ValidatedEvent, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_json(path: Path, error_type: type[Phase7Error], label: str) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_json_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise error_type(f"{label} is unreadable or corrupt: {path}") from exc


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_exact_keys(
    value: Any, expected: set[str], error_type: type[Phase7Error], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise error_type(f"{label} fields do not match schema")
    return value


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _valid_phase6_id(value: Any) -> bool:
    return isinstance(value, str) and _PHASE6_ID_RE.fullmatch(value) is not None


def _valid_artifact_reference(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(("/", "\\")) or "\\" in value or re.match(r"^[A-Za-z]:", value):
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


@contextmanager
def _exclusive_state_lock(state_path: Path) -> Iterator[None]:
    """Fail closed when another local Phase 7 process owns this state path.

    A crash deliberately leaves the lock behind. An operator must verify that no
    Phase 7 process still owns it before removing that one explicit lock file.
    """

    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(state_path.name + ".phase7.lock")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ProcessingStateError(
            f"Phase 7 state is locked by another or interrupted local invocation: {lock_path}; "
            "verify that no process is active before manually removing this exact lock file"
        ) from exc
    try:
        payload = canonical_json(
            {
                "integration": f"{INTEGRATION_NAME}/{INTEGRATION_VERSION}",
                "pid": os.getpid(),
                "acquired_at": utc_now(),
                "state_path": str(state_path.resolve()),
            }
        ) + "\n"
        os.write(descriptor, payload.encode("utf-8"))
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _stable_phase6_batch(batch: Mapping[str, Any]) -> dict[str, Any]:
    stable = json.loads(json.dumps(batch))
    stable.pop("generated_at", None)
    for delta in stable.get("deltas", []):
        generated = delta.get("generated")
        if isinstance(generated, dict):
            generated.pop("at", None)
    return stable


def derive_batch_id(batch: Mapping[str, Any]) -> str:
    return f"phase7-batch:{sha256_json(_stable_phase6_batch(batch))}"


def derive_event_id(batch: Mapping[str, Any], delta: Mapping[str, Any]) -> str:
    material = {
        "identity_contract": "phase7-delta-event-v1",
        "phase6_adapter": batch["adapter"],
        "phase6_delta_schema_version": batch["schema_version"],
        "source_store": batch["source_store"],
        "checkpoint_lineage": {
            "previous_id": batch["checkpoint"]["previous_id"],
            "current_id": batch["checkpoint"]["current_id"],
        },
        "transition": {
            "change": delta["change"],
            "permalink": delta["permalink"],
            "previous_sha256": delta["previous_sha256"],
            "current_sha256": delta["current_sha256"],
        },
    }
    return f"phase7-event:{sha256_json(material)}"


def derive_plan_id(plan_without_identity: Mapping[str, Any]) -> str:
    stable = json.loads(json.dumps(plan_without_identity))
    stable.pop("generated_at", None)
    return f"phase7-plan:{sha256_json(stable)}"


def derive_disposition_id(event_id: str, plan_id: str, disposition: str) -> str:
    material = {
        "identity_contract": "phase7-disposition-v1",
        "event_id": event_id,
        "plan_id": plan_id,
        "disposition": disposition,
    }
    return f"phase7-disposition:{sha256_json(material)}"


def validate_phase6_batch(
    batch: Any,
    *,
    expected_store_id: str,
    expected_harness: str,
    expected_default_intent: str,
    expected_previous_checkpoint_id: str | None,
) -> ValidatedBatch:
    root = _require_exact_keys(
        batch,
        {
            "schema",
            "schema_version",
            "adapter",
            "source_store",
            "generated_at",
            "checkpoint",
            "summary",
            "deltas",
        },
        BatchValidationError,
        "batch root",
    )
    if root["schema"] != PHASE6_DELTA_SCHEMA or root["schema_version"] != PHASE6_DELTA_SCHEMA_VERSION:
        raise BatchValidationError("unsupported Phase 6 delta schema/version")
    adapter = _require_exact_keys(
        root["adapter"], {"name", "version"}, BatchValidationError, "adapter"
    )
    if adapter != {"name": PHASE6_ADAPTER_NAME, "version": PHASE6_ADAPTER_VERSION}:
        raise BatchValidationError("unsupported Phase 6 adapter identity/version")
    source_store = _require_exact_keys(
        root["source_store"],
        {"id", "harness", "default_intent"},
        BatchValidationError,
        "source_store",
    )
    expected_store = {
        "id": expected_store_id,
        "harness": expected_harness,
        "default_intent": expected_default_intent,
    }
    if source_store != expected_store:
        raise BatchValidationError("source-store mismatch")
    if expected_default_intent not in {"explicit", "implicit"}:
        raise BatchValidationError("expected default intent is invalid")
    if not isinstance(root["generated_at"], str) or not root["generated_at"]:
        raise BatchValidationError("batch generated_at is invalid")

    checkpoint = _require_exact_keys(
        root["checkpoint"],
        {"previous_id", "current_id", "initial_discovery"},
        BatchValidationError,
        "checkpoint lineage",
    )
    previous_id = checkpoint["previous_id"]
    if previous_id is not None and not _valid_phase6_id(previous_id):
        raise BatchValidationError("previous checkpoint identity is invalid")
    if not _valid_phase6_id(checkpoint["current_id"]):
        raise BatchValidationError("current checkpoint identity is invalid")
    if not isinstance(checkpoint["initial_discovery"], bool):
        raise BatchValidationError("initial_discovery is invalid")
    if checkpoint["initial_discovery"] != (previous_id is None):
        raise BatchValidationError("checkpoint initial-discovery lineage is inconsistent")
    if previous_id != expected_previous_checkpoint_id:
        raise BatchValidationError("checkpoint-lineage mismatch")

    summary = _require_exact_keys(
        root["summary"],
        {"added", "changed", "deleted", "unchanged"},
        BatchValidationError,
        "summary",
    )
    if any(not isinstance(summary[key], int) or summary[key] < 0 for key in summary):
        raise BatchValidationError("summary counts are invalid")
    deltas = root["deltas"]
    if not isinstance(deltas, list):
        raise BatchValidationError("deltas must be an array")

    counts = {"added": 0, "changed": 0, "deleted": 0}
    events: list[ValidatedEvent] = []
    seen_ids: set[str] = set()
    seen_permalinks: set[str] = set()
    for index, delta in enumerate(deltas):
        _validate_delta(delta, checkpoint["current_id"], index)
        if delta["harness"] != expected_harness:
            raise BatchValidationError(f"delta {index} harness does not match source store")
        event_id = derive_event_id(root, delta)
        if event_id in seen_ids or delta["permalink"] in seen_permalinks:
            raise BatchValidationError("duplicate delta event identity/permalink inside batch")
        seen_ids.add(event_id)
        seen_permalinks.add(delta["permalink"])
        counts[delta["change"]] += 1
        events.append(ValidatedEvent(event_id, delta))
    if any(summary[key] != counts[key] for key in counts):
        raise BatchValidationError("summary does not match actionable delta records")
    if len(deltas) != summary["added"] + summary["changed"] + summary["deleted"]:
        raise BatchValidationError("unchanged records must not appear as actionable deltas")
    return ValidatedBatch(derive_batch_id(root), root, tuple(events))


def _validate_delta(delta: Any, checkpoint_id: str, index: int) -> None:
    required = {
        "change",
        "permalink",
        "previous_sha256",
        "current_sha256",
        "content_sha256",
        "source_reference",
        "previous_source_reference",
        "adapter_version",
        "checkpoint_id",
        "harness",
        "intent",
        "entry_mode",
        "authority",
        "orca_state",
        "generated",
        "sources",
        "provenance",
    }
    if not isinstance(delta, dict) or not required.issubset(delta):
        raise BatchValidationError(f"delta {index} is malformed")
    change = delta["change"]
    if change not in {"added", "changed", "deleted"}:
        raise BatchValidationError(f"delta {index} change kind is invalid")
    permalink = delta["permalink"]
    if not isinstance(permalink, str) or not permalink or permalink != permalink.strip():
        raise BatchValidationError(f"delta {index} permalink is invalid")
    if delta["adapter_version"] != PHASE6_ADAPTER_VERSION:
        raise BatchValidationError(f"delta {index} adapter version is unsupported")
    if delta["checkpoint_id"] != checkpoint_id:
        raise BatchValidationError(f"delta {index} checkpoint identity is inconsistent")
    if not isinstance(delta["harness"], str) or not delta["harness"]:
        raise BatchValidationError(f"delta {index} harness is invalid")
    if delta["intent"] not in {"explicit", "implicit"}:
        raise BatchValidationError(f"delta {index} intent is invalid")
    if delta["entry_mode"] not in {
        "explicit",
        "implicit",
        "conversational",
        "source",
        "reflection",
    }:
        raise BatchValidationError(f"delta {index} entry_mode is invalid")
    if delta["authority"] != "candidate" or delta["orca_state"] != "new":
        raise BatchValidationError(f"delta {index} candidate authority/state is invalid")
    if not _valid_hash(delta["content_sha256"]):
        raise BatchValidationError(f"delta {index} content hash is invalid")
    generated = delta["generated"]
    if not isinstance(generated, dict) or not isinstance(generated.get("by"), str) or not isinstance(generated.get("at"), str):
        raise BatchValidationError(f"delta {index} generation provenance is invalid")
    sources = delta["sources"]
    if not isinstance(sources, list) or not sources or any(
        not isinstance(item, dict) or not isinstance(item.get("resource"), str) or not item["resource"]
        for item in sources
    ):
        raise BatchValidationError(f"delta {index} source references are invalid")
    provenance = delta["provenance"]
    if not isinstance(provenance, dict) or any(
        not isinstance(key, str) or not key or not isinstance(value, str) or not value
        for key, value in provenance.items()
    ):
        raise BatchValidationError(f"delta {index} provenance is invalid")

    previous_hash = delta["previous_sha256"]
    current_hash = delta["current_sha256"]
    source_reference = delta["source_reference"]
    previous_source_reference = delta["previous_source_reference"]
    if change == "added":
        valid = (
            previous_hash is None
            and _valid_hash(current_hash)
            and current_hash == delta["content_sha256"]
            and isinstance(source_reference, str)
            and bool(source_reference)
            and previous_source_reference is None
            and isinstance(delta.get("content"), str)
            and content_sha256(delta["content"]) == current_hash
        )
    elif change == "changed":
        valid = (
            _valid_hash(previous_hash)
            and _valid_hash(current_hash)
            and previous_hash != current_hash
            and current_hash == delta["content_sha256"]
            and isinstance(source_reference, str)
            and bool(source_reference)
            and isinstance(previous_source_reference, str)
            and bool(previous_source_reference)
            and isinstance(delta.get("content"), str)
            and content_sha256(delta["content"]) == current_hash
        )
    else:
        valid = (
            _valid_hash(previous_hash)
            and current_hash is None
            and previous_hash == delta["content_sha256"]
            and source_reference is None
            and isinstance(previous_source_reference, str)
            and bool(previous_source_reference)
            and "content" not in delta
            and delta.get("semantics")
            == "source-candidate-removed; no canonical deletion or truth judgment"
        )
    if not valid:
        raise BatchValidationError(f"delta {index} {change} field semantics are invalid")


def _empty_state(source_store: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "schema_version": STATE_SCHEMA_VERSION,
        "integration": {"name": INTEGRATION_NAME, "version": INTEGRATION_VERSION},
        "source_store": dict(source_store),
        "events": {},
    }


def load_processing_state(path: Path, source_store: Mapping[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return _empty_state(source_store)
    state = _strict_json(path, ProcessingStateError, "processing state")
    root = _require_exact_keys(
        state,
        {"schema", "schema_version", "integration", "source_store", "events"},
        ProcessingStateError,
        "processing state",
    )
    if root["schema"] != STATE_SCHEMA or root["schema_version"] != STATE_SCHEMA_VERSION:
        raise ProcessingStateError("processing-state schema/version is unsupported; restore a valid state file or rebuild it from preserved intake, plan, and disposition evidence into a separately reviewed path")
    if root["integration"] != {"name": INTEGRATION_NAME, "version": INTEGRATION_VERSION}:
        raise ProcessingStateError("processing-state integration version is unsupported")
    if root["source_store"] != dict(source_store):
        raise ProcessingStateError("processing-state source-store mismatch")
    if not isinstance(root["events"], dict):
        raise ProcessingStateError("processing-state events must be an object")
    for event_id, event in root["events"].items():
        if not _EVENT_ID_RE.fullmatch(event_id) or not isinstance(event, dict):
            raise ProcessingStateError("processing-state event identity is invalid")
        required = {
            "event_id",
            "batch_id",
            "permalink",
            "change",
            "record_sha256",
            "status",
            "attempt_references",
            "intake_reference",
            "plan_id",
            "plan_reference",
            "disposition_id",
            "disposition_reference",
            "canonical_effect",
        }
        if set(event) != required or event["event_id"] != event_id:
            raise ProcessingStateError(f"processing-state record is malformed for {event_id}")
        if not _BATCH_ID_RE.fullmatch(event["batch_id"]):
            raise ProcessingStateError(f"processing-state batch identity is invalid for {event_id}")
        if not isinstance(event["permalink"], str) or not event["permalink"]:
            raise ProcessingStateError(f"processing-state permalink is invalid for {event_id}")
        if event["change"] not in {"added", "changed", "deleted"}:
            raise ProcessingStateError(f"processing-state change kind is invalid for {event_id}")
        if event["record_sha256"] != _state_record_sha256(event):
            raise ProcessingStateError(f"processing-state identity binding is invalid for {event_id}")
        if event["status"] not in _OPERATIONAL_STATUSES:
            raise ProcessingStateError(f"processing-state status is invalid for {event_id}")
        if not isinstance(event["attempt_references"], list) or any(
            not _valid_artifact_reference(item) for item in event["attempt_references"]
        ):
            raise ProcessingStateError(f"processing-state attempts are invalid for {event_id}")
        for key in ("intake_reference", "plan_reference", "disposition_reference"):
            if event[key] is not None and not _valid_artifact_reference(event[key]):
                raise ProcessingStateError(f"processing-state {key} is invalid for {event_id}")
        if event["plan_id"] is not None and not _PLAN_ID_RE.fullmatch(event["plan_id"]):
            raise ProcessingStateError(f"processing-state plan identity is invalid for {event_id}")
        if event["disposition_id"] is not None and not _DISPOSITION_ID_RE.fullmatch(event["disposition_id"]):
            raise ProcessingStateError(f"processing-state disposition identity is invalid for {event_id}")
        if event["canonical_effect"] is not None and not isinstance(event["canonical_effect"], dict):
            raise ProcessingStateError(f"processing-state canonical effect is invalid for {event_id}")
        if (event["plan_id"] is None) != (event["plan_reference"] is None):
            raise ProcessingStateError(f"processing-state plan lineage is incoherent for {event_id}")
        if (event["disposition_id"] is None) != (event["disposition_reference"] is None):
            raise ProcessingStateError(f"processing-state disposition lineage is incoherent for {event_id}")
        if event["disposition_id"] is not None and event["plan_id"] is None:
            raise ProcessingStateError(f"processing-state disposition lacks a plan for {event_id}")
        if event["status"] == "received" and (
            event["intake_reference"] is None
            or event["plan_id"] is not None
            or event["disposition_id"] is not None
            or event["canonical_effect"] is not None
        ):
            raise ProcessingStateError(f"received processing-state record is incoherent for {event_id}")
        if event["status"] == "planned" and (
            event["intake_reference"] is None
            or event["plan_id"] is None
            or event["disposition_id"] is not None
            or event["canonical_effect"] is not None
        ):
            raise ProcessingStateError(f"planned processing-state record is incoherent for {event_id}")
        if event["status"] == "applied" and (
            event["plan_id"] is None
            or event["disposition_id"] is None
            or event["disposition_reference"] is None
            or event["canonical_effect"] is None
        ):
            raise ProcessingStateError(f"applied processing-state record is incomplete for {event_id}")
        if event["status"] == "stale" and not event["attempt_references"]:
            raise ProcessingStateError(f"stale processing-state record lacks freshness evidence for {event_id}")
        if event["status"] == "indeterminate" and event["plan_id"] is None:
            raise ProcessingStateError(f"indeterminate processing-state record lacks a plan for {event_id}")
    return state


def _new_event_state(event: ValidatedEvent, batch_id: str) -> dict[str, Any]:
    record = {
        "event_id": event.event_id,
        "batch_id": batch_id,
        "permalink": event.delta["permalink"],
        "change": event.delta["change"],
        "record_sha256": "",
        "status": "received",
        "attempt_references": [],
        "intake_reference": None,
        "plan_id": None,
        "plan_reference": None,
        "disposition_id": None,
        "disposition_reference": None,
        "canonical_effect": None,
    }
    record["record_sha256"] = _state_record_sha256(record)
    return record


def _state_record_sha256(record: Mapping[str, Any]) -> str:
    return sha256_json(
        {
            "identity_contract": "phase7-processing-state-event-v1",
            "event_id": record.get("event_id"),
            "batch_id": record.get("batch_id"),
            "permalink": record.get("permalink"),
            "change": record.get("change"),
        }
    )


def _freshness(delta: Mapping[str, Any], entries: Mapping[str, Any], checked_at: str) -> dict[str, Any]:
    current = entries.get(delta["permalink"])
    if delta["change"] == "deleted":
        fresh = current is None
        expected_state = "absent"
        observed_state = "absent" if current is None else "present"
        expected_revision = None
    else:
        fresh = current is not None and current.content_sha256 == delta["current_sha256"]
        expected_state = "present"
        observed_state = "absent" if current is None else "present"
        expected_revision = delta["current_sha256"]
    observed_revision = current.content_sha256 if current is not None else None
    if fresh:
        reason = "source precondition matches immutable Phase 6 delta evidence"
    elif delta["change"] == "deleted" and current is not None:
        reason = "deleted permalink reappeared; fresh Phase 6 delta required"
    elif current is None:
        reason = "expected current candidate revision is unavailable; fresh Phase 6 delta required"
    else:
        reason = "source revision changed after batch emission; fresh Phase 6 delta required"
    return {
        "status": "fresh" if fresh else "stale",
        "expected_state": expected_state,
        "observed_state": observed_state,
        "expected_revision": expected_revision,
        "observed_revision": observed_revision,
        "reason": reason,
        "checked_at": checked_at,
        "checker": f"{INTEGRATION_NAME}/{INTEGRATION_VERSION}+phase6-scanner/{PHASE6_ADAPTER_VERSION}",
    }


def _attempt_id(event_id: str, freshness: Mapping[str, Any]) -> str:
    material = {
        "event_id": event_id,
        "status": freshness["status"],
        "observed_state": freshness["observed_state"],
        "observed_revision": freshness["observed_revision"],
    }
    return f"phase7-attempt:{sha256_json(material)}"


def _artifact_name(identity: str) -> str:
    return identity.split(":", 1)[1] + ".json"


def _prior_dispositions(state: Mapping[str, Any], permalink: str, event_id: str) -> list[dict[str, Any]]:
    refs = []
    for prior_id, record in sorted(state["events"].items()):
        if prior_id == event_id or record["permalink"] != permalink or not record["disposition_id"]:
            continue
        refs.append(
            {
                "event_id": prior_id,
                "plan_id": record["plan_id"],
                "disposition_id": record["disposition_id"],
                "disposition_reference": record["disposition_reference"],
            }
        )
    return refs


def _build_intake(
    validated: ValidatedBatch,
    event: ValidatedEvent,
    freshness: Mapping[str, Any],
    state: Mapping[str, Any],
) -> dict[str, Any]:
    delta = event.delta
    intake_id = f"phase7-intake:{sha256_json({'event_id': event.event_id})}"
    return {
        "schema": INTAKE_SCHEMA,
        "schema_version": INTAKE_SCHEMA_VERSION,
        "integration": {"name": INTEGRATION_NAME, "version": INTEGRATION_VERSION},
        "intake_id": intake_id,
        "event_id": event.event_id,
        "batch_id": validated.batch_id,
        "transport_state": "received",
        "phase6": {
            "adapter": validated.batch["adapter"],
            "delta_schema": validated.batch["schema"],
            "delta_schema_version": validated.batch["schema_version"],
            "source_store": validated.batch["source_store"],
            "checkpoint": validated.batch["checkpoint"],
        },
        "candidate": {
            "identity": delta["permalink"],
            "change": delta["change"],
            "previous_revision": delta["previous_sha256"],
            "current_revision": delta["current_sha256"],
            "content": delta.get("content"),
            "source_reference": delta["source_reference"],
            "previous_source_reference": delta["previous_source_reference"],
            "sources": delta["sources"],
            "provenance": delta["provenance"],
            "intent": delta["intent"],
            "entry_mode": delta["entry_mode"],
            "authority": delta["authority"],
            "orca_state": delta["orca_state"],
            "removal_semantics": delta.get("semantics"),
        },
        "prior_dispositions": _prior_dispositions(state, delta["permalink"], event.event_id),
        "freshness": dict(freshness),
        "curator_contract": {
            "workflow": "inspect -> plan -> apply",
            "skill": "orca-curator/0.2",
            "semantic_judgment": "required",
            "automatic_apply": False,
            "canonical_deletion_from_source_removal": False,
        },
    }


def process_batch(
    *,
    batch_path: Path,
    source_root: Path,
    state_path: Path,
    artifact_root: Path,
    store_id: str,
    harness: str,
    default_intent: str,
    expected_previous_checkpoint_id: str | None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    with _exclusive_state_lock(state_path):
        return _process_batch_locked(
            batch_path=batch_path,
            source_root=source_root,
            state_path=state_path,
            artifact_root=artifact_root,
            store_id=store_id,
            harness=harness,
            default_intent=default_intent,
            expected_previous_checkpoint_id=expected_previous_checkpoint_id,
            checked_at=checked_at,
        )


def _process_batch_locked(
    *,
    batch_path: Path,
    source_root: Path,
    state_path: Path,
    artifact_root: Path,
    store_id: str,
    harness: str,
    default_intent: str,
    expected_previous_checkpoint_id: str | None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    batch = _strict_json(batch_path, BatchValidationError, "Phase 6 delta batch")
    validated = validate_phase6_batch(
        batch,
        expected_store_id=store_id,
        expected_harness=harness,
        expected_default_intent=default_intent,
        expected_previous_checkpoint_id=expected_previous_checkpoint_id,
    )
    state = load_processing_state(state_path, validated.batch["source_store"])
    try:
        snapshot = scan_store(source_root)
    except Phase6ScanError as exc:
        raise IntakeError(f"current source store is not a complete valid Phase 6 snapshot: {exc}") from exc

    now = checked_at or utc_now()
    intake_dir = artifact_root / "intakes"
    attempts_dir = artifact_root / "attempts"
    results: list[dict[str, Any]] = []
    for event in validated.events:
        existing = state["events"].get(event.event_id)
        if existing and (
            existing["batch_id"] != validated.batch_id
            or existing["permalink"] != event.delta["permalink"]
            or existing["change"] != event.delta["change"]
        ):
            raise ProcessingStateError(
                f"processing-state event metadata conflicts with batch evidence for {event.event_id}"
            )
        if existing and existing["status"] in {"received", "planned", "applied", "failed", "indeterminate"}:
            visible_status = (
                existing["status"]
                if existing["status"] in {"failed", "indeterminate"}
                else "already_processed"
            )
            results.append(
                {
                    "event_id": event.event_id,
                    "permalink": event.delta["permalink"],
                    "status": visible_status,
                    "operational_status": existing["status"],
                    "reference": existing["disposition_reference"] or existing["plan_reference"] or existing["intake_reference"],
                }
            )
            continue

        record = existing or _new_event_state(event, validated.batch_id)
        freshness = _freshness(event.delta, snapshot.entries, now)
        attempt_id = _attempt_id(event.event_id, freshness)
        attempt = {
            "schema": "orca-phase7-freshness-attempt",
            "schema_version": 1,
            "integration": {"name": INTEGRATION_NAME, "version": INTEGRATION_VERSION},
            "attempt_id": attempt_id,
            "event_id": event.event_id,
            "freshness": freshness,
        }
        attempt_path = attempts_dir / event.event_id.split(":", 1)[1] / _artifact_name(attempt_id)
        _materialize_json(attempt_path, attempt, volatile_paths=(("freshness", "checked_at"),))
        attempt_ref = attempt_path.relative_to(artifact_root).as_posix()
        if attempt_ref not in record["attempt_references"]:
            record["attempt_references"].append(attempt_ref)

        if freshness["status"] == "stale":
            record["status"] = "stale"
            state["events"][event.event_id] = record
            _atomic_write_json(state_path, state)
            results.append(
                {
                    "event_id": event.event_id,
                    "permalink": event.delta["permalink"],
                    "status": "stale",
                    "freshness": freshness,
                    "reference": attempt_ref,
                }
            )
            continue

        if record["status"] == "stale" and record["plan_id"] is not None:
            state["events"][event.event_id] = record
            _atomic_write_json(state_path, state)
            results.append(
                {
                    "event_id": event.event_id,
                    "permalink": event.delta["permalink"],
                    "status": "stale_plan_ready_for_replan",
                    "operational_status": "stale",
                    "freshness": freshness,
                    "reference": record["plan_reference"],
                }
            )
            continue

        intake = _build_intake(validated, event, freshness, state)
        intake_path = intake_dir / _artifact_name(event.event_id)
        intake = _materialize_json(
            intake_path, intake, volatile_paths=(("freshness", "checked_at"),)
        )
        record["status"] = "received"
        record["intake_reference"] = intake_path.relative_to(artifact_root).as_posix()
        state["events"][event.event_id] = record
        _atomic_write_json(state_path, state)
        results.append(
            {
                "event_id": event.event_id,
                "permalink": event.delta["permalink"],
                "status": "fresh",
                "reference": record["intake_reference"],
            }
        )

    return {
        "batch_id": validated.batch_id,
        "event_count": len(validated.events),
        "unchanged_suppressed": validated.batch["summary"]["unchanged"],
        "results": results,
    }


def _load_intake(path: Path) -> dict[str, Any]:
    intake = _strict_json(path, IntakeError, "Curator intake")
    required = {
        "schema",
        "schema_version",
        "integration",
        "intake_id",
        "event_id",
        "batch_id",
        "transport_state",
        "phase6",
        "candidate",
        "prior_dispositions",
        "freshness",
        "curator_contract",
    }
    root = _require_exact_keys(intake, required, IntakeError, "Curator intake")
    if root["schema"] != INTAKE_SCHEMA or root["schema_version"] != INTAKE_SCHEMA_VERSION:
        raise IntakeError("Curator intake schema/version is unsupported")
    if root["integration"] != {"name": INTEGRATION_NAME, "version": INTEGRATION_VERSION}:
        raise IntakeError("Curator intake integration version is unsupported")
    if not _EVENT_ID_RE.fullmatch(root["event_id"]):
        raise IntakeError("Curator intake event identity is invalid")
    if not _BATCH_ID_RE.fullmatch(root["batch_id"]):
        raise IntakeError("Curator intake batch identity is invalid")
    if root["transport_state"] != "received":
        raise IntakeError("Curator intake transport state is invalid")
    if root["intake_id"] != f"phase7-intake:{sha256_json({'event_id': root['event_id']})}":
        raise IntakeError("Curator intake identity is invalid")
    phase6 = _require_exact_keys(
        root["phase6"],
        {"adapter", "delta_schema", "delta_schema_version", "source_store", "checkpoint"},
        IntakeError,
        "Curator intake Phase 6 evidence",
    )
    if phase6["adapter"] != {"name": PHASE6_ADAPTER_NAME, "version": PHASE6_ADAPTER_VERSION}:
        raise IntakeError("Curator intake Phase 6 adapter identity is invalid")
    if phase6["delta_schema"] != PHASE6_DELTA_SCHEMA or phase6["delta_schema_version"] != PHASE6_DELTA_SCHEMA_VERSION:
        raise IntakeError("Curator intake Phase 6 schema/version is invalid")
    source_store = _require_exact_keys(
        phase6["source_store"], {"id", "harness", "default_intent"}, IntakeError, "Curator intake source store"
    )
    if (
        not isinstance(source_store["id"], str)
        or not source_store["id"]
        or not isinstance(source_store["harness"], str)
        or not source_store["harness"]
        or source_store["default_intent"] not in {"explicit", "implicit"}
    ):
        raise IntakeError("Curator intake source store is invalid")
    checkpoint = _require_exact_keys(
        phase6["checkpoint"], {"previous_id", "current_id", "initial_discovery"}, IntakeError, "Curator intake checkpoint"
    )
    if (
        (checkpoint["previous_id"] is not None and not _valid_phase6_id(checkpoint["previous_id"]))
        or not _valid_phase6_id(checkpoint["current_id"])
        or not isinstance(checkpoint["initial_discovery"], bool)
        or checkpoint["initial_discovery"] != (checkpoint["previous_id"] is None)
    ):
        raise IntakeError("Curator intake checkpoint lineage is invalid")
    candidate = _require_exact_keys(
        root["candidate"],
        {
            "identity", "change", "previous_revision", "current_revision", "content",
            "source_reference", "previous_source_reference", "sources", "provenance",
            "intent", "entry_mode", "authority", "orca_state", "removal_semantics",
        },
        IntakeError,
        "Curator intake candidate",
    )
    if (
        not isinstance(candidate["identity"], str)
        or not candidate["identity"]
        or candidate["identity"] != candidate["identity"].strip()
        or candidate["change"] not in {"added", "changed", "deleted"}
        or candidate["intent"] not in {"explicit", "implicit"}
        or candidate["entry_mode"] not in {"explicit", "implicit", "conversational", "source", "reflection"}
        or candidate["authority"] != "candidate"
        or candidate["orca_state"] != "new"
        or not isinstance(candidate["sources"], list)
        or not candidate["sources"]
        or not isinstance(candidate["provenance"], dict)
    ):
        raise IntakeError("Curator intake candidate identity/provenance is invalid")
    previous = candidate["previous_revision"]
    current = candidate["current_revision"]
    if candidate["change"] == "added":
        candidate_valid = (
            previous is None
            and _valid_hash(current)
            and isinstance(candidate["content"], str)
            and content_sha256(candidate["content"]) == current
            and isinstance(candidate["source_reference"], str)
            and bool(candidate["source_reference"])
            and candidate["previous_source_reference"] is None
            and candidate["removal_semantics"] is None
        )
    elif candidate["change"] == "changed":
        candidate_valid = (
            _valid_hash(previous)
            and _valid_hash(current)
            and previous != current
            and isinstance(candidate["content"], str)
            and content_sha256(candidate["content"]) == current
            and isinstance(candidate["source_reference"], str)
            and bool(candidate["source_reference"])
            and isinstance(candidate["previous_source_reference"], str)
            and bool(candidate["previous_source_reference"])
            and candidate["removal_semantics"] is None
        )
    else:
        candidate_valid = (
            _valid_hash(previous)
            and current is None
            and candidate["content"] is None
            and candidate["source_reference"] is None
            and isinstance(candidate["previous_source_reference"], str)
            and bool(candidate["previous_source_reference"])
            and candidate["removal_semantics"] == "source-candidate-removed; no canonical deletion or truth judgment"
        )
    if not candidate_valid:
        raise IntakeError("Curator intake change-kind semantics are invalid")
    expected_event = derive_event_id(
        {
            "adapter": phase6["adapter"],
            "schema_version": phase6["delta_schema_version"],
            "source_store": phase6["source_store"],
            "checkpoint": phase6["checkpoint"],
        },
        {
            "change": candidate["change"],
            "permalink": candidate["identity"],
            "previous_sha256": previous,
            "current_sha256": current,
        },
    )
    if expected_event != root["event_id"]:
        raise IntakeError("Curator intake event identity does not match its Phase 6 evidence")
    freshness = _require_exact_keys(
        root["freshness"],
        {"status", "expected_state", "observed_state", "expected_revision", "observed_revision", "reason", "checked_at", "checker"},
        IntakeError,
        "Curator intake freshness",
    )
    expected_state = "absent" if candidate["change"] == "deleted" else "present"
    if (
        freshness["status"] != "fresh"
        or freshness["expected_state"] != expected_state
        or freshness["observed_state"] != expected_state
        or freshness["expected_revision"] != current
        or freshness["observed_revision"] != current
        or not isinstance(freshness["reason"], str)
        or not isinstance(freshness["checked_at"], str)
        or not isinstance(freshness["checker"], str)
    ):
        raise IntakeError("stale intake cannot be planned")
    if not isinstance(root["prior_dispositions"], list):
        raise IntakeError("Curator intake prior dispositions are invalid")
    for prior in root["prior_dispositions"]:
        if (
            not isinstance(prior, dict)
            or set(prior) != {"event_id", "plan_id", "disposition_id", "disposition_reference"}
            or not _EVENT_ID_RE.fullmatch(prior["event_id"])
            or not _PLAN_ID_RE.fullmatch(prior["plan_id"])
            or not _DISPOSITION_ID_RE.fullmatch(prior["disposition_id"])
            or not _valid_artifact_reference(prior["disposition_reference"])
        ):
            raise IntakeError("Curator intake prior disposition lineage is invalid")
    if root["curator_contract"] != {
        "workflow": "inspect -> plan -> apply",
        "skill": "orca-curator/0.2",
        "semantic_judgment": "required",
        "automatic_apply": False,
        "canonical_deletion_from_source_removal": False,
    }:
        raise IntakeError("Curator intake governance contract is invalid")
    return dict(root)


def _artifact_reference(path: Path, artifact_root: Path, error_type: type[Phase7Error], label: str) -> str:
    try:
        return path.resolve().relative_to(artifact_root.resolve()).as_posix()
    except ValueError as exc:
        raise error_type(f"{label} is outside the configured artifact root") from exc


def _resolve_target(canonical_root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise PlanError("canonical target must be a non-empty relative path")
    root = canonical_root.resolve()
    target = (root / Path(relative)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PlanError("canonical target escapes the configured fixture/vault root") from exc
    if target.suffix.casefold() != ".md":
        raise PlanError("canonical target must be a Markdown file")
    return target


def _validate_proposal(proposal: Any, event_id: str) -> dict[str, Any]:
    required = {
        "schema",
        "schema_version",
        "event_id",
        "comparison_class",
        "proposed_disposition",
        "canonical_target",
        "proposed_action",
        "evidence_references",
        "rationale",
        "authority_requirement",
    }
    root = _require_exact_keys(proposal, required, PlanError, "Curator proposal")
    if root["schema"] != PROPOSAL_SCHEMA or root["schema_version"] != PROPOSAL_SCHEMA_VERSION:
        raise PlanError("Curator proposal schema/version is unsupported")
    if root["event_id"] != event_id:
        raise PlanError("Curator proposal event identity mismatch")
    if not isinstance(root["comparison_class"], str) or not root["comparison_class"]:
        raise PlanError("comparison class must be supplied by Curator judgment")
    if root["proposed_disposition"] not in _TERMINAL_DISPOSITIONS:
        raise PlanError("proposed governance disposition is invalid")
    if root["canonical_target"] is not None and not isinstance(root["canonical_target"], str):
        raise PlanError("canonical target is invalid")
    action = root["proposed_action"]
    if not isinstance(action, dict) or action.get("kind") not in {"none", "write_markdown"}:
        raise PlanError("proposed action must be none or write_markdown; deletion is not supported")
    if action["kind"] == "none":
        if set(action) != {"kind"}:
            raise PlanError("none action contains unsupported fields")
    elif set(action) != {"kind", "content"} or not isinstance(action["content"], str):
        raise PlanError("write_markdown action requires exact content")
    if action["kind"] == "write_markdown" and not root["canonical_target"]:
        raise PlanError("write_markdown requires a Curator-selected canonical target")
    if not isinstance(root["evidence_references"], list) or not root["evidence_references"] or any(
        not isinstance(item, str) or not item for item in root["evidence_references"]
    ):
        raise PlanError("Curator proposal requires evidence references")
    if not isinstance(root["rationale"], str) or not root["rationale"]:
        raise PlanError("Curator proposal requires rationale")
    if root["authority_requirement"] not in {"curator", "human"}:
        raise PlanError("authority requirement must be curator or human")
    return dict(root)


def _source_precondition(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "permalink": candidate["identity"],
        "expected_state": "absent" if candidate["change"] == "deleted" else "present",
        "expected_revision": candidate["current_revision"],
    }


def _current_freshness_for_intake(intake: Mapping[str, Any], source_root: Path, checked_at: str) -> dict[str, Any]:
    candidate = intake["candidate"]
    pseudo_delta = {
        "permalink": candidate["identity"],
        "change": candidate["change"],
        "current_sha256": candidate["current_revision"],
    }
    try:
        snapshot = scan_store(source_root)
    except Phase6ScanError as exc:
        raise PlanError(f"cannot verify source precondition: {exc}") from exc
    return _freshness(pseudo_delta, snapshot.entries, checked_at)


def create_plan(
    *,
    intake_path: Path,
    proposal_path: Path,
    source_root: Path,
    canonical_root: Path,
    state_path: Path,
    artifact_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    with _exclusive_state_lock(state_path):
        return _create_plan_locked(
            intake_path=intake_path,
            proposal_path=proposal_path,
            source_root=source_root,
            canonical_root=canonical_root,
            state_path=state_path,
            artifact_root=artifact_root,
            generated_at=generated_at,
        )


def _create_plan_locked(
    *,
    intake_path: Path,
    proposal_path: Path,
    source_root: Path,
    canonical_root: Path,
    state_path: Path,
    artifact_root: Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    intake = _load_intake(intake_path)
    source_store = intake["phase6"]["source_store"]
    state = load_processing_state(state_path, source_store)
    record = state["events"].get(intake["event_id"])
    intake_reference = _artifact_reference(intake_path, artifact_root, PlanError, "Curator intake")
    if (
        not record
        or record["intake_reference"] != intake_reference
        or record["batch_id"] != intake["batch_id"]
        or record["permalink"] != intake["candidate"]["identity"]
        or record["change"] != intake["candidate"]["change"]
    ):
        raise PlanError("processing state has no matching received intake")
    if record["status"] == "applied":
        existing_plan = _load_plan(artifact_root / record["plan_reference"])
        if existing_plan["event_id"] != intake["event_id"] or existing_plan["plan_id"] != record["plan_id"]:
            raise PlanError("applied processing state does not match its preserved plan")
        _verify_applied_evidence(existing_plan, record, artifact_root, canonical_root)
        return existing_plan
    if record["status"] in {"failed", "indeterminate"}:
        raise PlanError(
            f"event has a {record['status']} operational outcome; recover it manually before replanning"
        )
    now = generated_at or utc_now()
    freshness = _current_freshness_for_intake(intake, source_root, now)
    if freshness["status"] != "fresh":
        record["status"] = "stale"
        _atomic_write_json(state_path, state)
        raise PlanError(f"source precondition is stale: {freshness['reason']}")
    proposal = _validate_proposal(
        _strict_json(proposal_path, PlanError, "Curator proposal"), intake["event_id"]
    )

    target_relative = proposal["canonical_target"]
    target = _resolve_target(canonical_root, target_relative) if target_relative else None
    expected_hash = file_sha256(target) if target is not None and target.exists() else None
    new_hash = (
        content_sha256(proposal["proposed_action"]["content"])
        if proposal["proposed_action"]["kind"] == "write_markdown"
        else None
    )
    plan_body = {
        "schema": PLAN_SCHEMA,
        "schema_version": PLAN_SCHEMA_VERSION,
        "integration": {"name": INTEGRATION_NAME, "version": INTEGRATION_VERSION},
        "generated_at": now,
        "event_id": intake["event_id"],
        "intake_id": intake["intake_id"],
        "intake_reference": intake_reference,
        "candidate_revision": {
            "permalink": intake["candidate"]["identity"],
            "previous_sha256": intake["candidate"]["previous_revision"],
            "current_sha256": intake["candidate"]["current_revision"],
            "change": intake["candidate"]["change"],
        },
        "comparison_class": proposal["comparison_class"],
        "proposed_disposition": proposal["proposed_disposition"],
        "canonical_target": target_relative,
        "proposed_action": proposal["proposed_action"],
        "evidence_references": proposal["evidence_references"],
        "rationale": proposal["rationale"],
        "authority_requirement": proposal["authority_requirement"],
        "source_precondition": _source_precondition(intake["candidate"]),
        "canonical_precondition": {
            "expected_sha256": expected_hash,
            "planned_sha256": new_hash,
        },
        "curator": {"skill": "orca-curator/0.2", "semantic_judgment": "external"},
    }
    plan_id = derive_plan_id(plan_body)
    disposition_id = derive_disposition_id(
        intake["event_id"], plan_id, proposal["proposed_disposition"]
    )
    plan = {**plan_body, "plan_id": plan_id, "disposition_id": disposition_id}
    plan_path = artifact_root / "plans" / _artifact_name(plan_id)
    if record["plan_id"] and record["plan_id"] != plan_id:
        raise PlanError("event already has a different recorded plan; preserve it and explicitly re-inspect/replan outside this v0.1 path")
    plan = _materialize_json(plan_path, plan, volatile_paths=(("generated_at",),))
    record["status"] = "planned"
    record["plan_id"] = plan_id
    record["plan_reference"] = plan_path.relative_to(artifact_root).as_posix()
    state["events"][intake["event_id"]] = record
    _atomic_write_json(state_path, state)
    return plan


def _load_plan(path: Path) -> dict[str, Any]:
    plan = _strict_json(path, PlanError, "Curator plan")
    required = {
        "schema",
        "schema_version",
        "integration",
        "generated_at",
        "event_id",
        "intake_id",
        "intake_reference",
        "candidate_revision",
        "comparison_class",
        "proposed_disposition",
        "canonical_target",
        "proposed_action",
        "evidence_references",
        "rationale",
        "authority_requirement",
        "source_precondition",
        "canonical_precondition",
        "curator",
        "plan_id",
        "disposition_id",
    }
    root = _require_exact_keys(plan, required, PlanError, "Curator plan")
    if root["schema"] != PLAN_SCHEMA or root["schema_version"] != PLAN_SCHEMA_VERSION:
        raise PlanError("Curator plan schema/version is unsupported")
    if not _EVENT_ID_RE.fullmatch(root["event_id"]):
        raise PlanError("Curator plan event identity is invalid")
    plan_body = {key: value for key, value in root.items() if key not in {"plan_id", "disposition_id"}}
    if not _PLAN_ID_RE.fullmatch(root["plan_id"]) or derive_plan_id(plan_body) != root["plan_id"]:
        raise PlanError("Curator plan identity is invalid")
    expected_disposition_id = derive_disposition_id(
        root["event_id"], root["plan_id"], root["proposed_disposition"]
    )
    if not _DISPOSITION_ID_RE.fullmatch(root["disposition_id"]) or root["disposition_id"] != expected_disposition_id:
        raise PlanError("Curator disposition identity is invalid")
    _validate_proposal(
        {
            "schema": PROPOSAL_SCHEMA,
            "schema_version": PROPOSAL_SCHEMA_VERSION,
            "event_id": root["event_id"],
            "comparison_class": root["comparison_class"],
            "proposed_disposition": root["proposed_disposition"],
            "canonical_target": root["canonical_target"],
            "proposed_action": root["proposed_action"],
            "evidence_references": root["evidence_references"],
            "rationale": root["rationale"],
            "authority_requirement": root["authority_requirement"],
        },
        root["event_id"],
    )
    return dict(root)


def _validate_authorization(authorization: Any, plan: Mapping[str, Any]) -> dict[str, Any]:
    required = {"schema", "schema_version", "plan_id", "approved", "actor", "authority", "scope"}
    root = _require_exact_keys(authorization, required, AuthorizationError, "apply authorization")
    if root["schema"] != AUTHORIZATION_SCHEMA or root["schema_version"] != AUTHORIZATION_SCHEMA_VERSION:
        raise AuthorizationError("apply authorization schema/version is unsupported")
    if root["plan_id"] != plan["plan_id"] or root["approved"] is not True:
        raise AuthorizationError("authorization does not approve this exact plan")
    if not isinstance(root["actor"], str) or not root["actor"]:
        raise AuthorizationError("authorization actor is missing")
    if root["authority"] not in {"curator", "human"}:
        raise AuthorizationError("authorization authority is invalid")
    if plan["authority_requirement"] == "human" and root["authority"] != "human":
        raise AuthorizationError("plan requires explicit human authority")
    if root["scope"] != "phase7-fixture-or-explicit-local-plan":
        raise AuthorizationError("authorization scope is invalid")
    return dict(root)


def _disposition_markdown(
    plan: Mapping[str, Any], authorization: Mapping[str, Any], applied_at: str, effect: Mapping[str, Any]
) -> str:
    yaml = {
        "type": "orca-curator-disposition",
        "authority": "candidate-disposition",
        "schema": DISPOSITION_SCHEMA,
        "schema_version": DISPOSITION_SCHEMA_VERSION,
        "disposition_id": plan["disposition_id"],
        "plan_id": plan["plan_id"],
        "delta_event_id": plan["event_id"],
        "candidate_id": plan["candidate_revision"]["permalink"],
        "content_sha256": plan["candidate_revision"]["current_sha256"] or plan["candidate_revision"]["previous_sha256"],
        "orca_state": plan["proposed_disposition"],
        "canonical_target": plan["canonical_target"],
        "curated_by": authorization["actor"],
        "curated_at": applied_at,
        "curator_skill": "orca-curator/0.2",
    }
    lines = ["---"]
    for key, value in yaml.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(
        [
            "---",
            "",
            "# Curator disposition",
            "",
            "## Governance result",
            "",
            f"- Comparison: {plan['comparison_class']}",
            f"- Disposition: {plan['proposed_disposition']}",
            f"- Rationale: {plan['rationale']}",
            "",
            "## Lineage",
            "",
            f"- Intake: {plan['intake_reference']}",
            f"- Delta event: {plan['event_id']}",
            f"- Plan: {plan['plan_id']}",
            f"- Canonical effect: {json.dumps(effect, ensure_ascii=False, sort_keys=True)}",
            "",
            "Cairn source removal is evidence only and never authorizes canonical deletion.",
            "",
        ]
    )
    return "\n".join(lines)


def apply_plan(
    *,
    plan_path: Path,
    authorization_path: Path,
    source_root: Path,
    canonical_root: Path,
    state_path: Path,
    artifact_root: Path,
    applied_at: str | None = None,
    after_canonical_write: Callable[[Path], None] | None = None,
    after_disposition_write: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    with _exclusive_state_lock(state_path):
        return _apply_plan_locked(
            plan_path=plan_path,
            authorization_path=authorization_path,
            source_root=source_root,
            canonical_root=canonical_root,
            state_path=state_path,
            artifact_root=artifact_root,
            applied_at=applied_at,
            after_canonical_write=after_canonical_write,
            after_disposition_write=after_disposition_write,
        )


def _apply_plan_locked(
    *,
    plan_path: Path,
    authorization_path: Path,
    source_root: Path,
    canonical_root: Path,
    state_path: Path,
    artifact_root: Path,
    applied_at: str | None = None,
    after_canonical_write: Callable[[Path], None] | None = None,
    after_disposition_write: Callable[[Path], None] | None = None,
) -> dict[str, Any]:
    plan = _load_plan(plan_path)
    intake_path = artifact_root / plan["intake_reference"]
    intake = _load_intake(intake_path)
    expected_revision = {
        "permalink": intake["candidate"]["identity"],
        "previous_sha256": intake["candidate"]["previous_revision"],
        "current_sha256": intake["candidate"]["current_revision"],
        "change": intake["candidate"]["change"],
    }
    if (
        plan["event_id"] != intake["event_id"]
        or plan["intake_id"] != intake["intake_id"]
        or plan["candidate_revision"] != expected_revision
        or plan["source_precondition"] != _source_precondition(intake["candidate"])
    ):
        raise PlanError("plan lineage/preconditions do not match the immutable intake")
    expected_planned_hash = (
        content_sha256(plan["proposed_action"]["content"])
        if plan["proposed_action"]["kind"] == "write_markdown"
        else None
    )
    if plan["canonical_precondition"].get("planned_sha256") != expected_planned_hash:
        raise PlanError("plan canonical effect hash is inconsistent")
    state = load_processing_state(state_path, intake["phase6"]["source_store"])
    record = state["events"].get(plan["event_id"])
    plan_reference = _artifact_reference(plan_path, artifact_root, PlanError, "Curator plan")
    if (
        not record
        or record["plan_id"] != plan["plan_id"]
        or record["plan_reference"] != plan_reference
        or record["intake_reference"] != plan["intake_reference"]
        or record["batch_id"] != intake["batch_id"]
        or record["permalink"] != intake["candidate"]["identity"]
        or record["change"] != intake["candidate"]["change"]
    ):
        raise PlanError("processing state does not contain this exact plan")
    authorization = _validate_authorization(
        _strict_json(authorization_path, AuthorizationError, "apply authorization"), plan
    )
    if record["status"] == "applied":
        current_effect_matches = _verify_applied_evidence(
            plan, record, artifact_root, canonical_root
        )
        return {
            "status": "already_applied",
            "event_id": plan["event_id"],
            "plan_id": plan["plan_id"],
            "disposition_id": record["disposition_id"],
            "canonical_effect": record["canonical_effect"],
            "canonical_effect_current": current_effect_matches,
        }
    if record["status"] in {"failed", "indeterminate"}:
        raise PlanError(
            f"event has a {record['status']} operational outcome; recover it manually before retrying apply"
        )
    if record["status"] != "planned":
        raise PlanError("plan is not in planned operational state; re-inspect/replan before apply")
    now = applied_at or utc_now()
    freshness = _current_freshness_for_intake(intake, source_root, now)
    if freshness["status"] != "fresh":
        record["status"] = "stale"
        _atomic_write_json(state_path, state)
        raise PlanError(f"source precondition changed; plan is stale: {freshness['reason']}")

    action = plan["proposed_action"]
    target = _resolve_target(canonical_root, plan["canonical_target"]) if plan["canonical_target"] else None
    expected_hash = plan["canonical_precondition"]["expected_sha256"]
    planned_hash = plan["canonical_precondition"]["planned_sha256"]
    current_hash = file_sha256(target) if target is not None and target.exists() else None
    if action["kind"] == "write_markdown":
        if current_hash == planned_hash:
            effect_status = "already_present"
        elif current_hash != expected_hash:
            record["status"] = "stale"
            _atomic_write_json(state_path, state)
            raise PlanError("canonical precondition changed; plan is stale and requires re-inspection/replan")
        else:
            _atomic_write_text(target, action["content"])
            effect_status = "written"
            if file_sha256(target) != planned_hash:
                record["status"] = "indeterminate"
                _atomic_write_json(state_path, state)
                raise PlanError("canonical effect verification failed; outcome is indeterminate")
            if after_canonical_write is not None:
                after_canonical_write(target)
        effect = {
            "kind": "write_markdown",
            "target": plan["canonical_target"],
            "before_sha256": expected_hash,
            "after_sha256": planned_hash,
            "status": effect_status,
        }
    else:
        if target is not None and current_hash != expected_hash:
            record["status"] = "stale"
            _atomic_write_json(state_path, state)
            raise PlanError("canonical comparison target changed; plan is stale and requires re-inspection/replan")
        effect = {"kind": "none", "target": plan["canonical_target"], "status": "no_canonical_mutation"}

    disposition_path = artifact_root / "dispositions" / (plan["disposition_id"].split(":", 1)[1] + ".md")
    disposition_text = _disposition_markdown(plan, authorization, now, effect)
    _materialize_disposition(disposition_path, disposition_text, plan, effect)
    if after_disposition_write is not None:
        after_disposition_write(disposition_path)
    record["status"] = "applied"
    record["disposition_id"] = plan["disposition_id"]
    record["disposition_reference"] = disposition_path.relative_to(artifact_root).as_posix()
    record["canonical_effect"] = effect
    state["events"][plan["event_id"]] = record
    _atomic_write_json(state_path, state)
    return {
        "status": "applied",
        "event_id": plan["event_id"],
        "plan_id": plan["plan_id"],
        "disposition_id": plan["disposition_id"],
        "disposition_reference": record["disposition_reference"],
        "canonical_effect": effect,
    }


def _without_paths(value: Any, paths: Sequence[tuple[str, ...]]) -> Any:
    copied = json.loads(json.dumps(value))
    for path in paths:
        current = copied
        for key in path[:-1]:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if isinstance(current, dict):
            current.pop(path[-1], None)
    return copied


def _materialize_json(
    path: Path, value: dict[str, Any], *, volatile_paths: Sequence[tuple[str, ...]] = ()
) -> dict[str, Any]:
    if path.exists():
        existing = _strict_json(path, Phase7Error, "existing artifact")
        if _without_paths(existing, volatile_paths) != _without_paths(value, volatile_paths):
            raise Phase7Error(f"artifact identity collision; preserve existing evidence: {path}")
        return existing
    _atomic_write_json(path, value)
    return value


def _materialize_text(path: Path, value: str) -> None:
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise Phase7Error(f"existing disposition is unreadable: {path}") from exc
        if existing != value:
            raise Phase7Error(f"disposition identity collision; preserve existing evidence: {path}")
        return
    _atomic_write_text(path, value)


def _materialize_disposition(
    path: Path, value: str, plan: Mapping[str, Any], effect: Mapping[str, Any]
) -> None:
    if not path.exists():
        _atomic_write_text(path, value)
        return
    existing_effect = _load_disposition_effect(path, plan)
    if _stable_effect(existing_effect) != _stable_effect(effect):
        raise Phase7Error(f"disposition canonical effect collision; preserve existing evidence: {path}")


def _stable_effect(effect: Mapping[str, Any]) -> dict[str, Any]:
    stable = dict(effect)
    stable.pop("status", None)
    return stable


def _load_disposition_effect(path: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    if not path.exists():
        raise Phase7Error(f"applied disposition evidence is missing: {path}")
    try:
        existing = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise Phase7Error(f"existing disposition is unreadable: {path}") from exc
    required_fragments = (
        f"disposition_id: {json.dumps(plan['disposition_id'])}",
        f"plan_id: {json.dumps(plan['plan_id'])}",
        f"delta_event_id: {json.dumps(plan['event_id'])}",
    )
    if any(fragment not in existing for fragment in required_fragments):
        raise Phase7Error(f"disposition identity collision; preserve existing evidence: {path}")
    effect_line = next(
        (line for line in existing.splitlines() if line.startswith("- Canonical effect: ")),
        None,
    )
    try:
        existing_effect = json.loads(effect_line.split(": ", 1)[1]) if effect_line else None
    except json.JSONDecodeError as exc:
        raise Phase7Error(f"existing disposition effect is malformed: {path}") from exc
    if not isinstance(existing_effect, dict):
        raise Phase7Error(f"existing disposition effect is missing: {path}")
    return existing_effect


def _verify_applied_evidence(
    plan: Mapping[str, Any],
    record: Mapping[str, Any],
    artifact_root: Path,
    canonical_root: Path,
) -> bool:
    if (
        record.get("plan_id") != plan["plan_id"]
        or record.get("disposition_id") != plan["disposition_id"]
        or record.get("canonical_effect") is None
    ):
        raise Phase7Error("applied processing state does not match its plan/disposition lineage")
    disposition_path = artifact_root / record["disposition_reference"]
    disposition_effect = _load_disposition_effect(disposition_path, plan)
    if _stable_effect(disposition_effect) != _stable_effect(record["canonical_effect"]):
        raise Phase7Error("applied disposition and processing-state canonical effects disagree")
    effect = record["canonical_effect"]
    if effect.get("kind") != "write_markdown":
        return True
    target = _resolve_target(canonical_root, effect.get("target"))
    current_hash = file_sha256(target) if target.exists() else None
    return current_hash == effect.get("after_sha256")


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _atomic_write_text(path: Path, value: str) -> None:
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
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    intake = subparsers.add_parser("intake", help="Validate a Phase 6 batch and create fresh Curator intake")
    intake.add_argument("--batch", required=True, type=Path)
    intake.add_argument("--source-root", required=True, type=Path)
    intake.add_argument("--state", required=True, type=Path)
    intake.add_argument("--artifact-root", required=True, type=Path)
    intake.add_argument("--store-id", required=True)
    intake.add_argument("--harness", required=True)
    intake.add_argument("--default-intent", required=True, choices=("explicit", "implicit"))
    intake.add_argument("--expected-previous-checkpoint-id", required=True, help="Phase 6 ID or literal null")

    plan = subparsers.add_parser("plan", help="Record a semantic Curator proposal as an immutable plan")
    plan.add_argument("--intake", required=True, type=Path)
    plan.add_argument("--proposal", required=True, type=Path)
    plan.add_argument("--source-root", required=True, type=Path)
    plan.add_argument("--canonical-root", required=True, type=Path)
    plan.add_argument("--state", required=True, type=Path)
    plan.add_argument("--artifact-root", required=True, type=Path)

    apply = subparsers.add_parser("apply", help="Apply an explicitly authorized recorded plan")
    apply.add_argument("--plan", required=True, type=Path)
    apply.add_argument("--authorization", required=True, type=Path)
    apply.add_argument("--source-root", required=True, type=Path)
    apply.add_argument("--canonical-root", required=True, type=Path)
    apply.add_argument("--state", required=True, type=Path)
    apply.add_argument("--artifact-root", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "intake":
            previous = None if args.expected_previous_checkpoint_id == "null" else args.expected_previous_checkpoint_id
            result = process_batch(
                batch_path=args.batch,
                source_root=args.source_root,
                state_path=args.state,
                artifact_root=args.artifact_root,
                store_id=args.store_id,
                harness=args.harness,
                default_intent=args.default_intent,
                expected_previous_checkpoint_id=previous,
            )
        elif args.command == "plan":
            result = create_plan(
                intake_path=args.intake,
                proposal_path=args.proposal,
                source_root=args.source_root,
                canonical_root=args.canonical_root,
                state_path=args.state,
                artifact_root=args.artifact_root,
            )
        else:
            result = apply_plan(
                plan_path=args.plan,
                authorization_path=args.authorization,
                source_root=args.source_root,
                canonical_root=args.canonical_root,
                state_path=args.state,
                artifact_root=args.artifact_root,
            )
    except Phase7Error as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
