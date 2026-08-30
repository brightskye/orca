from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.candidates import CandidateProposal, KnowledgeCandidate
from orca_memory.conflicts import ConflictProposal, SupersedeProposal, parse_conflict_record
from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.memory import RecordProposal
from orca_memory.pipeline import Step3Pipeline
from orca_memory.processor import (
    Abstention,
    CandidateInstruction,
    ProcessingProposal,
    Processor,
)
from orca_memory.storage import MemoryScope, Storage


class MutableProvider:
    name = "fake-provider/outcomes"

    def __init__(self, proposal: ProcessingProposal) -> None:
        self.proposal = proposal
        self.calls = 0

    def distill(self, request):
        self.calls += 1
        return self.proposal


def _batch(turn_id: str) -> ConversationBatch:
    turn = NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-outcomes",
        turn_id=turn_id,
        occurred_at="2026-08-30T10:00:00Z",
        source_uri=f"codex://session/conversation-outcomes/event/{turn_id}",
        text=f"Owner evidence for {turn_id}.",
        content_sha256=hashlib.sha256(f"Owner evidence for {turn_id}.".encode()).hexdigest(),
    )
    return ConversationBatch("codex-local", "conversation-outcomes", (turn,))


def _add() -> RecordProposal:
    return RecordProposal(
        operation="add",
        kind="decision",
        subject="Processed source index",
        scope="general",
        scope_id="general",
        current="Use the Manifest scan.",
        source_updated_at="2026-08-30T09:00:00Z",
    )


def _conflict(label: str, position: str, at: str) -> ConflictProposal:
    return ConflictProposal(
        target_memory_id="mem_memory",
        kind="decision",
        subject="Processed source index",
        scope="general",
        scope_id="general",
        label=label,
        position=position,
        position_at=at,
    )


