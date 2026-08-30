"""Deterministic ordinary Knowledge Candidate contracts.

Candidates are inspectable, noncanonical proposals.  This module validates
their artifact shape and produces fixed placement, materialization, support,
and disposition values; it does not write the vault, host configuration, or a
canonical target.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Iterable, Literal, Mapping
import unicodedata

from orca_memory.privacy import contains_secret
from orca_memory.projects import project_alias_slug


CANDIDATE_SCHEMA = "orca-knowledge-candidate/0.1"
DISPOSITION_SCHEMA = "orca-knowledge-candidate-disposition/0.1"
CANDIDATE_AUTHORITY = "noncanonical"

CandidateKind = Literal["fact", "decision", "preference", "lesson", "project-state"]
CandidateScope = Literal["project", "general", "unassigned"]
CandidateStatus = Literal["pending", "approved-for-manual-apply", "rejected"]
DispositionTarget = Literal["approved-for-manual-apply", "rejected"]
ReconciliationStatus = Literal["applied", "pending", "repair-required"]

CONTROLLED_KINDS = frozenset({"fact", "decision", "preference", "lesson", "project-state"})
CONTROLLED_SCOPES = frozenset({"project", "general", "unassigned"})
CONTROLLED_STATUSES = frozenset({"pending", "approved-for-manual-apply", "rejected"})

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_FRONTMATTER_KEYS = (
    "schema_version",
    "candidate_id",
    "candidate_kind",
    "subject",
    "authority",
    "scope",
    "scope_id",
    "status",
    "source_updated_at",
    "created_at",
    "updated_at",
)


@dataclass(frozen=True)
class CandidateProposal:
    """Semantic proposal accepted from Processor before Storage identity."""

    candidate_kind: str
    subject: str
    proposal: str
    scope: str
    scope_id: str
    context: str | None = None
    source_updated_at: str | datetime | None = None

    def __post_init__(self) -> None:
        _validate_semantic_fields(
            self.candidate_kind,
            self.subject,
            self.proposal,
            self.context,
            self.scope,
            self.scope_id,
            self.source_updated_at,
        )


@dataclass(frozen=True)
class KnowledgeCandidate:
    """One validated ordinary candidate Markdown artifact."""

    candidate_id: str
    candidate_kind: str
    subject: str
    authority: str
    scope: str
    scope_id: str
    status: str
    source_updated_at: str | datetime | None
    created_at: str | datetime
    updated_at: str | datetime
    proposal: str
    context: str | None = None
    schema_version: str = CANDIDATE_SCHEMA

    def __post_init__(self) -> None:
        _validate_id(self.candidate_id, "candidate_id")
        if self.schema_version != CANDIDATE_SCHEMA:
            raise ValueError(f"unsupported candidate schema: {self.schema_version!r}")
        if self.authority != CANDIDATE_AUTHORITY:
            raise ValueError("candidate authority must be noncanonical")
        _validate_semantic_fields(
            self.candidate_kind,
            self.subject,
            self.proposal,
            self.context,
            self.scope,
            self.scope_id,
            self.source_updated_at,
        )
        if self.status not in CONTROLLED_STATUSES:
            raise ValueError(f"unsupported candidate status: {self.status!r}")
        created = _utc_timestamp(self.created_at, "created_at")
        updated = _utc_timestamp(self.updated_at, "updated_at")
        if _parse_timestamp(updated) < _parse_timestamp(created):
            raise ValueError("updated_at cannot precede created_at")
        source = (
            None
            if self.source_updated_at is None
            else _utc_timestamp(self.source_updated_at, "source_updated_at")
        )
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "updated_at", updated)
        object.__setattr__(self, "source_updated_at", source)

    @classmethod
    def from_proposal(
        cls,
        proposal: CandidateProposal,
        *,
        candidate_id: str,
        created_at: str | datetime,
    ) -> "KnowledgeCandidate":
        """Materialize a Storage-assigned proposal as a pending candidate."""

        if not isinstance(proposal, CandidateProposal):
            raise TypeError("candidate materialization requires CandidateProposal")
        return cls(
            candidate_id=candidate_id,
            candidate_kind=proposal.candidate_kind,
            subject=proposal.subject,
            authority=CANDIDATE_AUTHORITY,
            scope=proposal.scope,
            scope_id=proposal.scope_id,
            status="pending",
            source_updated_at=proposal.source_updated_at,
            created_at=created_at,
            updated_at=created_at,
            proposal=proposal.proposal,
            context=proposal.context,
        )

    def to_proposal(self) -> CandidateProposal:
        return CandidateProposal(
            candidate_kind=self.candidate_kind,
            subject=self.subject,
            proposal=self.proposal,
            scope=self.scope,
            scope_id=self.scope_id,
            context=self.context,
            source_updated_at=self.source_updated_at,
        )

    def render(self) -> str:
        """Render exactly the candidate schema and permitted body sections."""

        lines = [
            "---",
            f"schema_version: {self.schema_version}",
            f"candidate_id: {self.candidate_id}",
            f"candidate_kind: {self.candidate_kind}",
            f"subject: {_yaml_scalar(self.subject)}",
            f"authority: {self.authority}",
            f"scope: {self.scope}",
            f"scope_id: {self.scope_id}",
            f"status: {self.status}",
            f"source_updated_at: {self.source_updated_at or 'null'}",
            f"created_at: {self.created_at}",
            f"updated_at: {self.updated_at}",
            "---",
            "## Proposal",
            "",
            self.proposal,
        ]
        if self.context is not None:
            lines.extend(("", "## Context", "", self.context))
        lines.append("")
        payload = "\n".join(lines)
        if contains_secret(payload):
            raise ValueError("candidate contains a credential-like value")
        return payload

    @classmethod
    def parse(cls, markdown: str) -> "KnowledgeCandidate":
        """Parse and strictly validate one complete candidate artifact."""

        if not isinstance(markdown, str):
            raise TypeError("candidate artifact must be text")
        lines = markdown.splitlines()
        if len(lines) < 15 or lines[0] != "---":
            raise ValueError("candidate must start with YAML frontmatter")
        try:
            end = lines.index("---", 1)
        except ValueError as exc:
            raise ValueError("candidate frontmatter is not closed") from exc
        frontmatter = lines[1:end]
        if len(frontmatter) != len(_FRONTMATTER_KEYS):
            raise ValueError("candidate has an unexpected frontmatter shape")
        values: dict[str, str | None] = {}
        for line, expected_key in zip(frontmatter, _FRONTMATTER_KEYS):
            if ":" not in line:
                raise ValueError(f"invalid candidate frontmatter line: {line!r}")
            key, raw = line.split(":", 1)
            if key != expected_key or key in values:
                raise ValueError("candidate frontmatter keys are not canonical")
            value = raw.strip()
            if key == "source_updated_at" and value == "null":
                values[key] = None
            else:
                values[key] = _parse_yaml_scalar(value)

        body = "\n".join(lines[end + 1 :])
        if not body.startswith("## Proposal\n\n"):
            raise ValueError("candidate body requires ## Proposal")
        body = body[len("## Proposal\n\n") :]
        context_marker = "\n\n## Context\n\n"
        if context_marker in body:
            proposal, context = body.split(context_marker, 1)
        else:
            proposal, context = body, None
        if context is not None and "\n\n## " in context:
            raise ValueError("candidate body contains an unsupported section")
        if proposal.endswith("\n"):
            proposal = proposal[:-1]
        if context is not None and context.endswith("\n"):
            context = context[:-1]
        return cls(
            schema_version=_required_text(values, "schema_version"),
            candidate_id=_required_text(values, "candidate_id"),
            candidate_kind=_required_text(values, "candidate_kind"),
            subject=_required_text(values, "subject"),
            authority=_required_text(values, "authority"),
            scope=_required_text(values, "scope"),
            scope_id=_required_text(values, "scope_id"),
            status=_required_text(values, "status"),
            source_updated_at=values["source_updated_at"],
            created_at=_required_text(values, "created_at"),
            updated_at=_required_text(values, "updated_at"),
            proposal=proposal,
            context=context,
        )

    @property
    def is_recall_eligible(self) -> bool:
        """Ordinary Recall never includes Knowledge Candidates."""

        return False


@dataclass(frozen=True)
class CandidatePlacement:
    """Pure deterministic candidate locator; no filesystem mutation."""

    path: Path
    relative_path: str
    filename: str


@dataclass(frozen=True)
class SupportResult:
    """Result of exact supporting evidence: the candidate is not rewritten."""

    candidate: KnowledgeCandidate
    operation: Literal["support"] = "support"
    changed: bool = False


@dataclass(frozen=True)
class DispositionReceipt:
    """Content-minimized receipt for one explicit Owner disposition."""

    operation_id: str
    candidate_id: str
    from_status: str
    to_status: str
    recorded_at: str | datetime
    candidate_before_sha256: str
    candidate_after_sha256: str
    schema_version: str = DISPOSITION_SCHEMA

    def __post_init__(self) -> None:
        _validate_id(self.operation_id, "operation_id")
        _validate_id(self.candidate_id, "candidate_id")
        if self.schema_version != DISPOSITION_SCHEMA:
            raise ValueError("unsupported disposition receipt schema")
        if self.from_status != "pending" or self.to_status not in {
            "approved-for-manual-apply",
            "rejected",
        }:
            raise ValueError("invalid candidate disposition transition")
        _validate_hash(self.candidate_before_sha256, "candidate_before_sha256")
        _validate_hash(self.candidate_after_sha256, "candidate_after_sha256")
        object.__setattr__(self, "recorded_at", _utc_timestamp(self.recorded_at, "recorded_at"))

    def render(self) -> str:
        value = {
            "schema_version": self.schema_version,
            "operation_id": self.operation_id,
            "candidate_id": self.candidate_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "recorded_at": self.recorded_at,
            "candidate_before_sha256": self.candidate_before_sha256,
            "candidate_after_sha256": self.candidate_after_sha256,
        }
        return json.dumps(value, indent=2, sort_keys=True) + "\n"

    @classmethod
    def parse(cls, payload: str) -> "DispositionReceipt":
        try:
            value = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid candidate disposition receipt") from exc
        expected = {
            "schema_version",
            "operation_id",
            "candidate_id",
            "from_status",
            "to_status",
            "recorded_at",
            "candidate_before_sha256",
            "candidate_after_sha256",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("candidate disposition receipt has an unexpected shape")
        return cls(**value)


@dataclass(frozen=True)
class DispositionPlan:
    """Fixed before/after candidate images and their content-free receipt."""

    before: KnowledgeCandidate
    after: KnowledgeCandidate
    receipt: DispositionReceipt

    def __post_init__(self) -> None:
        if self.before.candidate_id != self.after.candidate_id:
            raise ValueError("disposition plan changes candidate identity")
        if self.receipt.candidate_id != self.before.candidate_id:
            raise ValueError("disposition receipt does not match candidate plan")
        if self.before.status != self.receipt.from_status:
            raise ValueError("disposition plan has an unexpected source status")
        if self.after.status != self.receipt.to_status:
            raise ValueError("disposition plan has an unexpected target status")
        if _sha256(self.before.render()) != self.receipt.candidate_before_sha256:
            raise ValueError("disposition before hash does not match candidate")
        if _sha256(self.after.render()) != self.receipt.candidate_after_sha256:
            raise ValueError("disposition after hash does not match candidate")


@dataclass(frozen=True)
class DispositionReconciliation:
    """Result of comparing a candidate with a durable disposition receipt."""

    status: ReconciliationStatus
    candidate: KnowledgeCandidate
    receipt: DispositionReceipt

    @property
    def needs_owner_repair(self) -> bool:
        return self.status == "repair-required"


def materialize_candidate(
    proposal: CandidateProposal,
    *,
    candidate_id: str,
    created_at: str | datetime,
) -> KnowledgeCandidate:
    """Storage-side pending materialization wrapper."""

    return KnowledgeCandidate.from_proposal(
        proposal,
        candidate_id=candidate_id,
        created_at=created_at,
    )


def candidate_short_id(candidate_id: str) -> str:
    """Return the deterministic locator suffix derived from full identity."""

    _validate_id(candidate_id, "candidate_id")
    return hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:12]


def candidate_subject_slug(subject: str) -> str:
    """Build a portable deterministic filename slug from a candidate subject."""

    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("candidate subject is required")
    value = unicodedata.normalize("NFC", subject).casefold()
    chars = [char if char.isalnum() else "-" for char in value]
    slug = re.sub(r"-+", "-", "".join(chars)).strip("-")
    if not slug:
        raise ValueError("candidate subject does not produce a portable slug")
    slug = slug[:72].rstrip("-")
    if slug.casefold() in {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }:
        raise ValueError("candidate subject produces a nonportable filename")
    return slug


def candidate_filename(candidate: KnowledgeCandidate) -> str:
    """Return Storage's deterministic ordinary-candidate filename."""

    return f"{candidate_subject_slug(candidate.subject)}--{candidate_short_id(candidate.candidate_id)}.md"


