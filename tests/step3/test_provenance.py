from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import NormalizedTurn
from orca_memory.provenance import (
    CHECKPOINT_SCHEMA,
    MANIFEST_SCHEMA,
    checkpoint_payload,
    is_exact_replay,
    processed_sources,
    unsegmented_source,
    validate_manifest,
)


def _turn() -> NormalizedTurn:
    import hashlib

    text = "Remember the publication order."
    return NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-1",
        turn_id="turn-1",
        occurred_at="2026-08-30T10:00:00Z",
        source_uri="codex://session/conversation-1/event/turn-1",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


class ProvenanceTests(unittest.TestCase):
    def test_unsegmented_source_and_checkpoint_bind_exact_cursor(self) -> None:
        source = unsegmented_source(_turn(), source_ref="src-001")
        checkpoint = json.loads(
            checkpoint_payload(
                connector_id="codex-local",
                conversation_id="conversation-1",
                source=source,
                manifest_path="System/Orca Memory/manifests/2026/08/30/run.json",
            )
        )

        self.assertEqual(source["segment"]["index"], 1)
        self.assertEqual(source["segment"]["count"], 1)
        self.assertEqual(
            source["segment"]["end_byte"], len(_turn().text.encode("utf-8"))
        )
        self.assertEqual(checkpoint["schema_version"], CHECKPOINT_SCHEMA)
        self.assertEqual(checkpoint["processed_through"]["turn_id"], "turn-1")
        self.assertTrue(checkpoint["manifest_path"].endswith("run.json"))

    def test_mixed_manifest_scan_preserves_legacy_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            root = vault / "System/Orca Memory/manifests/2026/08/30"
            root.mkdir(parents=True)
            turn = _turn()
            legacy = {
                "schema_version": "orca-run-manifest/0.1",
                "status": "no_memory",
                "connector_id": turn.connector_id,
                "conversation_id": turn.conversation_id,
                "sources": [
                    {
                        "turn_id": turn.turn_id,
                        "content_sha256": turn.content_sha256,
                        "redaction_policy": turn.redaction_policy,
                    }
                ],
            }
            (root / "legacy.json").write_text(json.dumps(legacy), encoding="utf-8")

            receipt = processed_sources(vault)[
                (turn.connector_id, turn.conversation_id, turn.turn_id)
            ]

            self.assertTrue(is_exact_replay(turn, receipt))
            self.assertEqual(receipt.representation[-1], "legacy-0.1")

            current = {
                "schema": MANIFEST_SCHEMA,
                "status": "no_memory",
                "connector_id": turn.connector_id,
                "conversation_id": turn.conversation_id,
                "sources": [unsegmented_source(turn, source_ref="src-001")],
                "operations": [],
                "outputs": [],
            }
            (root / "current.json").write_text(json.dumps(current), encoding="utf-8")
            upgraded = processed_sources(vault)[
                (turn.connector_id, turn.conversation_id, turn.turn_id)
            ]
            self.assertTrue(is_exact_replay(turn, upgraded))
            self.assertNotEqual(upgraded.representation[-1], "legacy-0.1")

    def test_manifest_02_scan_detects_exact_replay_and_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            root = vault / "System/Orca Memory/manifests/2026/08/30"
            root.mkdir(parents=True)
            turn = _turn()
            source = unsegmented_source(turn, source_ref="src-001")
            manifest = {
                "schema": MANIFEST_SCHEMA,
                "status": "no_memory",
                "connector_id": turn.connector_id,
                "conversation_id": turn.conversation_id,
                "sources": [source],
                "operations": [],
                "outputs": [],
            }
            (root / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
            receipt = processed_sources(vault)[
                (turn.connector_id, turn.conversation_id, turn.turn_id)
            ]
            self.assertTrue(is_exact_replay(turn, receipt))

            source["segment"]["content_sha256"] = "f" * 64
            (root / "conflict.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting Manifest"):
                processed_sources(vault)

    def test_manifest_rejects_broken_operation_output_join(self) -> None:
        source = unsegmented_source(_turn(), source_ref="src-001")
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "status": "success",
            "connector_id": "codex-local",
            "conversation_id": "conversation-1",
            "sources": [source],
            "operations": [
                {
                    "operation_id": "op-001",
                    "operation": "add",
                    "outcome": "created",
                    "artifact_kind": "typed-memory-record",
                    "artifact_id": "mem-a",
                    "source_refs": ["src-001"],
                    "output_refs": ["out-001"],
                    "embedded_artifact": None,
                }
            ],
            "outputs": [
                {
                    "output_ref": "out-001",
                    "artifact_kind": "typed-memory-record",
                    "artifact_id": "mem-other",
                    "effect": "created",
                    "path": "System/Orca Memory/shallow/general/decisions/a.md",
                    "before_sha256": None,
                    "after_sha256": "a" * 64,
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            validate_manifest(manifest)

    def test_manifest_scan_rejects_missing_first_segment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            root = vault / "System/Orca Memory/manifests/2026/08/30"
            root.mkdir(parents=True)
            source = unsegmented_source(_turn(), source_ref="src-001")
            source["segment"].update(
                {
                    "index": 2,
                    "count": 2,
                    "start_byte": source["segment"]["end_byte"],
                    "end_byte": source["segment"]["end_byte"] + 1,
                    "content_sha256": hashlib.sha256(b"x").hexdigest(),
                }
            )
            manifest = {
                "schema": MANIFEST_SCHEMA,
                "status": "no_memory",
                "connector_id": "codex-local",
                "conversation_id": "conversation-1",
                "sources": [source],
                "operations": [],
                "outputs": [],
            }
            (root / "run.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "missing or out-of-order"):
                processed_sources(vault)


if __name__ == "__main__":
    unittest.main()
