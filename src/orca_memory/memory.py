"""Deterministic Typed Memory Record contracts.

This module deliberately contains no filesystem or vault writes.  Semantic
providers may supply :class:`RecordProposal` values, while Storage supplies
the identity and publication timestamps when it materializes a
:class:`MemoryRecord`.

Conflict variants, supersession lineage, and project registration are
intentionally outside this value/validation slice.  Inputs that would require
conflict variants fail closed; Project Summary values are included because
Storage publishes them beside project records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal, Mapping
import unicodedata

from orca_memory.privacy import contains_secret


MEMORY_SCHEMA = "orca-memory/0.2"
FILENAME_POLICY = "orca-memory-filename/0.1"
LAYOUT_POLICY = "orca-memory-layout/0.1"
BODY_POLICY = "orca-memory-body/0.1"
PROJECT_SUMMARY_SCHEMA = "orca-project-summary/1"

MemoryKind = Literal[
    "workstream-summary",
    "decision",
    "knowledge",
    "entity",
    "identity",
    "goal",
    "constraint",
    "open-question",
    "lesson",
    "topic",
]
MemoryScopeKind = Literal["project", "general", "unassigned"]
MemoryStatus = Literal["current", "closed"]
MemoryOperation = Literal["add", "support", "update"]

MEMORY_KINDS: frozenset[str] = frozenset(
    {
        "workstream-summary",
        "decision",
        "knowledge",
        "entity",
        "identity",
        "goal",
        "constraint",
        "open-question",
        "lesson",
        "topic",
    }
)
MEMORY_SCOPES: frozenset[str] = frozenset({"project", "general", "unassigned"})
MEMORY_STATUSES: frozenset[str] = frozenset({"current", "closed"})
MEMORY_OPERATIONS: frozenset[str] = frozenset({"add", "support", "update"})
KIND_DIRECTORIES: dict[str, str] = {
    "workstream-summary": "workstreams",
    "goal": "goals",
    "decision": "decisions",
    "knowledge": "knowledge",
    "entity": "entities",
    "identity": "identities",
    "constraint": "constraints",
    "open-question": "open-questions",
    "lesson": "lessons",
    "topic": "topics",
}

_FRONTMATTER_KEYS = (
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
)
_SUMMARY_FRONTMATTER_KEYS = ("schema_version", "kind", "authority", "project_id")
_PROPOSAL_KEYS = frozenset(
    {
        "operation",
        "target_memory_id",
        "kind",
        "subject",
        "scope",
        "scope_id",
        "status",
        "source_updated_at",
        "workstreams",
        "current",
        "context",
        "implications",
        "final",
        "closure",
        "source_segment_refs",
    }
)
_PROVIDER_OWNED_KEYS = frozenset(
    {
        "schema",
        "memory_id",
        "authority",
        "review_state",
        "created_at",
        "updated_at",
        "filename",
        "path",
        "hash",
        "content_hash",
    }
)
_GENERIC_SLUGS = frozenset(
    {
        "memory",
        "record",
        "note",
        "item",
        "misc",
        "untitled",
        "goal-1",
        "decision-final",
        "current-goal",
        "latest-decision",
    }
)
_WINDOWS_RESERVED = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_WORKSTREAM = re.compile(r"^[^\x00-\x1f\x7f]+$")
_PLAIN_YAML = re.compile(r"^[^\x00-\x1f\x7f\n\r]+$")
_UTC_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]00:00)$"
)


class MemoryValidationError(ValueError):
    """Raised when a record or proposal violates the accepted contract."""


def _fail(message: str) -> None:
    raise MemoryValidationError(message)


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{name} must be a non-empty string")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        _fail(f"{name} contains a control character")
    if contains_secret(value):
        _fail(f"{name} contains a credential-like value")
    return value


def _identifier(value: Any, name: str) -> str:
    value = _required_text(value, name)
    if not _SAFE_ID.fullmatch(value):
        _fail(f"{name} is not a portable opaque identifier")
    return value


def _utc_timestamp(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        _fail(f"{name} must be a UTC RFC 3339 timestamp")
    if not _UTC_RFC3339.fullmatch(value):
        _fail(f"{name} must be a UTC RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MemoryValidationError(f"{name} must be a UTC RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        _fail(f"{name} must use UTC")
    # Canonicalize equivalent +00:00 input so repeated rendering is byte-stable.
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_value(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def semantic_slug(subject: str) -> str:
    """Return the portable human-readable slug for a Memory Subject.

    The subject itself remains in frontmatter.  This function only derives the
    filename component and never falls back to an ID-only name.
    """

    subject = _required_text(subject, "subject")
    normalized = unicodedata.normalize("NFC", subject).lower()
    if subject[-1] in ". " or "\n" in subject or "\r" in subject:
        _fail("subject has an unsafe trailing character or line break")

    slug_parts: list[str] = []
    pending_separator = False
    for char in normalized:
        category = unicodedata.category(char)
        if category[0] in {"L", "N"}:
            if pending_separator and slug_parts:
                slug_parts.append("-")
            slug_parts.append(char)
            pending_separator = False
        else:
            pending_separator = True
    slug = "".join(slug_parts).strip("-")
    if len(slug) > 72:
        # Slugs are already word-separated; retain complete words whenever
        # possible and only split an unusually long first word as a last resort.
        words = slug.split("-")
        selected: list[str] = []
        size = 0
        for word in words:
            proposed = len(word) if not selected else size + 1 + len(word)
            if proposed > 72:
                break
            selected.append(word)
            size = proposed
        slug = "-".join(selected) or slug[:72]
        slug = slug.rstrip("-")
    if not slug:
        _fail(f"unsafe or non-descriptive slug: {subject!r}")
    if slug in _GENERIC_SLUGS:
        _fail(f"unsafe or non-descriptive slug: {subject!r}")
    if slug.split(".", 1)[0] in _WINDOWS_RESERVED:
        _fail(f"Windows-reserved subject slug: {subject!r}")
    if any(ord(char) < 32 or ord(char) == 127 for char in slug):
        _fail("subject slug contains a control character")
    return slug


def short_id(memory_id: str, existing_ids: tuple[str, ...] | list[str] = ()) -> str:
    """Derive the collision-resistant short locator suffix for ``memory_id``."""

    memory_id = _identifier(memory_id, "memory_id")
    digest = hashlib.sha256(memory_id.encode("utf-8"))
    hex_digest = digest.hexdigest()
    length = 12
    others = tuple(existing_ids)
    for other in others:
        _identifier(other, "existing memory_id")
    while any(
        other != memory_id
        and hashlib.sha256(other.encode("utf-8")).hexdigest()[:length]
        == hex_digest[:length]
        for other in others
    ):
        length += 4
        if length > len(hex_digest):
            _fail("unable to derive a unique short ID")
    return hex_digest[:length]


def kind_directory(kind: str) -> str:
    """Return the contract directory name for one controlled record kind."""

    if kind not in MEMORY_KINDS:
        _fail(f"unsupported memory kind: {kind!r}")
    return KIND_DIRECTORIES[kind]


def scope_directory(scope: str | Any, project_alias: str | None = None) -> Path:
    """Return the shallow-memory scope path relative to the vault root."""

    if not isinstance(scope, str):
        project_alias = project_alias or getattr(scope, "project_alias", None)
        scope = getattr(scope, "kind", None)
    if scope == "project":
        if project_alias is None:
            _fail("project scope requires project_alias for physical placement")
        return Path("System") / "Orca Memory" / "shallow" / "projects" / semantic_slug(
            project_alias
        )
    if scope in {"general", "unassigned"}:
        if project_alias is not None:
            _fail(f"{scope} scope cannot have a project alias")
        return Path("System") / "Orca Memory" / "shallow" / scope
    _fail(f"unsupported memory scope: {scope!r}")


def record_filename(
    subject: str,
    memory_id: str,
    *,
    existing_ids: tuple[str, ...] | list[str] = (),
) -> str:
    """Return Storage's deterministic record filename."""

    return f"{semantic_slug(subject)}--{short_id(memory_id, existing_ids)}.md"


