"""Strict, read-only loading for the accepted Phase 1 configuration."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import stat
from typing import Any

import yaml

from orca_memory.interaction import (
    AGGREGATION_POLICY,
    GUIDANCE_POLICY,
    OBSERVATION_POLICY,
)
from orca_memory.privacy import REDACTION_POLICY
from orca_memory.processor import PROCESSOR_POLICY
from orca_memory.projects import ProjectRegistry, RootMapping, validate_project_record
from orca_memory.segmentation import BudgetConfig


HOST_SCHEMA = 1
VAULT_SCHEMA = "orca-memory-config/0.1"
VAULT_CONFIG_RELATIVE_PATH = Path("System/Orca Memory/orca-memory.yaml")

_HOST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HOST_KEYS = {
    "schema_version",
    "host_id",
    "runtime",
    "vault_path",
    "runtime_path",
    "connectors",
    "project_root_mappings",
}
_HOST_REQUIRED_KEYS = _HOST_KEYS - {"vault_path"}
_VAULT_KEYS = {
    "schema_version",
    "provider",
    "lifecycle",
    "cadence",
    "privacy",
    "processing",
    "retry",
    "interaction",
    "budgets",
}
_VAULT_REQUIRED_KEYS = {
    "schema_version",
    "provider",
    "privacy",
    "processing",
    "interaction",
}


class ConfigurationError(ValueError):
    """A configuration source cannot produce the accepted Phase 1 value."""


@dataclass(frozen=True)
class HostConfiguration:
    schema_version: int
    host_id: str
    runtime: str
    vault_path: Path
    runtime_path: Path
    codex_rollout_store: Path
    project_root_mappings: tuple[RootMapping, ...]


@dataclass(frozen=True)
class ProviderConfiguration:
    adapter: str
    model: str


@dataclass(frozen=True)
class LifecycleConfiguration:
    enabled: bool = False


@dataclass(frozen=True)
class CadenceConfiguration:
    catch_up_minutes: int = 15
    index_reconcile_minutes: int = 15


@dataclass(frozen=True)
class RetryConfiguration:
    max_attempts: int = 3
    retention_hours: int = 72


@dataclass(frozen=True)
class PolicyConfiguration:
    redaction_policy: str
    processor_policy: str
    observation_policy: str
    aggregation_policy: str
    guidance_policy: str


@dataclass(frozen=True)
class ProcessorBudgetConfiguration:
    model_window_tokens: int = 32_768
    input_tokens: int = 20_000
    output_tokens: int = 4_000
    new_evidence_tokens: int = 8_000
    preceding_overlap_tokens: int = 1_000
    continuation_summary_tokens: int = 2_000
    project_summary_tokens: int = 2_000
    related_records_tokens: int = 5_000
    max_related_records: int = 5

    def as_processing_budget(self) -> BudgetConfig:
        """Translate accepted configuration names to the Processor value."""

        return BudgetConfig(
            new_evidence_tokens=self.new_evidence_tokens,
            preceding_turn_tokens=self.preceding_overlap_tokens,
            continuation_summary_tokens=self.continuation_summary_tokens,
            project_summary_tokens=self.project_summary_tokens,
            related_records_tokens=self.related_records_tokens,
            related_record_count=self.max_related_records,
            total_input_tokens=self.input_tokens,
            semantic_output_tokens=self.output_tokens,
        )


@dataclass(frozen=True)
class RecallBudgetConfiguration:
    total_tokens: int = 4_000
    per_document_tokens: int = 1_500
    exact_continuation_tokens: int = 2_000
    max_results: int = 6


@dataclass(frozen=True)
class InteractionBudgetConfiguration:
    auto_load_tokens: int = 500


@dataclass(frozen=True)
class BudgetConfiguration:
    processor: ProcessorBudgetConfiguration = field(default_factory=ProcessorBudgetConfiguration)
    recall: RecallBudgetConfiguration = field(default_factory=RecallBudgetConfiguration)
    interaction: InteractionBudgetConfiguration = field(
        default_factory=InteractionBudgetConfiguration
    )


@dataclass(frozen=True)
class VaultConfiguration:
    schema_version: str
    provider: ProviderConfiguration
    lifecycle: LifecycleConfiguration
    cadence: CadenceConfiguration
    policies: PolicyConfiguration
    retry: RetryConfiguration
    budgets: BudgetConfiguration


@dataclass(frozen=True)
class ValidatedConfiguration:
    """One immutable configuration value used by the current process."""

    host: HostConfiguration
    vault: VaultConfiguration
    project_registry: ProjectRegistry


def load_configuration(
    host_config_path: str | os.PathLike[str],
    *,
    environ: Mapping[str, str] | None = None,
    registered_provider_adapters: Collection[str],
) -> ValidatedConfiguration:
    """Load and validate host, vault, registry, policy, and budget settings.

    Loading is deliberately read-only.  The registered Adapter collection is
    supplied by the local runtime; validating it does not invoke the Adapter.
    """

    source = Path(host_config_path)
    if not source.is_file():
        raise ConfigurationError("required host configuration is missing")
    host_value = _load_yaml_mapping(source, "host configuration")
    environment = os.environ if environ is None else environ
    env_vault = environment.get("ORCA_VAULT_PATH")
    host = _validate_host(host_value, env_vault=env_vault)
    registry = _load_project_registry(host.vault_path)
    _validate_mapping_identities(host.project_root_mappings, registry)
    vault_path = host.vault_path / VAULT_CONFIG_RELATIVE_PATH
    _require_under(host.vault_path, vault_path, "vault configuration")
    vault_value = _load_yaml_mapping(vault_path, "vault configuration")
    vault = _validate_vault(vault_value, registered_provider_adapters)
    return ValidatedConfiguration(host, vault, registry)


def _validate_host(value: Mapping[str, Any], *, env_vault: str | None) -> HostConfiguration:
    _validate_keys(value, _HOST_KEYS, _HOST_REQUIRED_KEYS, "host configuration")
    if type(value["schema_version"]) is not int or value["schema_version"] != HOST_SCHEMA:
        raise ConfigurationError("unsupported host schema_version")
    host_id = _required_text(value["host_id"], "host_id")
    if not _HOST_ID.fullmatch(host_id):
        raise ConfigurationError("host_id has an invalid format")
    if value["runtime"] != "wsl":
        raise ConfigurationError("runtime must be wsl in Phase 1")

    file_vault = value.get("vault_path")
    file_path = _optional_path(file_vault, "vault_path", require_exists=True)
    env_path = _optional_path(env_vault, "ORCA_VAULT_PATH", require_exists=True)
    if file_path is None and env_path is None:
        raise ConfigurationError("vault_path is required from host configuration or environment")
    if file_path is not None and env_path is not None and file_path != env_path:
        raise ConfigurationError("vault_path conflicts with ORCA_VAULT_PATH")
    vault_path = file_path or env_path
    assert vault_path is not None

    runtime_path = _required_path(value["runtime_path"], "runtime_path", require_exists=True)
    connectors = _strict_group(value["connectors"], {"codex"}, {"codex"}, "connectors")
    codex = _strict_group(
        connectors["codex"], {"rollout_store"}, {"rollout_store"}, "connectors.codex"
    )
    rollout_store = _required_path(
        codex["rollout_store"], "connectors.codex.rollout_store", require_exists=True
    )
    _require_outside(vault_path, runtime_path, "runtime_path")
    _require_outside(vault_path, rollout_store, "connectors.codex.rollout_store")

    raw_mappings = value["project_root_mappings"]
    if not isinstance(raw_mappings, list):
        raise ConfigurationError("project_root_mappings must be a sequence")
    mappings: list[RootMapping] = []
    seen_roots: set[Path] = set()
    for index, raw in enumerate(raw_mappings):
        group = _strict_group(
            raw,
            {"root", "project_id"},
            {"root", "project_id"},
            f"project_root_mappings[{index}]",
        )
        try:
            mapping = RootMapping(
                _required_path(group["root"], f"project_root_mappings[{index}].root"),
                _required_text(group["project_id"], f"project_root_mappings[{index}].project_id"),
            )
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(str(exc)) from exc
        if mapping.normalized_root in seen_roots:
            raise ConfigurationError("duplicate normalized project root mapping")
        _require_outside(
            vault_path,
            mapping.normalized_root,
            f"project_root_mappings[{index}].root",
        )
        seen_roots.add(mapping.normalized_root)
        mappings.append(mapping)

    private_roots = tuple(mapping.normalized_root for mapping in mappings)
    for path in (vault_path, rollout_store):
        worktree_root = _git_worktree_root(path)
        if worktree_root is not None:
            private_roots += (worktree_root,)
    for boundary in private_roots:
        _require_outside_root(boundary, vault_path, "vault_path")
        _require_outside_root(boundary, rollout_store, "connectors.codex.rollout_store")

    return HostConfiguration(
        HOST_SCHEMA,
        host_id,
        "wsl",
        vault_path,
        runtime_path,
        rollout_store,
        tuple(mappings),
    )


def _validate_vault(
    value: Mapping[str, Any], registered_provider_adapters: Collection[str]
) -> VaultConfiguration:
    _validate_keys(value, _VAULT_KEYS, _VAULT_REQUIRED_KEYS, "vault configuration")
    if value["schema_version"] != VAULT_SCHEMA:
        raise ConfigurationError("unsupported vault schema_version")

    provider = _strict_group(
        value["provider"], {"adapter", "model"}, {"adapter", "model"}, "provider"
    )
    adapter = _required_text(provider["adapter"], "provider.adapter")
    model = _required_text(provider["model"], "provider.model")
    if adapter not in registered_provider_adapters:
        raise ConfigurationError("provider.adapter is not registered")

    lifecycle_value = _strict_group(
        value.get("lifecycle", {}), {"enabled"}, set(), "lifecycle"
    )
    lifecycle = LifecycleConfiguration(
        _boolean(lifecycle_value.get("enabled", False), "lifecycle.enabled")
    )

    cadence_value = _strict_group(
        value.get("cadence", {}),
        {"catch_up_minutes", "index_reconcile_minutes"},
        set(),
        "cadence",
    )
    cadence = CadenceConfiguration(
        _positive_int(cadence_value.get("catch_up_minutes", 15), "cadence.catch_up_minutes"),
        _positive_int(
            cadence_value.get("index_reconcile_minutes", 15),
            "cadence.index_reconcile_minutes",
        ),
    )

    privacy = _strict_group(
        value["privacy"], {"redaction_policy"}, {"redaction_policy"}, "privacy"
    )
    processing = _strict_group(
        value["processing"], {"processor_policy"}, {"processor_policy"}, "processing"
    )
    interaction = _strict_group(
        value["interaction"],
        {"observation_policy", "aggregation_policy", "guidance_policy"},
        {"observation_policy", "aggregation_policy", "guidance_policy"},
        "interaction",
    )
    policies = PolicyConfiguration(
        _exact(privacy["redaction_policy"], REDACTION_POLICY, "privacy.redaction_policy"),
        _exact(processing["processor_policy"], PROCESSOR_POLICY, "processing.processor_policy"),
        _exact(
            interaction["observation_policy"],
            OBSERVATION_POLICY,
            "interaction.observation_policy",
        ),
        _exact(
            interaction["aggregation_policy"],
            AGGREGATION_POLICY,
            "interaction.aggregation_policy",
        ),
        _exact(interaction["guidance_policy"], GUIDANCE_POLICY, "interaction.guidance_policy"),
    )

    retry_value = _strict_group(
        value.get("retry", {}), {"max_attempts", "retention_hours"}, set(), "retry"
    )
    retry = RetryConfiguration(
        _positive_int(retry_value.get("max_attempts", 3), "retry.max_attempts"),
        _positive_int(retry_value.get("retention_hours", 72), "retry.retention_hours"),
    )
    if retry.max_attempts > 3:
        raise ConfigurationError("retry.max_attempts exceeds the accepted ceiling")
    budgets = _validate_budgets(value.get("budgets", {}))
    return VaultConfiguration(
        VAULT_SCHEMA,
        ProviderConfiguration(adapter, model),
        lifecycle,
        cadence,
        policies,
        retry,
        budgets,
    )


def _validate_budgets(value: Any) -> BudgetConfiguration:
    groups = _strict_group(value, {"processor", "recall", "interaction"}, set(), "budgets")
    processor = _budget_group(
        groups.get("processor", {}), ProcessorBudgetConfiguration, "budgets.processor"
    )
    recall = _budget_group(groups.get("recall", {}), RecallBudgetConfiguration, "budgets.recall")
    interaction = _budget_group(
        groups.get("interaction", {}), InteractionBudgetConfiguration, "budgets.interaction"
    )
    if any(
        getattr(processor, field) > processor.input_tokens
        for field in (
            "new_evidence_tokens",
            "preceding_overlap_tokens",
            "continuation_summary_tokens",
            "project_summary_tokens",
            "related_records_tokens",
        )
    ):
        raise ConfigurationError("processor category ceiling exceeds input_tokens")
    if processor.input_tokens + processor.output_tokens > processor.model_window_tokens:
        raise ConfigurationError("processor input and output do not fit model_window_tokens")
    if recall.per_document_tokens > recall.total_tokens:
        raise ConfigurationError("recall per_document_tokens exceeds total_tokens")
    if recall.exact_continuation_tokens > recall.total_tokens:
        raise ConfigurationError("recall exact_continuation_tokens exceeds total_tokens")
    try:
        processor.as_processing_budget()
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc
    return BudgetConfiguration(processor, recall, interaction)


def _budget_group(value: Any, value_type: type[Any], label: str) -> Any:
    defaults = value_type()
    allowed = set(defaults.__dataclass_fields__)
    group = _strict_group(value, allowed, set(), label)
    values: dict[str, int] = {}
    for field in allowed:
        accepted = getattr(defaults, field)
        configured = _positive_int(group.get(field, accepted), f"{label}.{field}")
        if configured > accepted:
            raise ConfigurationError(f"{label}.{field} exceeds the accepted ceiling")
        values[field] = configured
    return value_type(**values)


def _load_project_registry(vault_path: Path) -> ProjectRegistry:
    root = vault_path / "System" / "Orca Memory" / "shallow" / "projects"
    _require_under(vault_path, root, "Project Registry")
    records = []
    if root.exists():
        for path in sorted(root.glob("*/project.md")):
            if not path.is_file():
                raise ConfigurationError("Project Registry contains an invalid project.md")
            _require_under(vault_path, path, "Project Registry project.md")
            try:
                records.append(validate_project_record(path.read_text(encoding="utf-8")))
            except (OSError, TypeError, ValueError) as exc:
                raise ConfigurationError(
                    "Project Registry contains an invalid project.md"
                ) from exc
    try:
        return ProjectRegistry(tuple(records))
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(str(exc)) from exc


def _validate_mapping_identities(
    mappings: tuple[RootMapping, ...], registry: ProjectRegistry
) -> None:
    for mapping in mappings:
        if registry.by_id(mapping.project_id) is None:
            raise ConfigurationError("project root mapping names an unknown project_id")


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader: yaml.Loader, node: yaml.Node, deep: bool = False) -> Any:
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ConfigurationError("configuration contains a duplicate key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _load_yaml_mapping(path: Path, label: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ConfigurationError(f"required {label} is missing")
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except ConfigurationError:
        raise
    except (OSError, TypeError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"invalid {label}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ConfigurationError(f"{label} keys must be strings")
    return value


def _validate_keys(
    value: Mapping[str, Any], allowed: set[str], required: set[str], label: str
) -> None:
    unknown = set(value) - allowed
    missing = required - set(value)
    if unknown:
        raise ConfigurationError(f"{label} contains unknown key: {sorted(unknown)[0]}")
    if missing:
        raise ConfigurationError(f"{label} is missing required key: {sorted(missing)[0]}")


def _strict_group(
    value: Any, allowed: set[str], required: set[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ConfigurationError(f"{label} keys must be strings")
    _validate_keys(value, allowed, required, label)
    return value


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ConfigurationError(f"{label} must be nonempty text")
    return value


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigurationError(f"{label} must be a positive integer")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{label} must be a boolean")
    return value


def _exact(value: Any, expected: str, label: str) -> str:
    if value != expected:
        raise ConfigurationError(f"unsupported {label}")
    return expected


def _optional_path(value: Any, label: str, *, require_exists: bool) -> Path | None:
    if value is None:
        return None
    return _required_path(value, label, require_exists=require_exists)


def _required_path(value: Any, label: str, *, require_exists: bool = False) -> Path:
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{label} must be an absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ConfigurationError(f"{label} must be an absolute path")
    try:
        normalized = path.resolve(strict=require_exists)
    except OSError as exc:
        raise ConfigurationError(f"{label} is inaccessible") from exc
    if require_exists and not normalized.is_dir():
        raise ConfigurationError(f"{label} must be an accessible directory")
    return Path(os.path.normcase(str(normalized)))


def _require_outside(vault: Path, candidate: Path, label: str) -> None:
    if candidate == vault or vault in candidate.parents:
        raise ConfigurationError(f"{label} must be outside the vault")


def _require_outside_root(boundary: Path, candidate: Path, label: str) -> None:
    """Reject private state at or below one project or Git root."""

    if candidate == boundary or boundary in candidate.parents:
        raise ConfigurationError(f"{label} must be outside the project checkout")


def _git_worktree_root(path: Path) -> Path | None:
    """Find one valid Git worktree boundary containing ``path``.

    An empty ``.git`` directory is ignored because it is not enough evidence
    of a checkout.  A linked-worktree ``.git`` file and a normal marker with
    its core entries are accepted.  A partial or unreadable marker fails
    closed so a private path is never accepted on uncertain evidence.
    """

    probe = path
    while not probe.exists() and not probe.is_symlink() and probe != probe.parent:
        probe = probe.parent
    for candidate in (probe, *probe.parents):
        marker = candidate / ".git"
        try:
            marker_info = marker.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ConfigurationError("cannot inspect Git worktree boundary") from exc
        if stat.S_ISLNK(marker_info.st_mode):
            try:
                marker = marker.resolve(strict=True)
                marker_info = marker.stat()
            except OSError as exc:
                raise ConfigurationError("Git worktree marker is unreadable") from exc
        if stat.S_ISREG(marker_info.st_mode):
            try:
                lines = marker.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                raise ConfigurationError("Git worktree marker is unreadable") from exc
            if len(lines) != 1 or not lines[0].startswith("gitdir: "):
                raise ConfigurationError("ambiguous Git worktree marker")
            raw_gitdir = lines[0][len("gitdir: ") :].strip()
            if not raw_gitdir or "\x00" in raw_gitdir:
                raise ConfigurationError("ambiguous Git worktree marker")
            gitdir = Path(raw_gitdir)
            if not gitdir.is_absolute():
                gitdir = candidate / gitdir
            try:
                if not gitdir.resolve(strict=True).is_dir():
                    raise ConfigurationError("Git worktree marker is unreadable")
            except OSError as exc:
                raise ConfigurationError("Git worktree marker is unreadable") from exc
            try:
                return Path(os.path.normcase(str(candidate.resolve(strict=True))))
            except OSError as exc:
                raise ConfigurationError("Git worktree root is unreadable") from exc
        if not stat.S_ISDIR(marker_info.st_mode):
            raise ConfigurationError("ambiguous Git worktree marker")

        expected = {"HEAD": stat.S_ISREG, "config": stat.S_ISREG,
                    "objects": stat.S_ISDIR, "refs": stat.S_ISDIR}
        present = False
        valid = True
        found: set[str] = set()
        for name, kind in expected.items():
            entry = marker / name
            try:
                info = entry.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ConfigurationError("Git worktree marker is unreadable") from exc
            present = True
            found.add(name)
            valid = valid and not stat.S_ISLNK(info.st_mode) and kind(info.st_mode)
        if not present:
            continue
        if not valid or found != set(expected):
            raise ConfigurationError("ambiguous Git worktree marker")
        try:
            return Path(os.path.normcase(str(candidate.resolve(strict=True))))
        except OSError as exc:
            raise ConfigurationError("Git worktree root is unreadable") from exc
    return None
def _require_under(vault: Path, candidate: Path, label: str) -> None:
    try:
        resolved = candidate.resolve(strict=False)
    except OSError as exc:
        raise ConfigurationError(f"cannot normalize {label}") from exc
    if vault not in resolved.parents:
        raise ConfigurationError(f"{label} must remain inside the vault")


__all__ = [
    "BudgetConfiguration",
    "CadenceConfiguration",
    "ConfigurationError",
    "HostConfiguration",
    "InteractionBudgetConfiguration",
    "LifecycleConfiguration",
    "PolicyConfiguration",
    "ProcessorBudgetConfiguration",
    "ProviderConfiguration",
    "RecallBudgetConfiguration",
    "RetryConfiguration",
    "ValidatedConfiguration",
    "VaultConfiguration",
    "load_configuration",
]
