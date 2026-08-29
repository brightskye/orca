from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE6_ROOT = PROJECT_ROOT / "prototype" / "integration" / "phase6"
sys.path.insert(0, str(PHASE6_ROOT))

from cairn_delta_adapter import (  # noqa: E402
    ADAPTER_VERSION,
    AdapterError,
    CheckpointError,
    ScanError,
    SourceStoreMismatch,
    content_sha256,
    load_checkpoint,
    parse_candidate_file,
    run_adapter,
)

FIXTURE_STORE = Path(__file__).parent / "fixtures" / "development" / "store"
TIME_1 = "2026-08-22T20:00:00+00:00"
TIME_2 = "2026-08-22T20:01:00+00:00"
TIME_3 = "2026-08-22T20:02:00+00:00"


def note_text(
    permalink: str,
    content: str,
    *,
    source_session: str | None = None,
    project: str = "Orca",
    extra: dict[str, str] | None = None,
) -> str:
    lines = [
        "---",
        f"title: {permalink}",
        "type: memory",
        f"permalink: {permalink}",
        "tags:",
        "- ingested",
        "- orca-candidate",
        f"source: {source_session or 'memory://session/' + permalink}",
        "harness: phase6-development",
        f"project: {project}",
        f"observed_project: {project}",
        "intent: implicit",
        "authority: candidate",
    ]
    for key, value in (extra or {}).items():
        lines.append(f"{key}: {value}")
    lines.extend(
        [
            "---",
            "",
            f"- [context] {content} #ingested #orca-candidate",
            "",
        ]
    )
    return "\n".join(lines)