def record_relative_path(
    record: "MemoryRecord",
    project_alias: str | None = None,
    *,
    existing_ids: tuple[str, ...] | list[str] = (),
) -> Path:
    """Return the logical vault path; this function performs no write."""

    # Project aliases are intentionally not part of the record schema.  Storage
    # supplies one when resolving the logical project scope.
    return scope_directory(record.scope, project_alias) / kind_directory(record.kind) / record_filename(
        record.subject, record.memory_id, existing_ids=existing_ids
    )


def _validate_scope(scope: Any, scope_id: Any) -> tuple[str, str]:
    if scope not in MEMORY_SCOPES:
        _fail(f"unsupported memory scope: {scope!r}")
    if scope in {"general", "unassigned"}:
        if scope_id != scope:
            _fail(f"{scope} scope must use scope_id {scope!r}")
    else:
        scope_id = _identifier(scope_id, "scope_id")
        if scope_id in {"general", "unassigned"}:
            _fail("project scope cannot use a fixed scope identity")
    return scope, scope_id


def _validate_workstreams(value: Any, scope: str) -> tuple[str, ...]:
    if value is None:
        value = ()
    if isinstance(value, str) or not isinstance(value, (tuple, list)):
        _fail("workstreams must be a list of labels")
    labels: list[str] = []
    for label in value:
        if (
            not isinstance(label, str)
            or not label.strip()
            or not _SAFE_WORKSTREAM.fullmatch(label)
            or "/" in label
            or "\\" in label
            or contains_secret(label)
        ):
            _fail("workstream labels must be safe non-empty strings")
        if label.casefold() in {item.casefold() for item in labels}:
            _fail("workstream labels must be unique")
        labels.append(label)
    if scope != "project" and labels:
        _fail("workstreams are allowed only in project scope")
    return tuple(labels)


