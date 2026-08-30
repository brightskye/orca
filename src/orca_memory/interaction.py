"""Validated interaction observations, derived profiles, and fixed guidance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Literal

import yaml

from orca_memory.projects import project_alias_slug
from orca_memory.segmentation import SourceSegment, estimate_tokens


OBSERVATION_SCHEMA = "orca-interaction-observation/1"
OBSERVATION_POLICY = "interaction-observation/1"
PROFILE_SCHEMA = "orca-adaptive-profile/1"
AGGREGATION_POLICY = "interaction-aggregation/1"
GUIDANCE_POLICY = "interaction-guidance/1"

DIMENSIONS = frozenset(
    {"detail", "structure", "question-frequency", "technical-depth", "tone", "progress-updates"}
)
CONTEXTS = frozenset(
    {"general", "status-update", "explanation", "design-discussion", "implementation", "review"}
)
EVIDENCE_CLASSES = frozenset(
    {"explicit-general", "natural-comparison", "direct-correction", "dimension-specific-praise"}
)
ABSTENTION_REASONS = frozenset(
    {
        "missing-preceding-request",
        "missing-evaluated-response",
        "ambiguous-target",
        "ambiguous-context",
        "temporary-instruction",
        "surface-signal-only",
        "disallowed-inference",
        "unsupported-scope",
        "private-or-excluded",
    }
)
VALUES = {
    "detail": {"concise", "balanced", "detailed"},
    "structure": {"minimal", "moderate", "highly-structured"},
    "question-frequency": {"blocking-only", "selective", "proactive"},
    "technical-depth": {"plain-language", "mixed", "expert"},
    "tone": {"formal", "neutral", "conversational"},
    "progress-updates": {"milestones-only", "periodic", "frequent"},
}
DIRECTIONS = {
    "detail": {"decrease", "increase"},
    "structure": {"decrease", "increase"},
    "question-frequency": {"decrease", "increase"},
    "technical-depth": {"decrease", "increase"},
    "tone": {"more-formal", "more-conversational"},
    "progress-updates": {"decrease", "increase"},
}


@dataclass(frozen=True)
class InteractionScope:
    type: Literal["global", "agent", "project", "project-agent"]
    agent_id: str | None = None
    project_id: str | None = None

    def __post_init__(self) -> None:
        if self.type not in {"global", "agent", "project", "project-agent"}:
            raise ValueError("unsupported interaction scope")
        if self.type == "global" and (self.agent_id or self.project_id):
            raise ValueError("global interaction scope has no identity fields")
        if self.type == "agent" and (not self.agent_id or self.project_id):
            raise ValueError("agent scope requires only agent_id")
        if self.type == "project" and (not self.project_id or self.agent_id):
            raise ValueError("project scope requires only project_id")
        if self.type == "project-agent" and (not self.project_id or not self.agent_id):
            raise ValueError("project-agent scope requires both identities")

    def value(self) -> dict[str, str]:
        result = {"type": self.type}
        if self.agent_id:
            result["agent_id"] = self.agent_id
        if self.project_id:
            result["project_id"] = self.project_id
        return result


@dataclass(frozen=True)
class ObservationProposal:
    dimension: str
    context: str
    scope: InteractionScope
    evidence_class: str
    feedback_turn_id: str
    evaluated_assistant_turn_ids: tuple[str, ...]
    preceding_request_turn_id: str
    value: str | None = None
    direction: str | None = None
    lasting: bool = False
    replaces_prior: bool = False

    def __post_init__(self) -> None:
        _validate_preference(self.dimension, self.value, self.direction)
        if self.context not in CONTEXTS:
            raise ValueError("unsupported interaction context")
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError("unsupported interaction evidence class")
        if not self.feedback_turn_id or not self.preceding_request_turn_id:
            raise ValueError("observation source identities are required")
        if not self.evaluated_assistant_turn_ids:
            raise ValueError("observation requires an evaluated assistant response")
        if self.context == "general" and self.evidence_class != "explicit-general":
            raise ValueError("general context requires explicit general applicability")
        if self.lasting and self.evidence_class != "explicit-general":
            raise ValueError("only explicit-general evidence can activate immediately")
        if self.replaces_prior and not self.lasting:
            raise ValueError("replacement applies only to explicit lasting evidence")


@dataclass(frozen=True)
class InteractionObservation:
    observation_id: str
    dimension: str
    context: str
    scope: InteractionScope
    evidence_class: str
    conversation_id: str
    feedback_turn_id: str
    evaluated_assistant_turn_ids: tuple[str, ...]
    preceding_request_turn_id: str
    occurred_at: str
    value: str | None = None
    direction: str | None = None
    lasting: bool = False
    replaces_prior: bool = False
    disposition: Literal["eligible"] = "eligible"
    schema_version: str = OBSERVATION_SCHEMA
    policy_version: str = OBSERVATION_POLICY
    abstention_reason: None = None

    def __post_init__(self) -> None:
        _validate_preference(self.dimension, self.value, self.direction)
        if self.schema_version != OBSERVATION_SCHEMA or self.policy_version != OBSERVATION_POLICY:
            raise ValueError("unsupported Interaction Observation schema or policy")
        if self.disposition != "eligible" or self.abstention_reason is not None:
            raise ValueError("eligible Interaction Observation has invalid disposition")
        if self.context not in CONTEXTS or self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError("unsupported Interaction Observation classification")
        if self.context == "general" and self.evidence_class != "explicit-general":
            raise ValueError("general context requires explicit general applicability")
        if self.lasting and self.evidence_class != "explicit-general":
            raise ValueError("lasting preference requires explicit-general evidence")
        if self.replaces_prior and not self.lasting:
            raise ValueError("replacement requires lasting explicit evidence")
        if (
            not self.observation_id
            or not self.conversation_id
            or not self.feedback_turn_id
            or not self.preceding_request_turn_id
            or not self.evaluated_assistant_turn_ids
            or any(not item for item in self.evaluated_assistant_turn_ids)
        ):
            raise ValueError("Interaction Observation lacks source identities")
        _utc(self.occurred_at)

    def value_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "disposition": "eligible",
            "dimension": self.dimension,
            "value": self.value,
            "direction": self.direction,
            "context": self.context,
            "scope": self.scope.value(),
            "evidence_class": self.evidence_class,
            "source": {
                "conversation_id": self.conversation_id,
                "feedback_turn_id": self.feedback_turn_id,
                "evaluated_assistant_turn_ids": list(self.evaluated_assistant_turn_ids),
                "preceding_request_turn_id": self.preceding_request_turn_id,
                "occurred_at": self.occurred_at,
            },
            "policy_version": self.policy_version,
            "abstention_reason": None,
            "lasting": self.lasting,
            "replaces_prior": self.replaces_prior,
        }


@dataclass(frozen=True)
class ObservationAbstention:
    observation_id: str
    abstention_reason: str
    disposition: Literal["abstained"] = "abstained"
    schema_version: str = OBSERVATION_SCHEMA
    policy_version: str = OBSERVATION_POLICY

    def __post_init__(self) -> None:
        if (
            not self.observation_id
            or self.schema_version != OBSERVATION_SCHEMA
            or self.policy_version != OBSERVATION_POLICY
            or self.disposition != "abstained"
        ):
            raise ValueError("invalid Interaction Observation abstention")
        if self.abstention_reason not in ABSTENTION_REASONS:
            raise ValueError("unsupported observation abstention reason")

    def value_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "disposition": "abstained",
            "policy_version": self.policy_version,
            "abstention_reason": self.abstention_reason,
        }


def admit_observation(
    proposal: ObservationProposal, segments: tuple[SourceSegment, ...]
) -> InteractionObservation | ObservationAbstention:
    """Admit only complete same-conversation feedback context."""

    if not isinstance(proposal, ObservationProposal):
        raise ValueError("invalid interaction observation proposal")
    turns: dict[str, SourceSegment] = {}
    order: list[str] = []
    for segment in segments:
        if segment.turn_id not in turns:
            turns[segment.turn_id] = segment
            order.append(segment.turn_id)
    identity = _observation_id(proposal, turns.get(proposal.feedback_turn_id))
    preceding = turns.get(proposal.preceding_request_turn_id)
    feedback = turns.get(proposal.feedback_turn_id)
    evaluated = [turns.get(turn_id) for turn_id in proposal.evaluated_assistant_turn_ids]
    if preceding is None or preceding.source_role != "owner":
        return ObservationAbstention(identity, "missing-preceding-request")
    if any(item is None or item.source_role != "assistant" for item in evaluated):
        return ObservationAbstention(identity, "missing-evaluated-response")
    if feedback is None or feedback.source_role != "owner" or feedback.occurred_at is None:
        return ObservationAbstention(identity, "private-or-excluded")
    indexes = [order.index(proposal.preceding_request_turn_id)]
    indexes.extend(order.index(item.turn_id) for item in evaluated if item is not None)
    indexes.append(order.index(proposal.feedback_turn_id))
    if indexes != sorted(indexes) or len(set(indexes)) != len(indexes):
        return ObservationAbstention(identity, "ambiguous-target")
    conversation_ids = {
        preceding.conversation_id,
        feedback.conversation_id,
        *(item.conversation_id for item in evaluated if item is not None),
    }
    if len(conversation_ids) != 1:
        return ObservationAbstention(identity, "ambiguous-context")
    return InteractionObservation(
        observation_id=identity,
        dimension=proposal.dimension,
        context=proposal.context,
        scope=proposal.scope,
        evidence_class=proposal.evidence_class,
        conversation_id=feedback.conversation_id,
        feedback_turn_id=proposal.feedback_turn_id,
        evaluated_assistant_turn_ids=proposal.evaluated_assistant_turn_ids,
        preceding_request_turn_id=proposal.preceding_request_turn_id,
        occurred_at=_utc(feedback.occurred_at),
        value=proposal.value,
        direction=proposal.direction,
        lasting=proposal.lasting,
        replaces_prior=proposal.replaces_prior,
    )


def _observation_id(
    proposal: ObservationProposal, feedback: SourceSegment | None
) -> str:
    value = {
        "conversation_id": feedback.conversation_id if feedback else "missing",
        "feedback_turn_id": proposal.feedback_turn_id,
        "evaluated_assistant_turn_ids": list(proposal.evaluated_assistant_turn_ids),
        "dimension": proposal.dimension,
        "policy_version": OBSERVATION_POLICY,
    }
    digest = hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return f"obs_{digest}"


@dataclass(frozen=True)
class ProfileCandidate:
    value: str | None
    direction: str | None
    basis: str
    supporting_conversations: int | None
    last_evidence_at: str

    def value_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProfileEntry:
    entry_id: str
    dimension: str
    context: str
    status: Literal["active", "conflicting"]
    value: str | None = None
    direction: str | None = None
    basis: str | None = None
    supporting_conversations: int | None = None
    last_evidence_at: str | None = None
    expires_at: str | None = None
    candidates: tuple[ProfileCandidate, ...] = ()

    def __post_init__(self) -> None:
        if self.entry_id != f"{self.dimension}--{self.context}":
            raise ValueError("profile entry_id does not match dimension/context")
        if self.status == "active":
            _validate_preference(self.dimension, self.value, self.direction)
            if self.candidates:
                raise ValueError("active profile entry cannot contain candidates")
        elif self.status == "conflicting":
            if self.value is not None or self.direction is not None or len(self.candidates) < 2:
                raise ValueError("conflicting entry requires candidate outcomes only")
        else:
            raise ValueError("unsupported profile lifecycle state")

    def value_dict(self) -> dict[str, Any]:
        value = {
            "entry_id": self.entry_id,
            "dimension": self.dimension,
            "context": self.context,
            "status": self.status,
        }
        if self.status == "active":
            value.update(
                {
                    "value": self.value,
                    "direction": self.direction,
                    "basis": self.basis,
                    "supporting_conversations": self.supporting_conversations,
                    "last_evidence_at": self.last_evidence_at,
                    "expires_at": self.expires_at,
                }
            )
        else:
            value["candidates"] = [item.value_dict() for item in self.candidates]
        return value


@dataclass(frozen=True)
class AdaptiveProfile:
    scope: InteractionScope
    entries: tuple[ProfileEntry, ...]
    schema_version: str = PROFILE_SCHEMA
    authority: str = "noncanonical"
    policy_version: str = AGGREGATION_POLICY

    def __post_init__(self) -> None:
        if self.authority != "noncanonical" or self.schema_version != PROFILE_SCHEMA:
            raise ValueError("invalid Adaptive Interaction Profile authority or schema")
        if len({entry.entry_id for entry in self.entries}) != len(self.entries):
            raise ValueError("duplicate profile entry")

    def render(self) -> str:
        value = {
            "schema_version": self.schema_version,
            "authority": self.authority,
            "scope": self.scope.value(),
            "policy_version": self.policy_version,
            "entries": [entry.value_dict() for entry in self.entries],
        }
        return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)

    @classmethod
    def parse(cls, text: str) -> "AdaptiveProfile":
        value = yaml.safe_load(text)
        if not isinstance(value, dict) or value.get("schema_version") != PROFILE_SCHEMA:
            raise ValueError("invalid Adaptive Interaction Profile schema")
        if set(value) != {
            "schema_version", "authority", "scope", "policy_version", "entries"
        }:
            raise ValueError("invalid Adaptive Interaction Profile fields")
        scope = InteractionScope(**value["scope"])
        entries_value = value.get("entries")
        if not isinstance(entries_value, list):
            raise ValueError("invalid Adaptive Interaction Profile entries")
        entries: list[ProfileEntry] = []
        for item in entries_value:
            if not isinstance(item, dict):
                raise ValueError("invalid Adaptive Interaction Profile entry")
            candidates = tuple(
                ProfileCandidate(**candidate)
                for candidate in item.get("candidates", [])
            )
            entry_value = dict(item)
            entry_value.pop("candidates", None)
            entries.append(ProfileEntry(**entry_value, candidates=candidates))
        return cls(
            scope=scope,
            entries=tuple(entries),
            schema_version=value["schema_version"],
            authority=value["authority"],
            policy_version=value["policy_version"],
        )


def consolidate_profile(
    observations: Iterable[InteractionObservation],
    *,
    scope: InteractionScope,
    as_of: str,
) -> AdaptiveProfile:
    """Derive active/conflicting entries using 3 conversations and 180 days."""

    now = datetime.fromisoformat(_utc(as_of).replace("Z", "+00:00"))
    cutoff = now - timedelta(days=180)
    grouped: dict[tuple[str, str], list[InteractionObservation]] = {}
    seen_ids: set[str] = set()
    for observation in observations:
        if observation.observation_id in seen_ids:
            continue
        seen_ids.add(observation.observation_id)
        if observation.scope != scope:
            continue
        occurred = datetime.fromisoformat(observation.occurred_at.replace("Z", "+00:00"))
        if occurred > now:
            continue
        grouped.setdefault((observation.dimension, observation.context), []).append(observation)
    entries: list[ProfileEntry] = []
    for (dimension, context), values in sorted(grouped.items()):
        explicit = [item for item in values if item.evidence_class == "explicit-general" and item.lasting]
        if explicit:
            latest = max(explicit, key=lambda item: item.occurred_at)
            explicit_outcomes = {(item.value, item.direction) for item in explicit}
            if len(explicit_outcomes) == 1 or latest.replaces_prior:
                entries.append(
                    ProfileEntry(
                        f"{dimension}--{context}",
                        dimension,
                        context,
                        "active",
                        latest.value,
                        latest.direction,
                        "explicit",
                        None,
                        latest.occurred_at,
                        None,
                    )
                )
            else:
                entries.append(
                    ProfileEntry(
                        f"{dimension}--{context}",
                        dimension,
                        context,
                        "conflicting",
                        candidates=tuple(
                            ProfileCandidate(value, direction, "explicit", None, max(
                                item.occurred_at
                                for item in explicit
                                if (item.value, item.direction) == (value, direction)
                            ))
                            for value, direction in sorted(explicit_outcomes, key=str)
                        ),
                    )
                )
            continue
        recent = [
            item
            for item in values
            if datetime.fromisoformat(item.occurred_at.replace("Z", "+00:00")) >= cutoff
        ]
        outcomes: dict[tuple[str | None, str | None], dict[str, InteractionObservation]] = {}
        for item in recent:
            outcomes.setdefault((item.value, item.direction), {})[item.conversation_id] = item
        qualified: list[ProfileCandidate] = []
        for (value, direction), by_conversation in sorted(
            outcomes.items(), key=lambda item: str(item[0])
        ):
            if len(by_conversation) < 3:
                continue
            latest = max(by_conversation.values(), key=lambda item: item.occurred_at)
            qualified.append(
                ProfileCandidate(
                    value,
                    direction,
                    "repeated-correction",
                    len(by_conversation),
                    latest.occurred_at,
                )
            )
        if len(qualified) == 1:
            item = qualified[0]
            expires = (
                datetime.fromisoformat(item.last_evidence_at.replace("Z", "+00:00"))
                + timedelta(days=180)
            ).isoformat().replace("+00:00", "Z")
            entries.append(
                ProfileEntry(
                    f"{dimension}--{context}",
                    dimension,
                    context,
                    "active",
                    item.value,
                    item.direction,
                    item.basis,
                    item.supporting_conversations,
                    item.last_evidence_at,
                    expires,
                )
            )
        elif len(qualified) > 1:
            entries.append(
                ProfileEntry(
                    f"{dimension}--{context}",
                    dimension,
                    context,
                    "conflicting",
                    candidates=tuple(qualified),
                )
            )
    return AdaptiveProfile(scope, tuple(entries))


def scan_observations(vault_root: Path) -> tuple[InteractionObservation, ...]:
    """Rebuild observation evidence from immutable Run Manifests."""

    root = vault_root / "System" / "Orca Memory" / "manifests"
    observations: dict[str, InteractionObservation] = {}
    if not root.exists():
        return ()
    for path in sorted(root.glob("**/*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        for operation in manifest.get("operations", []):
            if operation.get("operation") != "observation":
                continue
            observation = parse_observation(operation.get("embedded_artifact"))
            if operation.get("artifact_id") != observation.observation_id:
                raise ValueError("Manifest observation identity mismatch")
            prior = observations.get(observation.observation_id)
            if prior is not None and prior != observation:
                raise ValueError("conflicting duplicate Interaction Observation")
            observations[observation.observation_id] = observation
    return tuple(observations[key] for key in sorted(observations))


def profile_relative_path(
    scope: InteractionScope, *, project_alias: str | None = None
) -> Path:
    """Return the deterministic locator for a noncanonical profile view."""

    root = Path("System/Orca Memory/interaction/profiles")
    if scope.type == "global":
        return root / "global.yaml"
    if scope.type == "agent":
        return root / "agents" / f"{_identity_slug(scope.agent_id or '')}.yaml"
    if project_alias is None:
        raise ValueError("project profile path requires an unambiguous project alias")
    project_locator = (
        f"{project_alias_slug(project_alias)}--"
        f"{hashlib.sha256((scope.project_id or '').encode()).hexdigest()[:12]}"
    )
    if scope.type == "project":
        return root / "projects" / f"{project_locator}.yaml"
    return root / "project-agents" / (
        f"{project_locator}--{_identity_slug(scope.agent_id or '')}.yaml"
    )


def rebuild_profiles(
    vault_root: Path,
    *,
    as_of: str,
    project_aliases: dict[str, str] | None = None,
) -> tuple[Path, ...]:
    """Rebuild living profile views solely from immutable Manifest evidence."""

    observations = scan_observations(vault_root)
    aliases = project_aliases or {}
    scopes = sorted(
        {item.scope for item in observations},
        key=lambda scope: (
            _SCOPE_PRECEDENCE[scope.type], scope.project_id or "", scope.agent_id or ""
        ),
    )
    written: list[Path] = []
    for scope in scopes:
        alias = aliases.get(scope.project_id or "")
        if scope.type in {"project", "project-agent"} and alias is None:
            continue
        profile = consolidate_profile(observations, scope=scope, as_of=as_of)
        path = vault_root / profile_relative_path(scope, project_alias=alias)
        _atomic_replace(path, profile.render().encode("utf-8"))
        written.append(path)
    return tuple(written)


def load_applicable_profiles(
    vault_root: Path,
    *,
    agent_id: str,
    project_id: str | None = None,
    project_alias: str | None = None,
) -> tuple[AdaptiveProfile, ...]:
    """Load only exact, unambiguous profile identities for one agent context."""

    scopes = [InteractionScope("global"), InteractionScope("agent", agent_id=agent_id)]
    if project_id is not None and project_alias is not None:
        scopes.extend(
            (
                InteractionScope("project", project_id=project_id),
                InteractionScope("project-agent", agent_id=agent_id, project_id=project_id),
            )
        )
    profiles: list[AdaptiveProfile] = []
    for scope in scopes:
        alias = project_alias if scope.type in {"project", "project-agent"} else None
        path = vault_root / profile_relative_path(scope, project_alias=alias)
        if not path.is_file():
            continue
        profile = AdaptiveProfile.parse(path.read_text(encoding="utf-8"))
        if profile.scope != scope:
            raise ValueError(f"Adaptive Interaction Profile identity mismatch: {path}")
        profiles.append(profile)
    return tuple(profiles)


def select_guidance(
    vault_root: Path,
    *,
    context: str,
    agent_id: str,
    project_id: str | None = None,
    project_alias: str | None = None,
    owner_instruction_keys: frozenset[tuple[str, str]] = frozenset(),
    session_adjustment_keys: frozenset[tuple[str, str]] = frozenset(),
    token_budget: int = 500,
) -> str:
    """Use the same deterministic profile selector at every context boundary."""

    return compile_guidance(
        load_applicable_profiles(
            vault_root,
            agent_id=agent_id,
            project_id=project_id,
            project_alias=project_alias,
        ),
        context=context,
        agent_id=agent_id,
        project_id=project_id,
        overridden_keys=owner_instruction_keys | session_adjustment_keys,
        token_budget=token_budget,
    )


def parse_observation(value: Any) -> InteractionObservation:
    if not isinstance(value, dict) or value.get("schema_version") != OBSERVATION_SCHEMA:
        raise ValueError("invalid Interaction Observation schema")
    if value.get("disposition") != "eligible" or value.get("abstention_reason") is not None:
        raise ValueError("Manifest may embed only eligible observations")
    scope = InteractionScope(**value["scope"])
    source = value.get("source")
    if not isinstance(source, dict):
        raise ValueError("Interaction Observation lacks source identities")
    return InteractionObservation(
        observation_id=value["observation_id"],
        dimension=value["dimension"],
        value=value.get("value"),
        direction=value.get("direction"),
        context=value["context"],
        scope=scope,
        evidence_class=value["evidence_class"],
        conversation_id=source["conversation_id"],
        feedback_turn_id=source["feedback_turn_id"],
        evaluated_assistant_turn_ids=tuple(source["evaluated_assistant_turn_ids"]),
        preceding_request_turn_id=source["preceding_request_turn_id"],
        occurred_at=source["occurred_at"],
        lasting=value.get("lasting", False),
        replaces_prior=value.get("replaces_prior", False),
        policy_version=value["policy_version"],
    )


def parse_observation_abstention(value: Any) -> ObservationAbstention:
    if not isinstance(value, dict) or value.get("schema_version") != OBSERVATION_SCHEMA:
        raise ValueError("invalid Interaction Observation abstention schema")
    if value.get("disposition") != "abstained":
        raise ValueError("invalid Interaction Observation abstention disposition")
    if set(value) != {
        "schema_version",
        "observation_id",
        "disposition",
        "policy_version",
        "abstention_reason",
    }:
        raise ValueError("Interaction Observation abstention must be content-free")
    if value.get("policy_version") != OBSERVATION_POLICY:
        raise ValueError("unsupported Interaction Observation abstention policy")
    return ObservationAbstention(
        observation_id=value["observation_id"],
        abstention_reason=value["abstention_reason"],
        policy_version=value["policy_version"],
    )


def owner_resolved_entry(
    *,
    dimension: str,
    context: str,
    value: str | None = None,
    direction: str | None = None,
    basis: Literal["owner-resolution", "owner-clarification"] = "owner-resolution",
    resolved_at: str,
) -> ProfileEntry:
    """Build one explicit non-expiring entry from an Owner resolution."""

    _validate_preference(dimension, value, direction)
    if context not in CONTEXTS or basis not in {"owner-resolution", "owner-clarification"}:
        raise ValueError("invalid Owner-resolved interaction entry")
    return ProfileEntry(
        f"{dimension}--{context}",
        dimension,
        context,
        "active",
        value,
        direction,
        basis,
        None,
        _utc(resolved_at),
        None,
    )


CONTEXT_PREFIXES = {
    "general": "Generally, ",
    "status-update": "For status updates, ",
    "explanation": "For explanations, ",
    "design-discussion": "For design discussions, ",
    "implementation": "During implementation work, ",
    "review": "For reviews, ",
}
GUIDANCE = {
    "detail": {
        "concise": "keep the response concise and omit nonessential background.",
        "balanced": "provide enough detail to support the answer without unnecessary expansion.",
        "detailed": "provide thorough context, rationale, and supporting detail.",
        "decrease": "reduce unnecessary detail and prioritize the information needed to proceed.",
        "increase": "provide more context, rationale, and supporting detail.",
    },
    "structure": {
        "minimal": "use minimal formatting and only necessary headings.",
        "moderate": "use short sections or lists when they materially improve clarity.",
        "highly-structured": "organize the response into clear sections and actionable lists.",
        "decrease": "reduce headings, lists, and structural overhead.",
        "increase": "add clearer organization and section boundaries.",
    },
    "question-frequency": {
        "blocking-only": "ask questions only when proceeding would create meaningful risk.",
        "selective": "ask when the answer would materially change the outcome.",
        "proactive": "surface important ambiguities and alternatives before proceeding.",
        "decrease": "ask fewer questions and make reasonable low-risk assumptions.",
        "increase": "check important assumptions more explicitly before proceeding.",
    },
    "technical-depth": {
        "plain-language": "explain technical concepts in accessible language and define necessary terms.",
        "mixed": "use technical detail where useful and explain unfamiliar terms.",
        "expert": "use precise technical language without explaining standard concepts.",
        "decrease": "reduce specialist detail and explain concepts more plainly.",
        "increase": "include more technical mechanisms and implementation detail.",
    },
    "tone": {
        "formal": "use a professional and formal tone.",
        "neutral": "use a direct, neutral, and professional tone.",
        "conversational": "use a natural and conversational tone while remaining precise.",
        "more-formal": "use a more formal and restrained tone.",
        "more-conversational": "use a warmer and more conversational tone.",
    },
    "progress-updates": {
        "milestones-only": "report only meaningful milestones, blockers, and completion.",
        "periodic": "provide concise updates at useful intervals during ongoing work.",
        "frequent": "provide regular progress updates during ongoing work.",
        "decrease": "reduce routine progress narration and report only material changes.",
        "increase": "provide more frequent visibility into progress, blockers, and next steps.",
    },
}
_SCOPE_PRECEDENCE = {"global": 0, "agent": 1, "project": 2, "project-agent": 3}


def compile_guidance(
    profiles: Iterable[AdaptiveProfile],
    *,
    context: str,
    agent_id: str,
    project_id: str | None = None,
    overridden_keys: frozenset[tuple[str, str]] = frozenset(),
    token_budget: int = 500,
) -> str:
    """Compile fixed complete sentences at deterministic scope precedence."""

    if context not in CONTEXTS or token_budget < 0:
        raise ValueError("invalid guidance context or budget")
    selected: dict[tuple[str, str], tuple[int, ProfileEntry]] = {}
    for profile in profiles:
        scope = profile.scope
        applies = (
            scope.type == "global"
            or scope.type == "agent" and scope.agent_id == agent_id
            or scope.type == "project" and project_id is not None and scope.project_id == project_id
            or scope.type == "project-agent"
            and project_id is not None
            and scope.project_id == project_id
            and scope.agent_id == agent_id
        )
        if not applies:
            continue
        precedence = _SCOPE_PRECEDENCE[scope.type]
        for entry in profile.entries:
            key = (entry.context, entry.dimension)
            if (
                entry.status != "active"
                or entry.context not in {"general", context}
                or key in overridden_keys
            ):
                continue
            if key not in selected or precedence > selected[key][0]:
                selected[key] = (precedence, entry)
    candidates: list[tuple[int, int, str]] = []
    for (_, _), (precedence, entry) in selected.items():
        choice = entry.value or entry.direction
        clause = GUIDANCE.get(entry.dimension, {}).get(choice or "")
        prefix = CONTEXT_PREFIXES.get(entry.context)
        if clause is None or prefix is None:
            continue
        candidates.append(
            (
                1 if entry.context == context else 0,
                precedence,
                prefix + clause,
            )
        )
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    sentences: list[str] = []
    used = 0
    for _, _, sentence in candidates:
        if sentence in sentences:
            continue
        size = estimate_tokens(sentence)
        if used + size > token_budget:
            continue
        sentences.append(sentence)
        used += size
    return "\n".join(sentences)


def _validate_preference(
    dimension: str, value: str | None, direction: str | None
) -> None:
    if dimension not in DIMENSIONS:
        raise ValueError("unsupported interaction dimension")
    if (value is None) == (direction is None):
        raise ValueError("exactly one interaction value or direction is required")
    if value is not None and value not in VALUES[dimension]:
        raise ValueError("unsupported interaction value")
    if direction is not None and direction not in DIRECTIONS[dimension]:
        raise ValueError("unsupported interaction direction")


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("interaction timestamp must be UTC RFC 3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("interaction timestamp must use UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _identity_slug(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9._-]{0,63})", value):
        raise ValueError("interaction adapter identity is not path-safe")
    return value


def _atomic_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


__all__ = [
    "ABSTENTION_REASONS",
    "AGGREGATION_POLICY",
    "AdaptiveProfile",
    "CONTEXTS",
    "DIMENSIONS",
    "EVIDENCE_CLASSES",
    "GUIDANCE_POLICY",
    "InteractionObservation",
    "InteractionScope",
    "ObservationAbstention",
    "ObservationProposal",
    "OBSERVATION_POLICY",
    "OBSERVATION_SCHEMA",
    "ProfileEntry",
    "admit_observation",
    "compile_guidance",
    "consolidate_profile",
    "load_applicable_profiles",
    "owner_resolved_entry",
    "parse_observation",
    "parse_observation_abstention",
    "profile_relative_path",
    "rebuild_profiles",
    "scan_observations",
    "select_guidance",
]
