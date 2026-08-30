from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.pipeline import Step3Pipeline
from orca_memory.processor import ContinuationSummary, ProcessingProposal, Processor
from orca_memory.storage import MemoryScope, Storage


class FakeProvider:
    name = "fake-semantic-provider/1"

    def __init__(self, proposal: ProcessingProposal) -> None:
        self.proposal = proposal
        self.calls = 0
        self.requests = []

    def distill(self, request):
        self.calls += 1
        self.requests.append(request)
        return self.proposal


def _batch(*, text_hash: str | None = None) -> ConversationBatch:
    turn = NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-123",
        turn_id="turn-1",
        occurred_at="2026-08-29T10:00:00Z",
        source_uri="codex://session/conversation-123/event/turn-1",
        text="Design the Step 3 pipeline.",
        content_sha256=text_hash or hashlib.sha256(b"Design the Step 3 pipeline.").hexdigest(),
    )
    return ConversationBatch("codex-local", "conversation-123", (turn,))


def _batch_with_assistant_context() -> ConversationBatch:
    owner = _batch().turns[0]
    assistant = NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-123",
        turn_id="turn-1-answer",
        occurred_at="2026-08-29T10:01:00Z",
        source_uri="codex://session/conversation-123/event/turn-1-answer",
        text="A visible final response used only as context.",
        content_sha256=hashlib.sha256(b"A visible final response used only as context.").hexdigest(),
        source_role="assistant",
    )
    return ConversationBatch("codex-local", "conversation-123", (owner, assistant))


def _summary(*, state: str = "The publication flow is accepted.") -> ContinuationSummary:
    return ContinuationSummary(
        purpose="Step 3 memory implementation",
        current_state=state,
        important_outcomes=("Continuation Summary is a structural artifact.",),
        next_steps=("Implement typed memory records.",),
    )