def _validate_sections(
    *,
    status: str,
    current: str | None,
    context: str | None,
    implications: str | None,
    final: str | None,
    closure: str | None,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    values = {
        "current": current,
        "context": context,
        "implications": implications,
        "final": final,
        "closure": closure,
    }
    for name, value in values.items():
        if value is not None:
            _required_text(value, name)
    if status == "current":
        if current is None or not current.strip():
            _fail("current records require a non-empty current section")
        if final is not None or closure is not None:
            _fail("current records cannot contain final or closure sections")
    elif status == "closed":
        if final is None or not final.strip() or closure is None or not closure.strip():
            _fail("closed records require final and closure sections")
        if current is not None or context is not None or implications is not None:
            _fail("closed records cannot contain current sections")
    else:
        _fail(f"unsupported memory status: {status!r}")
    return current, context, implications, final, closure


def _render_body_values(
    subject: str,
    status: str,
    current: str | None,
    context: str | None,
    implications: str | None,
    final: str | None,
    closure: str | None,
    lineage: tuple[str, ...] = (),
) -> str:
    lines = [f"# {subject}", ""]
    if status == "current":
        assert current is not None
        lines.extend(("## Current", "", current.strip()))
        for heading, value in (("Context", context), ("Implications", implications)):
            if value is not None and value.strip():
                lines.extend(("", f"## {heading}", "", value.strip()))
        if lineage:
            lines.extend(("", "## Resolution lineage", ""))
            lines.extend(f"- {entry}" for entry in lineage)
    else:
        assert final is not None and closure is not None
        lines.extend(("## Final", "", final.strip(), "", "## Closure", "", closure.strip()))
    return "\n".join(lines)


def _parse_body(body: str, subject: str, status: str) -> dict[str, Any]:
    if not isinstance(body, str) or not body.strip():
        _fail("record body is required")
    if body.startswith("---"):
        _fail("record body must not contain frontmatter")
    lines = body.splitlines()
    if not lines or lines[0] != f"# {subject}":
        _fail("record body heading must match subject")
    sections: dict[str, list[str]] = {}
    section_order: list[str] = []
    current_heading: str | None = None
    for line in lines[1:]:
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading in sections:
                _fail(f"duplicate body section: {heading}")
            sections[heading] = []
            section_order.append(heading)
            current_heading = heading
        elif line.startswith("#") and line.strip():
            _fail("record body contains an unsupported heading")
        elif current_heading is not None:
            sections[current_heading].append(line)
        elif line.strip():
            _fail("record body text must be inside a section")
    allowed = {"Current", "Context", "Implications", "Resolution lineage"} if status == "current" else {
        "Final",
        "Closure",
    }
    unknown = set(sections) - allowed
    if unknown:
        _fail(f"unsupported record body section: {sorted(unknown)[0]}")
    expected_order = (
        ["Current"]
        + (["Context"] if "Context" in sections else [])
        + (["Implications"] if "Implications" in sections else [])
        + (["Resolution lineage"] if "Resolution lineage" in sections else [])
        if status == "current"
        else ["Final", "Closure"]
    )
    if section_order != expected_order:
        _fail("record body sections are not in canonical order")
    values: dict[str, str | None] = {}
    for heading in allowed - {"Resolution lineage"}:
        if heading not in sections:
            values[heading.lower()] = None
            continue
        value = "\n".join(sections[heading]).strip()
        if not value:
            _fail(f"record body section {heading!r} must be non-empty")
        values[heading.lower()] = value
    lineage: tuple[str, ...] = ()
    if "Resolution lineage" in sections:
        entries: list[str] = []
        for line in sections["Resolution lineage"]:
            if line.strip():
                if not line.startswith("- ") or not line[2:].strip():
                    _fail("resolution lineage must use non-empty bullet items")
                entries.append(_required_text(line[2:].strip(), "resolution lineage"))
        if not entries:
            _fail("resolution lineage must contain at least one entry")
        lineage = tuple(entries)
    return {
        "current": values.get("current"),
        "context": values.get("context"),
        "implications": values.get("implications"),
        "final": values.get("final"),
        "closure": values.get("closure"),
        "lineage": lineage,
    }


@dataclass(frozen=True)
class MemoryRecord:
    """One validated noncanonical, living Typed Memory Record.

    ``memory_id``, ``created_at``, and ``updated_at`` are required here because
    this is the materialized Storage-side record.  Use
    :class:`RecordProposal` for provider-side values that do not own them.
    """

    memory_id: str
    kind: str
    subject: str
    scope: str
    scope_id: str
    status: str
    source_updated_at: str | None
    created_at: str
    updated_at: str
    workstreams: tuple[str, ...] = ()
    authority: str = "noncanonical"
    review_state: str = "none"
    current: str | None = None
    context: str | None = None
    implications: str | None = None
    final: str | None = None
    closure: str | None = None
    lineage: tuple[str, ...] = ()
    body: str | None = field(default=None, compare=True)

    def __post_init__(self) -> None:
        memory_id = _identifier(self.memory_id, "memory_id")
        if self.kind not in MEMORY_KINDS:
            _fail(f"unsupported memory kind: {self.kind!r}")
        subject = _required_text(self.subject, "subject")
        semantic_slug(subject)
        scope, scope_id = _validate_scope(self.scope, self.scope_id)
        if self.kind == "workstream-summary" and scope != "project":
            _fail("workstream summaries are allowed only in project scope")
        if self.status not in MEMORY_STATUSES:
            if self.status == "conflict":
                _fail("conflict records are deferred to Milestone 3")
            _fail(f"unsupported memory status: {self.status!r}")
        if self.authority != "noncanonical":
            _fail("Typed Memory Records must be noncanonical")
        if self.review_state != "none":
            _fail("review state is only available for deferred conflict records")
        source_updated_at = _utc_timestamp(
            self.source_updated_at, "source_updated_at", nullable=True
        )
        created_at = _utc_timestamp(self.created_at, "created_at")
        updated_at = _utc_timestamp(self.updated_at, "updated_at")
        assert created_at is not None and updated_at is not None
        if _timestamp_value(updated_at) < _timestamp_value(created_at):
            _fail("updated_at cannot precede created_at")
        workstreams = _validate_workstreams(self.workstreams, scope)

        sections = {
            "current": self.current,
            "context": self.context,
            "implications": self.implications,
            "final": self.final,
            "closure": self.closure,
        }
        lineage = tuple(_required_text(item, "resolution lineage") for item in self.lineage)
        if self.status != "current" and lineage:
            _fail("only current records may retain resolution lineage")
        if self.body is not None:
            parsed = _parse_body(self.body, subject, self.status)
            parsed_lineage = parsed.pop("lineage")
            if lineage and lineage != parsed_lineage:
                _fail("body and resolution lineage field disagree")
            lineage = parsed_lineage
            for name, value in parsed.items():
                supplied = sections[name]
                if supplied is not None and supplied.strip() != (value or "").strip():
                    _fail(f"body and {name} field disagree")
                sections[name] = value
        current, context, implications, final, closure = _validate_sections(
            status=self.status, **sections
        )
        canonical_body = _render_body_values(
            subject,
            self.status,
            current,
            context,
            implications,
            final,
            closure,
            lineage,
        )
        object.__setattr__(self, "memory_id", memory_id)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(self, "source_updated_at", source_updated_at)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "updated_at", updated_at)
        object.__setattr__(self, "workstreams", workstreams)
        object.__setattr__(self, "lineage", lineage)
        for name, value in (
            ("current", current),
            ("context", context),
            ("implications", implications),
            ("final", final),
            ("closure", closure),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "body", canonical_body)

    @property
    def filename(self) -> str:
        """The current deterministic filename for this logical record."""

        return record_filename(self.subject, self.memory_id)

    def frontmatter(self) -> dict[str, Any]:
        """Return the exact schema fields, without path or provenance extras."""

        return {
            "schema": MEMORY_SCHEMA,
            "memory_id": self.memory_id,
            "kind": self.kind,
            "subject": self.subject,
            "authority": "noncanonical",
            "scope": self.scope,
            "scope_id": self.scope_id,
            "status": self.status,
            "review_state": "none",
            "source_updated_at": self.source_updated_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workstreams": list(self.workstreams),
        }

    def render(self) -> str:
        """Render this record using the canonical Markdown representation."""

        return render_record(self)

    @classmethod
    def parse(cls, document: str) -> "MemoryRecord":
        """Parse one canonical Markdown representation."""

        return parse_record(document)

    def validate(self) -> "MemoryRecord":
        """Return this record after deterministic validation."""

        return validate_record(self)


