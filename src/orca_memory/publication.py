"""Recoverable intent-first publication for validated vault artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Callable, Literal


PUBLICATION_INTENT_SCHEMA = "orca-publication-intent/0.1"


class PublicationRepairRequired(ValueError):
    """A fixed publication plan conflicts with observed filesystem state."""


@dataclass(frozen=True)
class PlannedOutput:
    output_ref: str
    artifact_kind: str
    artifact_id: str
    effect: Literal["created", "replaced", "deleted"]
    path: str
    before_sha256: str | None
    after_sha256: str | None
    payload: bytes | None

    def __post_init__(self) -> None:
        _safe_relative(self.path)
        payload_hash = _hash_bytes(self.payload) if self.payload is not None else None
        if payload_hash != self.after_sha256:
            raise ValueError("planned output payload does not match after_sha256")
        if self.effect == "created" and not (
            self.before_sha256 is None and self.after_sha256 is not None
        ):
            raise ValueError("created output requires only an after hash")
        if self.effect == "replaced" and not (
            self.before_sha256 is not None and self.after_sha256 is not None
        ):
            raise ValueError("replaced output requires before and after hashes")
        if self.effect == "deleted" and not (
            self.before_sha256 is not None
            and self.after_sha256 is None
            and self.payload is None
        ):
            raise ValueError("deleted output requires only a before hash")


@dataclass(frozen=True)
class PublicationPlan:
    run_id: str
    manifest_path: str
    manifest_payload: bytes
    checkpoint_path: str
    checkpoint_payload: bytes
    outputs: tuple[PlannedOutput, ...]

    def __post_init__(self) -> None:
        _safe_relative(self.manifest_path)
        _safe_relative(self.checkpoint_path)
        if len({output.output_ref for output in self.outputs}) != len(self.outputs):
            raise ValueError("duplicate publication output_ref")


class RecoverablePublisher:
    """Publish one fixed plan and recover it without repeating semantic work."""

    def __init__(self, vault_root: Path, runtime_root: Path) -> None:
        self.vault_root = vault_root.resolve()
        self.runtime_root = runtime_root.resolve()
        if self.vault_root == self.runtime_root or self.vault_root in self.runtime_root.parents:
            raise ValueError("runtime root must be outside the vault")

    def publish(
        self,
        plan: PublicationPlan,
        *,
        fault: Callable[[str], None] | None = None,
    ) -> Path:
        intent_path = self._prepare_intent(plan)
        self._fault(fault, "after-intent")
        return self._complete(intent_path, fault=fault)

    def recover(self, intent_path: Path) -> Path:
        """Complete a valid fixed intent or fail closed on mismatched state."""

        expected_root = self.runtime_root / "publications"
        resolved = intent_path.resolve()
        if expected_root not in resolved.parents:
            raise ValueError("publication intent is outside the runtime publication root")
        return self._complete(resolved, fault=None)

    def pending_intents(self) -> tuple[Path, ...]:
        root = self.runtime_root / "publications"
        return () if not root.exists() else tuple(sorted(root.glob("*/intent.json")))

    def _prepare_intent(self, plan: PublicationPlan) -> Path:
        run_dir = self.runtime_root / "publications" / plan.run_id
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(run_dir, 0o700)
        staged: list[dict[str, object]] = []
        for output in plan.outputs:
            staged_path: str | None = None
            if output.payload is not None:
                staged_name = f"{output.output_ref}.post"
                _write_new_private(run_dir / staged_name, output.payload)
                staged_path = staged_name
            staged.append(
                {
                    "output_ref": output.output_ref,
                    "artifact_kind": output.artifact_kind,
                    "artifact_id": output.artifact_id,
                    "effect": output.effect,
                    "path": output.path,
                    "before_sha256": output.before_sha256,
                    "after_sha256": output.after_sha256,
                    "staged_path": staged_path,
                }
            )
        intent = {
            "schema": PUBLICATION_INTENT_SCHEMA,
            "run_id": plan.run_id,
            "manifest": {
                "path": plan.manifest_path,
                "sha256": _hash_bytes(plan.manifest_payload),
                "payload": plan.manifest_payload.decode("utf-8"),
            },
            "checkpoint": {
                "path": plan.checkpoint_path,
                "sha256": _hash_bytes(plan.checkpoint_payload),
                "payload": plan.checkpoint_payload.decode("utf-8"),
            },
            "outputs": staged,
        }
        intent_path = run_dir / "intent.json"
        _write_new_private(
            intent_path,
            (json.dumps(intent, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        return intent_path

    def _complete(
        self,
        intent_path: Path,
        *,
        fault: Callable[[str], None] | None,
    ) -> Path:
        intent = self._load_intent(intent_path)
        run_dir = intent_path.parent
        for output in intent["outputs"]:
            target = self._vault_path(output["path"])
            current = _hash_path(target)
            before = output["before_sha256"]
            after = output["after_sha256"]
            if current == after:
                pass
            elif current == before:
                staged = output["staged_path"]
                if staged is None:
                    target.unlink()
                else:
                    payload = (run_dir / staged).read_bytes()
                    if _hash_bytes(payload) != after:
                        raise PublicationRepairRequired(
                            f"staged output hash mismatch for {output['artifact_id']}"
                        )
                    _replace_file(target, payload)
            else:
                raise PublicationRepairRequired(
                    f"publication target mismatch for {output['artifact_id']}"
                )
            self._fault(fault, f"after-output:{output['output_ref']}")

        manifest_info = intent["manifest"]
        manifest_path = self._vault_path(manifest_info["path"])
        manifest_payload = manifest_info["payload"].encode("utf-8")
        if _hash_bytes(manifest_payload) != manifest_info["sha256"]:
            raise PublicationRepairRequired("publication intent Manifest hash mismatch")
        if manifest_path.exists():
            if _hash_path(manifest_path) != manifest_info["sha256"]:
                raise PublicationRepairRequired("immutable Manifest hash mismatch")
        else:
            _publish_immutable(manifest_path, manifest_payload)
        self._fault(fault, "after-manifest")

        for output in intent["outputs"]:
            if _hash_path(self._vault_path(output["path"])) != output["after_sha256"]:
                raise PublicationRepairRequired(
                    f"published output integrity mismatch for {output['artifact_id']}"
                )
        checkpoint_info = intent["checkpoint"]
        checkpoint_payload = checkpoint_info["payload"].encode("utf-8")
        if _hash_bytes(checkpoint_payload) != checkpoint_info["sha256"]:
            raise PublicationRepairRequired("publication intent checkpoint hash mismatch")
        _replace_file(self._runtime_path(checkpoint_info["path"]), checkpoint_payload)
        self._fault(fault, "after-checkpoint")
        self._fault(fault, "before-cleanup")
        self._cleanup(run_dir)
        return manifest_path

    def _load_intent(self, path: Path) -> dict[str, object]:
        if path.stat().st_mode & 0o077:
            raise PublicationRepairRequired("unsafe publication intent permissions")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("schema") != PUBLICATION_INTENT_SCHEMA:
            raise PublicationRepairRequired("invalid publication intent")
        if not isinstance(value.get("outputs"), list):
            raise PublicationRepairRequired("invalid publication output plan")
        for group in ("manifest", "checkpoint"):
            entry = value.get(group)
            if not isinstance(entry, dict):
                raise PublicationRepairRequired(f"invalid publication {group} plan")
            _safe_relative(entry.get("path"))
            if not isinstance(entry.get("payload"), str) or not _is_hash(entry.get("sha256")):
                raise PublicationRepairRequired(f"invalid publication {group} payload")
        for output in value["outputs"]:
            if not isinstance(output, dict):
                raise PublicationRepairRequired("invalid publication output")
            _safe_relative(output.get("path"))
            if output.get("effect") not in {"created", "replaced", "deleted"}:
                raise PublicationRepairRequired("invalid publication effect")
            if output.get("before_sha256") is not None and not _is_hash(
                output.get("before_sha256")
            ):
                raise PublicationRepairRequired("invalid publication before hash")
            if output.get("after_sha256") is not None and not _is_hash(
                output.get("after_sha256")
            ):
                raise PublicationRepairRequired("invalid publication after hash")
            staged = output.get("staged_path")
            if staged is not None and (
                not isinstance(staged, str)
                or PurePosixPath(staged).name != staged
                or not (path.parent / staged).is_file()
            ):
                raise PublicationRepairRequired("invalid staged publication output")
        return value

    def _vault_path(self, relative: str) -> Path:
        return _under(self.vault_root, relative)

    def _runtime_path(self, relative: str) -> Path:
        return _under(self.runtime_root, relative)

    @staticmethod
    def _fault(fault: Callable[[str], None] | None, point: str) -> None:
        if fault is not None:
            fault(point)

    @staticmethod
    def _cleanup(run_dir: Path) -> None:
        for path in sorted(run_dir.iterdir()):
            if path.is_file():
                path.unlink()
            else:
                raise PublicationRepairRequired("unexpected publication-intent entry")
        run_dir.rmdir()


def _safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("publication path must be a nonempty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"unsafe publication path: {value!r}")
    return value


def _under(root: Path, relative: str) -> Path:
    _safe_relative(relative)
    candidate = (root / Path(*PurePosixPath(relative).parts)).resolve()
    if root not in candidate.parents:
        raise ValueError("publication path escapes its configured root")
    return candidate


def _hash_bytes(payload: bytes | None) -> str | None:
    return None if payload is None else hashlib.sha256(payload).hexdigest()


def _hash_path(path: Path) -> str | None:
    return _hash_bytes(path.read_bytes()) if path.is_file() else None


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _write_new_private(path: Path, payload: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _replace_file(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise PublicationRepairRequired("immutable Manifest already exists") from exc
    finally:
        temporary.unlink(missing_ok=True)
