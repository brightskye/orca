from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.pipeline import Step3Pipeline
from orca_memory.processor import ProcessingProposal, Processor
from orca_memory.segmentation import BudgetConfig
from orca_memory.storage import MemoryScope, Storage


class NoMemoryProvider:
    name = "fake-provider/segmented"

    def __init__(self) -> None:
        self.calls = 0
        self.requests = []

    def distill(self, request):
        self.calls += 1
        self.requests.append(request)
        return ProcessingProposal(None)


def _batch(text: str) -> ConversationBatch:
    turn = NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-segmented",
        turn_id="turn-large",
        occurred_at="2026-08-30T10:00:00Z",
        source_uri="codex://session/conversation-segmented/event/turn-large",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )
    return ConversationBatch("codex-local", "conversation-segmented", (turn,))


class SegmentedPipelineTests(unittest.TestCase):
    def test_oversized_turn_creates_sequential_manifests_and_exact_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ids = iter(("run-1", "run-2", "run-3"))
            storage = Storage(
                root / "vault",
                root / "runtime",
                clock=lambda: datetime(2026, 8, 30, 12, tzinfo=timezone.utc),
                id_factory=lambda: next(ids),
            )
            provider = NoMemoryProvider()
            pipeline = Step3Pipeline(Processor(provider), storage)
            budgets = BudgetConfig(new_evidence_tokens=4)
            batch = _batch("abcdefghij")

            results = pipeline.run_all(
                batch, scope=MemoryScope("general", "general"), budgets=budgets
            )

            self.assertEqual(len(results), 3)
            self.assertEqual(provider.calls, 3)
            manifests = sorted((root / "vault").glob("**/manifests/**/*.json"))
            receipts = [json.loads(path.read_text())["sources"][0] for path in manifests]
            receipts.sort(key=lambda source: source["segment"]["index"])
            self.assertEqual([item["segment"]["index"] for item in receipts], [1, 2, 3])
            self.assertTrue(all(item["segment"]["count"] == 3 for item in receipts))
            self.assertEqual(
                b"".join(
                    batch.turns[0].text.encode()[
                        item["segment"]["start_byte"] : item["segment"]["end_byte"]
                    ]
                    for item in receipts
                ),
                batch.turns[0].text.encode(),
            )
            checkpoint = json.loads(
                next((root / "runtime/checkpoints").glob("**/*.json")).read_text()
            )
            self.assertEqual(checkpoint["processed_through"]["segment_index"], 3)
            self.assertEqual(checkpoint["processed_through"]["segment_count"], 3)

            replay = pipeline.run_all(
                batch, scope=MemoryScope("general", "general"), budgets=budgets
            )
            self.assertTrue(all(item.status == "replay" for item in replay))
            self.assertEqual(provider.calls, 3)
            self.assertEqual(len(list((root / "vault").glob("**/manifests/**/*.json"))), 3)

    def test_segmentation_parameter_change_requires_governed_reprocessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ids = iter(("run-1", "run-2"))
            provider = NoMemoryProvider()
            pipeline = Step3Pipeline(
                Processor(provider),
                Storage(
                    root / "vault",
                    root / "runtime",
                    clock=lambda: datetime(2026, 8, 30, 12, tzinfo=timezone.utc),
                    id_factory=lambda: next(ids),
                ),
            )
            batch = _batch("abcdefgh")
            pipeline.run_all(
                batch,
                scope=MemoryScope("general", "general"),
                budgets=BudgetConfig(new_evidence_tokens=4),
            )

            with self.assertRaisesRegex(ValueError, "segmentation conflict"):
                pipeline.run_all(
                    batch,
                    scope=MemoryScope("general", "general"),
                    budgets=BudgetConfig(new_evidence_tokens=5),
                )
            self.assertEqual(provider.calls, 2)


if __name__ == "__main__":
    unittest.main()