@dataclass(frozen=True)
class RecordProposal:
    """Provider-side proposal containing semantic fields only."""

    operation: str
    kind: str
    subject: str
    scope: str
    scope_id: str
    status: str = "current"
    source_updated_at: str | None = None
    workstreams: tuple[str, ...] = ()
    target_memory_id: str | None = None
    current: str | None = None
    context: str | None = None
    implications: str | None = None
    final: str | None = None
    closure: str | None = None
    # Provider citations use the current run's deterministic segment locator
    # (``<turn_id>#<segment_index>``).  Storage turns these into Manifest refs.
    source_segment_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.operation not in MEMORY_OPERATIONS:
            if self.operation in {"conflict", "supersede"}:
                _fail(f"{self.operation} operations are deferred to Milestone 3")
            _fail(f"unsupported memory operation: {self.operation!r}")
        if self.kind not in MEMORY_KINDS:
            _fail(f"unsupported memory kind: {self.kind!r}")
        _required_text(self.subject, "subject")
        semantic_slug(self.subject)
        scope, scope_id = _validate_scope(self.scope, self.scope_id)
        if self.kind == "workstream-summary" and scope != "project":
            _fail("workstream summaries are allowed only in project scope")
        if self.operation in {"support", "update"}:
            if self.target_memory_id is None:
                _fail(f"{self.operation} requires target_memory_id")
            _identifier(self.target_memory_id, "target_memory_id")
        elif self.target_memory_id is not None:
            _fail("add cannot target an existing memory_id")
        source_updated_at = _utc_timestamp(
            self.source_updated_at, "source_updated_at", nullable=True
        )
        workstreams = _validate_workstreams(self.workstreams, scope)
        if not isinstance(self.source_segment_refs, (tuple, list)):
            _fail("source_segment_refs must be a sequence")
        refs = tuple(self.source_segment_refs)
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            _fail("source_segment_refs must contain non-empty strings")
        if len(set(refs)) != len(refs):
            _fail("source_segment_refs must be unique")
        current, context, implications, final, closure = _validate_sections(
            status=self.status,
            current=self.current,
            context=self.context,
            implications=self.implications,
            final=self.final,
            closure=self.closure,
        )
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(self, "source_updated_at", source_updated_at)
        object.__setattr__(self, "workstreams", workstreams)
        object.__setattr__(self, "source_segment_refs", refs)
        for name, value in (
            ("current", current),
            ("context", context),
            ("implications", implications),
            ("final", final),
            ("closure", closure),
        ):
            object.__setattr__(self, name, value)

    def validate(self) -> "RecordProposal":
        """Return this proposal after deterministic validation."""

        return RecordProposal(**{name: getattr(self, name) for name in _PROPOSAL_FIELDS})

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RecordProposal":
        """Parse a provider mapping while rejecting Storage-owned fields."""

        if not isinstance(value, Mapping):
            _fail("record proposal must be a mapping")
        keys = set(value)
        forbidden = keys & _PROVIDER_OWNED_KEYS
        if forbidden:
            _fail(f"provider cannot assign Storage-owned fields: {sorted(forbidden)[0]}")
        unknown = keys - _PROPOSAL_KEYS
        if unknown:
            _fail(f"unsupported record proposal field: {sorted(unknown)[0]}")
        missing = {"operation", "kind", "subject", "scope", "scope_id"} - keys
        if missing:
            _fail(f"record proposal missing field: {sorted(missing)[0]}")
        return cls(**dict(value))


