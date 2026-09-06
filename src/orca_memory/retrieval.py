"""Explicit, bounded Recall over deterministic local projections.

The retrieval adapter is deliberately a small replaceable seam.  Orca builds
and filters projections before handing them to an adapter; ranking cannot add
scope, authority, status, or provenance.  The bundled AgentCairn adapter wraps
an already-authorized local ranker and enables no capture, remember, or
canonical-write path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import math
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Callable, Iterable, Literal, Mapping, Protocol, Sequence

import yaml

from orca_memory.conflicts import parse_conflict_record
from orca_memory.memory import parse_project_summary, parse_record
from orca_memory.privacy import contains_secret


PROJECTION_POLICY = "orca-retrieval-projection/0.1"
INDEX_SCHEMA = "orca-retrieval-index/0.1"
AGENTCAIRN_ADAPTER_VERSION = "orca-agentcairn-retrieval/0.1"
MAX_RESULTS = 6
MAX_TOTAL_TOKENS = 4000
MAX_DOCUMENT_TOKENS = 1500
EXACT_CONTINUATION_TOKENS = 2000
EXACT_PROJECT_SUMMARY_TOKENS = 1000
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_ARTIFACTS = frozenset(
    {
        "typed-memory-record",
        "conflict-variant",
        "project-summary",
        "conversation-continuation",
    }
)
_ALLOWED_AUTHORITIES = frozenset({"canonical", "noncanonical"})
_ALLOWED_SCOPES = frozenset({"project", "general", "unassigned"})
_ALLOWED_STATUSES = frozenset({"current", "conflict", "closed"})


class RetrievalValidationError(ValueError):
    """Raised when a projection, adapter result, or Recall request is unsafe."""


class RetrievalUnavailable(RuntimeError):
    """Raised when the disposable index is absent or marked unavailable."""


@dataclass(frozen=True)
class ProjectionSource:
    """One explicitly selected source artifact for projection building.

    ``source_text`` is the complete current Markdown used for freshness
    hashing.  ``meaning`` is the bounded text made searchable.  Callers, not
    this module, choose which permitted files enter the source sequence; no
    broad vault scan is performed here.
    """

    path: str
    source_text: str
    meaning: str
    artifact_kind: str
    authority: str
    scope: str
    scope_id: str
    status: str
    projection_id: str
    memory_id: str | None = None
    visibility: str = "owner"
    memory_kind: str | None = None
    conversation_id: str | None = None
    structural_id: str | None = None
    source_updated_at: str | None = None
    stale: bool = False


@dataclass(frozen=True)
class RetrievalProjection:
    """A validated, non-authoritative searchable projection."""

    projection_id: str
    path: str
    meaning: str
    artifact_kind: str
    authority: str
    scope: str
    scope_id: str
    status: str
    source_sha256: str
    projection_policy: str = PROJECTION_POLICY
    memory_id: str | None = None
    visibility: str = "owner"
    memory_kind: str | None = None
    conversation_id: str | None = None
    structural_id: str | None = None
    source_updated_at: str | None = None

    def __post_init__(self) -> None:
        _safe_id(self.projection_id, "projection_id")
        _safe_relative_path(self.path)
        if self.artifact_kind not in _ALLOWED_ARTIFACTS:
            raise RetrievalValidationError(
                f"unsupported projection artifact kind: {self.artifact_kind!r}"
            )
        if self.authority not in _ALLOWED_AUTHORITIES:
            raise RetrievalValidationError("projection authority is invalid")
        _validate_scope(self.scope, self.scope_id)
        if self.status not in _ALLOWED_STATUSES:
            raise RetrievalValidationError("projection status is invalid")
        if self.projection_policy != PROJECTION_POLICY:
            raise RetrievalValidationError("unsupported retrieval projection policy")
        if not isinstance(self.meaning, str) or not self.meaning.strip():
            raise RetrievalValidationError("projection meaning is required")
        if contains_secret(self.meaning):
            raise RetrievalValidationError("projection contains a credential-like value")
        _validate_hash(self.source_sha256, "source_sha256")
        if self.memory_id is not None:
            _safe_id(self.memory_id, "memory_id")
        if self.conversation_id is not None:
            _safe_id(self.conversation_id, "conversation_id")
        if self.structural_id is not None:
            _safe_id(self.structural_id, "structural_id")
        if self.source_updated_at is not None:
            _validate_timestamp(self.source_updated_at, "source_updated_at")
        if not isinstance(self.visibility, str) or not self.visibility.strip():
            raise RetrievalValidationError("projection visibility is required")

    @property
    def source_identity(self) -> str:
        """Identity exposed to result consumers, without exposing source text."""

        return self.memory_id or self.structural_id or self.projection_id


def build_projection(source: ProjectionSource) -> RetrievalProjection | None:
    """Validate one explicitly selected artifact or skip a stale source."""

    if not isinstance(source, ProjectionSource):
        raise TypeError("projection source must be ProjectionSource")
    if source.stale:
        return None
    if not isinstance(source.source_text, str) or not isinstance(source.meaning, str):
        raise RetrievalValidationError("projection source text must be strings")
    if not source.source_text.strip():
        raise RetrievalValidationError("projection source text is required")
    if contains_secret(source.source_text):
        raise RetrievalValidationError("source artifact contains a credential-like value")
    return RetrievalProjection(
        projection_id=source.projection_id,
        path=source.path,
        meaning=source.meaning.strip(),
        artifact_kind=source.artifact_kind,
        authority=source.authority,
        scope=source.scope,
        scope_id=source.scope_id,
        status=source.status,
        source_sha256=_sha256(source.source_text),
        memory_id=source.memory_id,
        visibility=source.visibility,
        memory_kind=source.memory_kind,
        conversation_id=source.conversation_id,
        structural_id=source.structural_id,
        source_updated_at=source.source_updated_at,
    )


def projection_from_memory(
    record: Any,
    *,
    path: str,
    visibility: str = "owner",
) -> RetrievalProjection:
    """Project the current meaning of a validated Typed Memory Record."""

    if getattr(record, "status", None) not in {"current", "closed"}:
        raise RetrievalValidationError("only current or closed records are projectable")
    meaning_parts = [getattr(record, "current", None)]
    meaning_parts.extend((getattr(record, "context", None), getattr(record, "implications", None)))
    meaning = "\n\n".join(value.strip() for value in meaning_parts if isinstance(value, str) and value.strip())
    source_text = record.render()
    return _require_projection(
        build_projection(
            ProjectionSource(
                path=path,
                source_text=source_text,
                meaning=meaning,
                artifact_kind="typed-memory-record",
                authority=record.authority,
                scope=record.scope,
                scope_id=record.scope_id,
                status=record.status,
                projection_id=record.memory_id,
                memory_id=record.memory_id,
                visibility=visibility,
                memory_kind=record.kind,
                source_updated_at=getattr(record, "source_updated_at", None),
            )
        )
    )


def projections_from_conflict(
    record: Any,
    *,
    path: str,
    visibility: str = "owner",
) -> tuple[RetrievalProjection, ...]:
    """Project every active conflict variant without selecting a winner."""

    if getattr(record, "status", None) != "conflict":
        raise RetrievalValidationError("conflict projection requires conflict status")
    result: list[RetrievalProjection] = []
    for variant in record.variants:
        meaning = f"Conflict variant {variant.variant_id}: {variant.label}\n\n{variant.position}"
        projection = build_projection(
            ProjectionSource(
                path=path,
                source_text=record.render(),
                meaning=meaning,
                artifact_kind="conflict-variant",
                authority=record.authority,
                scope=record.scope,
                scope_id=record.scope_id,
                status="conflict",
                projection_id=f"{record.memory_id}:{variant.variant_id}",
                memory_id=record.memory_id,
                visibility=visibility,
                memory_kind=record.kind,
                source_updated_at=getattr(record, "source_updated_at", None),
            )
        )
        result.append(_require_projection(projection))
    return tuple(result)


def projection_from_summary(
    summary: Any,
    *,
    path: str,
    visibility: str = "owner",
) -> RetrievalProjection:
    """Project one current Project Summary as a structural artifact."""

    project_id = getattr(summary, "project_id", None)
    meaning_parts = [
        getattr(summary, "purpose", None),
        getattr(summary, "current_state", None),
        *(getattr(summary, name, ()) or () for name in (
            "active_workstreams",
            "important_outcomes",
            "open_questions",
            "next_steps",
        )),
    ]
    meaning = "\n".join(
        value if isinstance(value, str) else "\n".join(value)
        for value in meaning_parts
        if value
    )
    source_text = summary.render()
    return _require_projection(
        build_projection(
            ProjectionSource(
                path=path,
                source_text=source_text,
                meaning=meaning,
                artifact_kind="project-summary",
                authority=summary.authority,
                scope="project",
                scope_id=project_id,
                status="current",
                projection_id=f"project-summary:{project_id}",
                visibility=visibility,
                structural_id=f"project-summary:{project_id}",
            )
        )
    )


def projection_from_conversation(
    *,
    conversation_id: str,
    structural_id: str,
    path: str,
    source_text: str,
    meaning: str,
    scope: str,
    scope_id: str,
    project_id: str | None = None,
    visibility: str = "owner",
    source_updated_at: str | None = None,
) -> RetrievalProjection:
    """Project one current Conversation Continuation Summary."""

    if project_id is not None and scope == "project" and project_id != scope_id:
        raise RetrievalValidationError("conversation project identity disagrees with scope")
    return _require_projection(
        build_projection(
            ProjectionSource(
                path=path,
                source_text=source_text,
                meaning=meaning,
                artifact_kind="conversation-continuation",
                authority="noncanonical",
                scope=scope,
                scope_id=scope_id,
                status="current",
                projection_id=structural_id,
                visibility=visibility,
                conversation_id=conversation_id,
                structural_id=structural_id,
                source_updated_at=source_updated_at,
            )
        )
    )


@dataclass(frozen=True)
class ProjectionIndex:
    """Disposable validated projection set; source Markdown remains untouched."""

    projections: tuple[RetrievalProjection, ...]
    available: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.available, bool):
            raise TypeError("projection index availability must be boolean")
        projections = tuple(self.projections)
        seen: set[str] = set()
        paths: dict[str, str] = {}
        for projection in projections:
            if not isinstance(projection, RetrievalProjection):
                raise TypeError("projection index contains an invalid projection")
            if projection.projection_id in seen:
                raise RetrievalValidationError("duplicate projection identity")
            previous_kind = paths.get(projection.path)
            if previous_kind is not None and (
                previous_kind != "conflict-variant"
                or projection.artifact_kind != "conflict-variant"
            ):
                raise RetrievalValidationError("duplicate projection source path")
            seen.add(projection.projection_id)
            paths[projection.path] = projection.artifact_kind
        object.__setattr__(self, "projections", projections)

    @classmethod
    def rebuild(cls, sources: Iterable[ProjectionSource]) -> "ProjectionIndex":
        projections: list[RetrievalProjection] = []
        for source in sources:
            projection = build_projection(source)
            if projection is not None:
                projections.append(projection)
        return cls(tuple(projections))

    def reconcile(self, sources: Iterable[ProjectionSource]) -> "ProjectionIndex":
        """Replace the disposable set from explicit current source selections."""

        return type(self).rebuild(sources)


def rebuild_projections(sources: Iterable[ProjectionSource]) -> ProjectionIndex:
    return ProjectionIndex.rebuild(sources)


def publish_projection_index(index: ProjectionIndex, runtime_root: Path) -> Path:
    """Atomically publish one disposable private index from validated projections."""

    if not isinstance(index, ProjectionIndex) or not index.available:
        raise RetrievalValidationError("only an available validated index may publish")
    path = runtime_root / "retrieval" / "index.json"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    payload = {
        "schema": INDEX_SCHEMA,
        "projection_policy": PROJECTION_POLICY,
        "projections": [asdict(item) for item in index.projections],
    }
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".index.", dir=path.parent)
    try:
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return path


def load_projection_index(runtime_root: Path, vault_root: Path) -> ProjectionIndex:
    """Load an index and verify every cited source hash without scanning the vault."""

    path = runtime_root / "retrieval" / "index.json"
    if not path.is_file():
        raise RetrievalUnavailable("retrieval index is unavailable; rebuild required")
    if path.stat().st_mode & 0o077:
        raise RetrievalUnavailable("retrieval index permissions are unsafe; rebuild required")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RetrievalUnavailable("retrieval index is corrupt; rebuild required") from exc
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "projection_policy", "projections"}
        or value.get("schema") != INDEX_SCHEMA
        or value.get("projection_policy") != PROJECTION_POLICY
        or not isinstance(value.get("projections"), list)
    ):
        raise RetrievalUnavailable("retrieval index is corrupt; rebuild required")
    try:
        projections = tuple(RetrievalProjection(**item) for item in value["projections"])
        index = ProjectionIndex(projections)
    except (TypeError, ValueError) as exc:
        raise RetrievalUnavailable("retrieval index is corrupt; rebuild required") from exc
    resolved_vault = vault_root.resolve()
    for projection in index.projections:
        source = (resolved_vault / projection.path).resolve()
        if resolved_vault not in source.parents or not source.is_file():
            raise RetrievalUnavailable("retrieval source is missing; rebuild required")
        try:
            current_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        except OSError as exc:
            raise RetrievalUnavailable("retrieval source is unavailable; rebuild required") from exc
        if current_hash != projection.source_sha256:
            raise RetrievalUnavailable("retrieval source hash is stale; rebuild required")
    return index


def rebuild_projection_index(
    sources: Iterable[ProjectionSource], *, runtime_root: Path
) -> ProjectionIndex:
    """Rebuild only from explicitly selected permitted sources and publish the view."""

    index = ProjectionIndex.rebuild(sources)
    publish_projection_index(index, runtime_root)
    return index


def discover_projection_sources(vault_root: Path) -> tuple[ProjectionSource, ...]:
    """Select only governed Shallow Memory artifacts for an explicit rebuild."""

    resolved_vault = vault_root.resolve()
    root = resolved_vault / "System" / "Orca Memory" / "shallow"
    if not root.exists():
        return ()
    sources: list[ProjectionSource] = []
    for path in sorted(root.glob("**/*.md")):
        if path.name == "project.md":
            continue
        resolved = path.resolve()
        if resolved_vault not in resolved.parents:
            raise RetrievalValidationError("retrieval source escapes the configured vault")
        relative = path.relative_to(resolved_vault).as_posix()
        text = path.read_text(encoding="utf-8")
        if path.name == "summary.md":
            summary = parse_project_summary(text)
            projection = projection_from_summary(summary, path=relative)
            sources.append(_projection_source(projection, text))
            continue
        if "conversation-summaries" in path.parts:
            metadata, body = _markdown_parts(text)
            if metadata.get("schema_version") != "orca-conversation-continuation/1":
                raise RetrievalValidationError("invalid Conversation Continuation Summary")
            conversation_id = metadata.get("conversation_id")
            project_id = metadata.get("project_id")
            if not isinstance(conversation_id, str) or not conversation_id:
                raise RetrievalValidationError("continuation lacks conversation identity")
            scope = "project" if project_id is not None else (
                "unassigned" if "unassigned" in path.parts else "general"
            )
            scope_id = project_id if scope == "project" else scope
            structural_id = f"conv:{path.stem}"
            projection = projection_from_conversation(
                conversation_id=conversation_id,
                structural_id=structural_id,
                path=relative,
                source_text=text,
                meaning=body,
                scope=scope,
                scope_id=scope_id,
                project_id=project_id,
            )
            sources.append(_projection_source(projection, text))
            continue
        try:
            record = parse_record(text)
            projection = projection_from_memory(record, path=relative)
            sources.append(_projection_source(projection, text))
        except ValueError:
            conflict = parse_conflict_record(text)
            sources.extend(
                _projection_source(projection, text)
                for projection in projections_from_conflict(conflict, path=relative)
            )
    return tuple(sources)


@dataclass(frozen=True)
class AdapterHit:
    projection_id: str
    score: float


class RetrievalAdapter(Protocol):
    """Replaceable ranker over already permitted projections."""

    version: str

    def rank(
        self,
        query: str,
        projections: Sequence[RetrievalProjection],
        limit: int,
    ) -> Iterable[AdapterHit]:
        """Return bounded ranking candidates; never add projections."""


class AgentCairnRetrievalAdapter:
    """Governed AgentCairn seam over an injected local ranking function.

    The function receives only the pre-filtered projection sequence and must
    return ``AdapterHit`` values.  Orca validates every returned identity and
    score before presentation, so AgentCairn remains replaceable and
    non-authoritative.
    """

    version = AGENTCAIRN_ADAPTER_VERSION

    def __init__(
        self,
        ranker: Callable[[str, Sequence[RetrievalProjection], int], Iterable[AdapterHit]],
        *,
        version: str = AGENTCAIRN_ADAPTER_VERSION,
    ) -> None:
        if not callable(ranker):
            raise TypeError("AgentCairn ranker must be callable")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("AgentCairn adapter version is required")
        self._ranker = ranker
        self.version = version

    @classmethod
    def local(cls) -> "AgentCairnRetrievalAdapter":
        """Use AgentCairn BM25 over only the prefiltered in-memory projections."""

        def ranker(
            query: str,
            projections: Sequence[RetrievalProjection],
            limit: int,
        ) -> tuple[AdapterHit, ...]:
            try:
                from cairn.embed.fake import FakeEmbedder
                from cairn.index import bm25_search, build_fts, chunk_note, open_index
                from cairn.vault import Note
            except ImportError as exc:
                raise RetrievalUnavailable(
                    "AgentCairn retrieval dependency is unavailable"
                ) from exc
            embedder = FakeEmbedder()
            connection = open_index(":memory:", dim=embedder.dim, model_id=embedder.model_id)
            try:
                for projection in projections:
                    note = Note(
                        permalink=projection.projection_id,
                        frontmatter={
                            "title": projection.projection_id,
                            "type": "orca-retrieval-projection",
                        },
                        body=projection.meaning,
                    )
                    connection.execute(
                        "INSERT INTO notes (permalink,path,title,type,content_hash,mtime) "
                        "VALUES (?,?,?,?,?,?)",
                        [
                            projection.projection_id,
                            projection.path,
                            projection.projection_id,
                            "orca-retrieval-projection",
                            projection.source_sha256,
                            0.0,
                        ],
                    )
                    chunks = chunk_note(note)
                    vectors = embedder.embed([chunk.text for chunk in chunks])
                    for chunk, vector in zip(chunks, vectors, strict=True):
                        connection.execute(
                            "INSERT INTO chunks VALUES (?,?,?,?,?)",
                            [
                                chunk.chunk_id,
                                projection.projection_id,
                                chunk.heading_path,
                                chunk.ordinal,
                                chunk.text,
                            ],
                        )
                        connection.execute(
                            "INSERT INTO chunk_embeddings VALUES (?,?)",
                            [chunk.chunk_id, vector],
                        )
                if not projections:
                    return ()
                build_fts(connection)
                rows = bm25_search(connection, query, limit=max(limit * 4, 20))
                best: dict[str, float] = {}
                for chunk_id, _, score in rows:
                    row = connection.execute(
                        "SELECT note_permalink FROM chunks WHERE chunk_id = ?",
                        [chunk_id],
                    ).fetchone()
                    if row is not None:
                        best[row[0]] = max(best.get(row[0], 0.0), float(score))
                ordered = sorted(best.items(), key=lambda item: (-item[1], item[0]))
                return tuple(AdapterHit(identity, score) for identity, score in ordered[:limit])
            finally:
                connection.close()

        return cls(ranker)

    def rank(
        self,
        query: str,
        projections: Sequence[RetrievalProjection],
        limit: int,
    ) -> tuple[AdapterHit, ...]:
        values = self._ranker(query, tuple(projections), limit)
        if values is None:
            raise RetrievalValidationError("retrieval adapter returned no ranking sequence")
        result: list[AdapterHit] = []
        for value in values:
            if isinstance(value, AdapterHit):
                hit = value
            elif isinstance(value, tuple) and len(value) == 2:
                hit = AdapterHit(value[0], value[1])
            elif isinstance(value, Mapping):
                hit = AdapterHit(value.get("projection_id"), value.get("score"))
            else:
                raise RetrievalValidationError("retrieval adapter returned an invalid hit")
            if not isinstance(hit.projection_id, str) or not _SAFE_ID.fullmatch(hit.projection_id):
                raise RetrievalValidationError("retrieval adapter returned an invalid identity")
            if not isinstance(hit.score, (int, float)) or not math.isfinite(float(hit.score)):
                raise RetrievalValidationError("retrieval adapter returned an invalid score")
            if hit.score < 0:
                raise RetrievalValidationError("retrieval adapter returned a negative score")
            result.append(AdapterHit(hit.projection_id, float(hit.score)))
        return tuple(result)


AgentCairnAdapter = AgentCairnRetrievalAdapter


@dataclass(frozen=True)
class RecallRequest:
    """Owner- or agent-initiated Recall request and hard-filter context."""

    question: str
    project_id: str | None = None
    project_alias: str | None = None
    memory_kind: str | None = None
    scope: str | None = None
    allowed_visibility: frozenset[str] = frozenset({"owner"})
    allowed_authorities: frozenset[str] = frozenset({"canonical", "noncanonical"})
    requester_id: str | None = None
    topic: str | None = None
    time_from: str | None = None
    time_until: str | None = None
    conversation_context: str | None = None
    include_closed: bool = False
    max_results: int = MAX_RESULTS
    exact_conversation: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.question, str) or not self.question.strip():
            raise RetrievalValidationError("explicit Recall question is required")
        if contains_secret(self.question):
            raise RetrievalValidationError("Recall question contains a credential-like value")
        if self.project_id is not None:
            _safe_id(self.project_id, "project_id")
        if self.requester_id is not None:
            _safe_id(self.requester_id, "requester_id")
        if self.project_alias is not None and (
            not isinstance(self.project_alias, str) or not self.project_alias.strip()
        ):
            raise RetrievalValidationError("project_alias must be nonempty when supplied")
        if self.scope is not None and self.scope not in _ALLOWED_SCOPES:
            raise RetrievalValidationError("Recall scope is invalid")
        if self.topic is not None and (
            not isinstance(self.topic, str) or not self.topic.strip()
        ):
            raise RetrievalValidationError("Recall topic must be nonempty when supplied")
        if self.time_from is not None:
            _validate_timestamp(self.time_from, "time_from")
        if self.time_until is not None:
            _validate_timestamp(self.time_until, "time_until")
        if self.time_from and self.time_until and self.time_from > self.time_until:
            raise RetrievalValidationError("Recall time range is reversed")
        if self.conversation_context is not None:
            if not isinstance(self.conversation_context, str):
                raise RetrievalValidationError("conversation_context must be text")
            if contains_secret(self.conversation_context):
                raise RetrievalValidationError(
                    "conversation_context contains a credential-like value"
                )
        if not self.allowed_visibility:
            raise RetrievalValidationError("Recall visibility context cannot be empty")
        if not self.allowed_authorities or not self.allowed_authorities <= _ALLOWED_AUTHORITIES:
            raise RetrievalValidationError("Recall authority context is invalid")
        if not isinstance(self.max_results, int) or self.max_results <= 0:
            raise RetrievalValidationError("Recall max_results must be positive")
        if self.exact_conversation is not None:
            _safe_id(self.exact_conversation, "exact_conversation")

    @property
    def memory_question(self) -> str:
        return self.question


@dataclass(frozen=True)
class RecallResult:
    path: str
    memory_id: str | None
    authority: str
    scope: str
    scope_id: str
    status: str
    excerpt: str
    source_sha256: str
    projection_policy: str
    score: float
    artifact_kind: str
    structural_id: str | None = None

    def __post_init__(self) -> None:
        _safe_relative_path(self.path)
        if self.memory_id is not None:
            _safe_id(self.memory_id, "memory_id")
        if self.structural_id is not None:
            _safe_id(self.structural_id, "structural_id")
        if self.authority not in _ALLOWED_AUTHORITIES:
            raise RetrievalValidationError("Recall result authority is invalid")
        _validate_scope(self.scope, self.scope_id)
        if self.status not in _ALLOWED_STATUSES:
            raise RetrievalValidationError("Recall result status is invalid")
        if not self.excerpt.strip() or contains_secret(self.excerpt):
            raise RetrievalValidationError("Recall result excerpt is invalid")
        _validate_hash(self.source_sha256, "source_sha256")
        if self.projection_policy != PROJECTION_POLICY:
            raise RetrievalValidationError("Recall result projection policy is invalid")
        if (
            not isinstance(self.score, (int, float))
            or not math.isfinite(float(self.score))
            or self.score < 0
        ):
            raise RetrievalValidationError("Recall result score is invalid")

    @property
    def identity(self) -> str:
        """Return the permanent or structural source identity for citation."""

        return self.memory_id or self.structural_id or self.path


@dataclass(frozen=True)
class RecallResponse:
    results: tuple[RecallResult, ...]
    applied_filters: Mapping[str, object]
    omitted: tuple[str, ...] = ()
    refinement_required: bool = False


class RecallService:
    """Apply deterministic Recall filters and budgets around one adapter."""

    def __init__(
        self,
        index: ProjectionIndex,
        adapter: RetrievalAdapter,
        *,
        project_alias_resolver: Callable[[str], str | None] | None = None,
        total_tokens: int = MAX_TOTAL_TOKENS,
        per_document_tokens: int = MAX_DOCUMENT_TOKENS,
        exact_continuation_tokens: int = EXACT_CONTINUATION_TOKENS,
    ) -> None:
        if not isinstance(index, ProjectionIndex):
            raise TypeError("Recall requires a ProjectionIndex")
        if not hasattr(adapter, "rank") or not callable(adapter.rank):
            raise TypeError("Recall requires a RetrievalAdapter")
        for name, value, ceiling in (
            ("total_tokens", total_tokens, MAX_TOTAL_TOKENS),
            ("per_document_tokens", per_document_tokens, MAX_DOCUMENT_TOKENS),
            ("exact_continuation_tokens", exact_continuation_tokens, EXACT_CONTINUATION_TOKENS),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or not 0 < value <= ceiling:
                raise RetrievalValidationError(f"Recall {name} exceeds the accepted bound")
        self._index = index
        self._adapter = adapter
        self._project_alias_resolver = project_alias_resolver
        self._total_tokens = total_tokens
        self._per_document_tokens = per_document_tokens
        self._exact_continuation_tokens = exact_continuation_tokens

    def recall(self, request: RecallRequest) -> RecallResponse:
        """Perform one explicit bounded recall; no semantic summarization call."""

        if not isinstance(request, RecallRequest):
            raise TypeError("Recall requires RecallRequest")
        if not self._index.available:
            raise RetrievalUnavailable("retrieval index is unavailable; rebuild required")
        project_id = self._resolve_project(request)
        exact_key = request.exact_conversation or _conversation_key(request.question)
        exact_projection = self._exact_projection(exact_key)
        if project_id is not None and request.scope not in {None, "project"}:
            raise RetrievalValidationError("Recall scope and project disagree")
        if exact_projection is not None and (
            (request.scope is not None and request.scope != exact_projection.scope)
            or (
                project_id is not None
                and (exact_projection.scope != "project" or exact_projection.scope_id != project_id)
            )
        ):
            raise RetrievalValidationError("Recall scope and exact conversation disagree")
        if (
            project_id is None
            and request.scope not in {"general", "unassigned"}
            and exact_projection is None
        ):
            raise RetrievalValidationError(
                "Recall requires a project, explicit general/unassigned scope, or known exact conversation"
            )
        eligible = tuple(
            projection
            for projection in self._index.projections
            if self._eligible(
                projection,
                request,
                project_id,
                exact_key,
                exact_projection,
            )
        )
        if not eligible:
            return RecallResponse(
                results=(),
                applied_filters=_filters(request, project_id, exact_key),
                omitted=(),
                refinement_required=False,
            )
        hits = self._adapter.rank(request.question, eligible, len(eligible))
        if hits is None:
            raise RetrievalValidationError("retrieval adapter returned no ranking sequence")
        ranked = self._validate_and_order_hits(hits, eligible)
        if exact_projection is not None and exact_projection in eligible:
            # Reserve the handoff budget for the requested conversation before related hits.
            exact_hit = next(
                (item for item in ranked if item[0] == exact_projection),
                (exact_projection, 1.0),
            )
            ranked = [exact_hit, *(item for item in ranked if item[0] != exact_projection)]
        selected, collapsed = self._collapse(ranked)
        results, budget_omitted = self._make_results(
            selected,
            request.question,
            exact=exact_key is not None,
            max_results=min(MAX_RESULTS, request.max_results),
        )
        omitted = tuple(collapsed + budget_omitted)
        return RecallResponse(
            results=tuple(results),
            applied_filters=_filters(request, project_id, exact_key),
            omitted=omitted,
            refinement_required=not results and bool(ranked),
        )

    def _resolve_project(self, request: RecallRequest) -> str | None:
        if request.project_alias is None:
            return request.project_id
        if self._project_alias_resolver is None:
            raise RetrievalValidationError("unknown or ambiguous Project Alias")
        resolved = self._project_alias_resolver(request.project_alias)
        if not isinstance(resolved, str) or not resolved:
            raise RetrievalValidationError("unknown or ambiguous Project Alias")
        _safe_id(resolved, "resolved project_id")
        if request.project_id is not None and request.project_id != resolved:
            raise RetrievalValidationError("Project Alias and project_id disagree")
        return resolved

    @staticmethod
    def _eligible(
        projection: RetrievalProjection,
        request: RecallRequest,
        project_id: str | None,
        exact_key: str | None,
        exact_projection: RetrievalProjection | None,
    ) -> bool:
        if projection.authority not in request.allowed_authorities:
            return False
        if projection.visibility not in request.allowed_visibility:
            return False
        if projection.status == "closed" and not request.include_closed:
            return False
        if projection.status not in {"current", "conflict", "closed"}:
            return False
        if request.scope is not None and projection.scope != request.scope:
            return False
        if project_id is not None and (
            projection.scope != "project" or projection.scope_id != project_id
        ):
            return False
        if request.memory_kind is not None and projection.memory_kind != request.memory_kind:
            return False
        if request.topic is not None and not _topic_matches(projection, request.topic):
            return False
        if request.time_from is not None and (
            projection.source_updated_at is None
            or projection.source_updated_at < request.time_from
        ):
            return False
        if request.time_until is not None and (
            projection.source_updated_at is None
            or projection.source_updated_at > request.time_until
        ):
            return False
        if exact_key is not None:
            if projection.structural_id == exact_key:
                return True
            # Exact conversation recall may include its associated Project
            # Summary and project-scoped Typed Memory Records only.
            if exact_projection is None:
                return False
            return (
                projection.artifact_kind in {"project-summary", "typed-memory-record"}
                and projection.scope == exact_projection.scope
                and projection.scope_id == exact_projection.scope_id
            )
        return True

    def _exact_projection(self, exact_key: str | None) -> RetrievalProjection | None:
        if exact_key is None:
            return None
        matches = tuple(
            projection
            for projection in self._index.projections
            if projection.structural_id == exact_key
            and projection.artifact_kind == "conversation-continuation"
        )
        if len(matches) > 1:
            raise RetrievalValidationError("duplicate exact conversation projection")
        return matches[0] if matches else None

    @staticmethod
    def _validate_and_order_hits(
        hits: Iterable[AdapterHit],
        eligible: Sequence[RetrievalProjection],
    ) -> list[tuple[RetrievalProjection, float]]:
        by_id = {projection.projection_id: projection for projection in eligible}
        seen: set[str] = set()
        ranked: list[tuple[RetrievalProjection, float]] = []
        for hit in hits:
            if not isinstance(hit, AdapterHit):
                raise RetrievalValidationError("adapter returned an invalid hit")
            if hit.projection_id not in by_id:
                raise RetrievalValidationError("adapter returned an ineligible projection")
            if hit.projection_id in seen:
                raise RetrievalValidationError("adapter returned duplicate projection identity")
            seen.add(hit.projection_id)
            if (
                not isinstance(hit.score, (int, float))
                or not math.isfinite(float(hit.score))
                or hit.score < 0
            ):
                raise RetrievalValidationError("adapter returned an invalid score")
            if hit.score <= 0:
                continue
            ranked.append((by_id[hit.projection_id], hit.score))
        ranked.sort(key=lambda item: (-item[1], item[0].projection_id))
        # Canonical-first applies only inside a narrow relevance tie.  A weak
        # canonical result therefore cannot displace a materially stronger
        # Shallow result.
        ordered: list[tuple[RetrievalProjection, float]] = []
        index = 0
        while index < len(ranked):
            base_score = ranked[index][1]
            end = index + 1
            while end < len(ranked) and base_score - ranked[end][1] <= 0.05:
                end += 1
            group = ranked[index:end]
            group.sort(key=lambda item: (0 if item[0].authority == "canonical" else 1, item[0].projection_id))
            ordered.extend(group)
            index = end
        return ordered

    @staticmethod
    def _collapse(
        ranked: Sequence[tuple[RetrievalProjection, float]],
    ) -> tuple[list[tuple[RetrievalProjection, float]], list[str]]:
        selected: list[tuple[RetrievalProjection, float]] = []
        seen_identity: set[str] = set()
        omitted: list[str] = []
        for projection, score in ranked:
            identity = projection.source_identity
            # Active conflict variants are intentionally separate results; all
            # other projections sharing one source identity collapse.
            if projection.artifact_kind != "conflict-variant" and identity in seen_identity:
                omitted.append("duplicate identity")
                continue
            if any(
                _strong_overlap(projection.meaning, prior.meaning)
                for prior, _ in selected
                if projection.scope == prior.scope and projection.scope_id == prior.scope_id
                and projection.artifact_kind != "conflict-variant"
                and prior.artifact_kind != "conflict-variant"
            ):
                omitted.append("strongly overlapping result")
                continue
            seen_identity.add(identity)
            selected.append((projection, score))
        return selected, omitted

    def _make_results(
        self,
        ranked: Sequence[tuple[RetrievalProjection, float]],
        question: str,
        *,
        exact: bool,
        max_results: int,
    ) -> tuple[list[RecallResult], list[str]]:
        results: list[RecallResult] = []
        omitted: list[str] = []
        remaining = self._total_tokens
        for projection, score in ranked:
            if len(results) >= max_results:
                omitted.append("result-count limit")
                continue
            if exact and projection.artifact_kind == "conversation-continuation":
                cap = self._exact_continuation_tokens
            elif exact and projection.artifact_kind == "project-summary":
                cap = min(EXACT_PROJECT_SUMMARY_TOKENS, self._per_document_tokens)
            else:
                cap = self._per_document_tokens
            cap = min(cap, remaining)
            if cap <= 0:
                omitted.append("total token limit")
                continue
            if exact and projection.artifact_kind == "conversation-continuation":
                # An exact handoff needs its state and next steps, not a search snippet.
                excerpt = _truncate_words(projection.meaning, cap)
            else:
                excerpt = _select_excerpt(projection.meaning, question, cap)
            if not excerpt:
                omitted.append("irrelevant excerpt")
                continue
            used = len(excerpt.split()) + 12  # visible labels and provenance
            if used > remaining:
                available = max(1, remaining - 12)
                excerpt = _truncate_words(excerpt, available)
                used = len(excerpt.split()) + 12
            if used > remaining:
                omitted.append("total token limit")
                continue
            results.append(
                RecallResult(
                    path=projection.path,
                    memory_id=projection.memory_id,
                    authority=projection.authority,
                    scope=projection.scope,
                    scope_id=projection.scope_id,
                    status=projection.status,
                    excerpt=excerpt,
                    source_sha256=projection.source_sha256,
                    projection_policy=projection.projection_policy,
                    score=score,
                    artifact_kind=projection.artifact_kind,
                    structural_id=projection.structural_id,
                )
            )
            remaining -= used
        return results, omitted


Recall = RecallService


def explicit_recall(
    request: RecallRequest,
    *,
    index: ProjectionIndex,
    adapter: RetrievalAdapter,
    project_alias_resolver: Callable[[str], str | None] | None = None,
) -> RecallResponse:
    """Convenience explicit-invocation surface; it performs no automatic recall."""

    return RecallService(
        index,
        adapter,
        project_alias_resolver=project_alias_resolver,
    ).recall(request)


def _validate_scope(scope: str, scope_id: str) -> None:
    if scope not in _ALLOWED_SCOPES:
        raise RetrievalValidationError("projection scope is invalid")
    if not isinstance(scope_id, str) or not scope_id.strip():
        raise RetrievalValidationError("projection scope_id is required")
    if scope in {"general", "unassigned"} and scope_id != scope:
        raise RetrievalValidationError(f"{scope} projection requires fixed scope_id")
    if scope == "project":
        _safe_id(scope_id, "scope_id")


def _safe_id(value: object, field: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise RetrievalValidationError(f"{field} is not a safe identifier")


def _safe_relative_path(value: object) -> None:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RetrievalValidationError("projection path must be a relative POSIX path")
    if contains_secret(value):
        raise RetrievalValidationError("projection path contains a credential-like value")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise RetrievalValidationError("projection path is unsafe")


def _validate_hash(value: object, field: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise RetrievalValidationError(f"{field} is not a SHA-256 hash")


def _validate_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value
    ):
        raise RetrievalValidationError(f"{field} must be a UTC RFC 3339 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RetrievalValidationError(
            f"{field} must be a UTC RFC 3339 timestamp"
        ) from exc


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _projection_source(
    projection: RetrievalProjection, source_text: str
) -> ProjectionSource:
    return ProjectionSource(
        path=projection.path,
        source_text=source_text,
        meaning=projection.meaning,
        artifact_kind=projection.artifact_kind,
        authority=projection.authority,
        scope=projection.scope,
        scope_id=projection.scope_id,
        status=projection.status,
        projection_id=projection.projection_id,
        memory_id=projection.memory_id,
        visibility=projection.visibility,
        memory_kind=projection.memory_kind,
        conversation_id=projection.conversation_id,
        structural_id=projection.structural_id,
        source_updated_at=projection.source_updated_at,
    )


def _markdown_parts(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise RetrievalValidationError("invalid structural Markdown frontmatter")
    marker = text.index("\n---\n", 4)
    metadata = yaml.safe_load(text[4:marker])
    if not isinstance(metadata, dict):
        raise RetrievalValidationError("invalid structural Markdown frontmatter")
    return metadata, text[marker + 5 :].strip()


def _require_projection(value: RetrievalProjection | None) -> RetrievalProjection:
    if value is None:
        raise RetrievalValidationError("stale source cannot produce a projection")
    return value


def _conversation_key(question: str) -> str | None:
    if question.startswith("conv:") and "--" in question:
        key = question.strip()
        if _SAFE_ID.fullmatch(key):
            return key
    return None


def _filters(
    request: RecallRequest,
    project_id: str | None,
    exact_key: str | None,
) -> dict[str, object]:
    return {
        "project_id": project_id,
        "scope": request.scope,
        "memory_kind": request.memory_kind,
        "topic": request.topic,
        "time_from": request.time_from,
        "time_until": request.time_until,
        "requester_id": request.requester_id,
        "allowed_visibility": tuple(sorted(request.allowed_visibility)),
        "allowed_authorities": tuple(sorted(request.allowed_authorities)),
        "include_closed": request.include_closed,
        "exact_conversation": exact_key,
    }


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w]+", value.casefold()))


def _topic_matches(projection: RetrievalProjection, topic: str) -> bool:
    query = _tokens(topic)
    return bool(query) and query <= _tokens(projection.meaning)


def _strong_overlap(left: str, right: str) -> bool:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if len(left_tokens) < 3 or len(right_tokens) < 3:
        return False
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) >= 0.8


def _select_excerpt(text: str, question: str, cap: int) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", text) if chunk.strip()]
    if not chunks:
        return ""
    query_tokens = _tokens(question)
    scored = [
        (len(query_tokens & _tokens(chunk)), index, chunk)
        for index, chunk in enumerate(chunks)
    ]
    relevant = [item for item in scored if item[0] > 0]
    if relevant:
        relevant.sort(key=lambda item: (-item[0], item[1]))
        chosen = {relevant[0][1]}
        # Include adjacent sentences when they fit and preserve source order.
        for _, index, _ in relevant[1:]:
            if index in {relevant[0][1] - 1, relevant[0][1] + 1}:
                chosen.add(index)
    else:
        chosen = {0}
    excerpt = " ".join(chunks[index] for index in sorted(chosen))
    return _truncate_words(excerpt, cap)


def _truncate_words(value: str, cap: int) -> str:
    words = value.split()
    if len(words) <= cap:
        return value
    if cap <= 1:
        return "…"
    return " ".join(words[: cap - 1]) + " …"


__all__ = [
    "AGENTCAIRN_ADAPTER_VERSION",
    "AgentCairnAdapter",
    "AgentCairnRetrievalAdapter",
    "AdapterHit",
    "EXACT_CONTINUATION_TOKENS",
    "EXACT_PROJECT_SUMMARY_TOKENS",
    "MAX_DOCUMENT_TOKENS",
    "MAX_RESULTS",
    "MAX_TOTAL_TOKENS",
    "INDEX_SCHEMA",
    "PROJECTION_POLICY",
    "ProjectionIndex",
    "ProjectionSource",
    "Recall",
    "RecallRequest",
    "RecallResponse",
    "RecallResult",
    "RecallService",
    "RetrievalAdapter",
    "RetrievalProjection",
    "RetrievalUnavailable",
    "RetrievalValidationError",
    "build_projection",
    "discover_projection_sources",
    "explicit_recall",
    "load_projection_index",
    "projection_from_conversation",
    "projection_from_memory",
    "projection_from_summary",
    "projections_from_conflict",
    "rebuild_projections",
    "rebuild_projection_index",
    "publish_projection_index",
]
