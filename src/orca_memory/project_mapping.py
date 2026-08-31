"""Recoverable Project Registration and Project Relink filesystem workflow."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from dataclasses import dataclass
from typing import Any, Callable

import yaml

from orca_memory.projects import (
    MAPPING_INTENT_SCHEMA,
    MappingPlan,
    project_alias_slug,
    validate_project_record,
)


class ProjectMappingRepairRequired(ValueError):
    """A fixed mapping plan conflicts with observed registry or host state."""


@dataclass(frozen=True)
class ProjectMappingRepairItem:
    """Content-free local evidence that requires Owner mapping repair."""

    failure_class: str
    project_id: str
    locator: str


def detect_project_mapping_repairs(
    vault_root: Path, host_config_path: Path
) -> tuple[ProjectMappingRepairItem, ...]:
    """Find unlinked registry records and mappings with no registry identity."""

    config = _load_host_config(host_config_path.read_bytes())
    mapped_ids = {item["project_id"] for item in config["project_root_mappings"]}
    project_root = vault_root / "System" / "Orca Memory" / "shallow" / "projects"
    records: dict[str, str] = {}
    if project_root.exists():
        for path in sorted(project_root.glob("*/project.md")):
            record = validate_project_record(path.read_text(encoding="utf-8"))
            locator = path.relative_to(vault_root).as_posix()
            if record.project_id in records:
                raise ProjectMappingRepairRequired(
                    f"duplicate project registry identity: {record.project_id}"
                )
            records[record.project_id] = locator
    repairs = [
        ProjectMappingRepairItem("unlinked-project-record", project_id, locator)
        for project_id, locator in sorted(records.items())
        if project_id not in mapped_ids
    ]
    repairs.extend(
        ProjectMappingRepairItem(
            "mapping-record-disagreement",
            project_id,
            "config/host.yaml#project_root_mappings",
        )
        for project_id in sorted(mapped_ids - set(records))
    )
    return tuple(repairs)


class ProjectMappingPublisher:
    def __init__(self, vault_root: Path, runtime_root: Path) -> None:
        self.vault_root = vault_root.resolve()
        self.runtime_root = runtime_root.resolve()
        if self.vault_root == self.runtime_root or self.vault_root in self.runtime_root.parents:
            raise ValueError("runtime root must be outside the vault")

    def publish(
        self,
        plan: MappingPlan,
        *,
        host_config_path: Path,
        operation_id: str,
        fault: Callable[[str], None] | None = None,
    ) -> Path:
        """Persist one fixed intent, then project.md and host mapping in order."""

        if not operation_id or any(character in operation_id for character in "/\\"):
            raise ValueError("invalid project mapping operation_id")
        host_before = host_config_path.read_bytes()
        host_value = _load_host_config(host_before)
        host_after_value = copy.deepcopy(host_value)
        mappings = host_after_value["project_root_mappings"]
        normalized_root = str(plan.root)
        exact = [item for item in mappings if item.get("root") == normalized_root]
        if exact:
            if len(exact) == 1 and exact[0].get("project_id") == plan.project_id:
                return host_config_path
            raise ProjectMappingRepairRequired("project root mapping already conflicts")
        mappings.append({"root": normalized_root, "project_id": plan.project_id})
        host_after = yaml.safe_dump(
            host_after_value,
            sort_keys=False,
            allow_unicode=True,
        ).encode("utf-8")

        run_dir = self.runtime_root / "project-mappings" / operation_id
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(run_dir, 0o700)
        _write_new_private(run_dir / "host.post", host_after)
        project_entry: dict[str, Any] | None = None
        if plan.project_record is not None:
            project_payload = plan.project_record.render().encode("utf-8")
            _write_new_private(run_dir / "project.post", project_payload)
            project_relative = (
                Path("System/Orca Memory/shallow/projects")
                / project_alias_slug(plan.project_alias)
                / "project.md"
            ).as_posix()
            project_entry = {
                "path": project_relative,
                "before_sha256": None,
                "after_sha256": _sha(project_payload),
                "staged_path": "project.post",
            }
        intent = {
            "schema": MAPPING_INTENT_SCHEMA,
            "operation_id": operation_id,
            "action": plan.action,
            "root": normalized_root,
            "git_common_dir": str(plan.git_common_dir)
            if plan.git_common_dir is not None
            else None,
            "project_id": plan.project_id,
            "project_alias": plan.project_alias,
            "project": project_entry,
            "host_config": {
                "path": str(host_config_path.resolve()),
                "before_sha256": _sha(host_before),
                "after_sha256": _sha(host_after),
                "staged_path": "host.post",
            },
        }
        intent_path = run_dir / "intent.json"
        _write_new_private(
            intent_path,
            (json.dumps(intent, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        _fault(fault, "after-intent")
        self._complete(intent_path, fault=fault)
        return host_config_path

    def recover(
        self,
        intent_path: Path,
        *,
        host_config_path: Path | None = None,
    ) -> Path:
        expected_root = self.runtime_root / "project-mappings"
        resolved = intent_path.resolve()
        if expected_root not in resolved.parents:
            raise ValueError("project mapping intent is outside its runtime root")
        if host_config_path is not None:
            intent = _load_intent(resolved)
            if intent["host_config"].get("path") != str(host_config_path.resolve()):
                raise ProjectMappingRepairRequired(
                    "project mapping intent targets another host configuration"
                )
        self._complete(resolved, fault=None)
        return resolved

    def pending_intents(self) -> tuple[Path, ...]:
        root = self.runtime_root / "project-mappings"
        return () if not root.exists() else tuple(sorted(root.glob("*/intent.json")))

    def _complete(
        self,
        intent_path: Path,
        *,
        fault: Callable[[str], None] | None,
    ) -> None:
        intent = _load_intent(intent_path)
        run_dir = intent_path.parent
        project = intent["project"]
        if project is not None:
            target = _under(self.vault_root, project["path"])
            _reconcile_file(
                target,
                before=project["before_sha256"],
                after=project["after_sha256"],
                staged=run_dir / project["staged_path"],
                label=intent["project_id"],
            )
        _fault(fault, "after-project")

        host = intent["host_config"]
        host_target = Path(host["path"])
        if not host_target.is_absolute():
            raise ProjectMappingRepairRequired("host configuration path is not absolute")
        _reconcile_file(
            host_target,
            before=host["before_sha256"],
            after=host["after_sha256"],
            staged=run_dir / host["staged_path"],
            label="host-config",
        )
        _fault(fault, "after-host-config")

        if project is not None and _hash_path(_under(self.vault_root, project["path"])) != project[
            "after_sha256"
        ]:
            raise ProjectMappingRepairRequired("project registry verification failed")
        if _hash_path(host_target) != host["after_sha256"]:
            raise ProjectMappingRepairRequired("host mapping verification failed")
        _fault(fault, "before-cleanup")
        for path in sorted(run_dir.iterdir()):
            if not path.is_file():
                raise ProjectMappingRepairRequired("unexpected mapping-intent entry")
            path.unlink()
        run_dir.rmdir()


def _load_host_config(payload: bytes) -> dict[str, Any]:
    value = yaml.safe_load(payload)
    if not isinstance(value, dict):
        raise ValueError("host configuration must be a mapping")
    mappings = value.get("project_root_mappings")
    if not isinstance(mappings, list):
        raise ValueError("host configuration requires project_root_mappings")
    for item in mappings:
        if not isinstance(item, dict) or set(item) != {"root", "project_id"}:
            raise ValueError("invalid project_root_mappings entry")
        if not isinstance(item["root"], str) or not isinstance(item["project_id"], str):
            raise ValueError("invalid project_root_mappings value")
    return value


def _load_intent(path: Path) -> dict[str, Any]:
    if path.stat().st_mode & 0o077:
        raise ProjectMappingRepairRequired("unsafe project mapping intent permissions")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != MAPPING_INTENT_SCHEMA:
        raise ProjectMappingRepairRequired("invalid project mapping intent")
    if value.get("action") not in {"register", "relink", "worktree-reuse"}:
        raise ProjectMappingRepairRequired("invalid project mapping action")
    if not isinstance(value.get("host_config"), dict):
        raise ProjectMappingRepairRequired("invalid host mapping plan")
    return value


def _reconcile_file(
    target: Path,
    *,
    before: str | None,
    after: str,
    staged: Path,
    label: str,
) -> None:
    current = _hash_path(target)
    if current == after:
        return
    if current != before:
        raise ProjectMappingRepairRequired(f"project mapping state mismatch for {label}")
    payload = staged.read_bytes()
    if _sha(payload) != after:
        raise ProjectMappingRepairRequired(f"project mapping staged hash mismatch for {label}")
    _replace_file(target, payload)


def _under(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        raise ProjectMappingRepairRequired("project record path escapes the vault")
    return candidate


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _hash_path(path: Path) -> str | None:
    return _sha(path.read_bytes()) if path.is_file() else None


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


def _fault(fault: Callable[[str], None] | None, point: str) -> None:
    if fault is not None:
        fault(point)