class Step3PipelineTests(unittest.TestCase):
    def _storage(self, root: Path, *, publication_fault=None) -> Storage:
        return Storage(
            root / "vault",
            root / "runtime",
            clock=lambda: datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc),
            id_factory=lambda: "fixed-run-id",
            publication_fault=publication_fault,
        )

    def test_publishes_continuation_manifest_then_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = FakeProvider(ProcessingProposal(_summary()))
            storage = self._storage(root)
            result = Step3Pipeline(Processor(provider), storage).run(
                _batch(),
                scope=MemoryScope("project", "project-1", "Orca"),
            )

            self.assertEqual(result.status, "success")
            self.assertEqual(provider.calls, 1)
            self.assertEqual(len(result.output_paths), 1)
            summary_path = result.output_paths[0]
            self.assertEqual(summary_path.parent.name, "conversation-summaries")
            self.assertEqual(summary_path.parent.parent.name, "orca")
            summary_text = summary_path.read_text(encoding="utf-8")
            self.assertIn("schema_version: orca-conversation-continuation/1", summary_text)
            self.assertIn('conversation_id: "conversation-123"', summary_text)
            self.assertIn('project_id: "project-1"', summary_text)
            self.assertIn("## Current state", summary_text)

            self.assertIsNotNone(result.manifest_path)
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "orca-run-manifest/0.2")
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["sources"][0]["turn_id"], "turn-1")
            self.assertEqual(manifest["sources"][0]["source_role"], "owner")
            self.assertEqual(
                manifest["sources"][0]["segment"]["content_sha256"],
                _sha256(path=None, payload=_batch().turns[0].text.encode()),
            )
            self.assertEqual(manifest["operations"][0]["operation"], "summary-refresh")
            self.assertEqual(
                manifest["outputs"][0]["after_sha256"], _sha256(summary_path)
            )

            checkpoints = list((root / "runtime" / "checkpoints").glob("**/*.json"))
            self.assertEqual(len(checkpoints), 1)
            checkpoint = json.loads(checkpoints[0].read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["schema_version"], "orca-checkpoint/0.2")
            self.assertEqual(checkpoint["processed_through"]["turn_id"], "turn-1")
            self.assertEqual(
                checkpoint["manifest_path"],
                result.manifest_path.relative_to(root / "vault").as_posix(),
            )

    def test_manifest_replay_skips_provider_and_repairs_missing_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = FakeProvider(ProcessingProposal(_summary()))
            pipeline = Step3Pipeline(Processor(provider), self._storage(root))
            first = pipeline.run(
                _batch(), scope=MemoryScope("unassigned", "unassigned")
            )
            checkpoints = list((root / "runtime" / "checkpoints").glob("**/*.json"))
            checkpoints[0].unlink()

            replay = pipeline.run(
                _batch(), scope=MemoryScope("unassigned", "unassigned")
            )

            self.assertEqual(first.status, "success")
            self.assertEqual(replay.status, "replay")
            self.assertEqual(provider.calls, 1)
            self.assertEqual(
                len(list((root / "runtime" / "checkpoints").glob("**/*.json"))),
                1,
            )

    def test_provider_receives_owner_evidence_separate_from_assistant_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider(ProcessingProposal(_summary()))
            result = Step3Pipeline(
                Processor(provider), self._storage(Path(directory))
            ).run(
                _batch_with_assistant_context(),
                scope=MemoryScope("general", "general"),
            )

            request = provider.requests[0]
            self.assertEqual(
                [turn.turn_id for turn in request.owner_evidence], ["turn-1"]
            )
            self.assertEqual(
                [turn.turn_id for turn in request.assistant_context],
                ["turn-1-answer"],
            )
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [source["source_role"] for source in manifest["sources"]],
                ["owner", "assistant"],
            )

    def test_assistant_context_alone_cannot_create_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            provider = FakeProvider(ProcessingProposal(_summary()))
            assistant = _batch_with_assistant_context().turns[1]
            with self.assertRaisesRegex(ValueError, "Owner evidence"):
                Step3Pipeline(
                    Processor(provider), self._storage(Path(directory))
                ).run(
                    ConversationBatch(
                        "codex-local", "conversation-123", (assistant,)
                    ),
                    scope=MemoryScope("general", "general"),
                )

            self.assertEqual(provider.calls, 0)
            self.assertFalse((Path(directory) / "vault").exists())

    def test_manifest_allows_recovery_when_checkpoint_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = FakeProvider(ProcessingProposal(_summary()))
            def stop_after_manifest(point: str) -> None:
                if point == "after-manifest":
                    raise OSError("disk full")

            storage = self._storage(root, publication_fault=stop_after_manifest)
            pipeline = Step3Pipeline(Processor(provider), storage)
            with self.assertRaisesRegex(OSError, "disk full"):
                pipeline.run(
                    _batch(), scope=MemoryScope("general", "general")
                )

            manifests = list((root / "vault").glob("**/manifests/**/*.json"))
            self.assertEqual(len(manifests), 1)
            replay = pipeline.run(
                _batch(), scope=MemoryScope("general", "general")
            )
            self.assertEqual(replay.status, "replay")
            self.assertEqual(provider.calls, 1)

    def test_no_memory_still_publishes_manifest_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = FakeProvider(ProcessingProposal(None))
            result = Step3Pipeline(Processor(provider), self._storage(root)).run(
                _batch(), scope=MemoryScope("general", "general")
            )

            self.assertEqual(result.status, "no_memory")
            self.assertEqual(result.output_paths, ())
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "no_memory")
            self.assertEqual(manifest["outputs"], [])
            self.assertEqual(len(list((root / "runtime").glob("**/*.json"))), 1)

    def test_secret_in_semantic_output_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = FakeProvider(
                ProcessingProposal(_summary(state="Use api_key=unredacted-value."))
            )
            with self.assertRaisesRegex(ValueError, "credential-like"):
                Step3Pipeline(Processor(provider), self._storage(root)).run(
                    _batch(), scope=MemoryScope("general", "general")
                )

            self.assertFalse((root / "vault").exists())
            self.assertFalse((root / "runtime").exists())

    def test_known_turn_with_different_hash_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = FakeProvider(ProcessingProposal(_summary()))
            pipeline = Step3Pipeline(Processor(provider), self._storage(root))
            pipeline.run(_batch(), scope=MemoryScope("general", "general"))

            with self.assertRaisesRegex(ValueError, "source or segmentation conflict"):
                pipeline.run(
                    _batch(text_hash="f" * 64),
                    scope=MemoryScope("general", "general"),
                )
            self.assertEqual(provider.calls, 1)


def _sha256(path: Path | None, payload: bytes | None = None) -> str:
    import hashlib

    value = path.read_bytes() if path is not None else payload
    assert value is not None
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    unittest.main()
