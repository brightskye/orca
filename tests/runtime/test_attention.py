from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from orca_memory.attention import (
    AttentionItem,
    collect_attention,
    rebuild_status,
    session_reminder,
)
from orca_memory.candidates import KnowledgeCandidate
from orca_memory.memory import MemoryRecord, record_relative_path, render_record
from orca_memory.retrieval import discover_projection_sources, rebuild_projection_index


NOW = "2026-08-30T10:00:00Z"


class AttentionTests(unittest.TestCase):
    def test_collects_pending_candidate_and_unassigned_without_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            runtime = root / "runtime"
            candidate = KnowledgeCandidate(
                "cand_001", "fact", "Private candidate subject", "noncanonical",
                "general", "general", "pending", None, NOW, NOW,
                "Private candidate proposal.",
            )
            candidate_path = vault / "System/Orca Memory/candidates/knowledge/general/candidate.md"
            candidate_path.parent.mkdir(parents=True)
            candidate_path.write_text(candidate.render(), encoding="utf-8")
            record = MemoryRecord(
                "mem_001", "knowledge", "Private memory subject", "unassigned", "unassigned",
                "current", None, NOW, NOW, current="Private memory body.",
            )
            record_path = vault / record_relative_path(record)
            record_path.parent.mkdir(parents=True)
            record_path.write_text(render_record(record), encoding="utf-8")

            status = collect_attention(vault, runtime)

            self.assertEqual(len(status.items), 3)
            rendered = status.render()
            self.assertIn("cand_001", rendered)
            self.assertIn("mem_001", rendered)
            self.assertIn("retrieval-index", rendered)
            self.assertNotIn("Private", rendered)

    def test_missing_and_stale_retrieval_index_is_content_free_action_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            runtime = root / "runtime"
            record = MemoryRecord(
                "mem_002", "knowledge", "Runtime status", "general", "general",
                "current", None, NOW, NOW, current="Original private body.",
            )
            path = vault / record_relative_path(record)
            path.parent.mkdir(parents=True)
            path.write_text(render_record(record), encoding="utf-8")

            missing = collect_attention(vault, runtime)
            self.assertEqual(
                [(item.item_class, item.severity, item.workflow, item.locator) for item in missing.items],
                [("stale-derived-state", "action-required", "retrieval-rebuild", "retrieval-index")],
            )
            self.assertNotIn("Original private body", missing.render())

            rebuild_projection_index(
                discover_projection_sources(vault), runtime_root=runtime
            )
            self.assertFalse(
                any(item.item_class == "stale-derived-state" for item in collect_attention(vault, runtime).items)
            )

            path.write_text(
                render_record(record).replace("Original private body.", "Changed private body."),
                encoding="utf-8",
            )
            stale = collect_attention(vault, runtime)
            self.assertEqual(
                [item for item in stale.items if item.item_class == "stale-derived-state"][0].severity,
                "action-required",
            )
            self.assertNotIn("Changed private body", stale.render())

    def test_rebuild_is_deterministic_and_projection_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = AttentionItem(
                "configuration", "urgent", "configuration-repair", "host-config",
                NOW, NOW,
            )
            first = rebuild_status(root / "vault", root / "runtime", additional=(item,))
            path = root / "runtime/status/orca-status.json"
            payload = path.read_bytes()
            path.unlink()
            second = rebuild_status(root / "vault", root / "runtime", additional=(item,))
            self.assertEqual(first, second)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_reminder_is_counts_only_and_once_per_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = collect_attention(
                root / "vault",
                root / "runtime",
                additional=(
                    AttentionItem("configuration", "urgent", "repair", "safe", NOW, NOW),
                    AttentionItem("knowledge-review", "review", "review", "cand_001", NOW, NOW),
                ),
            )
            first = session_reminder(status, runtime_root=root / "runtime", session_id="s1")
            self.assertEqual(
                first,
                "Orca needs attention: 1 urgent, 1 review. Run Orca Status.",
            )
            self.assertIsNone(
                session_reminder(status, runtime_root=root / "runtime", session_id="s1")
            )
            self.assertIsNotNone(
                session_reminder(status, runtime_root=root / "runtime", session_id="s2")
            )

    def test_stuck_intent_and_malformed_artifact_stay_content_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "vault/System/Orca Memory/shallow/general/knowledge/private-title.md"
            bad.parent.mkdir(parents=True)
            bad.write_text("private body that cannot parse", encoding="utf-8")
            intent = root / "runtime/publications/run-safe/intent.json"
            intent.parent.mkdir(parents=True)
            intent.write_text("{}", encoding="utf-8")
            status = collect_attention(root / "vault", root / "runtime")
            rendered = status.render()
            self.assertEqual(len(status.items), 3)
            self.assertIn("run-safe", rendered)
            self.assertIn("retrieval-index", rendered)
            self.assertNotIn("private-title", rendered)
            self.assertNotIn("private body", rendered)


if __name__ == "__main__":
    unittest.main()
