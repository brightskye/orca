"""Deterministic processing budgets, turn chunking, and source segmentation.

The Processor owns the semantic call, while this module owns the bounded
mechanics needed before that call.  It never truncates evidence.  An oversized
turn is split at UTF-8 character boundaries and every output, including a
turn that did not need splitting, carries the same source-segment metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Iterable, Mapping, Sequence

from orca_memory.conversation import NormalizedTurn


SEGMENTATION_POLICY = "orca-segmentation/0.1"
TOKEN_ESTIMATOR_VERSION = "orca-token-estimator/0.1-byte-conservative"


class BudgetExceededError(ValueError):
    """A named budget was exceeded, without retaining the measured content."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(f"{category} exceeds its configured ceiling")


def estimate_tokens(text: str) -> int:
    """Return a deterministic conservative token estimate.

    UTF-8 byte units are intentionally an upper bound proxy rather than a
    language-model tokenizer.  This avoids undercounting non-ASCII text and
    keeps the bound stable without introducing a model or dependency.
    """

    if not isinstance(text, str):
        raise TypeError("token estimation requires text")
    try:
        byte_count = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("text contains an unencodable Unicode surrogate") from exc
    return byte_count


@dataclass(frozen=True)
class BudgetConfig:
    """Immutable accepted processing ceilings.

    Category ceilings are independent; ``total_input_tokens`` is the hard
    aggregate ceiling applied to the selected input.  Related-record count and
    token limits cannot be raised above the Phase 1 contract in this module.
    """

    new_evidence_tokens: int = 8_000
    preceding_turn_tokens: int = 1_000
    continuation_summary_tokens: int = 2_000
    project_summary_tokens: int = 2_000
    related_records_tokens: int = 5_000
    related_record_count: int = 5
    total_input_tokens: int = 20_000
    semantic_output_tokens: int = 4_000
    token_estimator_version: str = TOKEN_ESTIMATOR_VERSION

    def __post_init__(self) -> None:
        numeric = {
            "new_evidence_tokens": self.new_evidence_tokens,
            "preceding_turn_tokens": self.preceding_turn_tokens,
            "continuation_summary_tokens": self.continuation_summary_tokens,
            "project_summary_tokens": self.project_summary_tokens,
            "related_records_tokens": self.related_records_tokens,
            "related_record_count": self.related_record_count,
            "total_input_tokens": self.total_input_tokens,
            "semantic_output_tokens": self.semantic_output_tokens,
        }
        if any(not isinstance(value, int) or isinstance(value, bool) for value in numeric.values()):
            raise ValueError("budget ceilings must be integers")
        if any(value < 0 for value in numeric.values()):
            raise ValueError("budget ceilings cannot be negative")
        if self.total_input_tokens <= 0:
            raise ValueError("total_input_tokens must be positive")
        if self.semantic_output_tokens <= 0:
            raise ValueError("semantic_output_tokens must be positive")
        category_fields = (
            "new_evidence_tokens",
            "preceding_turn_tokens",
            "continuation_summary_tokens",
            "project_summary_tokens",
            "related_records_tokens",
        )
        if any(getattr(self, field) > self.total_input_tokens for field in category_fields):
            raise ValueError("a category ceiling cannot exceed total_input_tokens")
        if self.related_record_count > 5:
            raise ValueError("related_record_count cannot exceed five in Phase 1")
        if self.related_records_tokens > 5_000:
            raise ValueError("related_records_tokens cannot exceed 5,000 in Phase 1")
        if not isinstance(self.token_estimator_version, str) or not self.token_estimator_version.strip():
            raise ValueError("token_estimator_version is required")

    @property
    def input_category_ceiling_sum(self) -> int:
        """Return the sum of category ceilings for diagnostics."""

        return sum(
            (
                self.new_evidence_tokens,
                self.preceding_turn_tokens,
                self.continuation_summary_tokens,
                self.project_summary_tokens,
                self.related_records_tokens,
            )
        )


DEFAULT_BUDGETS = BudgetConfig()
DEFAULT_BUDGET = DEFAULT_BUDGETS
ProcessingBudgets = BudgetConfig
ContextBudgets = BudgetConfig