def validate_record(record: MemoryRecord) -> MemoryRecord:
    """Validate and return a materialized record for convenient composition."""

    if not isinstance(record, MemoryRecord):
        _fail("expected a MemoryRecord")
    # __post_init__ performs validation; reconstructing catches mutation by
    # hostile callers that bypassed the frozen dataclass through reflection.
    return MemoryRecord(**{name: getattr(record, name) for name in _RECORD_FIELDS})


_RECORD_FIELDS = (
    "memory_id",
    "kind",
    "subject",
    "scope",
    "scope_id",
    "status",
    "source_updated_at",
    "created_at",
    "updated_at",
    "workstreams",
    "authority",
    "review_state",
    "current",
    "context",
    "implications",
    "final",
    "closure",
    "lineage",
    "body",
)

_PROPOSAL_FIELDS = (
    "operation",
    "kind",
    "subject",
    "scope",
    "scope_id",
    "status",
    "source_updated_at",
    "workstreams",
    "target_memory_id",
    "current",
    "context",
    "implications",
    "final",
    "closure",
    "source_segment_refs",
)


def materialize_record(
    proposal: RecordProposal | Mapping[str, Any],
    *,
    memory_id: str,
    created_at: str,
    updated_at: str | None = None,
) -> MemoryRecord:
    """Materialize an ``add`` proposal with Storage-owned fields."""

    if not isinstance(proposal, RecordProposal):
        proposal = RecordProposal.from_mapping(proposal)
    if proposal.operation != "add":
        _fail("only add proposals can be materialized without an existing record")
    return MemoryRecord(
        memory_id=memory_id,
        kind=proposal.kind,
        subject=proposal.subject,
        scope=proposal.scope,
        scope_id=proposal.scope_id,
        status=proposal.status,
        source_updated_at=proposal.source_updated_at,
        created_at=created_at,
        updated_at=updated_at if updated_at is not None else created_at,
        workstreams=proposal.workstreams,
        current=proposal.current,
        context=proposal.context,
        implications=proposal.implications,
        final=proposal.final,
        closure=proposal.closure,
    )


def _semantic_values(record: MemoryRecord) -> tuple[Any, ...]:
    return (
        record.kind,
        record.subject,
        record.scope,
        record.scope_id,
        record.status,
        record.source_updated_at,
        record.workstreams,
        record.current,
        record.context,
        record.implications,
        record.final,
        record.closure,
    )


def _proposal_values(proposal: RecordProposal) -> tuple[Any, ...]:
    return (
        proposal.kind,
        proposal.subject,
        proposal.scope,
        proposal.scope_id,
        proposal.status,
        proposal.source_updated_at,
        proposal.workstreams,
        proposal.current,
        proposal.context,
        proposal.implications,
        proposal.final,
        proposal.closure,
    )


def validate_operation(
    operation: str,
    *,
    existing: MemoryRecord | None = None,
    proposal: RecordProposal | Mapping[str, Any],
) -> bool:
    """Validate add/support/update target and identity invariants.

    ``True`` means the operation is structurally admissible.  Storage remains
    responsible for publishing the returned materialized post-image.
    """

    if operation not in MEMORY_OPERATIONS:
        if operation in {"conflict", "supersede"}:
            _fail(f"{operation} operations are deferred to Milestone 3")
        _fail(f"unsupported memory operation: {operation!r}")
    if not isinstance(proposal, RecordProposal):
        proposal = RecordProposal.from_mapping(proposal)
    if proposal.operation != operation:
        _fail("operation does not match proposal operation")
    if operation == "add":
        if existing is not None:
            _fail("add cannot target an existing record")
        return True
    if existing is None:
        _fail(f"{operation} requires an existing target")
    validate_record(existing)
    if proposal.target_memory_id != existing.memory_id:
        _fail("operation target identity does not match existing record")
    if proposal.scope != existing.scope or proposal.scope_id != existing.scope_id:
        _fail("record scope cannot change")
    if proposal.kind != existing.kind:
        _fail("record kind cannot change")
    if operation == "support":
        if _proposal_values(proposal) != _semantic_values(existing):
            _fail("support must exactly preserve record meaning")
    return True


def apply_update(
    existing: MemoryRecord,
    proposal: RecordProposal | Mapping[str, Any],
    *,
    updated_at: str,
) -> MemoryRecord:
    """Build an updated post-image while preserving logical identity."""

    if not isinstance(proposal, RecordProposal):
        proposal = RecordProposal.from_mapping(proposal)
    validate_operation("update", existing=existing, proposal=proposal)
    return MemoryRecord(
        memory_id=existing.memory_id,
        kind=existing.kind,
        subject=proposal.subject,
        scope=existing.scope,
        scope_id=existing.scope_id,
        status=proposal.status,
        source_updated_at=proposal.source_updated_at,
        created_at=existing.created_at,
        updated_at=updated_at,
        workstreams=proposal.workstreams,
        current=proposal.current,
        context=proposal.context,
        implications=proposal.implications,
        final=proposal.final,
        closure=proposal.closure,
        lineage=existing.lineage,
    )