class Phase6AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = self.root / "store"
        shutil.copytree(FIXTURE_STORE, self.store)
        self.checkpoint = self.root / "state" / "checkpoint.json"
        self.output_index = 0
        self.output = self.root / "results" / "delta-0.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run(self, result=None):  # type: ignore[override]
        return super().run(result)

    def adapt(self, at: str = TIME_1):
        self.output_index += 1
        self.output = self.root / "results" / f"delta-{self.output_index}.json"
        return run_adapter(
            source_root=self.store,
            checkpoint_path=self.checkpoint,
            output_path=self.output,
            store_id="phase6-development-store",
            harness="phase6-development",
            default_intent="implicit",
            generated_at=at,
        )

    def write(self, filename: str, permalink: str, content: str, **kwargs) -> Path:
        path = self.store / filename
        path.write_text(note_text(permalink, content, **kwargs), encoding="utf-8")
        return path

    def checkpoint_json(self):
        return json.loads(self.checkpoint.read_text(encoding="utf-8"))

    def test_a1_initial_scan_emits_three_added(self):
        result = self.adapt()
        self.assertEqual(result["summary"], {"added": 3, "changed": 0, "deleted": 0, "unchanged": 0})
        self.assertTrue(result["checkpoint"]["initial_discovery"])
        self.assertEqual([item["permalink"] for item in result["deltas"]], ["phase6-alpha", "phase6-beta", "phase6-gamma"])

    def test_a2_unchanged_rescan_emits_no_actionable_delta(self):
        self.adapt(TIME_1)
        result = self.adapt(TIME_2)
        self.assertEqual(result["summary"], {"added": 0, "changed": 0, "deleted": 0, "unchanged": 3})
        self.assertEqual(result["deltas"], [])

    def test_a3_added_note(self):
        self.adapt(TIME_1)
        self.write("delta.md", "phase6-delta", "Delta is newly discovered.")
        result = self.adapt(TIME_2)
        self.assertEqual(result["summary"]["added"], 1)
        self.assertEqual(result["deltas"][0]["permalink"], "phase6-delta")

    def test_a4_changed_body_preserves_identity_and_changes_revision(self):
        first = self.adapt(TIME_1)
        prior_hash = next(item for item in first["deltas"] if item["permalink"] == "phase6-alpha")["current_sha256"]
        self.write("alpha.md", "phase6-alpha", "Alpha now has a revised candidate body.")
        result = self.adapt(TIME_2)
        delta = result["deltas"][0]
        self.assertEqual((result["summary"]["changed"], delta["permalink"]), (1, "phase6-alpha"))
        self.assertEqual(delta["previous_sha256"], prior_hash)
        self.assertNotEqual(delta["current_sha256"], prior_hash)

    def test_a5_frontmatter_only_change_is_excluded_by_frozen_hash_contract(self):
        self.adapt(TIME_1)
        alpha = self.store / "alpha.md"
        original = alpha.read_text(encoding="utf-8")
        alpha.write_text(original.replace("observed_project: Orca", "observed_project: Atlas"), encoding="utf-8")
        result = self.adapt(TIME_2)
        self.assertEqual(result["summary"], {"added": 0, "changed": 0, "deleted": 0, "unchanged": 3})
        self.assertEqual(self.checkpoint_json()["entries"]["phase6-alpha"]["provenance"]["observed_project"], "Atlas")

    def test_a6_deleted_note_emits_prior_evidence_only(self):
        self.adapt(TIME_1)
        (self.store / "beta.md").unlink()
        result = self.adapt(TIME_2)
        delta = result["deltas"][0]
        self.assertEqual((result["summary"]["deleted"], delta["permalink"]), (1, "phase6-beta"))
        self.assertIsNone(delta["current_sha256"])
        self.assertNotIn("content", delta)
        self.assertIn("no canonical deletion", delta["semantics"])

    def test_a7_filename_rename_does_not_create_candidate_or_revision(self):
        self.adapt(TIME_1)
        (self.store / "alpha.md").rename(self.store / "renamed-alpha.md")
        result = self.adapt(TIME_2)
        self.assertEqual(result["summary"], {"added": 0, "changed": 0, "deleted": 0, "unchanged": 3})
        self.assertEqual(self.checkpoint_json()["entries"]["phase6-alpha"]["source_reference"], "renamed-alpha.md")

    def test_a8_multiple_simultaneous_changes(self):
        self.adapt(TIME_1)
        (self.store / "beta.md").unlink()
        self.write("alpha.md", "phase6-alpha", "Alpha changed in the combined case.")
        self.write("delta.md", "phase6-delta", "Delta was added in the combined case.")
        result = self.adapt(TIME_2)
        self.assertEqual(result["summary"], {"added": 1, "changed": 1, "deleted": 1, "unchanged": 1})
        self.assertEqual([item["permalink"] for item in result["deltas"]], ["phase6-alpha", "phase6-beta", "phase6-delta"])

    def test_a9_duplicate_permalink_fails_without_checkpoint_advancement(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        self.write("collision.md", "phase6-alpha", "Conflicting claimant.")
        with self.assertRaisesRegex(ScanError, "duplicate permalink"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_a10_missing_permalink_fails_without_checkpoint_advancement(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        (self.store / "missing.md").write_text("---\ntitle: Missing\n---\n\n- [context] Missing identity.\n", encoding="utf-8")
        with self.assertRaisesRegex(ScanError, "missing or invalid permalink"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_a11_malformed_frontmatter_fails_without_checkpoint_advancement(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        (self.store / "malformed.md").write_text("---\ntitle Malformed\npermalink: bad\n- [context] no close\n", encoding="utf-8")
        with self.assertRaisesRegex(ScanError, "missing closing frontmatter"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_a12_corrupted_checkpoint_fails_closed_without_reset(self):
        self.checkpoint.parent.mkdir(parents=True)
        corrupt = b'{"schema": "orca-cairn-checkpoint"'
        self.checkpoint.write_bytes(corrupt)
        with self.assertRaisesRegex(CheckpointError, "restore or explicitly replace"):
            self.adapt(TIME_1)
        self.assertEqual(self.checkpoint.read_bytes(), corrupt)
        self.assertFalse(self.output.exists())

    def test_a13_retry_and_idempotency(self):
        self.adapt(TIME_1)
        self.write("alpha.md", "phase6-alpha", "Alpha changed before a simulated checkpoint failure.")
        prior_checkpoint = self.checkpoint.read_bytes()

        def fail_before_replace(_temporary: Path) -> None:
            raise RuntimeError("simulated checkpoint replacement failure")

        with self.assertRaisesRegex(RuntimeError, "simulated"):
            retry_output = self.root / "results" / "retry.json"
            run_adapter(
                source_root=self.store,
                checkpoint_path=self.checkpoint,
                output_path=retry_output,
                store_id="phase6-development-store",
                harness="phase6-development",
                default_intent="implicit",
                generated_at=TIME_2,
                before_checkpoint_replace=fail_before_replace,
            )
        failed_result = retry_output.read_bytes()
        self.assertEqual(self.checkpoint.read_bytes(), prior_checkpoint)
        replay = run_adapter(
            source_root=self.store,
            checkpoint_path=self.checkpoint,
            output_path=retry_output,
            store_id="phase6-development-store",
            harness="phase6-development",
            default_intent="implicit",
            generated_at=TIME_3,
        )
        self.assertEqual(retry_output.read_bytes(), failed_result)
        self.assertEqual(replay["summary"]["changed"], 1)
        self.assertEqual(replay["generated_at"], TIME_2)
        checkpoint_after_retry = self.checkpoint_json()
        self.assertEqual(checkpoint_after_retry["completed_at"], TIME_2)
        self.assertTrue(
            all(entry["last_seen_at"] == TIME_2 for entry in checkpoint_after_retry["entries"].values())
        )
        clean = self.adapt(TIME_3)
        self.assertEqual((clean["summary"]["unchanged"], clean["deltas"]), (3, []))

    def test_a14_source_store_mismatch_refuses_mass_diff(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        with self.assertRaises(SourceStoreMismatch):
            run_adapter(
                source_root=self.store,
                checkpoint_path=self.checkpoint,
                output_path=self.output,
                store_id="unrelated-store",
                harness="phase6-development",
                default_intent="implicit",
                generated_at=TIME_2,
            )
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_a15_delta_order_is_permalink_deterministic(self):
        for path in list(self.store.glob("*.md")):
            path.unlink()
        self.write("z-last.md", "p-02", "Second permalink.")
        self.write("a-first.md", "p-03", "Third permalink.")
        self.write("m-middle.md", "p-01", "First permalink.")
        result = self.adapt(TIME_1)
        self.assertEqual([item["permalink"] for item in result["deltas"]], ["p-01", "p-02", "p-03"])

    def test_hash_contract_exact_content_and_exclusions(self):
        alpha = self.store / "alpha.md"
        first = parse_candidate_file(alpha, "alpha.md")
        self.assertEqual(first.content_sha256, hashlib.sha256(first.content.encode("utf-8")).hexdigest())
        original = alpha.read_text(encoding="utf-8")
        alpha.write_text(original.replace("project: Orca", "project: Atlas"), encoding="utf-8")
        metadata_edit = parse_candidate_file(alpha, "different-name.md")
        self.assertEqual(first.content_sha256, metadata_edit.content_sha256)
        alpha.write_text(original.replace("first deterministic", "first revised deterministic"), encoding="utf-8")
        body_edit = parse_candidate_file(alpha, "alpha.md")
        self.assertNotEqual(first.content_sha256, body_edit.content_sha256)
        self.assertEqual(content_sha256("x\n"), hashlib.sha256(b"x\n").hexdigest())
        self.assertNotEqual(content_sha256("x\n"), content_sha256("x"))

    def test_checkpoint_restart_through_two_new_cli_processes(self):
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [
            sys.executable,
            "-B",
            str(PHASE6_ROOT / "cairn_delta_adapter.py"),
            "--source-root",
            str(self.store),
            "--checkpoint",
            str(self.checkpoint),
            "--output",
            str(self.root / "results" / "process-1.json"),
            "--store-id",
            "phase6-development-store",
            "--harness",
            "phase6-development",
            "--default-intent",
            "implicit",
        ]
        first = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
        command[command.index(str(self.root / "results" / "process-1.json"))] = str(
            self.root / "results" / "process-2.json"
        )
        second = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
        self.assertEqual(json.loads(first.stdout)["added"], 3)
        self.assertEqual(json.loads(second.stdout), {"added": 0, "changed": 0, "deleted": 0, "unchanged": 3})

    def test_curator_ready_added_changed_and_deleted_shapes(self):
        initial = self.adapt(TIME_1)
        added = initial["deltas"][0]
        required = {
            "permalink",
            "content_sha256",
            "content",
            "change",
            "checkpoint_id",
            "harness",
            "intent",
            "entry_mode",
            "authority",
            "orca_state",
            "generated",
            "sources",
            "provenance",
        }
        self.assertTrue(required <= set(added))
        self.write("alpha.md", "phase6-alpha", "Alpha changed for Curator compatibility.")
        changed = self.adapt(TIME_2)["deltas"][0]
        self.assertTrue(changed["previous_sha256"] and changed["current_sha256"])
        (self.store / "alpha.md").unlink()
        deleted = self.adapt(TIME_3)["deltas"][0]
        self.assertEqual(deleted["change"], "deleted")
        self.assertNotIn("content", deleted)
        self.assertEqual(deleted["authority"], "candidate")

    def test_checkpoint_and_delta_schema_files_are_valid_json(self):
        for name in ("checkpoint.schema.json", "delta.schema.json"):
            parsed = json.loads((PHASE6_ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(parsed["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_adapter_version_mismatch_fails_closed(self):
        self.adapt(TIME_1)
        checkpoint = self.checkpoint_json()
        checkpoint["adapter"]["version"] = ADAPTER_VERSION + "-other"
        self.checkpoint.write_text(json.dumps(checkpoint), encoding="utf-8")
        with self.assertRaisesRegex(CheckpointError, "version mismatch"):
            self.adapt(TIME_2)

    def test_checkpoint_schema_mutations_fail_closed(self):
        self.adapt(TIME_1)
        baseline = self.checkpoint_json()

        def without_completed_at(value):
            value.pop("completed_at")

        def without_last_seen(value):
            value["entries"]["phase6-alpha"].pop("last_seen_at")

        def without_provenance(value):
            value["entries"]["phase6-alpha"].pop("provenance")

        def invalid_checkpoint_id(value):
            value["checkpoint_id"] = "phase6:bad"

        for index, mutate in enumerate(
            (without_completed_at, without_last_seen, without_provenance, invalid_checkpoint_id)
        ):
            with self.subTest(mutation=mutate.__name__):
                value = json.loads(json.dumps(baseline))
                mutate(value)
                path = self.root / f"mutated-{index}.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaises(CheckpointError):
                    load_checkpoint(
                        path,
                        store_id="phase6-development-store",
                        harness="phase6-development",
                        default_intent="implicit",
                    )
                self.assertEqual(path.read_bytes(), before)

    def test_ordinary_verbatim_only_note_is_invalid(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        text = note_text("verbatim-only", "placeholder").replace("[context]", "[verbatim]")
        (self.store / "verbatim-only.md").write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ScanError, "exactly one non-empty"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_malformed_nested_frontmatter_is_invalid(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        malformed = note_text("nested-bad", "Malformed nested metadata.").replace(
            "- ingested\n- orca-candidate", "  this nested line has no colon"
        )
        (self.store / "nested-bad.md").write_text(malformed, encoding="utf-8")
        with self.assertRaisesRegex(ScanError, "malformed nested frontmatter"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_result_path_is_immutable_except_identical_retry(self):
        self.adapt(TIME_1)
        output = self.output
        checkpoint_before = self.checkpoint.read_bytes()
        with self.assertRaisesRegex(AdapterError, "unique path"):
            run_adapter(
                source_root=self.store,
                checkpoint_path=self.checkpoint,
                output_path=output,
                store_id="phase6-development-store",
                harness="phase6-development",
                default_intent="implicit",
                generated_at=TIME_2,
            )
        self.assertEqual(self.checkpoint.read_bytes(), checkpoint_before)

    def test_configured_intent_fallback_preserves_source_entry_mode(self):
        result = self.adapt(TIME_1)
        gamma = next(item for item in result["deltas"] if item["permalink"] == "phase6-gamma")
        self.assertEqual(gamma["intent"], "implicit")
        self.assertEqual(gamma["entry_mode"], "reflection")

    def test_invalid_intent_fails_without_checkpoint_advancement(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        invalid = note_text("invalid-intent", "Invalid intent must fail.").replace(
            "intent: implicit", "intent: bogus"
        )
        (self.store / "invalid-intent.md").write_text(invalid, encoding="utf-8")
        with self.assertRaisesRegex(ScanError, "invalid intent"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_invalid_entry_mode_fails_without_checkpoint_advancement(self):
        self.adapt(TIME_1)
        before = self.checkpoint.read_bytes()
        self.write(
            "invalid-entry-mode.md",
            "invalid-entry-mode",
            "Invalid entry mode must fail.",
            extra={"entry_mode": "bogus"},
        )
        with self.assertRaisesRegex(ScanError, "invalid entry_mode"):
            self.adapt(TIME_2)
        self.assertEqual(self.checkpoint.read_bytes(), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