@dataclass(frozen=True)
class BudgetUsage:
    """Measured category usage for one prospective provider call."""

    new_evidence_tokens: int = 0
    preceding_turn_tokens: int = 0
    continuation_summary_tokens: int = 0
    project_summary_tokens: int = 0
    related_records_tokens: int = 0
    semantic_output_tokens: int = 0

    @property
    def total_input_tokens(self) -> int:
        return sum(
            (
                self.new_evidence_tokens,
                self.preceding_turn_tokens,
                self.continuation_summary_tokens,
                self.project_summary_tokens,
                self.related_records_tokens,
            )
        )

    def validate(self, budgets: BudgetConfig = DEFAULT_BUDGETS) -> "BudgetUsage":
        """Fail closed if any category or the complete input exceeds a limit."""

        values = {
            "new_evidence_tokens": self.new_evidence_tokens,
            "preceding_turn_tokens": self.preceding_turn_tokens,
            "continuation_summary_tokens": self.continuation_summary_tokens,
            "project_summary_tokens": self.project_summary_tokens,
            "related_records_tokens": self.related_records_tokens,
            "semantic_output_tokens": self.semantic_output_tokens,
        }
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values.values()):
            raise ValueError("budget usage must contain integer values")
        if any(value < 0 for value in values.values()):
            raise ValueError("budget usage cannot be negative")
        for field in (
            "new_evidence_tokens",
            "preceding_turn_tokens",
            "continuation_summary_tokens",
            "project_summary_tokens",
            "related_records_tokens",
            "semantic_output_tokens",
        ):
            limit = (
                budgets.semantic_output_tokens
                if field == "semantic_output_tokens"
                else getattr(budgets, field)
            )
            if getattr(self, field) > limit:
                raise BudgetExceededError(field)
        if self.total_input_tokens > budgets.total_input_tokens:
            raise ValueError("complete provider input exceeds total_input_tokens")
        return self


def validate_budget_usage(
    usage: BudgetUsage | Mapping[str, int], budgets: BudgetConfig = DEFAULT_BUDGETS
) -> BudgetUsage:
    """Validate a usage value supplied either as a value object or mapping."""

    if not isinstance(usage, BudgetUsage):
        if not isinstance(usage, Mapping):
            raise TypeError("usage must be BudgetUsage or a mapping")
        usage = BudgetUsage(**dict(usage))
    return usage.validate(budgets)


def segmentation_parameters(*, max_segment_tokens: int, token_estimator_version: str) -> dict[str, Any]:
    """Return canonical parameters whose hash identifies one segmentation run."""

    if not isinstance(max_segment_tokens, int) or isinstance(max_segment_tokens, bool):
        raise ValueError("max_segment_tokens must be an integer")
    if max_segment_tokens <= 0:
        raise ValueError("max_segment_tokens must be positive")
    if not isinstance(token_estimator_version, str) or not token_estimator_version.strip():
        raise ValueError("token_estimator_version is required")
    return {
        "max_segment_tokens": max_segment_tokens,
        "policy_version": SEGMENTATION_POLICY,
        "token_estimator_version": token_estimator_version,
    }