class OutcomePipelineTests(unittest.TestCase):
    def _pipeline(self, root: Path, provider: MutableProvider) -> Step3Pipeline:
        values = iter(
            (
                "run-add",
                "memory",
                "run-conflict",
                "run-third",
                "run-overflow",
                "run-candidate",
                "candidate",
                "run-support",
                "run-abstain",
            )
        )
        return Step3Pipeline(
            Processor(provider),
            Storage(
                root / "vault",
                root / "runtime",
                clock=lambda: datetime(2026, 8, 30, 12, tzinfo=timezone.utc),
                id_factory=lambda: next(values),
            ),
        )

    def test_conflicts_overflow_and_candidates_publish_joined_noncanonical_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = MutableProvider(ProcessingProposal(None, (_add(),)))
            pipeline = self._pipeline(root, provider)
            scope = MemoryScope("general", "general")
            pipeline.run(_batch("turn-add"), scope=scope)

            provider.proposal = ProcessingProposal(
                None,
                conflict_proposals=(
                    _conflict("SQLite", "Use only SQLite.", "2026-08-30T10:00:00Z"),
                ),
            )
            first_conflict = pipeline.run(_batch("turn-conflict"), scope=scope)
            provider.proposal = ProcessingProposal(
                None,
                conflict_proposals=(
                    _conflict("Both", "Use both scan and SQLite.", "2026-08-30T11:00:00Z"),
                ),
            )
            pipeline.run(_batch("turn-third"), scope=scope)
            provider.proposal = ProcessingProposal(
                None,
                conflict_proposals=(
                    _conflict("Remote", "Use a remote index.", "2026-08-30T12:00:00Z"),
                ),
            )
            overflow_result = pipeline.run(_batch("turn-overflow"), scope=scope)

            record_path = next((root / "vault").glob("**/decisions/*.md"))
            conflict = parse_conflict_record(record_path.read_text())
            self.assertEqual(conflict.review_state, "overflow")
            self.assertEqual([item.variant_id for item in conflict.variants], ["v1", "v2", "v3"])
            overflow = next((root / "vault").glob("**/candidates/conflicts/**/*.md"))
            self.assertIn("variant_id: v4", overflow.read_text())
            manifest = json.loads(overflow_result.manifest_path.read_text())
            self.assertEqual(
                [item["artifact_kind"] for item in manifest["operations"]],
                ["typed-memory-record", "conflict-overflow-candidate"],
            )
            for operation in manifest["operations"]:
                self.assertEqual(operation["source_refs"], ["src-001"])
            self.assertEqual(
                json.loads(first_conflict.manifest_path.read_text())["operations"][0]["outcome"],
                "conflict-recorded",
            )

            candidate_proposal = CandidateProposal(
                candidate_kind="fact",
                subject="Manifest scan portability",
                proposal="The Manifest scan is the correctness baseline.",
                scope="general",
                scope_id="general",
            )
            provider.proposal = ProcessingProposal(
                None,
                candidate_operations=(CandidateInstruction("create", candidate_proposal),),
            )
            created = pipeline.run(_batch("turn-candidate"), scope=scope)
            candidate_path = next((root / "vault").glob("**/candidates/knowledge/**/*.md"))
            candidate = KnowledgeCandidate.parse(candidate_path.read_text())
            self.assertEqual(candidate.candidate_id, "cand_candidate")
            self.assertFalse(candidate.is_recall_eligible)
            provider.proposal = ProcessingProposal(
                None,
                candidate_operations=(
                    CandidateInstruction("support", candidate_proposal, candidate.candidate_id),
                ),
            )
            before = candidate_path.read_bytes()
            supported = pipeline.run(_batch("turn-support"), scope=scope)
            self.assertEqual(candidate_path.read_bytes(), before)
            self.assertEqual(
                json.loads(supported.manifest_path.read_text())["operations"][0]["outcome"],
                "no-change",
            )
            self.assertEqual(
                json.loads(created.manifest_path.read_text())["operations"][0]["artifact_id"],
                candidate.candidate_id,
            )

            provider.proposal = ProcessingProposal(
                None, abstentions=(Abstention("hypothetical"),)
            )
            abstained = pipeline.run(_batch("turn-abstain"), scope=scope)
            abstention_manifest = json.loads(abstained.manifest_path.read_text())
            self.assertEqual(abstention_manifest["status"], "no_memory")
            self.assertEqual(abstention_manifest["operations"], [])

    def test_explicit_supersede_publishes_lineage_under_stable_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = MutableProvider(ProcessingProposal(None, (_add(),)))
            pipeline = self._pipeline(root, provider)
            scope = MemoryScope("general", "general")
            pipeline.run(_batch("turn-add"), scope=scope)
            provider.proposal = ProcessingProposal(
                None,
                supersede_proposals=(
                    SupersedeProposal(
                        target_memory_id="mem_memory",
                        kind="decision",
                        subject="Processed source index",
                        scope="general",
                        scope_id="general",
                        current="Use the receipt-backed SQLite projection.",
                        source_updated_at="2026-08-30T13:00:00Z",
                    ),
                ),
            )
            result = pipeline.run(_batch("turn-supersede"), scope=scope)
            record = next((root / "vault").glob("**/decisions/*.md")).read_text()
            self.assertIn("memory_id: mem_memory", record)
            self.assertIn("## Resolution lineage", record)
            operation = json.loads(result.manifest_path.read_text())["operations"][0]
            self.assertEqual((operation["operation"], operation["outcome"]), ("supersede", "updated"))

    def test_overflow_support_records_provenance_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = MutableProvider(ProcessingProposal(None, (_add(),)))
            pipeline = self._pipeline(root, provider)
            scope = MemoryScope("general", "general")
            pipeline.run(_batch("turn-add"), scope=scope)
            for turn_id, proposal in (
                ("turn-v2", _conflict("SQLite", "Use only SQLite.", "2026-08-30T10:00:00Z")),
                ("turn-v3", _conflict("Both", "Use both scan and SQLite.", "2026-08-30T11:00:00Z")),
                ("turn-v4", _conflict("Remote", "Use a remote index.", "2026-08-30T12:00:00Z")),
            ):
                provider.proposal = ProcessingProposal(None, conflict_proposals=(proposal,))
                pipeline.run(_batch(turn_id), scope=scope)
            overflow = next((root / "vault").glob("**/candidates/conflicts/**/*.md"))
            before = overflow.read_bytes()
            provider.proposal = ProcessingProposal(
                None,
                conflict_proposals=(
                    ConflictProposal(
                        **{
                            **_conflict(
                                "Remote",
                                "Use a remote index.",
                                "2026-08-30T12:00:00Z",
                            ).__dict__,
                            "target_variant_id": "v4",
                        }
                    ),
                ),
            )
            result = pipeline.run(_batch("turn-v4-support"), scope=scope)
            self.assertEqual(overflow.read_bytes(), before)
            operation = json.loads(result.manifest_path.read_text())["operations"][0]
            self.assertEqual(operation["artifact_kind"], "conflict-overflow-candidate")
            self.assertEqual((operation["operation"], operation["outcome"]), ("support", "supported"))


if __name__ == "__main__":
    unittest.main()