def candidate_placement(
    vault_root: str | os.PathLike[str],
    candidate: KnowledgeCandidate,
    *,
    project_alias: str | None = None,
) -> CandidatePlacement:
    """Return the accepted ``candidates/knowledge`` path without writing it."""

    if candidate.scope == "project":
        if project_alias is None:
            raise ValueError("project candidate placement requires project_alias")
        scope_path = Path("projects") / project_alias_slug(project_alias)
    else:
        if project_alias is not None:
            raise ValueError("non-project candidate placement cannot use project_alias")
        scope_path = Path(candidate.scope)
    filename = candidate_filename(candidate)
    relative = Path("System") / "Orca Memory" / "candidates" / "knowledge" / scope_path / filename
    root = Path(vault_root)
    return CandidatePlacement(root / relative, relative.as_posix(), filename)


def support_candidate(
    candidate: KnowledgeCandidate,
    proposal: CandidateProposal | None = None,
    *,
    candidate_id: str | None = None,
) -> SupportResult:
    """Accept exact support while preserving body and Storage timestamps."""

    if candidate_id is not None and candidate_id != candidate.candidate_id:
        raise ValueError("support target candidate identity does not match")
    if proposal is not None:
        if not isinstance(proposal, CandidateProposal):
            raise TypeError("support requires CandidateProposal")
        _assert_same_meaning(candidate, proposal)
    return SupportResult(candidate)


