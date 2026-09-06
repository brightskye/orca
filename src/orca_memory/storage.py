"""Place validated Step 3 artifacts and publish operational receipts safely."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable, Literal
import unicodedata
import uuid

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.candidates import (
    KnowledgeCandidate,
    candidate_placement,
    materialize_candidate,
    support_candidate,
)
from orca_memory.conflicts import (
    ConflictRecord,
    apply_conflict,
    parse_conflict_record,
    start_conflict,
    supersede,
)
from orca_memory.memory import (
    MemoryRecord,
    ProjectSummary,
    apply_update,
    materialize_record,
    parse_record,
    record_relative_path,
    render_project_summary,
    render_record,
    validate_operation,
)
from orca_memory.interaction import parse_observation, rebuild_profiles
from orca_memory.privacy import contains_secret
from orca_memory.processor import (
    ContinuationSummary,
    ProcessedConversation,
    source_segment_ref,
)
from orca_memory.provenance import (
    CHECKPOINT_SCHEMA,
    MANIFEST_SCHEMA,
    checkpoint_payload,
    is_exact_replay,
    is_exact_segment_replay,
    processed_sources,
    processed_segment_receipts,
    segment_key,
    segmented_source,
    unsegmented_source,
    validate_manifest,
)
from orca_memory.publication import PlannedOutput, PublicationPlan, RecoverablePublisher
from orca_memory.segmentation import SourceSegment, segment_turn_with_budget


CONTINUATION_SCHEMA = "orca-conversation-continuation/1"
_GENERIC_SLUGS = {"memory", "record", "note", "item", "misc", "untitled"}


@dataclass(frozen=True)
class MemoryScope:
    """Governance-resolved location for one processing run."""

    kind: Literal["project", "general", "unassigned"]
    scope_id: str
    project_alias: str | None = None

    def __post_init__(self) -> None:
        if self.kind == "project":
            if not self.scope_id.strip() or not self.project_alias or not self.project_alias.strip():
                raise ValueError("project scope requires project_id and project_alias")
        elif self.kind in {"general", "unassigned"}:
            if self.scope_id != self.kind or self.project_alias is not None:
                raise ValueError(f"{self.kind} scope must use its fixed identity")
        else:
            raise ValueError(f"unsupported memory scope: {self.kind}")


@dataclass(frozen=True)
class PublicationResult:
    """Observable result of one Step 3 pipeline run."""

    status: Literal["success", "no_memory", "replay"]
    manifest_path: Path | None
    output_paths: tuple[Path, ...]
    processed_through_turn: str


class Storage:
    """Own artifact placement, manifest deduplication, and checkpoint ordering."""

    def __init__(
        self,
        vault_root: Path,
        runtime_root: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        publication_fault: Callable[[str], None] | None = None,
    ) -> None:
        self.vault_root = vault_root
        self.runtime_root = runtime_root
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)
        self._publisher = RecoverablePublisher(vault_root, runtime_root)
        self._publication_fault = publication_fault

    def select_unprocessed(self, conversation: ConversationBatch) -> ConversationBatch:
        """Return unknown turns; reject a known identity with revised content."""

        processed = processed_sources(self.vault_root)
        new_turns: list[NormalizedTurn] = []
        for turn in conversation.turns:
            key = (turn.connector_id, turn.conversation_id, turn.turn_id)
            known = processed.get(key)
            if known is None:
                new_turns.append(turn)
            elif is_exact_replay(turn, known):
                continue
            elif known.representation[1] != turn.redaction_policy:
                raise ValueError(
                    "redaction policy revision requires governed reprocessing for "
                    f"{turn.conversation_id}/{turn.turn_id}"
                )
            else:
                raise ValueError(
                    "source or segmentation conflict for known turn "
                    f"{turn.conversation_id}/{turn.turn_id}"
                )
        return ConversationBatch(
            conversation.connector_id,
            conversation.conversation_id,
            tuple(new_turns),
            conversation.processed_through,
            conversation.has_partial_tail,
        )

    def select_unprocessed_segments(
        self, segments: tuple[SourceSegment, ...]
    ) -> tuple[SourceSegment, ...]:
        """Return unprocessed segments and fail closed on representation drift."""

        processed, legacy = processed_segment_receipts(self.vault_root)
        selected: list[SourceSegment] = []
        for segment in segments:
            source = segmented_source(segment, source_ref="src-check")
            key = segment_key(segment.connector_id, segment.conversation_id, source)
            known = processed.get(key)
            turn_key = key[:3]
            legacy_receipt = legacy.get(turn_key)
            same_turn = [
                receipt
                for receipt_key, receipt in processed.items()
                if receipt_key[:3] == turn_key
            ]
            if known is not None:
                if is_exact_segment_replay(segment, known):
                    continue
                raise ValueError(
                    f"source or segmentation conflict for known segment {segment.turn_id}/{segment.index}"
                )
            if legacy_receipt is not None:
                if (
                    segment.count == 1
                    and legacy_receipt.representation[:2]
                    == (segment.turn_content_sha256, segment.redaction_policy)
                ):
                    continue
                raise ValueError(
                    f"governed reprocessing required for legacy turn {segment.turn_id}"
                )
            if same_turn:
                first = same_turn[0].source
                first_segment = first["segment"]
                if (
                    first["turn_content_sha256"] != segment.turn_content_sha256
                    or first["redaction_policy"] != segment.redaction_policy
                    or first_segment["policy_version"] != segment.policy_version
                    or first_segment["parameters_sha256"] != segment.parameters_sha256
                    or first_segment["count"] != segment.count
                ):
                    raise ValueError(
                        f"source or segmentation conflict for turn {segment.turn_id}"
                    )
            selected.append(segment)
        return tuple(selected)

    def recover_pending_publications(self) -> tuple[Path, ...]:
        """Complete every valid fixed publication intent without a provider call."""

        return tuple(
            self._publisher.recover(intent)
            for intent in self._publisher.pending_intents()
        )

    def load_continuation(
        self, conversation_id: str, *, scope: MemoryScope
    ) -> str | None:
        """Load the one existing continuation by Conversation Identity."""

        suffix = _short_id(conversation_id)
        base = self.vault_root / "System" / "Orca Memory" / "shallow"
        if scope.kind == "project":
            base = base / "projects" / _slug(scope.project_alias or "")
        else:
            base = base / scope.kind
        directory = base / "conversation-summaries"
        matches = [] if not directory.exists() else list(
            directory.glob(f"*--{suffix}.md")
        )
        exact = [
            path
            for path in matches
            if f"conversation_id: {json.dumps(conversation_id)}" in path.read_text(encoding="utf-8")
        ]
        if len(exact) > 1:
            raise ValueError(f"multiple continuations for conversation {conversation_id}")
        return exact[0].read_text(encoding="utf-8") if exact else None

    def load_project_summary(self, scope: MemoryScope) -> str | None:
        """Load the bounded current Project Summary only for project scope."""

        if scope.kind != "project":
            return None
        path = (
            self.vault_root
            / "System"
            / "Orca Memory"
            / "shallow"
            / "projects"
            / _slug(scope.project_alias or "")
            / "summary.md"
        )
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def load_related_records(self, scope: MemoryScope) -> tuple[MemoryRecord | ConflictRecord, ...]:
        """Load current same-scope records for the next bounded provider call."""

        records = self._memory_records()
        return tuple(
            sorted(
                (
                    record
                    for record in records.values()
                    if record.scope == scope.kind
                    and record.scope_id == scope.scope_id
                    and record.status == "current"
                ),
                key=lambda record: record.memory_id,
            )
        )

    def load_related_candidates(self, scope: MemoryScope) -> tuple[KnowledgeCandidate, ...]:
        """Load pending same-scope candidates for exact support targeting."""

        candidates = self._knowledge_candidates()
        return tuple(
            sorted(
                (
                    candidate
                    for candidate in candidates.values()
                    if candidate.scope == scope.kind
                    and candidate.scope_id == scope.scope_id
                    and candidate.status == "pending"
                ),
                key=lambda candidate: candidate.candidate_id,
            )
        )

    def publish(
        self,
        processed: ProcessedConversation,
        *,
        scope: MemoryScope,
    ) -> PublicationResult:
        """Publish outputs, then immutable manifest, then local checkpoint."""

        now = self._clock().astimezone(timezone.utc)
        timestamp = now.isoformat().replace("+00:00", "Z")
        run_id = f"run_{self._id_factory()}"
        sources = [
            segmented_source(segment, source_ref=f"src-{index:03d}")
            for index, segment in enumerate(processed.source_segments, start=1)
        ]
        segment_refs = [source_segment_ref(segment) for segment in processed.source_segments]
        if len(set(segment_refs)) != len(segment_refs):
            raise ValueError("Manifest source segment locators are not unique")
        source_refs_by_segment = {
            segment_ref: source["source_ref"]
            for segment_ref, source in zip(segment_refs, sources)
        }
        source_by_ref = {
            source["source_ref"]: source for source in sources
        }

        def exact_source_refs(refs: tuple[str, ...], label: str) -> list[str]:
            if not refs:
                raise ValueError(f"{label} must cite at least one source segment")
            try:
                mapped = [source_refs_by_segment[ref] for ref in refs]
            except KeyError as exc:
                raise ValueError(f"{label} cites a missing source segment") from exc
            if any(source_by_ref[ref].get("source_role") != "owner" for ref in mapped):
                raise ValueError(f"{label} must cite Owner source segments")
            return mapped
        owner_source_refs = [
            source["source_ref"]
            for source in sources
            if source.get("source_role") == "owner"
        ]
        if not owner_source_refs:
            raise ValueError("publication requires Owner evidence sources")
        operations: list[dict[str, object]] = []
        outputs: list[dict[str, object]] = []
        planned_outputs: list[PlannedOutput] = []
        output_paths: list[Path] = []

        def plan_output(
            *,
            artifact_kind: str,
            artifact_id: str,
            path: Path,
            payload: bytes | None,
            before_sha256: str | None,
        ) -> str | None:
            after_sha256 = (
                hashlib.sha256(payload).hexdigest() if payload is not None else None
            )
            if before_sha256 == after_sha256:
                return None
            output_ref = f"out-{len(outputs) + 1:03d}"
            effect = (
                "deleted"
                if payload is None
                else "created"
                if before_sha256 is None
                else "replaced"
            )
            output = {
                "output_ref": output_ref,
                "artifact_kind": artifact_kind,
                "artifact_id": artifact_id,
                "effect": effect,
                "path": path.relative_to(self.vault_root).as_posix(),
                "before_sha256": before_sha256,
                "after_sha256": after_sha256,
            }
            outputs.append(output)
            planned_outputs.append(PlannedOutput(payload=payload, **output))
            output_paths.append(path)
            return output_ref

        existing_records = self._memory_records()
        changed_record_ids: list[str] = []
        for proposal_index, proposal in enumerate(
            processed.record_proposals, start=1
        ):
            operation_id = f"op-{len(operations) + 1:03d}"
            target = (
                existing_records.get(proposal.target_memory_id)
                if proposal.target_memory_id is not None
                else None
            )
            if proposal.operation == "add":
                validate_operation("add", existing=None, proposal=proposal)
                memory_id = self._allocate_memory_id(existing_records)
                post_image = materialize_record(
                    proposal,
                    memory_id=memory_id,
                    created_at=timestamp,
                )
                outcome = "created"
            elif proposal.operation == "support":
                validate_operation("support", existing=target, proposal=proposal)
                assert target is not None
                memory_id = target.memory_id
                post_image = target
                outcome = "supported"
            elif proposal.operation == "update":
                validate_operation("update", existing=target, proposal=proposal)
                assert target is not None
                memory_id = target.memory_id
                unchanged = apply_update(
                    target, proposal, updated_at=target.updated_at
                )
                if unchanged == target:
                    post_image = target
                    outcome = "no-change"
                else:
                    post_image = apply_update(target, proposal, updated_at=timestamp)
                    outcome = "updated"
            else:
                raise ValueError(f"unsupported Milestone 2 operation: {proposal.operation}")

            output_refs: list[str] = []
            if outcome not in {"supported", "no-change"}:
                new_relative = record_relative_path(
                    post_image,
                    scope.project_alias if scope.kind == "project" else None,
                    existing_ids=tuple(existing_records),
                )
                new_path = self.vault_root / new_relative
                payload = render_record(post_image).encode("utf-8")
                if contains_secret(payload.decode("utf-8")):
                    raise ValueError("Typed Memory output contains a credential-like value")
                if target is not None:
                    old_relative = record_relative_path(
                        target,
                        scope.project_alias if scope.kind == "project" else None,
                        existing_ids=tuple(existing_records),
                    )
                    old_path = self.vault_root / old_relative
                else:
                    old_path = new_path
                if old_path != new_path:
                    deleted_ref = plan_output(
                        artifact_kind="typed-memory-record",
                        artifact_id=memory_id,
                        path=old_path,
                        payload=None,
                        before_sha256=_hash_path(old_path),
                    )
                    if deleted_ref is not None:
                        output_refs.append(deleted_ref)
                    created_ref = plan_output(
                        artifact_kind="typed-memory-record",
                        artifact_id=memory_id,
                        path=new_path,
                        payload=payload,
                        before_sha256=_hash_path(new_path),
                    )
                    if created_ref is not None:
                        output_refs.append(created_ref)
                else:
                    output_ref = plan_output(
                        artifact_kind="typed-memory-record",
                        artifact_id=memory_id,
                        path=new_path,
                        payload=payload,
                        before_sha256=_hash_path(new_path),
                    )
                    if output_ref is not None:
                        output_refs.append(output_ref)
                changed_record_ids.append(memory_id)
                existing_records[memory_id] = post_image
            operations.append(
                {
                    "operation_id": operation_id,
                    "operation": proposal.operation,
                    "outcome": outcome,
                    "artifact_kind": "typed-memory-record",
                    "artifact_id": memory_id,
                    "source_refs": exact_source_refs(
                        proposal.source_segment_refs, "record proposal"
                    ),
                    "output_refs": output_refs,
                    "embedded_artifact": None,
                }
            )

        for replacement in processed.supersede_proposals:
            target = existing_records.get(replacement.target_memory_id)
            if not isinstance(target, MemoryRecord):
                raise ValueError("supersede requires one current Typed Memory Record")
            post_image = supersede(target, replacement, updated_at=timestamp)
            relative = record_relative_path(
                post_image,
                scope.project_alias if scope.kind == "project" else None,
                existing_ids=tuple(existing_records),
            )
            path = self.vault_root / relative
            output_ref = plan_output(
                artifact_kind="typed-memory-record",
                artifact_id=post_image.memory_id,
                path=path,
                payload=render_record(post_image).encode("utf-8"),
                before_sha256=_hash_path(path),
            )
            changed_record_ids.append(post_image.memory_id)
            existing_records[post_image.memory_id] = post_image
            operations.append(
                {
                    "operation_id": f"op-{len(operations) + 1:03d}",
                    "operation": "supersede",
                    "outcome": "updated",
                    "artifact_kind": "typed-memory-record",
                    "artifact_id": post_image.memory_id,
                    "source_refs": exact_source_refs(
                        replacement.source_segment_refs, "supersede proposal"
                    ),
                    "output_refs": [output_ref] if output_ref else [],
                    "embedded_artifact": None,
                }
            )

        for conflict in processed.conflict_proposals:
            target = existing_records.get(conflict.target_memory_id)
            if (
                isinstance(target, ConflictRecord)
                and conflict.target_variant_id is not None
                and conflict.target_variant_id
                not in {variant.variant_id for variant in target.variants}
            ):
                overflow_id = self._validate_overflow_support(conflict)
                operations.append(
                    {
                        "operation_id": f"op-{len(operations) + 1:03d}",
                        "operation": "support",
                        "outcome": "supported",
                        "artifact_kind": "conflict-overflow-candidate",
                        "artifact_id": overflow_id,
                        "source_refs": exact_source_refs(
                            conflict.source_segment_refs, "conflict proposal"
                        ),
                        "output_refs": [],
                        "embedded_artifact": None,
                    }
                )
                continue
            if isinstance(target, MemoryRecord):
                post_image = start_conflict(target, conflict, updated_at=timestamp)
                overflow = None
                outcome = "conflict-recorded"
            elif isinstance(target, ConflictRecord):
                post_image, overflow, outcome = apply_conflict(
                    target,
                    conflict,
                    updated_at=timestamp,
                    next_variant_number=self._next_overflow_variant(target.memory_id),
                )
            else:
                raise ValueError("conflict requires an existing target record")
            output_refs: list[str] = []
            if post_image is not target:
                relative = record_relative_path(
                    post_image,  # type: ignore[arg-type]
                    scope.project_alias if scope.kind == "project" else None,
                    existing_ids=tuple(existing_records),
                )
                path = self.vault_root / relative
                output_ref = plan_output(
                    artifact_kind="typed-memory-record",
                    artifact_id=post_image.memory_id,
                    path=path,
                    payload=post_image.render().encode("utf-8"),
                    before_sha256=_hash_path(path),
                )
                if output_ref:
                    output_refs.append(output_ref)
                changed_record_ids.append(post_image.memory_id)
                existing_records[post_image.memory_id] = post_image
            operations.append(
                {
                    "operation_id": f"op-{len(operations) + 1:03d}",
                    "operation": "conflict" if outcome != "supported" else "support",
                    "outcome": outcome,
                    "artifact_kind": "typed-memory-record",
                    "artifact_id": post_image.memory_id,
                    "source_refs": exact_source_refs(
                        conflict.source_segment_refs, "conflict proposal"
                    ),
                    "output_refs": output_refs,
                    "embedded_artifact": None,
                }
            )
            if overflow is not None:
                overflow_path = self.vault_root / overflow.relative_path(
                    scope.project_alias if scope.kind == "project" else None
                )
                overflow_id = f"{overflow.memory_id}:{overflow.variant_id}"
                overflow_ref = plan_output(
                    artifact_kind="conflict-overflow-candidate",
                    artifact_id=overflow_id,
                    path=overflow_path,
                    payload=overflow.render().encode("utf-8"),
                    before_sha256=_hash_path(overflow_path),
                )
                operations.append(
                    {
                        "operation_id": f"op-{len(operations) + 1:03d}",
                        "operation": "conflict",
                        "outcome": "conflict-recorded",
                        "artifact_kind": "conflict-overflow-candidate",
                        "artifact_id": overflow_id,
                        "source_refs": exact_source_refs(
                            conflict.source_segment_refs, "conflict proposal"
                        ),
                        "output_refs": [overflow_ref] if overflow_ref else [],
                        "embedded_artifact": None,
                    }
                )

        existing_candidates = self._knowledge_candidates()
        for instruction in processed.candidate_operations:
            if instruction.operation == "create":
                candidate_id = self._allocate_candidate_id(existing_candidates)
                candidate = materialize_candidate(
                    instruction.proposal,
                    candidate_id=candidate_id,
                    created_at=timestamp,
                )
                placement = candidate_placement(
                    self.vault_root,
                    candidate,
                    project_alias=scope.project_alias if scope.kind == "project" else None,
                )
                output_ref = plan_output(
                    artifact_kind="knowledge-candidate",
                    artifact_id=candidate_id,
                    path=placement.path,
                    payload=candidate.render().encode("utf-8"),
                    before_sha256=_hash_path(placement.path),
                )
                existing_candidates[candidate_id] = candidate
                outcome = "created"
                output_refs = [output_ref] if output_ref else []
            else:
                candidate_id = instruction.target_candidate_id or ""
                candidate = existing_candidates.get(candidate_id)
                if candidate is None:
                    raise ValueError("candidate support target does not exist")
                support_candidate(candidate, instruction.proposal, candidate_id=candidate_id)
                outcome = "no-change"
                output_refs = []
            operations.append(
                {
                    "operation_id": f"op-{len(operations) + 1:03d}",
                    "operation": "candidate",
                    "outcome": outcome,
                    "artifact_kind": "knowledge-candidate",
                    "artifact_id": candidate_id,
                    "source_refs": exact_source_refs(
                        instruction.source_segment_refs, "candidate instruction"
                    ),
                    "output_refs": output_refs,
                    "embedded_artifact": None,
                }
            )

        project_summary_output: tuple[Path, bytes] | None = None
        if changed_record_ids:
            if scope.kind == "project":
                if processed.project_summary is None:
                    raise ValueError(
                        "material project-memory change requires a Project Summary refresh"
                    )
                project_summary_output = self._prepare_project_summary(
                    _include_changed_memory_ids(
                        processed.project_summary, changed_record_ids
                    ),
                    scope=scope,
                    records=existing_records,
                    required_memory_ids=tuple(changed_record_ids),
                )
            elif processed.project_summary is not None:
                raise ValueError("Project Summary is not allowed outside project scope")
        elif processed.project_summary is not None and scope.kind != "project":
            raise ValueError("Project Summary is not allowed outside project scope")
        # Support-only and no-change runs keep the existing Project Summary.
        # A redundant proposal must not block independent continuation capture.

        if processed.continuation is not None:
            path = self._continuation_path(
                scope,
                processed.conversation.conversation_id,
                processed.continuation,
            )
            payload = _render_continuation(
                processed.conversation.conversation_id,
                scope.scope_id if scope.kind == "project" else None,
                processed.continuation,
            ).encode("utf-8")
            if contains_secret(payload.decode("utf-8")):
                raise ValueError("proposed output contains a credential-like value")
            before_hash = _hash_path(path)
            after_hash = hashlib.sha256(payload).hexdigest()
            output_refs: list[str] = []
            output_ref = plan_output(
                artifact_kind="conversation-continuation-summary",
                artifact_id=processed.conversation.conversation_id,
                path=path,
                payload=payload,
                before_sha256=before_hash,
            )
            if output_ref is not None:
                output_refs.append(output_ref)
            operations.append(
                {
                    "operation_id": f"op-{len(operations) + 1:03d}",
                    "operation": "summary-refresh",
                    "outcome": (
                        "created"
                        if before_hash is None
                        else "no-change"
                        if before_hash == after_hash
                        else "updated"
                    ),
                    "artifact_kind": "conversation-continuation-summary",
                    "artifact_id": processed.conversation.conversation_id,
                    "source_refs": owner_source_refs,
                    "output_refs": output_refs,
                    "embedded_artifact": None,
                }
            )

        if project_summary_output is not None:
            summary_path, summary_payload = project_summary_output
            before_hash = _hash_path(summary_path)
            output_refs: list[str] = []
            output_ref = plan_output(
                artifact_kind="project-summary",
                artifact_id=scope.scope_id,
                path=summary_path,
                payload=summary_payload,
                before_sha256=before_hash,
            )
            if output_ref is not None:
                output_refs.append(output_ref)
            operations.append(
                {
                    "operation_id": f"op-{len(operations) + 1:03d}",
                    "operation": "summary-refresh",
                    "outcome": (
                        "created"
                        if before_hash is None
                        else "no-change"
                        if output_ref is None
                        else "updated"
                    ),
                    "artifact_kind": "project-summary",
                    "artifact_id": scope.scope_id,
                    "source_refs": owner_source_refs,
                    "output_refs": output_refs,
                    "embedded_artifact": None,
                }
            )

        source_refs_by_turn: dict[str, list[str]] = {}
        for source in sources:
            source_refs_by_turn.setdefault(str(source["turn_id"]), []).append(
                str(source["source_ref"])
            )
        seen_observations: set[str] = set()
        for observation in processed.observations:
            if observation.observation_id in seen_observations:
                continue
            seen_observations.add(observation.observation_id)
            cited_turns = {
                observation.preceding_request_turn_id,
                observation.feedback_turn_id,
                *observation.evaluated_assistant_turn_ids,
            }
            if not cited_turns.issubset(source_refs_by_turn):
                raise ValueError("Interaction Observation lacks exact Manifest sources")
            observation_source_refs = [
                str(source["source_ref"])
                for source in sources
                if source["turn_id"] in cited_turns
            ]
            embedded = observation.value_dict()
            parse_observation(embedded)
            operations.append(
                {
                    "operation_id": f"op-{len(operations) + 1:03d}",
                    "operation": "observation",
                    "outcome": "observed",
                    "artifact_kind": "interaction-observation",
                    "artifact_id": observation.observation_id,
                    "source_refs": observation_source_refs,
                    "output_refs": [],
                    "embedded_artifact": embedded,
                }
            )

        status = "success" if operations else "no_memory"
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "run_id": run_id,
            "status": status,
            "processed_at": timestamp,
            "connector_id": processed.conversation.connector_id,
            "conversation_id": processed.conversation.conversation_id,
            "scope": {
                "type": scope.kind,
                "scope_id": scope.scope_id,
            },
            "processor": {
                "provider": processed.provider,
                "policy_version": processed.policy,
            },
            "policies": {
                "filename": "orca-memory-filename/0.1",
                "layout": "orca-memory-layout/0.1",
                "relationships": "orca-memory-relations/0.1",
            },
            "sources": sources,
            "operations": operations,
            "outputs": outputs,
            "interaction_abstentions": [
                item.value_dict() for item in processed.observation_abstentions
            ],
        }
        validate_manifest(manifest)
        manifest_payload = (
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        manifest_path = (
            self.vault_root
            / "System"
            / "Orca Memory"
            / "manifests"
            / f"{now:%Y}"
            / f"{now:%m}"
            / f"{now:%d}"
            / f"{run_id}.json"
        )
        last_segment = processed.source_segments[-1]
        last_turn = last_segment.turn
        manifest_relative = manifest_path.relative_to(self.vault_root).as_posix()
        checkpoint_relative = self._checkpoint_relative_path(last_turn)
        checkpoint = checkpoint_payload(
            connector_id=last_turn.connector_id,
            conversation_id=last_turn.conversation_id,
            source=sources[-1],
            manifest_path=manifest_relative,
        )
        self._publisher.publish(
            PublicationPlan(
                run_id=run_id,
                manifest_path=manifest_relative,
                manifest_payload=manifest_payload,
                checkpoint_path=checkpoint_relative,
                checkpoint_payload=checkpoint,
                outputs=tuple(planned_outputs),
            ),
            fault=self._publication_fault,
        )
        if processed.observations:
            rebuild_profiles(
                self.vault_root,
                as_of=timestamp,
                project_aliases=(
                    {scope.scope_id: scope.project_alias or ""}
                    if scope.kind == "project"
                    else {}
                ),
            )
        return PublicationResult(
            status=status,
            manifest_path=manifest_path,
            output_paths=tuple(output_paths),
            processed_through_turn=last_turn.turn_id,
        )

    def record_segment_replay(
        self, segments: tuple[SourceSegment, ...]
    ) -> PublicationResult:
        """Repair the checkpoint to the last exact proven segment."""

        if not segments:
            raise ValueError("segment replay requires at least one segment")
        receipts, legacy = processed_segment_receipts(self.vault_root)
        last = segments[-1]
        source = segmented_source(last, source_ref="src-check")
        receipt = receipts.get(
            segment_key(last.connector_id, last.conversation_id, source)
        )
        if receipt is None:
            legacy_receipt = legacy.get(
                (last.connector_id, last.conversation_id, last.turn_id)
            )
            if legacy_receipt is None or last.count != 1:
                raise ValueError("replay has no proving Manifest")
            return self.record_replay(
                ConversationBatch(
                    last.connector_id, last.conversation_id, (last.turn,)
                )
            )
        if not is_exact_segment_replay(last, receipt):
            raise ValueError("replay segment representation does not match Manifest")
        manifest_relative = receipt.manifest_path.relative_to(self.vault_root).as_posix()
        _replace_file(
            self.runtime_root / self._checkpoint_relative_path(last.turn),
            checkpoint_payload(
                connector_id=last.connector_id,
                conversation_id=last.conversation_id,
                source=receipt.source,
                manifest_path=manifest_relative,
            ),
        )
        return PublicationResult("replay", receipt.manifest_path, (), last.turn_id)

    def _memory_records(self) -> dict[str, MemoryRecord | ConflictRecord]:
        """Load Typed Memory Records while rejecting duplicate identities."""

        root = self.vault_root / "System" / "Orca Memory" / "shallow"
        records: dict[str, MemoryRecord | ConflictRecord] = {}
        if not root.exists():
            return records
        for path in sorted(root.glob("**/*.md")):
            document = path.read_text(encoding="utf-8")
            if not document.startswith("---\nschema: orca-memory/0.2\n"):
                continue
            record = (
                parse_conflict_record(document)
                if "\nstatus: conflict\n" in document
                else parse_record(document)
            )
            if record.memory_id in records:
                raise ValueError(f"duplicate Typed Memory identity: {record.memory_id}")
            records[record.memory_id] = record
        return records

    def _allocate_memory_id(
        self, existing: dict[str, MemoryRecord | ConflictRecord]
    ) -> str:
        """Allocate a Storage-owned opaque ID, bounded with fixed test IDs."""

        for attempt in range(100):
            token = self._id_factory()
            memory_id = f"mem_{token}" if attempt == 0 else f"mem_{token}_{attempt + 1}"
            if memory_id not in existing:
                return memory_id
        raise ValueError("unable to allocate a unique Typed Memory identity")

    def _knowledge_candidates(self) -> dict[str, KnowledgeCandidate]:
        root = self.vault_root / "System" / "Orca Memory" / "candidates" / "knowledge"
        candidates: dict[str, KnowledgeCandidate] = {}
        if not root.exists():
            return candidates
        for path in sorted(root.glob("**/*.md")):
            candidate = KnowledgeCandidate.parse(path.read_text(encoding="utf-8"))
            if candidate.candidate_id in candidates:
                raise ValueError(f"duplicate Knowledge Candidate identity: {candidate.candidate_id}")
            candidates[candidate.candidate_id] = candidate
        return candidates

    def _next_overflow_variant(self, memory_id: str) -> int | None:
        root = self.vault_root / "System" / "Orca Memory" / "candidates" / "conflicts"
        highest = 3
        if root.exists():
            marker = f"memory_id: {memory_id}\n"
            for path in root.glob("**/*.md"):
                document = path.read_text(encoding="utf-8")
                if marker not in document:
                    continue
                match = re.search(r"^variant_id: v([1-9][0-9]*)$", document, re.MULTILINE)
                if match is None:
                    raise ValueError(f"invalid conflict overflow identity: {path}")
                highest = max(highest, int(match.group(1)))
        return highest + 1 if highest >= 4 else None

    def _validate_overflow_support(self, proposal) -> str:
        root = self.vault_root / "System" / "Orca Memory" / "candidates" / "conflicts"
        marker_id = f"memory_id: {proposal.target_memory_id}\n"
        marker_variant = f"variant_id: {proposal.target_variant_id}\n"
        matches = []
        if root.exists():
            for path in root.glob("**/*.md"):
                document = path.read_text(encoding="utf-8")
                if marker_id in document and marker_variant in document:
                    matches.append(document)
        if len(matches) != 1:
            raise ValueError("conflict overflow support target does not exist uniquely")
        document = matches[0]
        position = document.split("\n## Position\n\n", 1)[-1].strip()
        position_at_match = re.search(r"^position_at: (.+)$", document, re.MULTILINE)
        recorded_at = None if position_at_match is None else position_at_match.group(1)
        expected_at = proposal.position_at or "null"
        if position != proposal.position or recorded_at != expected_at:
            raise ValueError("conflict overflow support must exactly preserve meaning")
        return f"{proposal.target_memory_id}:{proposal.target_variant_id}"

    def _allocate_candidate_id(
        self, existing: dict[str, KnowledgeCandidate]
    ) -> str:
        for attempt in range(100):
            token = self._id_factory()
            candidate_id = (
                f"cand_{token}" if attempt == 0 else f"cand_{token}_{attempt + 1}"
            )
            if candidate_id not in existing:
                return candidate_id
        raise ValueError("unable to allocate a unique Knowledge Candidate identity")

    def _prepare_project_summary(
        self,
        summary: ProjectSummary,
        *,
        scope: MemoryScope,
        records: dict[str, MemoryRecord | ConflictRecord],
        required_memory_ids: tuple[str, ...],
    ) -> tuple[Path, bytes]:
        """Validate and render the bounded project executive view."""

        if scope.kind != "project" or summary.project_id != scope.scope_id:
            raise ValueError("Project Summary identity must match the project scope")
        if not set(required_memory_ids).issubset(summary.relevant_memory_ids):
            raise ValueError(
                "Project Summary must link every Typed Memory Record changed by the run"
            )
        memory_paths: dict[str, str] = {}
        for memory_id in summary.relevant_memory_ids:
            record = records.get(memory_id)
            if record is None:
                raise ValueError(f"Project Summary references unknown memory_id: {memory_id}")
            if record.scope != "project" or record.scope_id != scope.scope_id:
                raise ValueError(
                    f"Project Summary references out-of-scope memory_id: {memory_id}"
                )
            memory_paths[memory_id] = record_relative_path(
                record,
                scope.project_alias,
                existing_ids=tuple(records),
            ).as_posix()
        payload = render_project_summary(
            summary, memory_paths=memory_paths
        ).encode("utf-8")
        if contains_secret(payload.decode("utf-8")):
            raise ValueError("Project Summary contains a credential-like value")
        path = (
            self.vault_root
            / "System"
            / "Orca Memory"
            / "shallow"
            / "projects"
            / _slug(scope.project_alias or "")
            / "summary.md"
        )
        return path, payload

    def record_replay(self, conversation: ConversationBatch) -> PublicationResult:
        """Repair the disposable checkpoint without repeating semantic work."""

        if not conversation.turns:
            raise ValueError("replay requires at least one source turn")
        receipts = processed_sources(self.vault_root)
        last_turn = conversation.turns[-1]
        receipt = receipts.get(
            (last_turn.connector_id, last_turn.conversation_id, last_turn.turn_id)
        )
        if receipt is None or not is_exact_replay(last_turn, receipt):
            raise ValueError("replay has no proving Manifest")
        manifest_relative = receipt.manifest_path.relative_to(self.vault_root).as_posix()
        if receipt.representation[-1] == "legacy-0.1":
            self._write_legacy_checkpoint(last_turn, receipt.manifest_path)
        else:
            _replace_file(
                self.runtime_root / self._checkpoint_relative_path(last_turn),
                checkpoint_payload(
                    connector_id=last_turn.connector_id,
                    conversation_id=last_turn.conversation_id,
                    source=receipt.source,
                    manifest_path=manifest_relative,
                ),
            )
        return PublicationResult(
            "replay", receipt.manifest_path, (), last_turn.turn_id
        )

    def _continuation_path(
        self,
        scope: MemoryScope,
        conversation_id: str,
        summary: ContinuationSummary,
    ) -> Path:
        base = self.vault_root / "System" / "Orca Memory" / "shallow"
        if scope.kind == "project":
            base = base / "projects" / _slug(scope.project_alias or "")
        else:
            base = base / scope.kind
        directory = base / "conversation-summaries"
        suffix = _short_id(conversation_id)
        existing = [] if not directory.exists() else list(directory.glob(f"*--{suffix}.md"))
        if len(existing) > 1:
            raise ValueError(f"continuation filename collision for {conversation_id}")
        if existing:
            content = existing[0].read_text(encoding="utf-8")
            if f"conversation_id: {json.dumps(conversation_id)}" not in content:
                raise ValueError(f"continuation short-id collision for {conversation_id}")
            return existing[0]
        return directory / f"{_slug(summary.purpose)}--{suffix}.md"

    def _checkpoint_relative_path(self, turn: NormalizedTurn) -> str:
        return (
            Path("checkpoints")
            / _slug(turn.connector_id)
            / f"{hashlib.sha256(turn.conversation_id.encode('utf-8')).hexdigest()}.json"
        ).as_posix()

    def _write_legacy_checkpoint(
        self, turn: NormalizedTurn, manifest_path: Path
    ) -> None:
        path = self.runtime_root / self._checkpoint_relative_path(turn)
        payload = {
            "schema_version": "orca-checkpoint/0.1",
            "connector_id": turn.connector_id,
            "conversation_id": turn.conversation_id,
            "processed_through_turn": turn.turn_id,
            "content_sha256": turn.content_sha256,
            "redaction_policy": turn.redaction_policy,
            "manifest_path": manifest_path.relative_to(self.vault_root).as_posix(),
        }
        _replace_file(
            path,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )


def _render_continuation(
    conversation_id: str,
    project_id: str | None,
    summary: ContinuationSummary,
) -> str:
    lines = [
        "---",
        f"schema_version: {CONTINUATION_SCHEMA}",
        "kind: conversation-continuation-summary",
        "authority: noncanonical",
        f"conversation_id: {json.dumps(conversation_id)}",
        f"project_id: {json.dumps(project_id) if project_id is not None else 'null'}",
        "---",
        "",
        f"# {summary.purpose.strip()}",
        "",
        "## Current state",
        "",
        summary.current_state.strip(),
    ]
    for heading, values in (
        ("Important outcomes", summary.important_outcomes),
        ("Open questions", summary.open_questions),
        ("Next steps", summary.next_steps),
        ("Relevant artifacts", summary.relevant_artifacts),
    ):
        if values:
            lines.extend(("", f"## {heading}", ""))
            lines.extend(f"- {value.strip()}" for value in values)
    return "\n".join(lines) + "\n"


def _include_changed_memory_ids(
    summary: ProjectSummary, changed_memory_ids: list[str]
) -> ProjectSummary:
    """Attach Storage-assigned IDs to a validated Project Summary.

    Providers cannot know IDs allocated later in the same publication.  Keep
    their validated summary meaning and append each changed record identity in
    deterministic publication order before Storage resolves links.
    """

    existing = list(summary.relevant_memory_ids)
    for memory_id in changed_memory_ids:
        if memory_id not in existing:
            existing.append(memory_id)
    return replace(summary, relevant_memory_ids=tuple(existing), body=None)


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).lower()
    slug = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-_")[:72].rstrip("-")
    if not slug or slug in _GENERIC_SLUGS:
        raise ValueError(f"unsafe or non-descriptive slug: {value!r}")
    return slug


def _short_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _hash_path(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _replace_file(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _publish_immutable(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError as exc:
            raise ValueError(f"immutable manifest already exists: {path}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)
