"""Deterministic Project Registry and local project-root resolution.

Project identity records are durable vault artifacts, but project roots and
Git metadata are host-local evidence.  This module keeps those concerns
separate: it validates and renders ``project.md`` records and produces
immutable mapping plans for a caller that owns the local configuration and
recovery protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Callable, Collection, Iterable, Literal, Mapping, Sequence
import unicodedata


PROJECT_SCHEMA = "orca-project/0.1"
MAPPING_INTENT_SCHEMA = "orca-project-mapping-intent/0.1"
PROJECT_AUTHORITY = "noncanonical"
REGISTRATION_METHOD = "owner-confirmed"
RESERVED_PROJECT_ALIASES = frozenset({"general", "unassigned"})
_WINDOWS_RESERVED_SLUGS = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
)

ResolutionStatus = Literal[
    "mapped", "worktree-reused", "owner-choice-required", "unassigned", "error"
]
MappingAction = Literal["register", "relink", "worktree-reuse"]
OwnerChoice = Literal["create", "link", "unassigned"]

_PROJECT_ID = re.compile(r"^proj_[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_FRONTMATTER_KEYS = (
    "schema_version",
    "project_id",
    "project_alias",
    "authority",
    "registration_method",
    "created_at",
    "updated_at",
)


def normalize_root(root: str | os.PathLike[str], *, require_exists: bool = False) -> Path:
    """Return one absolute host-local root in the platform's comparison form.

    ``resolve`` removes symlinks and redundant separators.  A mapping may
    point to a directory that was moved or is currently unavailable, so the
    default is non-strict.  Workspace discovery should use ``require_exists``.
    """

    path = Path(root)
    if not path.is_absolute():
        raise ValueError(f"project root must be absolute: {root!r}")
    try:
        path = path.resolve(strict=require_exists)
    except OSError as exc:
        raise ValueError(f"cannot normalize project root: {root!r}") from exc
    # normcase is a no-op on case-sensitive hosts and lowercases Windows paths.
    return Path(os.path.normcase(str(path)))


def project_alias_slug(alias: str) -> str:
    """Build the portable locator slug for one Project Alias.

    This follows the Memory Model's semantic-slug normalization, with the
    additional project-specific requirement that an alias cannot become an
    empty or reserved locator.
    """

    _validate_alias_text(alias)
    value = unicodedata.normalize("NFC", alias).casefold()
    chars: list[str] = []
    for char in value:
        if char.isalnum():
            chars.append(char)
        else:
            chars.append("-")
    slug = re.sub(r"-+", "-", "".join(chars)).strip("-")
    if not slug:
        raise ValueError("project alias does not produce a portable slug")
    if slug in RESERVED_PROJECT_ALIASES:
        raise ValueError(f"reserved project alias: {alias!r}")
    if slug in _WINDOWS_RESERVED_SLUGS:
        raise ValueError(f"nonportable project alias: {alias!r}")
    if len(slug) > 72:
        slug = slug[:72].rstrip("-")
    if not slug:
        raise ValueError("project alias does not produce a portable slug")
    return slug


def allocate_project_id(
    id_factory: Callable[[], str],
    *,
    existing_ids: Collection[str] = (),
    max_attempts: int = 100,
) -> str:
    """Allocate one opaque permanent ID from a Storage-owned source.

    IDs are deliberately independent of aliases, roots, Git metadata, and
    hashes.  ``existing_ids`` makes retries and collision handling explicit;
    callers can persist the resulting ID in a mapping intent before any final
    artifact changes.
    """

    if not callable(id_factory):
        raise TypeError("id_factory must be callable")
    if not isinstance(max_attempts, int) or max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    occupied = set(existing_ids)
    for _ in range(max_attempts):
        candidate = id_factory()
        _validate_project_id(candidate)
        if candidate not in occupied:
            return candidate
    raise ValueError("project ID allocator exhausted without a unique ID")


@dataclass(frozen=True)
class ProjectRecord:
    """Validated durable identity represented by one ``project.md`` file."""

    project_id: str
    project_alias: str
    created_at: str | datetime
    updated_at: str | datetime
    schema_version: str = PROJECT_SCHEMA
    authority: str = PROJECT_AUTHORITY
    registration_method: str = REGISTRATION_METHOD

    def __post_init__(self) -> None:
        _validate_project_id(self.project_id)
        _validate_alias_text(self.project_alias)
        project_alias_slug(self.project_alias)
        if self.schema_version != PROJECT_SCHEMA:
            raise ValueError(f"unsupported project schema: {self.schema_version!r}")
        if self.authority != PROJECT_AUTHORITY:
            raise ValueError("project authority must be noncanonical")
        if self.registration_method != REGISTRATION_METHOD:
            raise ValueError("project registration_method must be owner-confirmed")
        created = _utc_timestamp(self.created_at, "created_at")
        updated = _utc_timestamp(self.updated_at, "updated_at")
        if _parse_timestamp(updated) < _parse_timestamp(created):
            raise ValueError("updated_at cannot precede created_at")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "updated_at", updated)

    @property
    def alias_slug(self) -> str:
        return project_alias_slug(self.project_alias)

    def render(self) -> str:
        """Render the exact noncanonical project registry artifact."""

        # Only the accepted identity fields are emitted.  In particular, this
        # cannot accidentally copy a root, remote, branch, or Git common dir.
        return "\n".join(
            (
                "---",
                f"schema_version: {self.schema_version}",
                f"project_id: {self.project_id}",
                f"project_alias: {_yaml_scalar(self.project_alias)}",
                f"authority: {self.authority}",
                f"registration_method: {self.registration_method}",
                f"created_at: {self.created_at}",
                f"updated_at: {self.updated_at}",
                "---",
                f"# {self.project_alias}",
                "",
                "Project registry identity record.",
                "",
            )
        )

    @classmethod
    def parse(cls, markdown: str) -> "ProjectRecord":
        """Parse and strictly validate one rendered ``project.md`` record."""

        if not isinstance(markdown, str):
            raise TypeError("project record must be text")
        lines = markdown.splitlines()
        if len(lines) < 4 or lines[0] != "---":
            raise ValueError("project.md must start with YAML frontmatter")
        try:
            end = lines.index("---", 1)
        except ValueError as exc:
            raise ValueError("project.md frontmatter is not closed") from exc
        frontmatter = lines[1:end]
        if len(frontmatter) != len(_FRONTMATTER_KEYS):
            raise ValueError("project.md has an unexpected frontmatter shape")
        values: dict[str, str] = {}
        for line, expected_key in zip(frontmatter, _FRONTMATTER_KEYS):
            if ":" not in line:
                raise ValueError(f"invalid project frontmatter line: {line!r}")
            key, raw = line.split(":", 1)
            if key != expected_key or key in values:
                raise ValueError("project.md frontmatter keys are not canonical")
            values[key] = _parse_yaml_scalar(raw.strip())
        body = "\n".join(lines[end + 1 :])
        expected_body = f"# {values['project_alias']}\n\nProject registry identity record."
        if body != expected_body:
            raise ValueError("project.md body does not match its identity record")
        return cls(
            project_id=values["project_id"],
            project_alias=values["project_alias"],
            schema_version=values["schema_version"],
            authority=values["authority"],
            registration_method=values["registration_method"],
            created_at=values["created_at"],
            updated_at=values["updated_at"],
        )


@dataclass(frozen=True)
class RootMapping:
    """One host-local normalized root-to-project association."""

    root: str | os.PathLike[str]
    project_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", normalize_root(self.root))
        _validate_project_id(self.project_id)

    @property
    def normalized_root(self) -> Path:
        """Canonical name for the root used in exact comparisons."""

        return self.root


@dataclass(frozen=True)
class WorktreeEvidence:
    """Local Git evidence supplied by discovery, never stored in project.md."""

    root: str | os.PathLike[str]
    common_dir: str | os.PathLike[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", normalize_root(self.root))
        object.__setattr__(self, "common_dir", normalize_root(self.common_dir))

    @property
    def normalized_root(self) -> Path:
        return self.root

    @property
    def normalized_common_dir(self) -> Path:
        return self.common_dir


@dataclass(frozen=True)
class MappingPlan:
    """A deterministic local mapping change for the caller's recovery layer."""

    action: MappingAction
    root: Path
    project_id: str
    project_alias: str
    project_record: ProjectRecord | None = None
    git_common_dir: Path | None = None

    def __post_init__(self) -> None:
        if self.action not in {"register", "relink", "worktree-reuse"}:
            raise ValueError(f"unsupported mapping action: {self.action!r}")
        object.__setattr__(self, "root", normalize_root(self.root))
        if self.git_common_dir is not None:
            object.__setattr__(self, "git_common_dir", normalize_root(self.git_common_dir))
        _validate_project_id(self.project_id)
        _validate_alias_text(self.project_alias)
        project_alias_slug(self.project_alias)
        if self.action == "register":
            if (
                self.project_record is None
                or self.project_record.project_id != self.project_id
                or self.project_record.project_alias != self.project_alias
            ):
                raise ValueError("registration plan requires its matching project record")
        elif self.action == "worktree-reuse" and self.git_common_dir is None:
            raise ValueError("worktree-reuse plan requires Git common-directory evidence")
        elif self.project_record is not None:
            raise ValueError("relink and worktree plans cannot rewrite project.md")


