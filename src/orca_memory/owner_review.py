"""Recoverable explicit Owner review workflows for noncanonical artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Callable, Literal

from orca_memory.candidates import (
    DispositionReceipt,
    KnowledgeCandidate,
    candidate_placement,
    plan_disposition,
    reconcile_disposition,
)
from orca_memory.conflicts import (
    ConflictOverflow,
    ConflictRecord,
    ConflictVariant,
    parse_conflict_record,
    review_conflict,
)
from orca_memory.memory import parse_record, record_relative_path
from orca_memory.projects import ProjectRecord


OWNER_REVIEW_INTENT_SCHEMA = "orca-owner-review-intent/0.1"
CONFLICT_REVIEW_RECEIPT_SCHEMA = "orca-conflict-review-receipt/0.1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")


class OwnerReviewRepairRequired(ValueError):
    """A fixed Owner review plan conflicts with current durable state."""


@dataclass(frozen=True)
class ReviewOutput:
    artifact_kind: str
    artifact_id: str
    path: str
    before_sha256: str
    after_sha256: str | None
    payload: bytes | None

    def __post_init__(self) -> None:
        _safe_relative(self.path)
        if not _SAFE_ARTIFACT_ID.fullmatch(self.artifact_id):
            raise ValueError("invalid Owner review artifact identity")
        if _hash_bytes(self.payload) != self.after_sha256:
            raise ValueError("Owner review output hash does not match payload")


@dataclass(frozen=True)
class OwnerReviewPlan:
    operation_id: str
    operation: Literal["candidate-disposition", "conflict-review"]
    artifact_id: str
    receipt_path: str
    receipt_payload: bytes
    outputs: tuple[ReviewOutput, ...]

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.operation_id) or not _SAFE_ID.fullmatch(
            self.artifact_id
        ):
            raise ValueError("invalid Owner review operation identity")
        _safe_relative(self.receipt_path)
        if not self.outputs:
            raise ValueError("Owner review requires at least one output")


class OwnerReviewPublisher:
    """Publish one explicit review receipt and its fixed artifact post-images."""

    def __init__(
        self,
        vault_root: Path,
        runtime_root: Path,
        *,
        fault: Callable[[str], None] | None = None,
    ) -> None:
        self.vault_root = vault_root.resolve()
        self.runtime_root = runtime_root.resolve()
        if self.vault_root == self.runtime_root or self.vault_root in self.runtime_root.parents:
            raise ValueError("runtime root must be outside the vault")
        self._fault = fault

    def publish(self, plan: OwnerReviewPlan) -> Path:
        with self._lock():
            review_root = self.runtime_root / "owner-reviews"
            if review_root.exists() and any(review_root.iterdir()):
                raise OwnerReviewRepairRequired(
                    "recover the pending Owner review before starting another"
                )
            intent = self._prepare(plan)
            return self._complete(intent)

    def recover(self, operation_id: str) -> Path:
        if not _SAFE_ID.fullmatch(operation_id):
            raise ValueError("invalid Owner review operation identity")
        intent = self.runtime_root / "owner-reviews" / operation_id / "intent.json"
        with self._lock():
            if not _private_regular_file(intent, expected_parent=intent.parent):
                raise ValueError("Owner review intent does not exist")
            return self._complete(intent)

    def pending_intents(self) -> tuple[Path, ...]:
        root = self.runtime_root / "owner-reviews"
        return () if not root.exists() else tuple(sorted(root.glob("*/intent.json")))

    def candidate_disposition(
        self,
        candidate_id: str,
        *,
        target_status: Literal["approved-for-manual-apply", "rejected"],
        operation_id: str,
        changed_at: datetime,
    ) -> Path:
        path, candidate = self._find_candidate(candidate_id)
        if candidate.status == target_status:
            receipts = self._candidate_receipts(candidate, target_status)
            if len(receipts) == 1:
                return receipts[0]
            raise OwnerReviewRepairRequired(
                "terminal candidate lacks one matching durable disposition receipt"
            )
        plan = plan_disposition(
            candidate,
            target_status=target_status,
            owner_confirmed=True,
            operation_id=operation_id,
            changed_at=changed_at,
            expected_candidate_id=candidate_id,
        )
        relative = path.relative_to(self.vault_root).as_posix()
        output = ReviewOutput(
            "knowledge-candidate",
            candidate_id,
            relative,
            _hash_bytes(plan.before.render().encode("utf-8")) or "",
            _hash_bytes(plan.after.render().encode("utf-8")),
            plan.after.render().encode("utf-8"),
        )
        review = OwnerReviewPlan(
            operation_id,
            "candidate-disposition",
            candidate_id,
            _receipt_path(operation_id),
            plan.receipt.render().encode("utf-8"),
            (output,),
        )
        return self.publish(review)

    def conflict_review(
        self,
        memory_id: str,
        *,
        operation_id: str,
        changed_at: datetime,
        select_variant_id: str | None = None,
        owner_resolution: str | None = None,
        resolution_at: str | None = None,
        keep_unresolved: bool = False,
    ) -> Path:
        path, conflict = self._find_conflict(memory_id)
        overflows = self._find_overflows(memory_id)
        changed = _utc(changed_at)
        after = review_conflict(
            conflict,
            owner_confirmed=True,
            updated_at=changed,
            select_variant_id=select_variant_id,
            owner_resolution=owner_resolution,
            resolution_at=resolution_at,
            keep_unresolved=keep_unresolved,
            overflow_variants=tuple(item for _, item in overflows),
        )
        variants = conflict.variants + tuple(
            ConflictVariant(
                overflow.variant_id,
                overflow.label,
                overflow.position,
                overflow.position_at,
            )
            for _, overflow in overflows
        )
        before_payload = conflict.render().encode("utf-8")
        after_payload = after.render().encode("utf-8")
        relative = path.relative_to(self.vault_root).as_posix()
        outputs = [ReviewOutput(
            "typed-memory-record",
            memory_id,
            relative,
            _hash_bytes(before_payload) or "",
            _hash_bytes(after_payload),
            after_payload,
        )]
        if not keep_unresolved:
            outputs.extend(
                ReviewOutput(
                    "conflict-overflow-candidate",
                    f"{memory_id}:{overflow.variant_id}",
                    overflow_path.relative_to(self.vault_root).as_posix(),
                    _hash_bytes(overflow_path.read_bytes()) or "",
                    None,
                    None,
                )
                for overflow_path, overflow in overflows
            )
        action = (
            "keep-unresolved"
            if keep_unresolved
            else "owner-resolution"
            if owner_resolution is not None
            else f"select:{select_variant_id}"
        )
        receipt = {
            "schema": CONFLICT_REVIEW_RECEIPT_SCHEMA,
            "operation_id": operation_id,
            "memory_id": memory_id,
            "action": action,
            "recorded_at": changed,
            "variant_dispositions": [
                {
                    "variant_id": variant.variant_id,
                    "disposition": (
                        "kept-unresolved"
                        if keep_unresolved
                        else "replaced-by-owner-resolution"
                        if owner_resolution is not None
                        else "selected"
                        if variant.variant_id == select_variant_id
                        else "not-selected"
                    ),
                }
                for variant in variants
            ],
            "outputs": [
                {
                    "artifact_kind": output.artifact_kind,
                    "artifact_id": output.artifact_id,
                    "before_sha256": output.before_sha256,
                    "after_sha256": output.after_sha256,
                }
                for output in outputs
            ],
        }
        review = OwnerReviewPlan(
            operation_id,
            "conflict-review",
            memory_id,
            _receipt_path(operation_id),
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            tuple(outputs),
        )
        return self.publish(review)

    def _find_candidate(self, candidate_id: str) -> tuple[Path, KnowledgeCandidate]:
        if not _SAFE_ID.fullmatch(candidate_id):
            raise ValueError("invalid candidate identity")
        root = self.vault_root / "System" / "Orca Memory" / "candidates" / "knowledge"
        matches: list[tuple[Path, KnowledgeCandidate]] = []
        if root.exists():
            for path in sorted(root.glob("**/*.md")):
                self._validate_source_path(path)
                candidate = KnowledgeCandidate.parse(path.read_text(encoding="utf-8"))
                if candidate.candidate_id == candidate_id:
                    alias = self._project_alias(candidate.scope, candidate.scope_id)
                    expected = candidate_placement(
                        self.vault_root, candidate, project_alias=alias
                    ).path.resolve()
                    if path.resolve() != expected:
                        raise OwnerReviewRepairRequired(
                            "candidate is outside its Storage-owned placement"
                        )
                    matches.append((expected, candidate))
        if len(matches) != 1:
            raise ValueError("candidate identity does not resolve uniquely")
        return matches[0]

    def _candidate_receipts(
        self, candidate: KnowledgeCandidate, target_status: str
    ) -> tuple[Path, ...]:
        root = self.vault_root / "System" / "Orca Memory" / "provenance" / "owner-reviews"
        matches: list[Path] = []
        if root.exists():
            for path in sorted(root.glob("*.json")):
                try:
                    receipt = DispositionReceipt.parse(path.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                if (
                    receipt.candidate_id == candidate.candidate_id
                    and receipt.to_status == target_status
                    and reconcile_disposition(candidate, receipt).status == "applied"
                ):
                    matches.append(path.resolve())
        return tuple(matches)

    def _find_conflict(self, memory_id: str) -> tuple[Path, ConflictRecord]:
        if not _SAFE_ID.fullmatch(memory_id):
            raise ValueError("invalid memory identity")
        root = self.vault_root / "System" / "Orca Memory" / "shallow"
        matches: list[tuple[Path, ConflictRecord]] = []
        if root.exists():
            for path in sorted(root.glob("**/*.md")):
                self._validate_source_path(path)
                document = path.read_text(encoding="utf-8")
                if "\nstatus: conflict\n" not in document:
                    continue
                record = parse_conflict_record(document)
                if record.memory_id == memory_id:
                    alias = self._project_alias(record.scope, record.scope_id)
                    expected = (self.vault_root / record_relative_path(record, alias)).resolve()
                    if path.resolve() != expected:
                        raise OwnerReviewRepairRequired(
                            "conflict is outside its Storage-owned placement"
                        )
                    matches.append((expected, record))
        if len(matches) != 1:
            raise ValueError("conflict identity does not resolve uniquely")
        return matches[0]

    def _find_overflows(self, memory_id: str) -> tuple[tuple[Path, ConflictOverflow], ...]:
        root = self.vault_root / "System" / "Orca Memory" / "candidates" / "conflicts"
        matches: list[tuple[Path, ConflictOverflow]] = []
        if root.exists():
            for path in sorted(root.glob("**/*.md")):
                self._validate_source_path(path)
                document = path.read_text(encoding="utf-8")
                if f"memory_id: {memory_id}\n" not in document:
                    continue
                overflow = ConflictOverflow.parse(document)
                if overflow.memory_id == memory_id:
                    alias = self._project_alias(overflow.scope, overflow.scope_id)
                    expected = (self.vault_root / overflow.relative_path(alias)).resolve()
                    if path.resolve() != expected:
                        raise OwnerReviewRepairRequired(
                            "conflict overflow is outside its Storage-owned placement"
                        )
                    matches.append((expected, overflow))
        matches.sort(key=lambda item: int(item[1].variant_id[1:]))
        identities = [item.variant_id for _, item in matches]
        if len(identities) != len(set(identities)):
            raise OwnerReviewRepairRequired("duplicate conflict overflow identity")
        return tuple(matches)

    def _project_alias(self, scope: str, scope_id: str) -> str | None:
        if scope != "project":
            return None
        root = self.vault_root / "System" / "Orca Memory" / "shallow" / "projects"
        matches: list[ProjectRecord] = []
        if root.exists():
            for path in sorted(root.glob("*/project.md")):
                self._validate_source_path(path)
                record = ProjectRecord.parse(path.read_text(encoding="utf-8"))
                if path.parent.name != record.alias_slug:
                    raise OwnerReviewRepairRequired(
                        "project registry record is outside its Storage-owned placement"
                    )
                if record.project_id == scope_id:
                    matches.append(record)
        if len(matches) != 1:
            raise OwnerReviewRepairRequired(
                "project scope does not resolve to one registry record"
            )
        return matches[0].project_alias

    def _validate_source_path(self, path: Path) -> None:
        try:
            relative = path.relative_to(self.vault_root)
        except ValueError as exc:
            raise OwnerReviewRepairRequired("Owner review source escapes the vault") from exc
        current = self.vault_root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise OwnerReviewRepairRequired("Owner review source contains a symlink")
        resolved = path.resolve()
        if self.vault_root not in resolved.parents or not resolved.is_file():
            raise OwnerReviewRepairRequired("Owner review source is not a vault file")

    def _prepare(self, plan: OwnerReviewPlan) -> Path:
        self._validate_plan(plan)
        run_dir = self.runtime_root / "owner-reviews" / plan.operation_id
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        staged: list[dict[str, object]] = []
        for index, output in enumerate(plan.outputs, start=1):
            staged_name = None
            if output.payload is not None:
                staged_name = f"output-{index}.post"
                _write_new(run_dir / staged_name, output.payload)
            staged.append(
                {
                    "artifact_kind": output.artifact_kind,
                    "artifact_id": output.artifact_id,
                    "path": output.path,
                    "before_sha256": output.before_sha256,
                    "after_sha256": output.after_sha256,
                    "staged_path": staged_name,
                }
            )
        intent = {
            "schema": OWNER_REVIEW_INTENT_SCHEMA,
            "operation_id": plan.operation_id,
            "operation": plan.operation,
            "artifact_id": plan.artifact_id,
            "receipt": {
                "path": plan.receipt_path,
                "sha256": _hash_bytes(plan.receipt_payload),
                "payload": plan.receipt_payload.decode("utf-8"),
            },
            "outputs": staged,
        }
        path = run_dir / "intent.json"
        _write_new(path, (json.dumps(intent, indent=2, sort_keys=True) + "\n").encode())
        return path

    def _validate_plan(self, plan: OwnerReviewPlan) -> None:
        if plan.receipt_path != _receipt_path(plan.operation_id):
            raise OwnerReviewRepairRequired("invalid Owner review receipt path")
        outputs = [
            {
                "artifact_kind": output.artifact_kind,
                "artifact_id": output.artifact_id,
                "path": output.path,
                "before_sha256": output.before_sha256,
                "after_sha256": output.after_sha256,
                "staged_path": None if output.payload is None else "staged.post",
            }
            for output in plan.outputs
        ]
        value = {
            "operation_id": plan.operation_id,
            "operation": plan.operation,
            "artifact_id": plan.artifact_id,
            "receipt": {"payload": plan.receipt_payload.decode("utf-8")},
            "outputs": outputs,
        }
        self._validate_output_locations(value)
        self._validate_receipt(value)
        if plan.operation == "candidate-disposition":
            candidate = KnowledgeCandidate.parse(plan.outputs[0].payload.decode("utf-8"))
            receipt = DispositionReceipt.parse(plan.receipt_payload.decode("utf-8"))
            if (
                candidate.candidate_id != plan.artifact_id
                or candidate.status not in {"approved-for-manual-apply", "rejected"}
                or candidate.status != receipt.to_status
            ):
                raise OwnerReviewRepairRequired("invalid candidate review post-image")
            alias = self._project_alias(candidate.scope, candidate.scope_id)
            expected = candidate_placement(
                self.vault_root, candidate, project_alias=alias
            ).relative_path
            if plan.outputs[0].path != expected:
                raise OwnerReviewRepairRequired("candidate review path is not canonical")
            target = _under(self.vault_root, plan.outputs[0].path)
            self._validate_source_path(target)
            before = KnowledgeCandidate.parse(target.read_text(encoding="utf-8"))
            if (
                before.candidate_id != plan.artifact_id
                or before.status != "pending"
                or _hash_path(target) != plan.outputs[0].before_sha256
                or receipt.from_status != "pending"
            ):
                raise OwnerReviewRepairRequired("candidate review source is not pending")
        else:
            payload = plan.outputs[0].payload.decode("utf-8")
            try:
                record = parse_record(payload)
            except ValueError:
                record = parse_conflict_record(payload)
            if record.memory_id != plan.artifact_id:
                raise OwnerReviewRepairRequired("invalid conflict review post-image")
            alias = self._project_alias(record.scope, record.scope_id)
            expected = record_relative_path(record, alias).as_posix()
            if plan.outputs[0].path != expected:
                raise OwnerReviewRepairRequired("conflict review path is not canonical")
            source_path, source = self._find_conflict(plan.artifact_id)
            if (
                source_path.relative_to(self.vault_root).as_posix()
                != plan.outputs[0].path
                or _hash_path(source_path) != plan.outputs[0].before_sha256
            ):
                raise OwnerReviewRepairRequired("conflict review source changed")
            overflows = self._find_overflows(plan.artifact_id)
            receipt = json.loads(plan.receipt_payload.decode("utf-8"))
            action = receipt["action"]
            if action == "keep-unresolved":
                expected_record = review_conflict(
                    source,
                    owner_confirmed=True,
                    updated_at=record.updated_at,
                    keep_unresolved=True,
                    overflow_variants=tuple(item for _, item in overflows),
                )
                expected_overflows: tuple[tuple[Path, ConflictOverflow], ...] = ()
            elif action == "owner-resolution":
                if not hasattr(record, "current") or record.current is None:
                    raise OwnerReviewRepairRequired("invalid Owner resolution post-image")
                expected_record = review_conflict(
                    source,
                    owner_confirmed=True,
                    updated_at=record.updated_at,
                    owner_resolution=record.current,
                    resolution_at=record.source_updated_at,
                    overflow_variants=tuple(item for _, item in overflows),
                )
                expected_overflows = overflows
            else:
                selected = action.removeprefix("select:")
                expected_record = review_conflict(
                    source,
                    owner_confirmed=True,
                    updated_at=record.updated_at,
                    select_variant_id=selected,
                    overflow_variants=tuple(item for _, item in overflows),
                )
                expected_overflows = overflows
            if expected_record.render().encode("utf-8") != plan.outputs[0].payload:
                raise OwnerReviewRepairRequired(
                    "conflict review post-image disagrees with explicit outcome"
                )
            if len(plan.outputs[1:]) != len(expected_overflows):
                raise OwnerReviewRepairRequired("conflict overflow disposition is incomplete")
            for output, (target, overflow) in zip(
                plan.outputs[1:], expected_overflows, strict=True
            ):
                self._validate_source_path(target)
                if (
                    output.artifact_id
                    != f"{overflow.memory_id}:{overflow.variant_id}"
                    or output.path != overflow.relative_path(alias).as_posix()
                    or output.before_sha256 != _hash_path(target)
                    or output.after_sha256 is not None
                    or output.payload is not None
                ):
                    raise OwnerReviewRepairRequired(
                        "conflict overflow review path is not canonical"
                    )
            variants = source.variants + tuple(item for _, item in overflows)
            expected_dispositions = [
                {
                    "variant_id": variant.variant_id,
                    "disposition": (
                        "kept-unresolved"
                        if action == "keep-unresolved"
                        else "replaced-by-owner-resolution"
                        if action == "owner-resolution"
                        else "selected"
                        if action == f"select:{variant.variant_id}"
                        else "not-selected"
                    ),
                }
                for variant in variants
            ]
            if receipt["variant_dispositions"] != expected_dispositions:
                raise OwnerReviewRepairRequired(
                    "conflict variant dispositions are incomplete"
                )

    def _complete(self, intent_path: Path) -> Path:
        intent = self._load_intent(intent_path)
        all_before = True
        for output in intent["outputs"]:
            target = _under(self.vault_root, output["path"])
            current = _hash_path(target)
            if current not in {output["before_sha256"], output["after_sha256"]}:
                raise OwnerReviewRepairRequired(
                    f"Owner review target mismatch for {output['artifact_id']}"
                )
            if current != output["before_sha256"]:
                all_before = False
            staged = output["staged_path"]
            if staged is not None:
                payload = _read_private_file(
                    intent_path.parent / staged,
                    expected_parent=intent_path.parent,
                )
                if _hash_bytes(payload) != output["after_sha256"]:
                    raise OwnerReviewRepairRequired("Owner review staged output mismatch")
        if all_before:
            self._validate_plan(self._plan_from_intent(intent, intent_path.parent))
        receipt = intent["receipt"]
        receipt_path = _under(self.vault_root, receipt["path"])
        receipt_payload = receipt["payload"].encode("utf-8")
        if _hash_bytes(receipt_payload) != receipt["sha256"]:
            raise OwnerReviewRepairRequired("Owner review receipt hash mismatch")
        _publish_immutable(receipt_path, receipt_payload, receipt["sha256"])
        if self._fault is not None:
            self._fault("after-receipt")
        for output in intent["outputs"]:
            target = _under(self.vault_root, output["path"])
            current = _hash_path(target)
            if current == output["after_sha256"]:
                continue
            if current != output["before_sha256"]:
                raise OwnerReviewRepairRequired(
                    f"Owner review target mismatch for {output['artifact_id']}"
                )
            staged = output["staged_path"]
            if staged is None:
                target.unlink()
            else:
                payload = _read_private_file(
                    intent_path.parent / staged,
                    expected_parent=intent_path.parent,
                )
                if _hash_bytes(payload) != output["after_sha256"]:
                    raise OwnerReviewRepairRequired("Owner review staged output mismatch")
                _replace(target, payload)
            if self._fault is not None:
                self._fault(f"after-output:{output['artifact_id']}")
        for output in intent["outputs"]:
            if _hash_path(_under(self.vault_root, output["path"])) != output["after_sha256"]:
                raise OwnerReviewRepairRequired("Owner review output verification failed")
        self._cleanup(intent_path.parent)
        return receipt_path

    @staticmethod
    def _plan_from_intent(intent: dict[str, object], run_dir: Path) -> OwnerReviewPlan:
        outputs = tuple(
            ReviewOutput(
                output["artifact_kind"],
                output["artifact_id"],
                output["path"],
                output["before_sha256"],
                output["after_sha256"],
                None
                if output["staged_path"] is None
                else _read_private_file(
                    run_dir / output["staged_path"],
                    expected_parent=run_dir,
                ),
            )
            for output in intent["outputs"]
        )
        return OwnerReviewPlan(
            intent["operation_id"],
            intent["operation"],
            intent["artifact_id"],
            intent["receipt"]["path"],
            intent["receipt"]["payload"].encode("utf-8"),
            outputs,
        )

    def _load_intent(self, path: Path) -> dict[str, object]:
        expected_root = self.runtime_root / "owner-reviews"
        run_dir = path.parent
        if (
            path.name != "intent.json"
            or run_dir.parent != expected_root
            or expected_root.is_symlink()
            or run_dir.is_symlink()
            or not run_dir.is_dir()
            or run_dir.stat().st_mode & 0o077
        ):
            raise OwnerReviewRepairRequired("unsafe Owner review intent")
        try:
            payload = _read_private_file(path, expected_parent=run_dir)
            value = json.loads(payload.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise OwnerReviewRepairRequired("invalid Owner review intent") from exc
        if (
            not isinstance(value, dict)
            or set(value)
            != {"schema", "operation_id", "operation", "artifact_id", "receipt", "outputs"}
            or value.get("schema") != OWNER_REVIEW_INTENT_SCHEMA
            or value.get("operation") not in {"candidate-disposition", "conflict-review"}
            or not isinstance(value.get("operation_id"), str)
            or not _SAFE_ID.fullmatch(value["operation_id"])
            or value["operation_id"] != path.parent.name
            or not isinstance(value.get("artifact_id"), str)
            or not _SAFE_ID.fullmatch(value["artifact_id"])
            or not isinstance(value.get("receipt"), dict)
            or not isinstance(value.get("outputs"), list)
            or not value["outputs"]
        ):
            raise OwnerReviewRepairRequired("invalid Owner review intent")
        receipt = value["receipt"]
        if set(receipt) != {"path", "sha256", "payload"}:
            raise OwnerReviewRepairRequired("invalid Owner review receipt")
        _safe_relative(receipt.get("path"))
        if (
            receipt.get("path") != _receipt_path(value["operation_id"])
            or not isinstance(receipt.get("payload"), str)
            or not _is_hash(receipt.get("sha256"))
        ):
            raise OwnerReviewRepairRequired("invalid Owner review receipt")
        for output in value["outputs"]:
            if (
                not isinstance(output, dict)
                or set(output)
                != {
                    "artifact_kind",
                    "artifact_id",
                    "path",
                    "before_sha256",
                    "after_sha256",
                    "staged_path",
                }
                or output.get("artifact_kind")
                not in {
                    "knowledge-candidate",
                    "typed-memory-record",
                    "conflict-overflow-candidate",
                }
                or not isinstance(output.get("artifact_id"), str)
                or not _SAFE_ARTIFACT_ID.fullmatch(output["artifact_id"])
            ):
                raise OwnerReviewRepairRequired("invalid Owner review output")
            _safe_relative(output.get("path"))
            if not _is_hash(output.get("before_sha256")) or (
                output.get("after_sha256") is not None
                and not _is_hash(output.get("after_sha256"))
            ):
                raise OwnerReviewRepairRequired("invalid Owner review output hash")
            staged = output.get("staged_path")
            if (output["after_sha256"] is None) != (staged is None):
                raise OwnerReviewRepairRequired("invalid Owner review staged output")
            if staged is not None and (
                not isinstance(staged, str)
                or PurePosixPath(staged).name != staged
                or not _private_regular_file(
                    path.parent / staged,
                    expected_parent=path.parent,
                )
            ):
                raise OwnerReviewRepairRequired("invalid Owner review staged output")
        self._validate_output_locations(value)
        self._validate_receipt(value)
        return value

    @staticmethod
    def _validate_output_locations(intent: dict[str, object]) -> None:
        outputs = intent["outputs"]
        if intent["operation"] == "candidate-disposition":
            output = outputs[0]
            if (
                len(outputs) != 1
                or output["artifact_kind"] != "knowledge-candidate"
                or output["artifact_id"] != intent["artifact_id"]
                or not output["path"].startswith(
                    "System/Orca Memory/candidates/knowledge/"
                )
            ):
                raise OwnerReviewRepairRequired("invalid candidate review output")
            return
        first = outputs[0]
        if (
            first["artifact_kind"] != "typed-memory-record"
            or first["artifact_id"] != intent["artifact_id"]
            or not first["path"].startswith("System/Orca Memory/shallow/")
        ):
            raise OwnerReviewRepairRequired("invalid conflict review output")
        for output in outputs[1:]:
            if (
                output["artifact_kind"] != "conflict-overflow-candidate"
                or not output["artifact_id"].startswith(f"{intent['artifact_id']}:")
                or not output["path"].startswith(
                    "System/Orca Memory/candidates/conflicts/"
                )
            ):
                raise OwnerReviewRepairRequired("invalid conflict overflow output")

    @staticmethod
    def _validate_receipt(intent: dict[str, object]) -> None:
        receipt = intent["receipt"]
        payload = receipt["payload"]
        outputs = intent["outputs"]
        if intent["operation"] == "candidate-disposition":
            try:
                parsed = DispositionReceipt.parse(payload)
            except ValueError as exc:
                raise OwnerReviewRepairRequired("invalid candidate disposition receipt") from exc
            if (
                parsed.operation_id != intent["operation_id"]
                or parsed.candidate_id != intent["artifact_id"]
                or len(outputs) != 1
                or outputs[0]["artifact_kind"] != "knowledge-candidate"
                or parsed.candidate_before_sha256 != outputs[0]["before_sha256"]
                or parsed.candidate_after_sha256 != outputs[0]["after_sha256"]
            ):
                raise OwnerReviewRepairRequired("candidate disposition receipt disagrees with intent")
            return
        try:
            value = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise OwnerReviewRepairRequired("invalid conflict review receipt") from exc
        if (
            not isinstance(value, dict)
            or set(value)
            != {
                "schema",
                "operation_id",
                "memory_id",
                "action",
                "recorded_at",
                "variant_dispositions",
                "outputs",
            }
            or value.get("schema") != CONFLICT_REVIEW_RECEIPT_SCHEMA
            or value.get("operation_id") != intent["operation_id"]
            or value.get("memory_id") != intent["artifact_id"]
            or not isinstance(value.get("action"), str)
            or not isinstance(value.get("recorded_at"), str)
            or not isinstance(value.get("variant_dispositions"), list)
            or not value["variant_dispositions"]
            or not isinstance(value.get("outputs"), list)
            or len(value["outputs"]) != len(outputs)
        ):
            raise OwnerReviewRepairRequired("conflict review receipt disagrees with intent")
        expected = [
            {
                "artifact_kind": output["artifact_kind"],
                "artifact_id": output["artifact_id"],
                "before_sha256": output["before_sha256"],
                "after_sha256": output["after_sha256"],
            }
            for output in outputs
        ]
        if value["outputs"] != expected:
            raise OwnerReviewRepairRequired("conflict review outputs disagree with intent")
        dispositions = value["variant_dispositions"]
        if any(
            not isinstance(item, dict)
            or set(item) != {"variant_id", "disposition"}
            or not isinstance(item["variant_id"], str)
            or re.fullmatch(r"v[1-9][0-9]*", item["variant_id"]) is None
            or item["disposition"]
            not in {
                "selected",
                "not-selected",
                "replaced-by-owner-resolution",
                "kept-unresolved",
            }
            for item in dispositions
        ) or len({item["variant_id"] for item in dispositions}) != len(dispositions):
            raise OwnerReviewRepairRequired("invalid conflict variant dispositions")
        action = value["action"]
        if action == "keep-unresolved":
            expected_dispositions = {"kept-unresolved"}
            selected_variant = None
        elif action == "owner-resolution":
            expected_dispositions = {"replaced-by-owner-resolution"}
            selected_variant = None
        elif action.startswith("select:"):
            selected_variant = action.removeprefix("select:")
            if re.fullmatch(r"v[1-9][0-9]*", selected_variant) is None:
                raise OwnerReviewRepairRequired("invalid conflict review action")
            expected_dispositions = {"selected", "not-selected"}
        else:
            raise OwnerReviewRepairRequired("invalid conflict review action")
        observed = {item["disposition"] for item in dispositions}
        if not observed.issubset(expected_dispositions):
            raise OwnerReviewRepairRequired("conflict disposition disagrees with action")
        selected = [
            item for item in dispositions if item["disposition"] == "selected"
        ]
        if selected_variant is None:
            if selected:
                raise OwnerReviewRepairRequired("conflict disposition disagrees with action")
        elif len(selected) != 1 or selected[0]["variant_id"] != selected_variant:
            raise OwnerReviewRepairRequired("conflict selection receipt is incomplete")

    def _lock(self):
        return _FileLock(self.runtime_root / "locks" / "owner-review.lock")

    @staticmethod
    def _cleanup(run_dir: Path) -> None:
        for path in sorted(run_dir.iterdir()):
            if not _private_regular_file(path, expected_parent=run_dir):
                raise OwnerReviewRepairRequired("unexpected Owner review intent entry")
            path.unlink()
        run_dir.rmdir()


class _FileLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.descriptor: int | None = None

    def __enter__(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(self.descriptor, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_):
        assert self.descriptor is not None
        os.close(self.descriptor)


def _receipt_path(operation_id: str) -> str:
    return f"System/Orca Memory/provenance/owner-reviews/{operation_id}.json"


def _utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Owner review time must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Owner review path must be relative")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise ValueError("unsafe Owner review path")
    return value


def _under(root: Path, relative: str) -> Path:
    _safe_relative(relative)
    path = (root / Path(*PurePosixPath(relative).parts)).resolve()
    if root not in path.parents:
        raise ValueError("Owner review path escapes its root")
    return path


def _hash_bytes(payload: bytes | None) -> str | None:
    return None if payload is None else hashlib.sha256(payload).hexdigest()


def _hash_path(path: Path) -> str | None:
    return _hash_bytes(path.read_bytes()) if path.is_file() else None


def _private_regular_file(path: Path, *, expected_parent: Path) -> bool:
    if path.parent != expected_parent or path.is_symlink():
        return False
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(info.st_mode) and not info.st_mode & 0o077


def _read_private_file(path: Path, *, expected_parent: Path) -> bytes:
    if not _private_regular_file(path, expected_parent=expected_parent):
        raise OwnerReviewRepairRequired("unsafe Owner review runtime file")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise OwnerReviewRepairRequired("unsafe Owner review runtime file")
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_immutable(path: Path, payload: bytes, expected_hash: str) -> None:
    if path.exists():
        if _hash_path(path) != expected_hash:
            raise OwnerReviewRepairRequired("immutable Owner review receipt mismatch")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise OwnerReviewRepairRequired("immutable Owner review receipt exists") from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "CONFLICT_REVIEW_RECEIPT_SCHEMA",
    "OWNER_REVIEW_INTENT_SCHEMA",
    "OwnerReviewPlan",
    "OwnerReviewPublisher",
    "OwnerReviewRepairRequired",
    "ReviewOutput",
]