def plan_disposition(
    candidate: KnowledgeCandidate,
    *,
    target_status: DispositionTarget,
    owner_confirmed: bool,
    operation_id: str,
    changed_at: str | datetime,
    expected_candidate_id: str | None = None,
    expected_status: str = "pending",
) -> DispositionPlan:
    """Plan an Owner-only terminal disposition with stale-state checks."""

    if owner_confirmed is not True:
        raise PermissionError("candidate disposition requires explicit Owner confirmation")
    if expected_candidate_id is not None and expected_candidate_id != candidate.candidate_id:
        raise ValueError("candidate disposition identity does not match")
    if candidate.status != expected_status or expected_status != "pending":
        raise ValueError("candidate disposition requires the current pending status")
    if target_status not in {"approved-for-manual-apply", "rejected"}:
        raise ValueError(f"unsupported terminal candidate status: {target_status!r}")
    if _parse_timestamp(_utc_timestamp(changed_at, "changed_at")) < _parse_timestamp(
        candidate.updated_at
    ):
        raise ValueError("candidate disposition time cannot precede updated_at")
    after = KnowledgeCandidate(
        candidate_id=candidate.candidate_id,
        candidate_kind=candidate.candidate_kind,
        subject=candidate.subject,
        authority=candidate.authority,
        scope=candidate.scope,
        scope_id=candidate.scope_id,
        status=target_status,
        source_updated_at=candidate.source_updated_at,
        created_at=candidate.created_at,
        updated_at=changed_at,
        proposal=candidate.proposal,
        context=candidate.context,
        schema_version=candidate.schema_version,
    )
    before_hash = _sha256(candidate.render())
    after_hash = _sha256(after.render())
    receipt = DispositionReceipt(
        operation_id=operation_id,
        candidate_id=candidate.candidate_id,
        from_status="pending",
        to_status=target_status,
        recorded_at=changed_at,
        candidate_before_sha256=before_hash,
        candidate_after_sha256=after_hash,
    )
    return DispositionPlan(candidate, after, receipt)