@dataclass(frozen=True)
class ProjectResolution:
    """One deterministic discovery result and optional local mapping plan."""

    status: ResolutionStatus
    root: Path | None = None
    project_id: str | None = None
    project_alias: str | None = None
    reason: str | None = None
    candidate_project_ids: tuple[str, ...] = ()
    mapping_plan: MappingPlan | None = None

    def __post_init__(self) -> None:
        if self.status not in {
            "mapped",
            "worktree-reused",
            "owner-choice-required",
            "unassigned",
            "error",
        }:
            raise ValueError(f"unsupported project resolution status: {self.status!r}")
        if self.status in {"mapped", "worktree-reused"}:
            if self.root is None or self.project_id is None or self.project_alias is None:
                raise ValueError(f"{self.status} result requires a project identity")
        if self.status == "unassigned" and self.mapping_plan is not None:
            raise ValueError("Unassigned resolution cannot carry a mapping plan")
        if self.root is not None:
            object.__setattr__(self, "root", normalize_root(self.root))
        if self.project_id is not None:
            _validate_project_id(self.project_id)

    @property
    def allows_project_processing(self) -> bool:
        return self.status in {"mapped", "worktree-reused"}


@dataclass(frozen=True)
class ProjectRegistry:
    """Validated collection of durable Project Identity records."""

    records: tuple[ProjectRecord, ...] = ()

    def __post_init__(self) -> None:
        records = tuple(self.records)
        by_id: set[str] = set()
        by_alias: dict[str, ProjectRecord] = {}
        by_slug: dict[str, ProjectRecord] = {}
        for record in records:
            if not isinstance(record, ProjectRecord):
                raise TypeError("registry records must be ProjectRecord values")
            if record.project_id in by_id:
                raise ValueError(f"duplicate project_id: {record.project_id}")
            by_id.add(record.project_id)
            alias_key = record.project_alias.casefold()
            slug_key = record.alias_slug.casefold()
            if alias_key in by_alias:
                raise ValueError(f"project alias collision: {record.project_alias!r}")
            if slug_key in by_slug:
                raise ValueError(f"project alias slug collision: {record.alias_slug!r}")
            by_alias[alias_key] = record
            by_slug[slug_key] = record
        object.__setattr__(self, "records", records)

    @classmethod
    def from_markdown(cls, values: Iterable[str]) -> "ProjectRegistry":
        return cls(tuple(ProjectRecord.parse(value) for value in values))

    def by_id(self, project_id: str) -> ProjectRecord | None:
        matches = [record for record in self.records if record.project_id == project_id]
        if len(matches) > 1:
            raise ValueError(f"duplicate project identity: {project_id}")
        return matches[0] if matches else None

    def by_alias(self, alias: str) -> ProjectRecord | None:
        key = alias.casefold() if isinstance(alias, str) else ""
        matches = [record for record in self.records if record.project_alias.casefold() == key]
        if len(matches) > 1:
            raise ValueError(f"ambiguous project alias: {alias!r}")
        return matches[0] if matches else None

    def add(self, record: ProjectRecord) -> "ProjectRegistry":
        return ProjectRegistry(self.records + (record,))

    @property
    def projects(self) -> tuple[ProjectRecord, ...]:
        """Domain-language alias for the registry's validated records."""

        return self.records