def _yaml_scalar(value: str | None) -> str:
    if value is None:
        return "null"
    if (
        _PLAIN_YAML.fullmatch(value)
        and value == value.strip()
        and value not in {"null", "true", "false", "Null", "True", "False"}
        and not value.startswith(("- ", "? ", ": ", "#", "!", "&", "*", "{", "["))
        and not re.search(r"\s+#|:\s", value)
        and not any(char in value for char in "{}[]&*!|>'\"%@`")
    ):
        return value
    return json.dumps(value, ensure_ascii=False)


def render_record(record: MemoryRecord) -> str:
    """Render one canonical Typed Memory Record Markdown document."""

    record = validate_record(record)
    frontmatter = record.frontmatter()
    lines = ["---"]
    for key in _FRONTMATTER_KEYS:
        value = frontmatter[key]
        if key == "workstreams":
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        elif key == "source_updated_at":
            rendered = _yaml_scalar(value)
        else:
            rendered = _yaml_scalar(value)
        lines.append(f"{key}: {rendered}")
    lines.extend(("---", "", record.body or ""))
    return "\n".join(lines) + "\n"


def _parse_scalar(value: str, key: str) -> Any:
    if value == "null":
        return None
    if value.startswith("["):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise MemoryValidationError(f"invalid {key} list") from exc
        if not isinstance(parsed, list):
            _fail(f"{key} must be a list")
        return parsed
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise MemoryValidationError(f"invalid quoted {key}") from exc
        if not isinstance(parsed, str):
            _fail(f"{key} must be a string")
        return parsed
    if not value:
        _fail(f"{key} must not be empty")
    if any(char in value for char in "{}[]&*!|>'\"%@`"):
        _fail(f"unsupported YAML syntax in {key}")
    return value


def parse_record(document: str) -> MemoryRecord:
    """Parse and validate a canonical Typed Memory Record document."""

    if not isinstance(document, str) or not document.startswith("---\n"):
        _fail("record must start with YAML frontmatter")
    marker = document.find("\n---", 4)
    if marker < 0:
        _fail("record frontmatter is not closed")
    end = marker + len("\n---")
    if end < len(document) and document[end] not in {"\n", "\r"}:
        _fail("record frontmatter terminator is malformed")
    metadata_text = document[4:marker]
    metadata: dict[str, Any] = {}
    ordered_keys: list[str] = []
    for line in metadata_text.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            _fail("frontmatter line is malformed")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            _fail(f"duplicate frontmatter field: {key}")
        if key not in _FRONTMATTER_KEYS:
            _fail(f"unsupported frontmatter field: {key}")
        metadata[key] = _parse_scalar(value.strip(), key)
        ordered_keys.append(key)
    if tuple(ordered_keys) != _FRONTMATTER_KEYS:
        _fail("frontmatter fields are not in canonical order")
    missing = set(_FRONTMATTER_KEYS) - set(metadata)
    if missing:
        _fail(f"missing frontmatter field: {sorted(missing)[0]}")
    if metadata["schema"] != MEMORY_SCHEMA:
        _fail("unsupported memory schema")
    body = document[end:]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    if body.startswith("\n"):
        body = body[1:]
    if body.endswith("\n"):
        body = body[:-1]
    try:
        return MemoryRecord(
            memory_id=metadata["memory_id"],
            kind=metadata["kind"],
            subject=metadata["subject"],
            scope=metadata["scope"],
            scope_id=metadata["scope_id"],
            status=metadata["status"],
            source_updated_at=metadata["source_updated_at"],
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            workstreams=metadata["workstreams"],
            authority=metadata["authority"],
            review_state=metadata["review_state"],
            body=body,
        )
    except TypeError as exc:
        raise MemoryValidationError("frontmatter field has an invalid type") from exc


@dataclass(frozen=True)
class ProjectSummary:
    """Bounded, noncanonical executive view for one project.

    The summary has no ``memory_id``.  ``relevant_memory_ids`` are validated
    stable relationships; Storage may provide their current paths when
    rendering human-readable links.
    """

    project_id: str
    purpose: str
    current_state: str
    active_workstreams: tuple[str, ...] = ()
    important_outcomes: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()
    relevant_memory_ids: tuple[str, ...] = ()
    authority: str = "noncanonical"
    body: str | None = field(default=None, compare=True)

    def __post_init__(self) -> None:
        project_id = _identifier(self.project_id, "project_id")
        purpose = _required_text(self.purpose, "summary purpose")
        current_state = _required_text(self.current_state, "summary current state")
        if self.authority != "noncanonical":
            _fail("Project Summaries must be noncanonical")
        groups: dict[str, tuple[str, ...]] = {}
        for name, values in (
            ("active_workstreams", self.active_workstreams),
            ("important_outcomes", self.important_outcomes),
            ("open_questions", self.open_questions),
            ("next_steps", self.next_steps),
        ):
            if isinstance(values, str) or not isinstance(values, (tuple, list)):
                _fail(f"{name} must be a list of strings")
            normalized: list[str] = []
            for value in values:
                _required_text(value, name)
                normalized.append(value.strip())
            groups[name] = tuple(normalized)
        if isinstance(self.relevant_memory_ids, str) or not isinstance(
            self.relevant_memory_ids, (tuple, list)
        ):
            _fail("relevant_memory_ids must be a list of identifiers")
        memory_ids: list[str] = []
        for memory_id in self.relevant_memory_ids:
            _identifier(memory_id, "relevant memory_id")
            if memory_id in memory_ids:
                _fail("relevant memory_id values must be unique")
            memory_ids.append(memory_id)

        sections = {
            "active_workstreams": groups["active_workstreams"],
            "important_outcomes": groups["important_outcomes"],
            "open_questions": groups["open_questions"],
            "next_steps": groups["next_steps"],
        }
        if self.body is not None:
            parsed = _parse_summary_body(self.body, purpose)
            if parsed["current_state"] != current_state.strip():
                _fail("body and summary current_state field disagree")
            for name in sections:
                if parsed[name] != sections[name]:
                    _fail(f"body and summary {name} field disagree")
            if tuple(parsed["relevant_memory_ids"]) != tuple(memory_ids):
                _fail("body and summary relevant memory IDs disagree")
        canonical_body = _render_summary_body(
            purpose,
            current_state,
            sections["active_workstreams"],
            sections["important_outcomes"],
            sections["open_questions"],
            sections["next_steps"],
            tuple(memory_ids),
            None,
        )
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "current_state", current_state.strip())
        for name, values in sections.items():
            object.__setattr__(self, name, values)
        object.__setattr__(self, "relevant_memory_ids", tuple(memory_ids))
        object.__setattr__(self, "body", canonical_body)

    def render(self, *, memory_paths: Mapping[str, str] | None = None) -> str:
        """Render this summary, optionally resolving validated record paths."""

        return render_project_summary(self, memory_paths=memory_paths)

    @classmethod
    def parse(cls, document: str) -> "ProjectSummary":
        """Parse one canonical Project Summary representation."""

        return parse_project_summary(document)

    def validate(self) -> "ProjectSummary":
        """Return this summary after deterministic validation."""

        return validate_project_summary(self)