def reconcile_disposition(
    candidate: KnowledgeCandidate,
    receipt: DispositionReceipt,
) -> DispositionReconciliation:
    """Reconcile an interrupted disposition without semantic or content input."""

    if candidate.candidate_id != receipt.candidate_id:
        raise ValueError("disposition receipt targets a different candidate")
    current_hash = _sha256(candidate.render())
    if candidate.status == receipt.to_status and current_hash == receipt.candidate_after_sha256:
        status: ReconciliationStatus = "applied"
    elif candidate.status == receipt.from_status and current_hash == receipt.candidate_before_sha256:
        status = "pending"
    else:
        status = "repair-required"
    return DispositionReconciliation(status, candidate, receipt)


def render_candidate(candidate: KnowledgeCandidate) -> str:
    return candidate.render()


def validate_candidate(markdown: str) -> KnowledgeCandidate:
    return KnowledgeCandidate.parse(markdown)


def render_disposition_receipt(receipt: DispositionReceipt) -> str:
    return receipt.render()


def _validate_semantic_fields(
    kind: str,
    subject: str,
    proposal: str,
    context: str | None,
    scope: str,
    scope_id: str,
    source_updated_at: str | datetime | None,
) -> None:
    if kind not in CONTROLLED_KINDS:
        raise ValueError(f"unsupported candidate kind: {kind!r}")
    if scope not in CONTROLLED_SCOPES:
        raise ValueError(f"unsupported candidate scope: {scope!r}")
    _validate_text(subject, "candidate subject")
    _validate_body_text(proposal, "candidate proposal")
    if context is not None:
        _validate_body_text(context, "candidate context")
    if scope == "project":
        _validate_id(scope_id, "project scope_id")
    elif scope_id != scope:
        raise ValueError(f"{scope} candidate must use scope_id {scope!r}")
    if source_updated_at is not None:
        _utc_timestamp(source_updated_at, "source_updated_at")
    for value in (subject, proposal, context):
        if value is not None and contains_secret(value):
            raise ValueError("candidate contains a credential-like value")