def render_project_record(record: ProjectRecord) -> str:
    """Functional wrapper for callers that do not need the record method."""

    return record.render()


def validate_project_record(markdown: str) -> ProjectRecord:
    """Validate and parse a complete ``project.md`` payload."""

    return ProjectRecord.parse(markdown)


def prepare_registration(
    root: str | os.PathLike[str],
    project_alias: str,
    registry: ProjectRegistry,
    *,
    project_id: str,
    now: str | datetime,
    git_common_dir: str | os.PathLike[str] | None = None,
) -> MappingPlan:
    """Prepare a new Project Registration without changing either filesystem.

    Alias validation happens before accepting the Storage-supplied permanent
    ID.  The caller should persist this fixed plan in its mapping intent before
    publishing the rendered record or changing host configuration.
    """

    _validate_unique_alias(project_alias, registry)
    _validate_project_id(project_id)
    if registry.by_id(project_id) is not None:
        raise ValueError(f"project ID already exists: {project_id}")
    record = ProjectRecord(
        project_id=project_id,
        project_alias=project_alias,
        created_at=now,
        updated_at=now,
    )
    return MappingPlan(
        action="register",
        root=normalize_root(root),
        project_id=project_id,
        project_alias=project_alias,
        project_record=record,
        git_common_dir=git_common_dir,
    )