_SUMMARY_SECTIONS = {
    "Active workstreams": "active_workstreams",
    "Important outcomes": "important_outcomes",
    "Open questions": "open_questions",
    "Next steps": "next_steps",
    "Relevant memory": "relevant_memory_ids",
}


def _render_summary_body(
    purpose: str,
    current_state: str,
    active_workstreams: tuple[str, ...],
    important_outcomes: tuple[str, ...],
    open_questions: tuple[str, ...],
    next_steps: tuple[str, ...],
    relevant_memory_ids: tuple[str, ...],
    memory_paths: Mapping[str, str] | None,
) -> str:
    lines = [f"# {purpose}", "", "## Current state", "", current_state.strip()]
    for heading, values in (
        ("Active workstreams", active_workstreams),
        ("Important outcomes", important_outcomes),
        ("Open questions", open_questions),
        ("Next steps", next_steps),
    ):
        if values:
            lines.extend(("", f"## {heading}", ""))
            lines.extend(f"- {value}" for value in values)
    if relevant_memory_ids:
        if memory_paths is not None:
            missing = set(relevant_memory_ids) - set(memory_paths)
            if missing:
                _fail(f"missing path for relevant memory_id: {sorted(missing)[0]}")
        lines.extend(("", "## Relevant memory", ""))
        for memory_id in relevant_memory_ids:
            if memory_paths is None:
                lines.append(f"- `{memory_id}`")
            else:
                path = memory_paths[memory_id]
                _validate_memory_link_path(path)
                lines.append(f"- [{memory_id}]({path})")
    return "\n".join(lines)


def _validate_memory_link_path(path: Any) -> str:
    path = _required_text(path, "memory link path")
    if (
        path.startswith("/")
        or "\\" in path
        or ":" in path
        or ".." in Path(path).parts
        or any(char in path for char in "()[]")
    ):
        _fail("memory link path must be a vault-relative path")
    return path


def _parse_summary_body(body: str, purpose: str) -> dict[str, Any]:
    if not isinstance(body, str) or not body.strip():
        _fail("project summary body is required")
    lines = body.splitlines()
    if not lines or lines[0] != f"# {purpose}":
        _fail("project summary heading must match purpose")
    sections: dict[str, list[str]] = {}
    section_order: list[str] = []
    current_heading: str | None = None
    for line in lines[1:]:
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading == "Current state":
                key = "current_state"
            else:
                key = _SUMMARY_SECTIONS.get(heading)
            if key is None or key in sections:
                _fail(f"unsupported or duplicate project summary section: {heading}")
            sections[key] = []
            section_order.append(key)
            current_heading = key
        elif line.startswith("#") and line.strip():
            _fail("project summary contains an unsupported heading")
        elif current_heading is not None:
            sections[current_heading].append(line)
        elif line.strip():
            _fail("project summary text must be inside a section")
    if "current_state" not in sections:
        _fail("project summary requires current state")
    expected_order = ["current_state"]
    expected_order.extend(
        key
        for key in (
            "active_workstreams",
            "important_outcomes",
            "open_questions",
            "next_steps",
            "relevant_memory_ids",
        )
        if key in sections
    )
    if section_order != expected_order:
        _fail("project summary sections are not in canonical order")
    current_state = "\n".join(sections.pop("current_state")).strip()
    if not current_state:
        _fail("project summary current state must be non-empty")
    result: dict[str, Any] = {"current_state": current_state}
    for key in ("active_workstreams", "important_outcomes", "open_questions", "next_steps"):
        values = []
        for line in sections.pop(key, []):
            if line.strip():
                if not line.startswith("- ") or not line[2:].strip():
                    _fail(f"project summary {key} must use non-empty bullet items")
                values.append(line[2:].strip())
        result[key] = tuple(values)
    ids: list[str] = []
    for line in sections.pop("relevant_memory_ids", []):
        if line.strip():
            match = re.fullmatch(r"- `([^`]+)`", line.strip())
            if match is None:
                match = re.fullmatch(r"- \[([^]]+)\]\(([^)]+)\)", line.strip())
            if match is None:
                _fail("project summary relevant memory must use stable links")
            elif line.lstrip().startswith("- ["):
                memory_id = match.group(1)
                _validate_memory_link_path(match.group(2))
            else:
                memory_id = match.group(1)
            _identifier(memory_id, "relevant memory_id")
            if memory_id in ids:
                _fail("duplicate relevant memory_id")
            ids.append(memory_id)
    result["relevant_memory_ids"] = tuple(ids)
    return result