def _validate_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    if _CONTROL.search(value) or "\r" in value:
        raise ValueError(f"{field} contains nonportable control characters")
    if value != value.strip():
        raise ValueError(f"{field} has leading or trailing whitespace")


def _validate_body_text(value: str, field: str) -> None:
    _validate_text(value, field)
    if any(line.startswith("## ") for line in value.splitlines()):
        raise ValueError(f"{field} contains an unsupported body section")
    if re.search(
        r"(?im)^\s*(?:sources?|source_(?:uri|hash)|manifest(?:_path)?|"
        r"canonical[_ -]?target|memory_id|support[_ -]?count)\s*:",
        value,
    ):
        raise ValueError(f"{field} contains forbidden provenance or target fields")


def _assert_same_meaning(candidate: KnowledgeCandidate, proposal: CandidateProposal) -> None:
    if (
        candidate.candidate_kind,
        candidate.subject,
        candidate.proposal,
        candidate.context,
        candidate.scope,
        candidate.scope_id,
    ) != (
        proposal.candidate_kind,
        proposal.subject,
        proposal.proposal,
        proposal.context,
        proposal.scope,
        proposal.scope_id,
    ):
        raise ValueError("support proposal is materially different; create a new candidate")


def _validate_id(value: str, field: str) -> None:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} must be a safe opaque identifier")


def _validate_hash(value: str, field: str) -> None:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 hash")


def _utc_timestamp(value: str | datetime, field: str) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = _parse_timestamp(value)
    else:
        raise TypeError(f"{field} must be an ISO timestamp")
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError("timestamp must be text")
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
            result = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid quoted candidate scalar") from exc
        if not isinstance(result, str):
            raise ValueError("candidate scalar must be text")
        return result
    if not value or value.startswith(("'", "[", "{", "|", ">")):
        raise ValueError("unsupported candidate frontmatter scalar")
    return value


def _required_text(values: Mapping[str, str | None], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str):
        raise ValueError(f"candidate field {key} must be text")
    return value


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "CANDIDATE_AUTHORITY",
    "CANDIDATE_SCHEMA",
    "CONTROLLED_KINDS",
    "CONTROLLED_SCOPES",
    "CONTROLLED_STATUSES",
    "DISPOSITION_SCHEMA",
    "CandidatePlacement",
    "CandidateProposal",
    "DispositionPlan",
    "DispositionReceipt",
    "DispositionReconciliation",
    "KnowledgeCandidate",
    "SupportResult",
    "candidate_filename",
    "candidate_placement",
    "candidate_short_id",
    "candidate_subject_slug",
    "materialize_candidate",
    "plan_disposition",
    "reconcile_disposition",
    "render_candidate",
    "render_disposition_receipt",
    "support_candidate",
    "validate_candidate",
]
