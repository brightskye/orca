"""Use prevalidated Orca distillation through AgentCairn's public seam."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from cairn.ingest import Candidate, content_hash
from cairn.vault import Note


ADAPTER_VERSION = "orca-agentcairn-adapter/0.1.0"


@dataclass(frozen=True)
class AgentCairnDistillation:
    """One prevalidated noncanonical Orca note keyed to its source text."""

    harness: str
    session_id: str
    source_text: str
    permalink: str
    frontmatter: Mapping[str, Any]
    body: str

    def __post_init__(self) -> None:
        for field, value in (
            ("harness", self.harness),
            ("session_id", self.session_id),
            ("source_text", self.source_text),
            ("permalink", self.permalink),
            ("body", self.body),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} is required")
        authority = self.frontmatter.get("authority")
        if not isinstance(authority, str) or not authority or authority == "canonical":
            raise ValueError("AgentCairn distillation must declare noncanonical authority")

    @property
    def key(self) -> tuple[str, str, str]:
        return self.harness, self.session_id, content_hash(self.source_text)

    def to_note(self) -> Note:
        """Create a fresh AgentCairn note for one distillation call."""

        return Note(
            permalink=self.permalink,
            frontmatter=deepcopy(dict(self.frontmatter)),
            body=self.body,
        )


class OrcaDecisionDistiller:
    """Replace AgentCairn distillation with prevalidated Orca decisions."""

    def __init__(self, distillations: list[AgentCairnDistillation]) -> None:
        self._distillations: dict[tuple[str, str, str], AgentCairnDistillation] = {}
        self.calls = 0
        for distillation in distillations:
            if distillation.key in self._distillations:
                raise ValueError(f"ambiguous distillation lookup key: {distillation.key}")
            self._distillations[distillation.key] = distillation

    def distill(self, candidate: Candidate) -> Note:
        """Return the validated Orca note matching an AgentCairn candidate."""

        self.calls += 1
        key = (
            candidate.harness or "",
            candidate.session_id,
            content_hash(candidate.text),
        )
        distillation = self._distillations.get(key)
        if distillation is None:
            raise KeyError(f"no validated Orca distillation for AgentCairn candidate {key}")
        return distillation.to_note()