def parameters_sha256(*, max_segment_tokens: int, token_estimator_version: str) -> str:
    """Hash canonical segmentation parameters for Manifest identity."""

    payload = json.dumps(
        segmentation_parameters(
            max_segment_tokens=max_segment_tokens,
            token_estimator_version=token_estimator_version,
        ),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class SourceSegment:
    """One complete source turn or deterministic UTF-8 segment."""

    turn: NormalizedTurn
    text: str
    index: int
    count: int
    start_byte: int
    end_byte: int
    parameters_sha256: str
    policy_version: str = SEGMENTATION_POLICY

    def __post_init__(self) -> None:
        if not isinstance(self.turn, NormalizedTurn):
            raise TypeError("segment turn must be a NormalizedTurn")
        if not isinstance(self.text, str):
            raise TypeError("segment text must be a string")
        encoded = self.text.encode("utf-8")
        if self.index < 1 or self.count < 1 or self.index > self.count:
            raise ValueError("segment index/count is invalid")
        if self.start_byte < 0 or self.end_byte < self.start_byte:
            raise ValueError("segment byte range is invalid")
        if self.end_byte - self.start_byte != len(encoded):
            raise ValueError("segment byte range does not match segment text")
        if not isinstance(self.parameters_sha256, str) or not re_full_hex(self.parameters_sha256):
            raise ValueError("segment parameters hash is invalid")
        if self.policy_version != SEGMENTATION_POLICY:
            raise ValueError("unsupported segmentation policy")

    @property
    def turn_content_sha256(self) -> str:
        return self.turn.content_sha256

    @property
    def turn_id(self) -> str:
        return self.turn.turn_id

    @property
    def source_role(self) -> str:
        return self.turn.source_role

    @property
    def connector_id(self) -> str:
        return self.turn.connector_id

    @property
    def conversation_id(self) -> str:
        return self.turn.conversation_id

    @property
    def occurred_at(self) -> str | None:
        return self.turn.occurred_at

    @property
    def source_uri(self) -> str:
        return self.turn.source_uri

    @property
    def redaction_policy(self) -> str:
        return self.turn.redaction_policy

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def segment(self) -> dict[str, Any]:
        """Return the nested source-segment fields used by a Manifest."""

        return {
            "policy_version": self.policy_version,
            "parameters_sha256": self.parameters_sha256,
            "index": self.index,
            "count": self.count,
            "start_byte": self.start_byte,
            "end_byte": self.end_byte,
            "content_sha256": self.content_sha256,
        }

    @property
    def token_count(self) -> int:
        return estimate_tokens(self.text)

    def as_manifest_source(self, source_ref: str) -> dict[str, Any]:
        """Return the uniform source receipt shape owned by Provenance."""

        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError("source_ref is required")
        return {
            "source_ref": source_ref,
            "turn_id": self.turn.turn_id,
            "source_role": self.turn.source_role,
            "source_uri": self.turn.source_uri,
            "occurred_at": self.turn.occurred_at,
            "turn_content_sha256": self.turn_content_sha256,
            "redaction_policy": self.turn.redaction_policy,
            "segment": {
                **self.segment,
            },
        }


def re_full_hex(value: str) -> bool:
    """Small dependency-free hash shape check kept local to this module."""

    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _split_utf8_text(text: str, max_bytes: int) -> tuple[tuple[str, int, int], ...]:
    if max_bytes <= 0:
        raise ValueError("max segment size must be positive")
    if not isinstance(text, str):
        raise TypeError("turn text must be a string")
    encoded = text.encode("utf-8")
    if not encoded:
        return (("", 0, 0),)
    pieces: list[tuple[str, int, int]] = []
    start = 0
    while start < len(encoded):
        end = min(start + max_bytes, len(encoded))
        if end < len(encoded):
            # Back up to a UTF-8 character boundary.  A leading byte has either
            # 0xxxxxxx, 110xxxxx, 1110xxxx, or 11110xxx shape.
            while end > start and (encoded[end] & 0xC0) == 0x80:
                end -= 1
            if end == start:
                # The configured bound cannot fit even one Unicode code point.
                first_byte = encoded[start]
                if first_byte < 0x80:
                    first_width = 1
                elif first_byte & 0xE0 == 0xC0:
                    first_width = 2
                elif first_byte & 0xF0 == 0xE0:
                    first_width = 3
                else:
                    first_width = 4
                raise ValueError(
                    f"max segment size {max_bytes} cannot fit a UTF-8 character of {first_width} bytes"
                )
        piece = encoded[start:end].decode("utf-8")
        pieces.append((piece, start, end))
        start = end
    return tuple(pieces)


def segment_turn(
    turn: NormalizedTurn,
    *,
    max_segment_tokens: int,
    token_estimator_version: str = TOKEN_ESTIMATOR_VERSION,
) -> tuple[SourceSegment, ...]:
    """Return one or more complete source segments for ``turn``."""

    if not isinstance(turn, NormalizedTurn):
        raise TypeError("segment_turn requires a NormalizedTurn")
    params_hash = parameters_sha256(
        max_segment_tokens=max_segment_tokens,
        token_estimator_version=token_estimator_version,
    )
    pieces = _split_utf8_text(turn.text, max_segment_tokens)
    count = len(pieces)
    return tuple(
        SourceSegment(
            turn=turn,
            text=text,
            index=index,
            count=count,
            start_byte=start,
            end_byte=end,
            parameters_sha256=params_hash,
        )
        for index, (text, start, end) in enumerate(pieces, start=1)
    )


def segment_turn_with_budget(
    turn: NormalizedTurn, budgets: BudgetConfig = DEFAULT_BUDGETS
) -> tuple[SourceSegment, ...]:
    """Segment a turn using the new-evidence ceiling and configured estimator."""

    return segment_turn(
        turn,
        max_segment_tokens=budgets.new_evidence_tokens,
        token_estimator_version=budgets.token_estimator_version,
    )


@dataclass(frozen=True)
class ProcessingChunk:
    """One chronological provider input chunk containing complete segments."""

    segments: tuple[SourceSegment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("processing chunks cannot be empty")
        object.__setattr__(self, "segments", tuple(self.segments))

    @property
    def token_count(self) -> int:
        return sum(segment.token_count for segment in self.segments)

    @property
    def turns(self) -> tuple[NormalizedTurn, ...]:
        result: list[NormalizedTurn] = []
        seen: set[str] = set()
        for segment in self.segments:
            if segment.turn.turn_id not in seen:
                result.append(segment.turn)
                seen.add(segment.turn.turn_id)
        return tuple(result)


def _validate_turn_batch(turns: Sequence[NormalizedTurn]) -> tuple[NormalizedTurn, ...]:
    if not turns:
        raise ValueError("chunking requires at least one turn")
    result = tuple(turns)
    first = result[0]
    if not isinstance(first, NormalizedTurn):
        raise TypeError("chunking requires NormalizedTurn values")
    seen: set[str] = set()
    previous_occurred_at: str | None = None
    for turn in result:
        if not isinstance(turn, NormalizedTurn):
            raise TypeError("chunking requires NormalizedTurn values")
        if turn.connector_id != first.connector_id or turn.conversation_id != first.conversation_id:
            raise ValueError("chunking cannot combine conversations or connectors")
        if turn.turn_id in seen:
            raise ValueError(f"duplicate turn in chunk input: {turn.turn_id}")
        if (
            previous_occurred_at is not None
            and turn.occurred_at is not None
            and turn.occurred_at < previous_occurred_at
        ):
            raise ValueError("chunk input turns must be chronological")
        if turn.occurred_at is not None:
            previous_occurred_at = turn.occurred_at
        seen.add(turn.turn_id)
    return result


def chunk_turns(
    turns: Sequence[NormalizedTurn], budgets: BudgetConfig = DEFAULT_BUDGETS
) -> tuple[ProcessingChunk, ...]:
    """Pack chronological turns into boundary-preserving bounded chunks.

    The caller supplies the capture connector's chronological order.  This
    function never reorders turns and never drops or truncates their text.
    """

    turns = _validate_turn_batch(turns)
    if budgets.new_evidence_tokens <= 0:
        raise ValueError("new_evidence_tokens must be positive for chunking")
    chunks: list[ProcessingChunk] = []
    current: list[SourceSegment] = []
    current_tokens = 0
    for turn in turns:
        segments = segment_turn_with_budget(turn, budgets)
        for segment in segments:
            token_count = segment.token_count
            if token_count > budgets.new_evidence_tokens:
                raise ValueError("segmentation produced an over-budget segment")
            if current and current_tokens + token_count > budgets.new_evidence_tokens:
                chunks.append(ProcessingChunk(tuple(current)))
                current = []
                current_tokens = 0
            current.append(segment)
            current_tokens += token_count
    if current:
        chunks.append(ProcessingChunk(tuple(current)))
    return tuple(chunks)


def _scope_tuple(scope: Any, scope_id: str | None = None) -> tuple[str, str]:
    if isinstance(scope, str):
        if scope_id is None:
            raise ValueError("scope_id is required when scope is a string")
        return scope, scope_id
    kind = getattr(scope, "kind", None)
    identity = getattr(scope, "scope_id", None)
    if not isinstance(kind, str) or not isinstance(identity, str):
        raise ValueError("scope must provide kind and scope_id")
    return kind, identity


def _related_record_text(record: Any) -> str:
    body = getattr(record, "body", None)
    if isinstance(body, str):
        return body
    if isinstance(record, Mapping):
        body = record.get("body") or record.get("current") or record.get("final")
        if isinstance(body, str):
            return body
    raise ValueError("related record has no bounded text representation")


def _related_candidate_text(candidate: Any) -> str:
    """Return the bounded semantic text for one pending candidate target."""

    def value(name: str) -> Any:
        if isinstance(candidate, Mapping):
            return candidate.get(name)
        return getattr(candidate, name, None)

    proposal = value("proposal")
    context = value("context")
    if not isinstance(proposal, str):
        raise ValueError("related candidate has no bounded proposal")
    if isinstance(context, str) and context.strip():
        return f"{proposal}\n{context}"
    return proposal


def select_related_records(
    records: Iterable[Any],
    scope: Any,
    scope_id: str | None = None,
    *,
    budgets: BudgetConfig = DEFAULT_BUDGETS,
    rank_key: Callable[[Any], Any] | None = None,
) -> tuple[Any, ...]:
    """Select ranked same-scope current records within count/token ceilings.

    Input order is the relevance order supplied by the retrieval layer unless
    ``rank_key`` is explicitly provided.  Invalid, non-current, and
    cross-scope records are excluded; no record is truncated.
    """

    scope_kind, scope_identity = _scope_tuple(scope, scope_id)
    candidates = list(records)
    if rank_key is not None:
        candidates.sort(key=rank_key)
    selected: list[Any] = []
    used_tokens = 0
    for record in candidates:
        record_scope = record.get("scope") if isinstance(record, Mapping) else getattr(record, "scope", None)
        record_scope_id = (
            record.get("scope_id") if isinstance(record, Mapping) else getattr(record, "scope_id", None)
        )
        status = record.get("status") if isinstance(record, Mapping) else getattr(record, "status", None)
        if (record_scope, record_scope_id) != (scope_kind, scope_identity) or status != "current":
            continue
        if len(selected) >= budgets.related_record_count:
            break
        text = _related_record_text(record)
        token_count = estimate_tokens(text)
        if token_count > budgets.related_records_tokens:
            continue
        if used_tokens + token_count > budgets.related_records_tokens:
            # Input is relevance ordered, so omitting this and later records
            # is equivalent to removing the lowest-ranked records first.
            break
        selected.append(record)
        used_tokens += token_count
    return tuple(selected)


def measure_context(
    *,
    new_evidence: str | Sequence[str] = (),
    preceding_turn: str = "",
    continuation_summary: str = "",
    project_summary: str = "",
    related_records: Iterable[Any] = (),
    related_candidates: Iterable[Any] = (),
    semantic_output: str = "",
) -> BudgetUsage:
    """Measure text categories without applying a provider call."""

    if isinstance(new_evidence, str):
        new_evidence = (new_evidence,)
    if not isinstance(new_evidence, Sequence):
        raise TypeError("new_evidence must be text or a sequence of text")
    evidence_tokens = sum(estimate_tokens(value) for value in new_evidence)
    related_tokens = sum(estimate_tokens(_related_record_text(value)) for value in related_records)
    related_tokens += sum(
        estimate_tokens(_related_candidate_text(value)) for value in related_candidates
    )
    return BudgetUsage(
        new_evidence_tokens=evidence_tokens,
        preceding_turn_tokens=estimate_tokens(preceding_turn),
        continuation_summary_tokens=estimate_tokens(continuation_summary),
        project_summary_tokens=estimate_tokens(project_summary),
        related_records_tokens=related_tokens,
        semantic_output_tokens=estimate_tokens(semantic_output),
    )


# Explicit aliases keep the seam easy to discover for Processor integration.
segment_oversized_turn = segment_turn
chunk_processing_turns = chunk_turns
select_current_related_records = select_related_records
validate_context_budget = validate_budget_usage


__all__ = [
    "BudgetConfig",
    "BudgetUsage",
    "ContextBudgets",
    "DEFAULT_BUDGET",
    "DEFAULT_BUDGETS",
    "ProcessingBudgets",
    "ProcessingChunk",
    "SEGMENTATION_POLICY",
    "SourceSegment",
    "TOKEN_ESTIMATOR_VERSION",
    "chunk_turns",
    "chunk_processing_turns",
    "estimate_tokens",
    "measure_context",
    "parameters_sha256",
    "segment_turn",
    "segment_oversized_turn",
    "segment_turn_with_budget",
    "segmentation_parameters",
    "select_related_records",
    "select_current_related_records",
    "validate_context_budget",
    "validate_budget_usage",
]
