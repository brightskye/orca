"""Fresh-vault scaffold boundaries and release-resource checks."""

import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.scaffold_vault import scaffold


_RESOURCES = {
    "AGENTS.md": b"Read [rules](System/rules.md).\n",
    "index.md": b"# Vault\n[System](System/)\n",
    "System/index.md": b"# System\n[rules](rules.md)\n",
    "System/configuration.md": b"# Configuration\n",
    "System/rules.md": b"# Rules\nThis starter is tentative.\n",
    "System/workflows.md": b"# Workflows\nReview intake before curation.\n",
}
_POLICY = (Path(__file__).parents[2] / "config/orca-memory.example.yaml").read_bytes()
_WHEEL_NAME = "orca_memory-0.1.0-py3-none-any.whl"


def _wheel(resources=None, *, extra=(), symlink=None):
    resources = _RESOURCES if resources is None else resources
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("orca_memory/__init__.py", b"")
        archive.writestr("orca_memory/vault_template/", b"")
        archive.writestr("orca_memory/vault_template/System/", b"")
        for relative, content in resources.items():
            archive.writestr(f"orca_memory/vault_template/{relative}", content)
        for relative, content in extra:
            archive.writestr(f"orca_memory/vault_template/{relative}", content)
        if symlink is not None:
            relative, content = symlink
            info = zipfile.ZipInfo(f"orca_memory/vault_template/{relative}")
            info.create_system = 3
            info.external_attr = 0o120000 << 16
            archive.writestr(info, content)
    return output.getvalue()


def _bundle(root, *, resources=None, policy=_POLICY, script=False, wheel=None, name="bundle"):
    bundle = root / name
    bundle.mkdir(parents=True)
    files = {
        _WHEEL_NAME: _wheel(resources) if wheel is None else wheel,
        "orca-memory.example.yaml": policy,
    }
    if script:
        files["install.py"] = (
            Path(__file__).parents[2] / "tools/install_release.py"
        ).read_bytes()
        files["scaffold_vault.py"] = (
            Path(__file__).parents[2] / "tools/scaffold_vault.py"
        ).read_bytes()
    for name, content in files.items():
        (bundle / name).write_bytes(content)
    manifest = {
        "version": "0.1.0",
        "wheel": _WHEEL_NAME,
        "files": {
            name: hashlib.sha256(content).hexdigest()
            for name, content in files.items()
        },
    }
    (bundle / "release.json").write_text(json.dumps(manifest), encoding="utf-8")
    return bundle


class VaultScaffoldTests(unittest.TestCase):
    def test_authored_templates_use_relative_links_and_tentative_rules(self):
        template_root = Path(__file__).parents[2] / "src/orca_memory/vault_template"
        for path in template_root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\]\(/|\b[A-Za-z]:[\\/]")
        self.assertIn("System/rules.md", (template_root / "AGENTS.md").read_text())
        self.assertIn("tentative", (template_root / "System/rules.md").read_text())

    def test_fresh_scaffold_has_portable_layout_and_disabled_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            destination = root / "vault"

            created = scaffold(bundle, destination)

            self.assertEqual(created, destination)
            for relative in (
                "Knowledge",
                "Projects",
                "People",
                "Daily",
                "System/Context",
                "System/Orca Memory",
                "Inbox/Raw",
                "Inbox/Notes",
                "Archive",
            ):
                self.assertTrue((destination / relative).is_dir(), relative)
            for relative, content in _RESOURCES.items():
                self.assertEqual((destination / relative).read_bytes(), content)
            self.assertEqual(
                (destination / "System/Orca Memory/orca-memory.yaml").read_bytes(),
                _POLICY,
            )
            text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in destination.rglob("*.md")
            )
            self.assertNotRegex(text, r"\]\(/|\b[A-Za-z]:[\\/]")
            self.assertIn(
                "enabled: false",
                (destination / "System/Orca Memory/orca-memory.yaml").read_text(),
            )

    def test_existing_vault_is_rejected_without_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            destination = root / "existing"
            destination.mkdir()
            marker = destination / "keep.md"
            marker.write_text("owner content", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "new directory"):
                scaffold(bundle, destination)

            self.assertEqual(marker.read_text(encoding="utf-8"), "owner content")
            self.assertEqual(sorted(path.name for path in destination.iterdir()), ["keep.md"])

    def test_existing_file_symlink_and_unsafe_parents_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            existing_file = root / "file"
            existing_file.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "new directory"):
                scaffold(bundle, existing_file)
            self.assertEqual(existing_file.read_text(encoding="utf-8"), "keep")

            target = root / "target"
            target.mkdir()
            linked = root / "linked-vault"
            linked.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "new directory"):
                scaffold(bundle, linked)
            self.assertEqual(list(target.iterdir()), [])

            parent_target = root / "parent-target"
            parent_target.mkdir()
            parent_link = root / "parent-link"
            parent_link.symlink_to(parent_target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink parent"):
                scaffold(bundle, parent_link / "vault")
            self.assertEqual(list(parent_target.iterdir()), [])

    def test_git_checkout_and_bundle_targets_are_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            checkout = root / "checkout"
            (checkout / ".git").mkdir(parents=True)
            (checkout / ".git/HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Git checkout"):
                scaffold(bundle, checkout / "vault")
            self.assertFalse((checkout / "vault").exists())

            with self.assertRaisesRegex(ValueError, "release program"):
                scaffold(bundle, bundle / "vault")
            self.assertFalse((bundle / "vault").exists())

    def test_retained_package_rejects_program_runtime_and_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = root / "program"
            (program / "env").mkdir(parents=True)
            (program / "hooks.json").write_text("{}", encoding="utf-8")
            bundle = _bundle(program, name="package")

            for relative in ("runtime/vault", "skills/vault"):
                with self.subTest(relative=relative), self.assertRaisesRegex(
                    ValueError, "release program/runtime"
                ):
                    scaffold(bundle, program / relative)
                self.assertFalse((program / relative).exists())

    def test_invalid_resources_and_enabled_policy_fail_before_target_creation(self):
        cases = (
            ("traversal", _wheel(extra=(("../outside.md", b"escape"),)), _POLICY,
             "invalid vault-template path"),
            ("drive", _wheel(extra=(("C:/outside.md", b"escape"),)), _POLICY,
             "invalid vault-template path"),
            ("symlink", _wheel(symlink=("link.md", b"target")), _POLICY, "symlink"),
        )
        for name, wheel, policy, message in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = _bundle(root, policy=policy, wheel=wheel)
                destination = root / "vault"
                with self.assertRaisesRegex(ValueError, message):
                    scaffold(bundle, destination)
                self.assertFalse(destination.exists())

    def test_bundle_hash_mismatch_fails_before_target_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            (bundle / "orca-memory.example.yaml").write_bytes(b"lifecycle:\n  enabled: true\n")
            destination = root / "vault"

            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                scaffold(bundle, destination)

            self.assertFalse(destination.exists())

    def test_copied_script_runs_from_installed_bundle_without_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root, script=True)
            destination = root / "vault"
            script = bundle / "scaffold_vault.py"

            result = subprocess.run(
                [sys.executable, str(script), "--vault-path", str(destination)],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(str(destination), result.stdout)
            self.assertEqual(
                (destination / "System/Orca Memory/orca-memory.yaml").read_bytes(),
                _POLICY,
            )


if __name__ == "__main__":
    unittest.main()
