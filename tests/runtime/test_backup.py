from __future__ import annotations

import hashlib
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from orca_memory.backup import (
    BackupBlockedError,
    BackupError,
    BackupIntegrityError,
    create_backup,
    decrypt_backup_to_staging,
    verify_backup,
)
from orca_memory.runtime import SCOPE_CHOICE_SCHEMA, SOURCE_CURSOR_SCHEMA
from orca_memory.cli import main


class _FakeGpg:
    """Copy the tar payload to simulate gpg without requiring a keyring."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess:
        self.commands.append(command)
        output = Path(command[command.index("--output") + 1])
        source = Path(command[-1])
        shutil.copyfile(source, output)
        os.chmod(output, 0o600)
        return subprocess.CompletedProcess(command, 0)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


class BackupTests(unittest.TestCase):
    def test_cli_recovers_without_loading_missing_or_invalid_host_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            fake = _FakeGpg()
            created = create_backup(
                vault, runtime, recipient="test@example.invalid",
                output_path=output, command_runner=fake,
            )
            invalid = root / "invalid.yaml"
            invalid.write_text("not: [valid YAML", encoding="utf-8")
            for host in (root / "missing.yaml", invalid):
                def run(command: list[str], **kwargs):
                    if command[:1] == ["git"]:
                        return subprocess.CompletedProcess(command, 1, "", "")
                    return fake(command)

                with (
                    self.subTest(host=host.name),
                    patch("orca_memory.cli.load_configuration", side_effect=AssertionError("loaded live config")),
                    patch("orca_memory.backup.subprocess.run", side_effect=run),
                ):
                    result = io.StringIO()
                    with redirect_stdout(result):
                        self.assertEqual(main([
                            "--host-config", str(host), "backup", "verify", "--source", str(output),
                        ]), 0)
                    self.assertEqual(json.loads(result.getvalue())["manifest_sha256"], created.manifest_sha256)
                    staging = root / (host.stem + "-staging")
                    result = io.StringIO()
                    with redirect_stdout(result):
                        self.assertEqual(main([
                            "--host-config", str(host), "backup", "stage", "--standalone",
                            "--source", str(output), "--destination", str(staging),
                        ]), 0)
                    self.assertFalse(json.loads(result.getvalue())["live_state_changed"])
                    self.assertEqual(
                        (staging / "vault/System/Orca Memory/memory.md").read_bytes(),
                        (vault / "System/Orca Memory/memory.md").read_bytes(),
                    )
                    with self.assertRaisesRegex(BackupError, "must not already exist"):
                        main([
                            "--host-config", str(host), "backup", "stage", "--standalone",
                            "--source", str(output), "--destination", str(staging),
                        ])

    def _roots(self, root: Path) -> tuple[Path, Path, Path]:
        vault = root / "vault"
        runtime = root / "runtime"
        output = root / "backups" / "orca.tar.gpg"
        vault.mkdir()
        runtime.mkdir()
        (vault / "System/Orca Memory").mkdir(parents=True)
        (vault / "System/Orca Memory/memory.md").write_text(
            "Private memory", encoding="utf-8"
        )
        return vault, runtime, output

    def _state(self, runtime: Path) -> None:
        _write_json(
            runtime / "source-cursors/cursor.json",
            {
                "schema": SOURCE_CURSOR_SCHEMA,
                "connector_id": "codex-local",
                "conversation_id": "conversation-1",
                "source_path": "/private/rollouts/conversation-1.jsonl",
                "processed_through": 42,
            },
        )
        _write_json(
            runtime / "scope-choices/conversation-1.json",
            {
                "schema": SCOPE_CHOICE_SCHEMA,
                "conversation_id": "conversation-1",
                "scope_kind": "general",
            },
        )

    def test_round_trip_contains_only_vault_and_essential_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            self._state(runtime)
            # These are deliberately populated: they must remain outside the
            # backup even when the runtime is otherwise settled.
            _write_json(runtime / "retrieval/index.json", {"disposable": True})
            _write_json(runtime / "status/orca-status.json", {"disposable": True})
            _write_json(runtime / "receipts/old.json", {"disposable": True})
            (runtime / "locks").mkdir(mode=0o700)
            (runtime / "locks/processor.lock").write_bytes(b"")
            host = root / "host.yaml"
            host.write_text("vault_path: private\n", encoding="utf-8")
            rollout = root / "rollout.jsonl"
            rollout.write_text("raw conversation", encoding="utf-8")
            fake = _FakeGpg()

            created = create_backup(
                vault,
                runtime,
                recipient="owner@example.invalid",
                output_path=output,
                command_runner=fake,
            )

            self.assertEqual(created.output_path, output)
            self.assertEqual(created.member_count, 3)
            self.assertGreater(created.total_bytes, len("Private memory"))
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(fake.commands[0][fake.commands[0].index("--recipient") + 1], "owner@example.invalid")
            self.assertIn("--encrypt", fake.commands[0])

            with tarfile.open(output, mode="r:") as archive:
                names = {member.name for member in archive.getmembers()}
                self.assertIn("manifest.json", names)
                self.assertIn("vault/System/Orca Memory/memory.md", names)
                self.assertIn("runtime/source-cursors/cursor.json", names)
                self.assertIn("runtime/scope-choices/conversation-1.json", names)
                self.assertNotIn("runtime/retrieval/index.json", names)
                self.assertNotIn("runtime/status/orca-status.json", names)
                self.assertNotIn("runtime/receipts/old.json", names)
                self.assertNotIn("host.yaml", names)
                self.assertNotIn("rollout.jsonl", names)
                manifest = json.loads(archive.extractfile("manifest.json").read())
                self.assertEqual(manifest["schema"], "orca-backup/0.1")
                self.assertEqual(
                    [entry["path"] for entry in manifest["members"]],
                    sorted(entry["path"] for entry in manifest["members"]),
                )
                memory_entry = next(
                    item for item in manifest["members"] if item["path"].endswith("memory.md")
                )
                self.assertEqual(memory_entry["sha256"], hashlib.sha256(b"Private memory").hexdigest())

            verified = verify_backup(output, command_runner=fake)
            self.assertEqual(verified.member_count, created.member_count)
            self.assertEqual(verified.total_bytes, created.total_bytes)
            self.assertEqual(verified.manifest_sha256, created.manifest_sha256)
            staging = decrypt_backup_to_staging(output, command_runner=fake)
            try:
                self.assertEqual(
                    (staging / "vault/System/Orca Memory/memory.md").read_text(),
                    "Private memory",
                )
                self.assertEqual(
                    (staging / "runtime/scope-choices/conversation-1.json").read_text().strip(),
                    json.dumps(
                        {
                            "schema": SCOPE_CHOICE_SCHEMA,
                            "conversation_id": "conversation-1",
                            "scope_kind": "general",
                        },
                    ),
                )
                self.assertEqual((staging / "vault/System/Orca Memory/memory.md").stat().st_mode & 0o777, 0o600)
            finally:
                shutil.rmtree(staging)

    def test_pending_runtime_work_blocks_backup(self) -> None:
        for pending_root in (
            "queue",
            "retry-spool",
            "publications",
            "project-mappings",
            "owner-review",
            "owner-reviews",
        ):
            with self.subTest(pending_root=pending_root), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                vault, runtime, output = self._roots(root)
                pending = runtime / pending_root / "pending.json"
                _write_json(pending, {"pending": True})
                with self.assertRaisesRegex(BackupBlockedError, pending_root):
                    create_backup(
                        vault,
                        runtime,
                        recipient="owner@example.invalid",
                        output_path=output,
                        command_runner=_FakeGpg(),
                    )
                self.assertFalse(output.exists())

    def test_empty_orphan_operation_directory_blocks_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            (runtime / "owner-reviews/review-orphan").mkdir(parents=True)

            with self.assertRaisesRegex(BackupBlockedError, "owner-reviews"):
                create_backup(
                    vault,
                    runtime,
                    recipient="owner@example.invalid",
                    output_path=output,
                    command_runner=_FakeGpg(),
                )

    def test_rejects_invalid_or_non_content_free_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            _write_json(runtime / "source-cursors/not-a-cursor.json", {"conversation": "secret"})
            with self.assertRaisesRegex(BackupError, "source cursor"):
                create_backup(
                    vault,
                    runtime,
                    recipient="owner@example.invalid",
                    output_path=output,
                    command_runner=_FakeGpg(),
                )

    def test_rejects_symlink_and_special_source_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            os.symlink(outside, vault / "escape.txt")
            with self.assertRaisesRegex(BackupError, "symlink"):
                create_backup(
                    vault,
                    runtime,
                    recipient="owner@example.invalid",
                    output_path=output,
                    command_runner=_FakeGpg(),
                )

    def test_output_recipient_and_staging_boundaries_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            fake = _FakeGpg()
            with self.assertRaisesRegex(BackupError, "recipient"):
                create_backup(vault, runtime, recipient="", output_path=output, command_runner=fake)
            with self.assertRaisesRegex(BackupError, "outside"):
                create_backup(
                    vault,
                    runtime,
                    recipient="owner@example.invalid",
                    output_path=vault / "backup.gpg",
                    command_runner=fake,
                )
            created = create_backup(
                vault,
                runtime,
                recipient="owner@example.invalid",
                output_path=output,
                command_runner=fake,
            )
            self.assertIsNotNone(created)
            with self.assertRaisesRegex(BackupError, "must not already exist"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=runtime,
                    command_runner=fake,
                )
            with self.assertRaisesRegex(BackupError, "outside"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=runtime / "new-restore",
                    vault_root=vault,
                    runtime_root=runtime,
                    command_runner=fake,
                )

    def test_staging_rejects_configured_and_detected_worktree_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            fake = _FakeGpg()
            create_backup(
                vault,
                runtime,
                recipient="owner@example.invalid",
                output_path=output,
                command_runner=fake,
            )

            project = root / "project"
            project.mkdir()
            with self.assertRaisesRegex(BackupError, "outside protected roots"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=project / "nested-restore",
                    project_roots=(project,),
                    command_runner=fake,
                )

            project_link = root / "project-link"
            project_link.symlink_to(project, target_is_directory=True)
            with self.assertRaisesRegex(BackupError, "outside protected roots"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=project_link / "symlinked-restore",
                    project_roots=(project,),
                    command_runner=fake,
                )

            git_root = root / "git-root"
            subprocess.run(
                ["git", "init", "--quiet", str(git_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            with self.assertRaisesRegex(BackupError, "outside protected roots"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=git_root / "git-restore",
                    command_runner=fake,
                )

            with patch("orca_memory.backup.tempfile.tempdir", str(git_root)):
                with self.assertRaisesRegex(
                    BackupError, "temporary backup workspace overlaps a Git worktree"
                ):
                    create_backup(
                        vault,
                        runtime,
                        recipient="owner@example.invalid",
                        output_path=root / "second-backup.gpg",
                        command_runner=fake,
                    )

            empty_marker_root = root / "empty-marker-root"
            (empty_marker_root / ".git").mkdir(parents=True)
            staged = decrypt_backup_to_staging(
                output,
                staging_path=empty_marker_root / "restore",
                command_runner=fake,
            )
            shutil.rmtree(staged)

            partial_marker_root = root / "partial-marker-root"
            (partial_marker_root / ".git").mkdir(parents=True)
            (partial_marker_root / ".git" / "HEAD").write_text(
                "ref: refs/heads/main\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(BackupError, "ambiguous Git worktree marker"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=partial_marker_root / "restore",
                    command_runner=fake,
                )

            linked_root = root / "linked-root"
            linked_root.mkdir()
            linked_gitdir = root / "linked-gitdir"
            linked_gitdir.mkdir()
            (linked_root / ".git").write_text(
                f"gitdir: {linked_gitdir}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(BackupError, "outside protected roots"):
                decrypt_backup_to_staging(
                    output,
                    staging_path=linked_root / "restore",
                    command_runner=fake,
                )

            with patch("orca_memory.backup.tempfile.tempdir", str(git_root)):
                with self.assertRaisesRegex(
                    BackupError, "temporary verification workspace overlaps a Git worktree"
                ):
                    decrypt_backup_to_staging(output, command_runner=fake)

    def test_tampered_payload_fails_before_staging_is_exposed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault, runtime, output = self._roots(root)
            fake = _FakeGpg()
            create_backup(
                vault,
                runtime,
                recipient="owner@example.invalid",
                output_path=output,
                command_runner=fake,
            )
            output.write_bytes(b"tampered")
            os.chmod(output, 0o600)
            with self.assertRaises(BackupIntegrityError):
                verify_backup(output, command_runner=fake)
            staging = root / "staging"
            with self.assertRaises(BackupIntegrityError):
                decrypt_backup_to_staging(output, staging_path=staging, command_runner=fake)
            self.assertFalse(staging.exists())


if __name__ == "__main__":
    unittest.main()