def validate_project_summary(summary: ProjectSummary) -> ProjectSummary:
    if not isinstance(summary, ProjectSummary):
        _fail("expected a ProjectSummary")
    return ProjectSummary(**{name: getattr(summary, name) for name in _SUMMARY_FIELDS})


_SUMMARY_FIELDS = (
    "project_id",
    "purpose",
    "current_state",
    "active_workstreams",
    "important_outcomes",
    "open_questions",
    "next_steps",
    "relevant_memory_ids",
    "authority",
    "body",
)


def render_project_summary(
    summary: ProjectSummary, *, memory_paths: Mapping[str, str] | None = None
) -> str:
    """Render a Project Summary with optional Storage-resolved memory links."""

    summary = validate_project_summary(summary)
    body = _render_summary_body(
        summary.purpose,
        summary.current_state,
        summary.active_workstreams,
        summary.important_outcomes,
        summary.open_questions,
        summary.next_steps,
        summary.relevant_memory_ids,
        memory_paths,
    )
    lines = [
        "---",
        "schema_version: orca-project-summary/1",
        "kind: project-summary",
        "authority: noncanonical",
        f"project_id: {_yaml_scalar(summary.project_id)}",
        "---",
        "",
        body,
    ]
    return "\n".join(lines) + "\n"


def parse_project_summary(document: str) -> ProjectSummary:
    """Parse and validate a Project Summary document."""

    if not isinstance(document, str) or not document.startswith("---\n"):
        _fail("project summary must start with YAML frontmatter")
    marker = document.find("\n---", 4)
    if marker < 0:
        _fail("project summary frontmatter is not closed")
    end = marker + len("\n---")
    metadata: dict[str, Any] = {}
    ordered_keys: list[str] = []
    for line in document[4:marker].splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            _fail("project summary frontmatter line is malformed")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            _fail(f"duplicate project summary field: {key}")
        if key not in _SUMMARY_FRONTMATTER_KEYS:
            _fail(f"unsupported project summary field: {key}")
        metadata[key] = _parse_scalar(value.strip(), key)
        ordered_keys.append(key)
    if tuple(ordered_keys) != _SUMMARY_FRONTMATTER_KEYS:
        _fail("project summary fields are not in canonical order")
    missing = set(_SUMMARY_FRONTMATTER_KEYS) - set(metadata)
    if missing:
        _fail(f"missing project summary field: {sorted(missing)[0]}")
    if metadata["schema_version"] != PROJECT_SUMMARY_SCHEMA:
        _fail("unsupported project summary schema")
    body = document[end:]
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    if body.startswith("\n"):
        body = body[1:]
    if body.endswith("\n"):
        body = body[:-1]
    parsed = _parse_summary_body(body, _extract_summary_purpose(body))
    return ProjectSummary(
        project_id=metadata["project_id"],
        purpose=_extract_summary_purpose(body),
        current_state=parsed["current_state"],
        active_workstreams=parsed["active_workstreams"],
        important_outcomes=parsed["important_outcomes"],
        open_questions=parsed["open_questions"],
        next_steps=parsed["next_steps"],
        relevant_memory_ids=parsed["relevant_memory_ids"],
        authority=metadata["authority"],
        body=body,
    )


def _extract_summary_purpose(body: str) -> str:
    first = body.splitlines()[0] if body.splitlines() else ""
    if not first.startswith("# ") or not first[2:].strip():
        _fail("project summary requires a purpose heading")
    return first[2:].strip()


# Small compatibility aliases make the contract discoverable without creating
# a second implementation surface.
slugify_subject = semantic_slug
memory_short_id = short_id
filename_for_record = record_filename
record_directory = scope_directory
render_memory_record = render_record
parse_memory_record = parse_record
validate_memory_record = validate_record
render_summary = render_project_summary
parse_summary = parse_project_summary
validate_summary = validate_project_summary


__all__ = [
    "BODY_POLICY",
    "FILENAME_POLICY",
    "KIND_DIRECTORIES",
    "LAYOUT_POLICY",
    "MEMORY_KINDS",
    "MEMORY_SCHEMA",
    "MEMORY_SCOPES",
    "MEMORY_STATUSES",
    "PROJECT_SUMMARY_SCHEMA",
    "MemoryRecord",
    "MemoryValidationError",
    "ProjectSummary",
    "RecordProposal",
    "apply_update",
    "filename_for_record",
    "kind_directory",
    "materialize_record",
    "memory_short_id",
    "parse_memory_record",
    "parse_record",
    "parse_project_summary",
    "parse_summary",
    "record_filename",
    "record_directory",
    "record_relative_path",
    "render_memory_record",
    "render_record",
    "render_project_summary",
    "render_summary",
    "scope_directory",
    "semantic_slug",
    "short_id",
    "slugify_subject",
    "validate_memory_record",
    "validate_operation",
    "validate_project_summary",
    "validate_record",
    "validate_summary",
]