def prepare_relink(
    root: str | os.PathLike[str],
    registry: ProjectRegistry,
    *,
    project_id: str | None = None,
    project_alias: str | None = None,
) -> MappingPlan:
    """Prepare an Owner-confirmed relink to one existing Project Identity."""

    if (project_id is None) == (project_alias is None):
        raise ValueError("relink requires exactly one project_id or project_alias")
    record = registry.by_id(project_id) if project_id is not None else registry.by_alias(project_alias or "")
    if record is None:
        raise ValueError("selected project identity does not exist")
    return MappingPlan(
        action="relink",
        root=normalize_root(root),
        project_id=record.project_id,
        project_alias=record.project_alias,
    )


def resolve_project(
    workspace_root: str | os.PathLike[str],
    mappings: Iterable[RootMapping | Mapping[str, str] | tuple[str, str]],
    registry: ProjectRegistry,
    *,
    git_root: str | os.PathLike[str] | None = None,
    git_common_dir: str | os.PathLike[str] | None = None,
    mapped_worktrees: Iterable[WorktreeEvidence | tuple[str, str]] = (),
    owner_choice: OwnerChoice | None = None,
) -> ProjectResolution:
    """Resolve one workspace using only exact local evidence.

    ``mapped_worktrees`` is discovery evidence for existing mapped roots; it
    is intentionally not part of ``RootMapping`` or any rendered vault record.
    The resolver never writes host configuration.  Unknown roots return
    ``owner-choice-required`` unless the caller explicitly chooses
    ``unassigned``.
    """

    if owner_choice not in {None, "create", "link", "unassigned"}:
        raise ValueError(f"unsupported Owner choice: {owner_choice!r}")
    try:
        root = normalize_root(workspace_root, require_exists=True)
        if not root.is_dir():
            raise ValueError("workspace root must be an existing directory")
        effective_root = normalize_root(git_root, require_exists=True) if git_root else root
        if not effective_root.is_dir():
            raise ValueError("Git workspace root must be an existing directory")
        if git_root is None and git_common_dir is not None:
            # Common-dir evidence without an explicit Git root is still useful,
            # but the workspace root remains the selected local root.
            current_common = normalize_root(git_common_dir)
        else:
            current_common = normalize_root(git_common_dir) if git_common_dir else None
        normalized_mappings = _coerce_mappings(mappings)
        _validate_mapping_set(normalized_mappings)
        for mapping in normalized_mappings:
            if mapping.root == effective_root:
                record = registry.by_id(mapping.project_id)
                if record is None:
                    return ProjectResolution(
                        "error",
                        effective_root,
                        reason=f"mapping points to missing project identity: {mapping.project_id}",
                    )
                return ProjectResolution(
                    "mapped",
                    effective_root,
                    record.project_id,
                    record.project_alias,
                    reason="exact local root mapping",
                )

        if current_common is not None:
            evidence = _coerce_worktrees(mapped_worktrees)
            evidence_by_root: dict[Path, Path] = {}
            for item in evidence:
                prior_common = evidence_by_root.get(item.root)
                if prior_common is not None and prior_common != item.common_dir:
                    if owner_choice == "unassigned":
                        return ProjectResolution(
                            "unassigned",
                            effective_root,
                            reason="Owner chose to keep conflicting Git evidence Unassigned",
                        )
                    return ProjectResolution(
                        "owner-choice-required",
                        effective_root,
                        reason="conflicting Git common-directory evidence",
                    )
                evidence_by_root[item.root] = item.common_dir
            candidates: dict[str, WorktreeEvidence] = {}
            for item in evidence:
                if item.common_dir != current_common:
                    continue
                mapping = next((m for m in normalized_mappings if m.root == item.root), None)
                if mapping is None:
                    continue
                record = registry.by_id(mapping.project_id)
                if record is None:
                    return ProjectResolution(
                        "error",
                        effective_root,
                        reason=f"worktree mapping points to missing project identity: {mapping.project_id}",
                    )
                candidates.setdefault(record.project_id, item)
            project_ids = tuple(sorted(candidates))
            if len(project_ids) == 1:
                project_id = project_ids[0]
                record = registry.by_id(project_id)
                assert record is not None
                return ProjectResolution(
                    "worktree-reused",
                    effective_root,
                    project_id,
                    record.project_alias,
                    reason="exact nonconflicting Git common directory",
                    mapping_plan=MappingPlan(
                        action="worktree-reuse",
                        root=effective_root,
                        project_id=record.project_id,
                        project_alias=record.project_alias,
                        git_common_dir=current_common,
                    ),
                )
            if len(project_ids) > 1:
                if owner_choice == "unassigned":
                    return ProjectResolution(
                        "unassigned",
                        effective_root,
                        reason="Owner chose to keep conflicting project evidence Unassigned",
                    )
                return ProjectResolution(
                    "owner-choice-required",
                    effective_root,
                    reason="Git common directory matches conflicting project identities",
                    candidate_project_ids=project_ids,
                )

        if owner_choice == "unassigned":
            return ProjectResolution(
                "unassigned",
                effective_root,
                reason="Owner chose to keep the unknown root Unassigned",
            )
        return ProjectResolution(
            "owner-choice-required",
            effective_root,
            reason="no exact project mapping or nonconflicting worktree evidence",
        )
    except (OSError, TypeError, ValueError) as exc:
        # Discovery failures are a deterministic error result.  Callers still
        # get the exception text without any private file contents being read
        # or emitted by this module.
        return ProjectResolution("error", reason=str(exc))


