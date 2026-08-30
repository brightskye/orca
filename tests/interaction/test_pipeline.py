from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.interaction import (
    InteractionScope,
    ObservationProposal,
    rebuild_profiles,
    select_guidance,
)
from orca_memory.pipeline import Step3Pipeline
from orca_memory.processor import ProcessingProposal, Processor
from orca_memory.storage import MemoryScope, Storage


class _Provider:
    name = "interaction-test-provider/1"

    def __init__(self, proposal: ProcessingProposal) -> None:
        self.proposal = proposal
        self.calls = 0

    def distill(self, request):
        self.calls += 1
        return self.proposal


def _turn(turn_id: str, role: str, text: str, minute: int) -> NormalizedTurn:
    return NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-interaction",
        turn_id=turn_id,
        occurred_at=f"2026-08-30T10:{minute:02d}:00Z",
        source_uri=f"codex://session/conversation-interaction/event/{turn_id}",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        source_role=role,
    )


def _batch() -> ConversationBatch:
    return ConversationBatch(
        "codex-local",
        "conversation-interaction",
        (
            _turn("request", "owner", "Give me a status update.", 0),
            _turn("response", "assistant", "A deliberately long response.", 1),
            _turn("feedback", "owner", "Keep status updates concise from now on.", 2),
        ),
    )


def _proposal(*, evaluated: str = "response") -> ObservationProposal:
    return ObservationProposal(
        dimension="detail",
        value="concise",
        direction=None,
        context="status-update",
        scope=InteractionScope("agent", agent_id="codex"),
        evidence_class="explicit-general",
        feedback_turn_id="feedback",
        evaluated_assistant_turn_ids=(evaluated,),
        preceding_request_turn_id="request",
        lasting=True,
    )


class InteractionPipelineTests(unittest.TestCase):
    def _storage(self, root: Path) -> Storage:
        return Storage(
            root / "vault",
            root / "runtime",
            clock=lambda: datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
            id_factory=lambda: "interaction-run",
        )

    def test_observation_manifest_profile_guidance_replay_and_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = _Provider(
                ProcessingProposal(None, observation_proposals=(_proposal(),))
            )
            pipeline = Step3Pipeline(Processor(provider), self._storage(root))

            result = pipeline.run(
                _batch(), scope=MemoryScope("general", "general")
            )

            self.assertEqual(result.status, "success")
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            operation = manifest["operations"][0]
            self.assertEqual(operation["operation"], "observation")
            self.assertEqual(operation["outcome"], "observed")
            self.assertEqual(
                {source["turn_id"] for source in manifest["sources"] if source["source_ref"] in operation["source_refs"]},
                {"request", "response", "feedback"},
            )
            self.assertEqual(operation["output_refs"], [])
            serialized = json.dumps(manifest, sort_keys=True)
            self.assertNotIn("deliberately long", serialized)
            self.assertNotIn("concise from now", serialized)

            expected = (
                "For status updates, keep the response concise and omit "
                "nonessential background."
            )
            self.assertEqual(
                select_guidance(
                    root / "vault", context="status-update", agent_id="codex"
                ),
                expected,
            )
            profile_path = next(
                (root / "vault/System/Orca Memory/interaction/profiles").glob("**/*.yaml")
            )
            original_profile = profile_path.read_bytes()
            self.assertNotIn(b"deliberately long", original_profile)
            profile_path.unlink()
            rebuilt = rebuild_profiles(
                root / "vault", as_of="2026-08-30T12:00:00Z"
            )
            self.assertEqual(rebuilt, (profile_path,))
            self.assertEqual(profile_path.read_bytes(), original_profile)

            replay = pipeline.run(
                _batch(), scope=MemoryScope("general", "general")
            )
            self.assertEqual(replay.status, "replay")
            self.assertEqual(provider.calls, 1)

    def test_plausible_incomplete_signal_records_content_free_abstention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = _Provider(
                ProcessingProposal(
                    None, observation_proposals=(_proposal(evaluated="missing"),)
                )
            )
            result = Step3Pipeline(Processor(provider), self._storage(root)).run(
                _batch(), scope=MemoryScope("general", "general")
            )

            self.assertEqual(result.status, "no_memory")
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["operations"], [])
            self.assertEqual(
                manifest["interaction_abstentions"][0]["abstention_reason"],
                "missing-evaluated-response",
            )
            self.assertEqual(
                set(manifest["interaction_abstentions"][0]),
                {
                    "schema_version",
                    "observation_id",
                    "disposition",
                    "policy_version",
                    "abstention_reason",
                },
            )
            self.assertFalse(
                (root / "vault/System/Orca Memory/interaction/profiles").exists()
            )


if __name__ == "__main__":
    unittest.main()
