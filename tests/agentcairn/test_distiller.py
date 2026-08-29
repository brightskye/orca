from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from cairn.ingest import Candidate, DedupLedger, ingest_transcripts, transcript_from_messages

from orca_memory.agentcairn import AgentCairnDistillation, OrcaDecisionDistiller


def _distillation(text: str = "Remember this.") -> AgentCairnDistillation:
    return AgentCairnDistillation(
        harness="codex",
        session_id="session-123",
        source_text=text,
        permalink="orca-candidate-remember-this",
        frontmatter={
            "title": "Remember this",
            "type": "memory",
            "authority": "candidate",
            "source_event_id": "event-456",
        },
        body="- [context] Remember this. #orca-candidate\n",
    )


class OrcaDecisionDistillerTests(unittest.TestCase):
    def test_agentcairn_ingest_uses_prevalidated_orca_distillation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            distiller = OrcaDecisionDistiller([_distillation()])
            transcript = transcript_from_messages(
                [{"role": "user", "content": "Remember this."}],
                session_id="session-123",
                cwd="/workspace/projects/orca",
                source_path=root / "rollout.jsonl",
                harness="codex",
            )

            report = ingest_transcripts(
                [transcript],
                vault_root=root / "vault",
                ledger=DedupLedger(root / "dedup-ledger.txt"),
                threshold=0.0,
                judge=None,
                distiller=distiller,
                subdir="candidates",
                dry_run=False,
                consolidator=None,
                neighbor_index=None,
            )

            self.assertEqual(distiller.calls, 1)
            self.assertEqual(len(report.written), 1)
            note_text = report.written[0].read_text(encoding="utf-8")
            self.assertIn("authority: candidate", note_text)
            self.assertIn("source_event_id: event-456", note_text)
            self.assertIn("Remember this.", note_text)

    def test_unknown_candidate_fails_closed(self) -> None:
        distiller = OrcaDecisionDistiller([_distillation()])
        candidate = Candidate(
            text="Different text.",
            session_id="session-123",
            cwd=None,
            git_branch=None,
            timestamp=None,
            source_path=Path("rollout.jsonl"),
            harness="codex",
        )

        with self.assertRaisesRegex(KeyError, "no validated Orca distillation"):
            distiller.distill(candidate)

    def test_canonical_distillation_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "noncanonical authority"):
            AgentCairnDistillation(
                harness="codex",
                session_id="session-123",
                source_text="Remember this.",
                permalink="canonical-memory",
                frontmatter={"authority": "canonical"},
                body="Canonical content.\n",
            )


if __name__ == "__main__":
    unittest.main()