def _validate_project_id(project_id: str) -> None:
    if not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("project_id must match proj_<opaque-id>")


def _validate_alias_text(alias: str) -> None:
    if not isinstance(alias, str) or not alias.strip():
        raise ValueError("project alias is required")
    if _CONTROL.search(alias) or any(char in alias for char in "/\\"):
        raise ValueError("project alias contains nonportable characters")
    if alias != alias.strip() or alias.endswith((".", " ")):
        raise ValueError("project alias has nonportable leading/trailing whitespace")
    if alias.casefold() in RESERVED_PROJECT_ALIASES:
        raise ValueError(f"reserved project alias: {alias!r}")


def _validate_unique_alias(alias: str, registry: ProjectRegistry) -> None:
    _validate_alias_text(alias)
    slug = project_alias_slug(alias)
    if registry.by_alias(alias) is not None:
        raise ValueError(f"project alias collision: {alias!r}")
    if any(record.alias_slug.casefold() == slug.casefold() for record in registry.records):
        raise ValueError(f"project alias slug collision: {slug!r}")


def _utc_timestamp(value: str | datetime, field: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = _parse_timestamp(value)
    else:
        raise TypeError(f"{field} must be an ISO timestamp")
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError("timestamp must be a string")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp: {value!r}") from exc


def _yaml_scalar(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._+&()\-]*", value) and value.casefold() not in {
        "null",
        "true",
        "false",
        "yes",
        "no",
    }:
        return value
    return json.dumps(value, ensure_ascii=False)


