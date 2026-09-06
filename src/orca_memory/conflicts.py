"""Deterministic conflict variants and overflow candidates for Typed Memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Literal

import yaml

from orca_memory.memory import (
    MemoryRecord,
    MemoryValidationError,
    record_filename,
    scope_directory,
    semantic_slug,
    short_id,
)
from orca_memory.privacy import contains_secret


CONFLICT_OVERFLOW_SCHEMA = "orca-conflict-overflow/0.2"
LEGACY_CONFLICT_OVERFLOW_SCHEMA = "orca-conflict-overflow/0.1"
_VARIANT_ID = re.compile(r"^v([1-9][0-9]*)$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or contains_secret(value):
        raise MemoryValidationError(f"{name} must be safe non-empty text")
    return value.strip()


def _label(value: str) -> str:
    value = _text(value, "variant label")
    if "\n" in value or "\r" in value or "—" in value:
        raise MemoryValidationError("variant label must be one safe heading line")
    return value


def _position(value: str) -> str:
    value = _text(value, "variant position")
    if any(line.startswith("### ") for line in value.splitlines()):
        raise MemoryValidationError("variant position cannot inject a variant heading")
    return value


def _timestamp(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise MemoryValidationError(f"{name} must be a UTC RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise MemoryValidationError(f"{name} must use UTC")
    return parsed.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ConflictVariant:
    variant_id: str
    label: str
    position: str
    position_at: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.variant_id, str) or _VARIANT_ID.fullmatch(self.variant_id) is None:
            raise MemoryValidationError("invalid conflict variant_id")
        object.__setattr__(self, "label", _label(self.label))
        object.__setattr__(self, "position", _position(self.position))
        object.__setattr__(self, "position_at", _timestamp(self.position_at, "position_at"))


@dataclass(frozen=True)
class ConflictProposal:
    """Provider-owned meaning for a new or supported incompatible position."""

    target_memory_id: str
    kind: str
    subject: str
    scope: str
    scope_id: str
    label: str
    position: str
    position_at: str | None
    target_variant_id: str | None = None
    # Deterministic current-run segment locators supplied by the provider.
    source_segment_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.target_memory_id, str) or _SAFE_ID.fullmatch(self.target_memory_id) is None:
            raise MemoryValidationError("invalid conflict target_memory_id")
        semantic_slug(self.subject)
        _label(self.label)
        _position(self.position)
        _timestamp(self.position_at, "position_at")
        if self.target_variant_id is not None and _VARIANT_ID.fullmatch(self.target_variant_id) is None:
            raise MemoryValidationError("invalid target_variant_id")
        if not isinstance(self.source_segment_refs, (tuple, list)):
            raise MemoryValidationError("source_segment_refs must be a sequence")
        refs = tuple(self.source_segment_refs)
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise MemoryValidationError("source_segment_refs must contain non-empty strings")
        if len(set(refs)) != len(refs):
            raise MemoryValidationError("source_segment_refs must be unique")
        object.__setattr__(self, "source_segment_refs", refs)


@dataclass(frozen=True)
class SupersedeProposal:
    """Explicit replacement meaning; Storage retains compact prior lineage."""

    target_memory_id: str
    kind: str
    subject: str
    scope: str
    scope_id: str
    current: str
    source_updated_at: str | None
    context: str | None = None
    implications: str | None = None
    explicit_replacement: bool = True
    # Deterministic current-run segment locators supplied by the provider.
    source_segment_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.explicit_replacement:
            raise MemoryValidationError("supersession requires explicit replacement intent")
        if not isinstance(self.target_memory_id, str) or _SAFE_ID.fullmatch(self.target_memory_id) is None:
            raise MemoryValidationError("invalid supersede target_memory_id")
        semantic_slug(self.subject)
        _text(self.current, "superseding current meaning")
        if self.context is not None:
            _text(self.context, "superseding context")
        if self.implications is not None:
            _text(self.implications, "superseding implications")
        _timestamp(self.source_updated_at, "source_updated_at")
        if not isinstance(self.source_segment_refs, (tuple, list)):
            raise MemoryValidationError("source_segment_refs must be a sequence")
        refs = tuple(self.source_segment_refs)
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise MemoryValidationError("source_segment_refs must contain non-empty strings")
        if len(set(refs)) != len(refs):
            raise MemoryValidationError("source_segment_refs must be unique")
        object.__setattr__(self, "source_segment_refs", refs)


@dataclass(frozen=True)
class ConflictRecord:
    """One unresolved living Typed Memory Record with at most three variants."""

    memory_id: str
    kind: str
    subject: str
    scope: str
    scope_id: str
    source_updated_at: str | None
    created_at: str
    updated_at: str
    variants: tuple[ConflictVariant, ...]
    workstreams: tuple[str, ...] = ()
    review_state: Literal["none", "required", "acknowledged", "overflow"] = "none"
    status: Literal["conflict"] = "conflict"
    authority: Literal["noncanonical"] = "noncanonical"

    def __post_init__(self) -> None:
        if len(self.variants) not in {2, 3}:
            raise MemoryValidationError("a conflict requires two or three active variants")
        expected = tuple(f"v{index}" for index in range(1, len(self.variants) + 1))
        if tuple(item.variant_id for item in self.variants) != expected:
            raise MemoryValidationError("active conflict variants must be monotonic")
        if self.authority != "noncanonical" or self.status != "conflict":
            raise MemoryValidationError("conflict records remain noncanonical conflicts")
        if len(self.variants) == 2 and self.review_state not in {"none", "acknowledged", "overflow"}:
            raise MemoryValidationError("invalid two-variant review state")
        if len(self.variants) == 3 and self.review_state not in {"required", "acknowledged", "overflow"}:
            raise MemoryValidationError("three variants require review")
        # Reuse the ordinary record validator for core identity, scope, kind,
        # timestamps, subject, and workstream policy.
        MemoryRecord(
            memory_id=self.memory_id,
            kind=self.kind,
            subject=self.subject,
            scope=self.scope,
            scope_id=self.scope_id,
            status="current",
            source_updated_at=self.source_updated_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
            workstreams=self.workstreams,
            current="Conflict placeholder used only for core validation.",
        )

    @property
    def body(self) -> str:
        lines = [f"# {self.subject}", "", "## Conflict"]
        for variant in self.variants:
            lines.extend(
                (
                    "",
                    f"### {variant.variant_id} — {variant.label}",
                    "",
                    f"Position at: {variant.position_at or 'unknown'}",
                    "",
                    variant.position,
                )
            )
        return "\n".join(lines)

    def render(self) -> str:
        fields = (
            ("schema", "orca-memory/0.2"),
            ("memory_id", self.memory_id),
            ("kind", self.kind),
            ("subject", json.dumps(self.subject, ensure_ascii=False)),
            ("authority", "noncanonical"),
            ("scope", self.scope),
            ("scope_id", self.scope_id),
            ("status", "conflict"),
            ("review_state", self.review_state),
            ("source_updated_at", self.source_updated_at),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
            ("workstreams", list(self.workstreams)),
        )
        lines = ["---"]
        for key, value in fields:
            rendered = (
                "null"
                if value is None
                else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                if isinstance(value, list)
                else str(value)
            )
            lines.append(f"{key}: {rendered}")
        return "\n".join(lines + ["---", "", self.body, ""])


def parse_conflict_record(document: str) -> ConflictRecord:
    """Parse the strict conflict representation emitted by ``ConflictRecord``."""

    if not document.startswith("---\n") or "\n---\n" not in document[4:]:
        raise MemoryValidationError("conflict record requires frontmatter")
    marker = document.find("\n---\n", 4)
    metadata = yaml.safe_load(document[4:marker])
    expected = {
        "schema",
        "memory_id",
        "kind",
        "subject",
        "authority",
        "scope",
        "scope_id",
        "status",
        "review_state",
        "source_updated_at",
        "created_at",
        "updated_at",
        "workstreams",
    }
    if not isinstance(metadata, dict) or set(metadata) != expected:
        raise MemoryValidationError("invalid conflict frontmatter fields")
    if metadata["schema"] != "orca-memory/0.2":
        raise MemoryValidationError("unsupported conflict schema")
    for key in ("source_updated_at", "created_at", "updated_at"):
        if isinstance(metadata[key], datetime):
            metadata[key] = metadata[key].isoformat().replace("+00:00", "Z")
    body = document[marker + 5 :].strip()
    lines = body.splitlines()
    if lines[:3] != [f"# {metadata['subject']}", "", "## Conflict"]:
        raise MemoryValidationError("invalid conflict body heading")
    variants: list[ConflictVariant] = []
    index = 3
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        match = re.fullmatch(r"### (v[1-9][0-9]*) — (.+)", lines[index])
        if match is None:
            raise MemoryValidationError("invalid conflict variant heading")
        index += 1
        if index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines) or not lines[index].startswith("Position at: "):
            raise MemoryValidationError("conflict variant lacks position_at")
        at_value = lines[index][len("Position at: ") :]
        position_at = None if at_value == "unknown" else at_value
        index += 1
        if index < len(lines) and not lines[index].strip():
            index += 1
        position_lines: list[str] = []
        while index < len(lines) and not lines[index].startswith("### "):
            position_lines.append(lines[index])
            index += 1
        position = "\n".join(position_lines).strip()
        variants.append(ConflictVariant(match.group(1), match.group(2), position, position_at))
    record = ConflictRecord(
        memory_id=metadata["memory_id"],
        kind=metadata["kind"],
        subject=metadata["subject"],
        scope=metadata["scope"],
        scope_id=metadata["scope_id"],
        source_updated_at=metadata["source_updated_at"],
        created_at=metadata["created_at"],
        updated_at=metadata["updated_at"],
        variants=tuple(variants),
        workstreams=tuple(metadata["workstreams"]),
        review_state=metadata["review_state"],
        status=metadata["status"],
        authority=metadata["authority"],
    )
    if record.body != body:
        raise MemoryValidationError("conflict body is not canonical")
    return record


def start_conflict(
    existing: MemoryRecord,
    proposal: ConflictProposal,
    *,
    updated_at: str,
) -> ConflictRecord:
    """Turn one current record and one incompatible position into v1/v2."""

    if existing.status != "current" or proposal.target_variant_id is not None:
        raise MemoryValidationError("new conflict requires one current record")
    _matching_target(existing, proposal)
    return ConflictRecord(
        memory_id=existing.memory_id,
        kind=existing.kind,
        subject=existing.subject,
        scope=existing.scope,
        scope_id=existing.scope_id,
        source_updated_at=proposal.position_at,
        created_at=existing.created_at,
        updated_at=updated_at,
        workstreams=existing.workstreams,
        variants=(
            ConflictVariant("v1", "Prior position", existing.current or "", existing.source_updated_at),
            ConflictVariant("v2", proposal.label, proposal.position, proposal.position_at),
        ),
    )


def supersede(
    existing: MemoryRecord,
    proposal: SupersedeProposal,
    *,
    updated_at: str,
) -> MemoryRecord:
    """Replace current meaning while preserving stable compact lineage."""

    if existing.status != "current" or (
        proposal.target_memory_id != existing.memory_id
        or proposal.kind != existing.kind
        or proposal.subject != existing.subject
        or proposal.scope != existing.scope
        or proposal.scope_id != existing.scope_id
    ):
        raise MemoryValidationError("supersede proposal changes target identity or scope")
    used = [
        int(match.group(1))
        for entry in existing.lineage
        if (match := re.match(r"`v([1-9][0-9]*)`", entry)) is not None
    ]
    variant_id = f"v{max(used, default=0) + 1}"
    position_at = existing.source_updated_at or "unknown"
    lineage = existing.lineage + (
        f"`{variant_id}` — Prior position — replaced — {position_at}",
    )
    return MemoryRecord(
        memory_id=existing.memory_id,
        kind=existing.kind,
        subject=existing.subject,
        scope=existing.scope,
        scope_id=existing.scope_id,
        status="current",
        source_updated_at=proposal.source_updated_at,
        created_at=existing.created_at,
        updated_at=updated_at,
        workstreams=existing.workstreams,
        current=proposal.current,
        context=proposal.context,
        implications=proposal.implications,
        lineage=lineage,
    )


def review_conflict(
    existing: ConflictRecord,
    *,
    owner_confirmed: bool,
    updated_at: str,
    select_variant_id: str | None = None,
    owner_resolution: str | None = None,
    resolution_at: str | None = None,
    keep_unresolved: bool = False,
    overflow_variants: tuple["ConflictOverflow", ...] = (),
) -> MemoryRecord | ConflictRecord:
    """Apply exactly one explicit Owner conflict-review outcome."""

    if owner_confirmed is not True:
        raise PermissionError("conflict review requires explicit Owner confirmation")
    outcomes = sum(
        (
            select_variant_id is not None,
            owner_resolution is not None,
            keep_unresolved,
        )
    )
    if outcomes != 1:
        raise MemoryValidationError("conflict review requires exactly one outcome")
    if keep_unresolved:
        return ConflictRecord(
            **{
                **existing.__dict__,
                "updated_at": updated_at,
                "review_state": (
                    "overflow" if existing.review_state == "overflow" else "acknowledged"
                ),
            }
        )
    overflow_as_variants: tuple[ConflictVariant, ...] = tuple(
        ConflictVariant(item.variant_id, item.label, item.position, item.position_at)
        for item in overflow_variants
    )
    for overflow in overflow_variants:
        if (
            overflow.memory_id != existing.memory_id
            or overflow.subject != existing.subject
            or overflow.scope != existing.scope
            or overflow.scope_id != existing.scope_id
        ):
            raise MemoryValidationError("conflict overflow changes target identity or scope")
    all_variants = existing.variants + overflow_as_variants
    if len({item.variant_id for item in all_variants}) != len(all_variants):
        raise MemoryValidationError("duplicate conflict review variant identity")
    selected = next(
        (item for item in all_variants if item.variant_id == select_variant_id),
        None,
    )
    if select_variant_id is not None and selected is None:
        raise MemoryValidationError("selected conflict variant does not exist")
    if owner_resolution is not None:
        current = _text(owner_resolution, "Owner conflict resolution")
        source_updated_at = _timestamp(resolution_at, "resolution_at")
    else:
        assert selected is not None
        current = selected.position
        source_updated_at = selected.position_at
    lineage = tuple(
        f"`{variant.variant_id}` — {variant.label} — "
        f"{'replaced by Owner resolution' if owner_resolution is not None else 'selected' if variant is selected else 'not selected'} — "
        f"{variant.position_at or 'unknown'}"
        for variant in all_variants
    )
    return MemoryRecord(
        memory_id=existing.memory_id,
        kind=existing.kind,
        subject=existing.subject,
        scope=existing.scope,
        scope_id=existing.scope_id,
        status="current",
        source_updated_at=source_updated_at,
        created_at=existing.created_at,
        updated_at=updated_at,
        workstreams=existing.workstreams,
        current=current,
        lineage=lineage,
    )
def apply_conflict(
    existing: ConflictRecord,
    proposal: ConflictProposal,
    *,
    updated_at: str,
    next_variant_number: int | None = None,
) -> tuple[ConflictRecord, ConflictOverflow | None, str]:
    """Support a variant, append v3, or create the next overflow position."""

    _matching_target(existing, proposal)
    if proposal.target_variant_id is not None:
        variant = next(
            (item for item in existing.variants if item.variant_id == proposal.target_variant_id),
            None,
        )
        if variant is None or variant.label != proposal.label or variant.position != proposal.position:
            raise MemoryValidationError("conflict support must exactly preserve a variant")
        return existing, None, "supported"
    next_number = next_variant_number or (len(existing.variants) + 1)
    if next_number < len(existing.variants) + 1:
        raise MemoryValidationError("next conflict variant would reuse an identity")
    variant = ConflictVariant(
        f"v{next_number}", proposal.label, proposal.position, proposal.position_at
    )
    if next_number <= 3:
        return (
            ConflictRecord(
                memory_id=existing.memory_id,
                kind=existing.kind,
                subject=existing.subject,
                scope=existing.scope,
                scope_id=existing.scope_id,
                source_updated_at=proposal.position_at,
                created_at=existing.created_at,
                updated_at=updated_at,
                workstreams=existing.workstreams,
                variants=existing.variants + (variant,),
                review_state="required",
            ),
            None,
            "conflict-recorded",
        )
    overflow = ConflictOverflow.from_variant(existing, variant, created_at=updated_at)
    return (
        ConflictRecord(
            **{
                **existing.__dict__,
                "source_updated_at": proposal.position_at,
                "updated_at": updated_at,
                "review_state": "overflow",
            }
        ),
        overflow,
        "conflict-recorded",
    )


@dataclass(frozen=True)
class ConflictOverflow:
    memory_id: str
    variant_id: str
    subject: str
    scope: str
    scope_id: str
    position_at: str | None
    created_at: str
    updated_at: str
    label: str
    position: str

    def __post_init__(self) -> None:
        if not isinstance(self.memory_id, str) or _SAFE_ID.fullmatch(self.memory_id) is None:
            raise MemoryValidationError("invalid conflict overflow memory_id")
        match = _VARIANT_ID.fullmatch(self.variant_id)
        if match is None or int(match.group(1)) < 4:
            raise MemoryValidationError("conflict overflow variant_id must be v4 or later")
        semantic_slug(self.subject)
        if self.scope not in {"project", "general", "unassigned"}:
            raise MemoryValidationError("invalid conflict overflow scope")
        if self.scope == "project":
            if not _SAFE_ID.fullmatch(self.scope_id):
                raise MemoryValidationError("invalid conflict overflow project scope")
        elif self.scope_id != self.scope:
            raise MemoryValidationError("conflict overflow scope identity mismatch")
        object.__setattr__(self, "position_at", _timestamp(self.position_at, "position_at"))
        object.__setattr__(self, "created_at", _timestamp(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _timestamp(self.updated_at, "updated_at"))
        object.__setattr__(self, "label", _label(self.label))
        object.__setattr__(self, "position", _position(self.position))

    @classmethod
    def from_variant(
        cls, record: ConflictRecord, variant: ConflictVariant, *, created_at: str
    ) -> "ConflictOverflow":
        return cls(
            record.memory_id,
            variant.variant_id,
            record.subject,
            record.scope,
            record.scope_id,
            variant.position_at,
            created_at,
            created_at,
            variant.label,
            variant.position,
        )

    def render(self) -> str:
        values = (
            ("schema", CONFLICT_OVERFLOW_SCHEMA),
            ("memory_id", self.memory_id),
            ("variant_id", self.variant_id),
            ("subject", self.subject),
            ("authority", "noncanonical"),
            ("scope", self.scope),
            ("scope_id", self.scope_id),
            ("position_at", self.position_at),
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
            ("label", self.label),
        )
        lines = ["---"]
        for key, value in values:
            lines.append(f"{key}: {'null' if value is None else value}")
        lines.extend(("---", "", f"# {self.subject} — {self.variant_id}", "", "## Position", "", self.position, ""))
        return "\n".join(lines)

    @classmethod
    def parse(cls, document: str) -> "ConflictOverflow":
        if not document.startswith("---\n") or "\n---\n" not in document[4:]:
            raise MemoryValidationError("conflict overflow requires frontmatter")
        marker = document.find("\n---\n", 4)
        metadata = yaml.safe_load(document[4:marker])
        common = {
            "schema",
            "memory_id",
            "variant_id",
            "subject",
            "authority",
            "scope",
            "scope_id",
            "position_at",
            "created_at",
            "updated_at",
        }
        schema = metadata.get("schema") if isinstance(metadata, dict) else None
        expected = common | ({"label"} if schema == CONFLICT_OVERFLOW_SCHEMA else set())
        if (
            not isinstance(metadata, dict)
            or set(metadata) != expected
            or schema not in {CONFLICT_OVERFLOW_SCHEMA, LEGACY_CONFLICT_OVERFLOW_SCHEMA}
            or metadata["authority"] != "noncanonical"
        ):
            raise MemoryValidationError("invalid conflict overflow frontmatter")
        for key in ("position_at", "created_at", "updated_at"):
            if isinstance(metadata[key], datetime):
                metadata[key] = metadata[key].isoformat().replace("+00:00", "Z")
        body = document[marker + 5 :].strip()
        prefix = f"# {metadata['subject']} — {metadata['variant_id']}\n\n## Position\n\n"
        if not body.startswith(prefix):
            raise MemoryValidationError("invalid conflict overflow body")
        position = body[len(prefix) :]
        return cls(
            memory_id=metadata["memory_id"],
            variant_id=metadata["variant_id"],
            subject=metadata["subject"],
            scope=metadata["scope"],
            scope_id=metadata["scope_id"],
            position_at=metadata["position_at"],
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            label=metadata.get("label", f"Overflow {metadata['variant_id']}"),
            position=position,
        )

    def relative_path(self, project_alias: str | None = None) -> Path:
        scope = scope_directory(self.scope, project_alias).relative_to(
            Path("System/Orca Memory/shallow")
        )
        suffix = short_id(self.memory_id)
        filename = f"{semantic_slug(self.subject)}--{suffix}--{self.variant_id}.md"
        return Path("System/Orca Memory/candidates/conflicts") / scope / filename


def _matching_target(existing: MemoryRecord | ConflictRecord, proposal: ConflictProposal) -> None:
    if (
        proposal.target_memory_id != existing.memory_id
        or proposal.kind != existing.kind
        or proposal.subject != existing.subject
        or proposal.scope != existing.scope
        or proposal.scope_id != existing.scope_id
    ):
        raise MemoryValidationError("conflict proposal changes target identity or scope")


__all__ = [
    "CONFLICT_OVERFLOW_SCHEMA",
    "LEGACY_CONFLICT_OVERFLOW_SCHEMA",
    "ConflictOverflow",
    "ConflictProposal",
    "ConflictRecord",
    "ConflictVariant",
    "SupersedeProposal",
    "apply_conflict",
    "parse_conflict_record",
    "review_conflict",
    "start_conflict",
    "supersede",
]
