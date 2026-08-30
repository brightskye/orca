from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from orca_memory.publication import (
    PlannedOutput,
    PublicationPlan,
    PublicationRepairRequired,
    RecoverablePublisher,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _plan(*, before: bytes | None = None, after: bytes = b"after\n") -> PublicationPlan:
    manifest = b'{"schema":"orca-run-manifest/0.2"}\n'
    checkpoint = b'{"schema_version":"orca-checkpoint/0.2"}\n'
    return PublicationPlan(
        run_id="run_test",
        manifest_path="System/Orca Memory/manifests/2026/08/30/run_test.json",
        manifest_payload=manifest,
        checkpoint_path="checkpoints/codex-local/conversation.json",
        checkpoint_payload=checkpoint,
        outputs=(
            PlannedOutput(
                output_ref="out-001",
                artifact_kind="typed-memory-record",
                artifact_id="mem_test",
                effect="created" if before is None else "replaced",
                path="System/Orca Memory/shallow/general/decisions/test.md",
                before_sha256=None if before is None else _sha(before),
                after_sha256=_sha(after),
                payload=after,
            ),
        ),
    )


class PublicationTests(unittest.TestCase):
    def test_intent_precedes_artifact_manifest_and_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            publisher = RecoverablePublisher(root / "vault", root / "runtime")
            observed: list[str] = []

            def inspect(point: str) -> None:
                observed.append(point)
                target = root / "vault/System/Orca Memory/shallow/general/decisions/test.md"
                manifest = root / "vault/System/Orca Memory/manifests/2026/08/30/run_test.json"
                checkpoint = root / "runtime/checkpoints/codex-local/conversation.json"
                if point == "after-intent":
                    self.assertFalse(target.exists())
                elif point == "after-output:out-001":
                    self.assertTrue(target.exists())
                    self.assertFalse(manifest.exists())
                elif point == "after-manifest":
                    self.assertTrue(manifest.exists())
                    self.assertFalse(checkpoint.exists())

            manifest_path = publisher.publish(_plan(), fault=inspect)

            self.assertTrue(manifest_path.exists())
            self.assertTrue(
                (root / "runtime/checkpoints/codex-local/conversation.json").exists()
            )
            self.assertEqual(publisher.pending_intents(), ())
            self.assertEqual(
                observed,
                [
                    "after-intent",
                    "after-output:out-001",
                    "after-manifest",
                    "after-checkpoint",
                    "before-cleanup",
                ],
            )

    def test_interruption_recovers_fixed_after_image_without_semantic_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            publisher = RecoverablePublisher(root / "vault", root / "runtime")

            def stop(point: str) -> None:
                if point == "after-output:out-001":
                    raise OSError("simulated stop")

            with self.assertRaisesRegex(OSError, "simulated stop"):
                publisher.publish(_plan(), fault=stop)

            intent = publisher.pending_intents()[0]
            manifest = publisher.recover(intent)

            self.assertTrue(manifest.exists())
            self.assertEqual(publisher.pending_intents(), ())
            self.assertEqual(
                (root / "vault/System/Orca Memory/shallow/general/decisions/test.md").read_bytes(),
                b"after\n",
            )

    def test_manifest_checkpoint_and_cleanup_interruptions_are_idempotent(self) -> None:
        for stop_point in ("after-manifest", "after-checkpoint", "before-cleanup"):
            with self.subTest(stop_point=stop_point), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                publisher = RecoverablePublisher(root / "vault", root / "runtime")

                def stop(point: str) -> None:
                    if point == stop_point:
                        raise OSError("simulated stop")

                with self.assertRaisesRegex(OSError, "simulated stop"):
                    publisher.publish(_plan(), fault=stop)
                publisher.recover(publisher.pending_intents()[0])
                self.assertEqual(publisher.pending_intents(), ())

    def test_target_matching_neither_before_nor_after_requires_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "vault/System/Orca Memory/shallow/general/decisions/test.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"before\n")
            publisher = RecoverablePublisher(root / "vault", root / "runtime")

            def stop(point: str) -> None:
                if point == "after-intent":
                    raise OSError("simulated stop")

            with self.assertRaises(OSError):
                publisher.publish(_plan(before=b"before\n"), fault=stop)
            target.write_bytes(b"unrelated\n")

            with self.assertRaisesRegex(PublicationRepairRequired, "mem_test"):
                publisher.recover(publisher.pending_intents()[0])

            self.assertEqual(target.read_bytes(), b"unrelated\n")
            self.assertEqual(len(publisher.pending_intents()), 1)

    def test_paths_cannot_escape_configured_roots(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsafe publication path"):
            PlannedOutput(
                output_ref="out-001",
                artifact_kind="typed-memory-record",
                artifact_id="mem_test",
                effect="created",
                path="../outside.md",
                before_sha256=None,
                after_sha256=_sha(b"after"),
                payload=b"after",
            )


if __name__ == "__main__":
    unittest.main()