def _parse_yaml_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid quoted project frontmatter scalar") from exc
        if not isinstance(parsed, str):
            raise ValueError("project frontmatter scalar must be text")
        return parsed
    if not value or value.startswith(("'", "[", "{", "|", ">")):
        raise ValueError("unsupported project frontmatter scalar")
    return value


def _coerce_mappings(
    mappings: Iterable[RootMapping | Mapping[str, str] | tuple[str, str]],
) -> tuple[RootMapping, ...]:
    if isinstance(mappings, Mapping):
        mappings = tuple(mappings.items())
    result: list[RootMapping] = []
    for value in mappings:
        if isinstance(value, RootMapping):
            result.append(value)
        elif isinstance(value, Mapping):
            if set(value) != {"root", "project_id"}:
                raise ValueError("project root mapping must contain root and project_id")
            result.append(RootMapping(value["root"], value["project_id"]))
        elif isinstance(value, tuple) and len(value) == 2:
            result.append(RootMapping(value[0], value[1]))
        else:
            raise TypeError("invalid project root mapping")
    return tuple(result)


def _validate_mapping_set(mappings: Sequence[RootMapping]) -> None:
    roots: dict[Path, str] = {}
    for mapping in mappings:
        prior = roots.get(mapping.root)
        if prior is not None:
            raise ValueError(f"duplicate normalized project root mapping: {mapping.root}")
        roots[mapping.root] = mapping.project_id


def _coerce_worktrees(
    evidence: Iterable[WorktreeEvidence | tuple[str, str]],
) -> tuple[WorktreeEvidence, ...]:
    if isinstance(evidence, Mapping):
        evidence = tuple(evidence.items())
    result: list[WorktreeEvidence] = []
    for value in evidence:
        if isinstance(value, WorktreeEvidence):
            result.append(value)
        elif isinstance(value, tuple) and len(value) == 2:
            result.append(WorktreeEvidence(value[0], value[1]))
        else:
            raise TypeError("invalid Git worktree evidence")
    return tuple(result)


# Domain-language aliases keep the API aligned with the accepted glossary
# while retaining the concise record/evidence names used internally.
ProjectIdentity = ProjectRecord
ProjectRootMapping = RootMapping
GitWorktreeEvidence = WorktreeEvidence


__all__ = [
    "MAPPING_INTENT_SCHEMA",
    "PROJECT_AUTHORITY",
    "PROJECT_SCHEMA",
    "REGISTRATION_METHOD",
    "RESERVED_PROJECT_ALIASES",
    "MappingPlan",
    "GitWorktreeEvidence",
    "ProjectIdentity",
    "ProjectRecord",
    "ProjectRegistry",
    "ProjectResolution",
    "ProjectRootMapping",
    "RootMapping",
    "WorktreeEvidence",
    "allocate_project_id",
    "normalize_root",
    "prepare_registration",
    "prepare_relink",
    "project_alias_slug",
    "render_project_record",
    "resolve_project",
    "validate_project_record",
]
