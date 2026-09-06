"""Release installer boundaries; real installed-package checks run separately."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from tools.install_release import install, verify_bundle


_SKILL_FILES = {
    "orca-conversation": {
        "SKILL.md": b"synthetic conversation skill from packaged wheel\n",
        "agents/openai.yaml": b"interface:\n  display_name: Synthetic Conversation\n",
    },
    "orca-wiki": {
        "SKILL.md": b"synthetic wiki skill from packaged wheel\n",
        "agents/openai.yaml": b"interface:\n  display_name: Synthetic Wiki\n",
    },
}


def _wheel(skills):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("orca_memory/__init__.py", b"")
        archive.writestr(
            "orca_memory-0.1.0.dist-info/METADATA",
            b"Metadata-Version: 2.1\nName: orca-memory\nVersion: 0.1.0\n",
        )
        archive.writestr(
            "orca_memory-0.1.0.dist-info/WHEEL",
            b"Wheel-Version: 1.0\nGenerator: synthetic\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        for skill_name in skills:
            for relative_path, data in _SKILL_FILES[skill_name].items():
                archive.writestr(
                    f"orca_memory/skills/{skill_name}/{relative_path}", data
                )
    return output.getvalue()


def _bundle(
    root,
    *,
    skills=("orca-conversation", "orca-wiki"),
    license=False,
    scaffolder=False,
):
    bundle = root / "bundle"
    bundle.mkdir()
    wheel_name = "orca_memory-0.1.0-py3-none-any.whl"
    wheel_bytes = _wheel(skills)
    files = {
        wheel_name: wheel_bytes,
        "install.py": (Path(__file__).parents[2] / "tools/install_release.py").read_bytes(),
        "requirements.txt": b"",
        "host.example.yaml": b"placeholder-host\n",
        "orca-memory.example.yaml": b"lifecycle:\n  enabled: false\n",
        "README.md": b"Synthetic installer fixture\n",
        "hooks.template.json": json.dumps({"hooks": {
            "SessionStart": [{"hooks": [{"command": "placeholder"}]}],
        }}).encode(),
    }
    if license:
        files["LICENSE"] = b"synthetic license\n"
    if scaffolder:
        files["scaffold_vault.py"] = (
            b"from pathlib import Path\n"
            b"def _validate_destination(destination, bundle):\n"
            b"    if Path(destination).exists():\n"
            b"        raise ValueError('vault exists')\n"
            b"def scaffold(bundle, destination):\n"
            b"    destination = Path(destination)\n"
            b"    destination.mkdir()\n"
            b"    (destination / 'created.txt').write_text('synthetic')\n"
        )
    for name, data in files.items():
        (bundle / name).write_bytes(data)
    manifest = {"version": "0.1.0", "wheel": wheel_name,
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    (bundle / "release.json").write_text(json.dumps(manifest))
    return bundle


def _install(bundle, prefix, host_config, skills_dir, **options):
    with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
            patch("tools.install_release.subprocess.run") as run:
        install(bundle, prefix, host_config, skills_dir, **options)
    return run


class ReleaseInstallerTests(unittest.TestCase):
    def test_damaged_bundle_stops_before_creating_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            (bundle / "requirements.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                install(
                    bundle,
                    root / "application",
                    root / "config/host.yaml",
                    root / "skills",
                )
            self.assertFalse((root / "application").exists())
            self.assertFalse((root / "config").exists())
            self.assertFalse((root / "skills").exists())

    def test_existing_installation_is_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            prefix = root / "application"
            prefix.mkdir()
            (prefix / "keep").write_text("previous installation")
            with self.assertRaisesRegex(ValueError, "already exists"):
                install(bundle, prefix, root / "config/host.yaml", root / "skills")
            self.assertEqual((prefix / "keep").read_text(), "previous installation")
            self.assertFalse((root / "config").exists())

    def test_extra_file_is_not_silently_shipped(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = _bundle(Path(directory))
            (bundle / "private.yaml").write_text("unexpected")
            with self.assertRaisesRegex(ValueError, "do not match"):
                verify_bundle(bundle)

    def test_launchers_bind_external_config_and_preserve_existing_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            prefix = root / "install with spaces"
            config = root / "settings with 'quotes'/host.yaml"
            skills = root / "skills with spaces"
            config.parent.mkdir()
            config.write_text("existing-settings")
            _install(bundle, prefix, config, skills)
            self.assertEqual(config.read_text(), "existing-settings")
            self.assertEqual(
                (skills / "orca-conversation" / "SKILL.md").read_bytes(),
                _SKILL_FILES["orca-conversation"]["SKILL.md"],
            )
            # Exercise the generated shell launchers with an argument recorder
            # at the interpreter seam, including paths requiring shell quoting.
            python = prefix / "env/bin/python"
            python.parent.mkdir(parents=True)
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$ORCA_HOST_CONFIG" "$@"\n')
            python.chmod(0o700)
            result = subprocess.run([str(prefix / "bin/orca"), "status"],
                                    check=True, capture_output=True, text=True, cwd=root)
            self.assertIn(str(config), result.stdout.splitlines())
            self.assertEqual(result.stdout.splitlines()[-1], "status")
            hook = json.loads((prefix / "hooks.json").read_text())["hooks"]["SessionStart"][0]["hooks"][0]
            result = subprocess.run(["sh", "-c", hook["command"]],
                                    check=True, capture_output=True, text=True, cwd=root)
            self.assertEqual(result.stdout.splitlines()[0], str(config))
            self.assertIn("orca_memory.codex_hook", result.stdout)
            self.assertFalse((root / ".codex").exists())

    def test_default_layout_has_private_runtime_physical_skills_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root, license=True)
            prefix = root / "application"
            skills = root / "codex skills"

            _install(bundle, prefix, prefix / "config/host.yaml", skills)

            self.assertTrue((prefix / "runtime").is_dir())
            self.assertTrue((prefix / "runtime").stat().st_mode & 0o777 <= 0o700)
            self.assertEqual(
                (prefix / "config/host.yaml").read_text(),
                "placeholder-host\nruntime_path: " + json.dumps(str(prefix / "runtime")) + "\n",
            )
            for skill_name, files in _SKILL_FILES.items():
                physical = prefix / "skills" / skill_name
                self.assertTrue(physical.is_dir())
                self.assertTrue((skills / skill_name).is_symlink())
                self.assertEqual((skills / skill_name).resolve(), physical)
                for relative_path, expected in files.items():
                    self.assertEqual((physical / relative_path).read_bytes(), expected)
            package = prefix / "package"
            self.assertEqual(
                {path.name for path in package.iterdir()},
                set(path.name for path in bundle.iterdir()),
            )

    def test_uv_uses_prefix_cache_and_existing_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            prefix = root / "application"

            run = _install(bundle, prefix, prefix / "config/host.yaml", root / "skills")

            uv_calls = [call for call in run.call_args_list if call.args and call.args[0][1] in {"venv", "pip"}]
            self.assertTrue(uv_calls)
            for call in uv_calls:
                self.assertEqual(call.kwargs["env"]["UV_CACHE_DIR"], str(prefix / "cache/uv"))
                self.assertEqual(call.kwargs["env"]["UV_NO_MANAGED_PYTHON"], "1")
                self.assertIn("--no-managed-python", call.args[0])

    def test_packaged_skills_are_deployed_from_wheel_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            skills = root / "codex skills"

            _install(bundle, root / "application", root / "config/host.yaml", skills)

            for skill_name, files in _SKILL_FILES.items():
                for relative_path, expected in files.items():
                    deployed = root / "application" / "skills" / skill_name / relative_path
                    self.assertEqual(deployed.read_bytes(), expected)
                self.assertTrue((skills / skill_name).is_symlink())

    def test_identical_existing_skills_are_preserved_but_require_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            skills = root / "codex skills"
            for skill_name, files in _SKILL_FILES.items():
                for relative_path, expected in files.items():
                    destination = skills / skill_name / relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(expected)
            unrelated = skills / "unrelated" / "SKILL.md"
            unrelated.parent.mkdir()
            unrelated.write_bytes(b"leave this installed skill alone\n")
            before = {
                path: path.read_bytes()
                for path in skills.rglob("*")
                if path.is_file()
            }

            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "copied skill|reconciliation|reconcile"):
                    install(bundle, root / "application", root / "config/host.yaml", skills)

            run.assert_not_called()
            after = {
                path: path.read_bytes()
                for path in skills.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)
            self.assertFalse((root / "application").exists())

    def test_conflicting_skill_directory_stops_before_install_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            skills = root / "skills"
            conflict = skills / "orca-conversation" / "SKILL.md"
            conflict.parent.mkdir(parents=True)
            conflict.write_bytes(b"different installed skill\n")
            prefix = root / "application"
            host_config = root / "config/host.yaml"

            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "skill|conflict|differ"):
                    install(bundle, prefix, host_config, skills)

            run.assert_not_called()
            self.assertFalse(prefix.exists())
            self.assertFalse(host_config.parent.exists())
            self.assertEqual(conflict.read_bytes(), b"different installed skill\n")

    def test_release_package_is_a_self_sufficient_installer_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root, license=True)
            first_prefix = root / "first"
            first_skills = root / "first skills"
            _install(bundle, first_prefix, first_prefix / "config/host.yaml", first_skills)

            package = first_prefix / "package"
            self.assertEqual(verify_bundle(package)["wheel"], "orca_memory-0.1.0-py3-none-any.whl")
            second_prefix = root / "second"
            second_skills = root / "second skills"
            _install(package, second_prefix, second_prefix / "config/host.yaml", second_skills)
            self.assertTrue((second_prefix / "skills/orca-wiki/SKILL.md").is_file())
            self.assertTrue((second_skills / "orca-wiki").is_symlink())

    def test_release_bundle_cannot_be_used_as_a_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "release bundle|separate"):
                    install(bundle, bundle / "install", bundle / "host.yaml", bundle / "skills")
            run.assert_not_called()

    def test_vault_binding_updates_new_host_without_touching_vault(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            prefix = root / "application"
            vault = root / "movable vault"
            _install(
                bundle,
                prefix,
                prefix / "config/host.yaml",
                root / "skills",
                vault_path=vault,
            )
            host = (prefix / "config/host.yaml").read_text()
            self.assertIn("vault_path: " + json.dumps(str(vault)), host)
            self.assertFalse(vault.exists())

    def test_relative_vault_binding_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            with self.assertRaisesRegex(ValueError, "Vault path must be absolute"):
                install(
                    bundle,
                    root / "application",
                    root / "host.yaml",
                    root / "skills",
                    vault_path=Path("relative-vault"),
                )
            self.assertFalse((root / "application").exists())

    def test_existing_host_with_different_vault_stops_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            host = root / "host.yaml"
            host.write_text("vault_path: /already/configured\n")
            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "preserving an existing host config"):
                    install(bundle, root / "application", host, root / "skills", vault_path=root / "new-vault")
            run.assert_not_called()
            self.assertEqual(host.read_text(), "vault_path: /already/configured\n")

    def test_create_vault_preflights_and_uses_only_bundled_scaffolder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root, scaffolder=True)
            prefix = root / "application"
            vault = root / "new vault: safe"

            _install(
                bundle,
                prefix,
                prefix / "config/host.yaml",
                root / "skills",
                vault_path=vault,
                create_vault=True,
            )

            self.assertTrue((vault / "created.txt").is_file())
            self.assertFalse(any(bundle.glob("__pycache__/*")))

    def test_invalid_bundled_scaffolder_stops_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root, scaffolder=True)
            scaffolder = bundle / "scaffold_vault.py"
            scaffolder.write_text("def scaffold(:\n")
            manifest = json.loads((bundle / "release.json").read_text())
            manifest["files"]["scaffold_vault.py"] = hashlib.sha256(
                scaffolder.read_bytes()
            ).hexdigest()
            (bundle / "release.json").write_text(json.dumps(manifest))

            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "could not be loaded"):
                    install(
                        bundle,
                        root / "application",
                        root / "host.yaml",
                        root / "skills",
                        vault_path=root / "vault",
                        create_vault=True,
                    )
            run.assert_not_called()
            self.assertFalse((root / "application").exists())

    def test_create_vault_requires_explicit_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            with self.assertRaisesRegex(ValueError, "requires --vault-path"):
                install(
                    bundle,
                    root / "application",
                    root / "host.yaml",
                    root / "skills",
                    create_vault=True,
                )

    def test_conflicting_skill_file_stops_before_install_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            skills = root / "skills"
            skills.mkdir()
            conflicting_path = skills / "orca-wiki"
            conflicting_path.write_bytes(b"a file cannot replace a skill directory\n")
            prefix = root / "application"
            host_config = root / "config/host.yaml"

            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "skill|directory|conflict"):
                    install(bundle, prefix, host_config, skills)

            run.assert_not_called()
            self.assertFalse(prefix.exists())
            self.assertFalse(host_config.parent.exists())
            self.assertEqual(conflicting_path.read_bytes(), b"a file cannot replace a skill directory\n")

    def test_symlink_skill_destination_stops_before_install_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root)
            skills = root / "skills"
            target = root / "skill-target"
            target.mkdir()
            (target / "SKILL.md").write_bytes(b"target remains unchanged\n")
            skills.mkdir()
            (skills / "orca-conversation").symlink_to(target, target_is_directory=True)
            prefix = root / "application"
            host_config = root / "config/host.yaml"

            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "symlink|skill"):
                    install(bundle, prefix, host_config, skills)

            run.assert_not_called()
            self.assertFalse(prefix.exists())
            self.assertFalse(host_config.parent.exists())
            self.assertTrue((skills / "orca-conversation").is_symlink())
            self.assertEqual((target / "SKILL.md").read_bytes(), b"target remains unchanged\n")

    def test_missing_bundled_skill_stops_before_install_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _bundle(root, skills=("orca-conversation",))
            prefix = root / "application"
            host_config = root / "config/host.yaml"
            skills = root / "skills"

            with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                    patch("tools.install_release.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "skill|orca-wiki"):
                    install(bundle, prefix, host_config, skills)

            run.assert_not_called()
            self.assertFalse(prefix.exists())
            self.assertFalse(host_config.parent.exists())
            self.assertFalse(skills.exists())

    def test_skills_destination_cannot_overlap_prefix_or_host_config(self):
        cases = (
            "prefix",
            "inside-prefix",
            "host-config-parent",
            "host-config-file",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = _bundle(root)
                prefix = root / "application"
                host_config = root / "settings" / "host.yaml"
                if case == "prefix":
                    skills = prefix
                elif case == "inside-prefix":
                    skills = prefix / "skills"
                elif case == "host-config-parent":
                    skills = host_config.parent
                else:
                    skills = host_config

                with patch("tools.install_release.shutil.which", return_value="/synthetic/uv"), \
                        patch("tools.install_release.subprocess.run") as run:
                    with self.assertRaisesRegex(ValueError, "separate|overlap|[Ss]kills"):
                        install(bundle, prefix, host_config, skills)

                run.assert_not_called()
                self.assertFalse(prefix.exists())
                self.assertFalse(host_config.parent.exists())

    def test_cli_defaults_skills_destination_to_codex_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module_path = root / "install_release.py"
            module_path.write_bytes(
                (Path(__file__).parents[2] / "tools/install_release.py").read_bytes()
            )
            (root / "release.json").write_text(json.dumps({"version": "0.1.0"}))
            spec = importlib.util.spec_from_file_location("synthetic_install_release", module_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            codex_home = root / "codex home"

            with patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}), \
                    patch.object(sys, "argv", [
                        "install_release.py",
                        "--prefix", str(root / "application"),
                        "--host-config", str(root / "host.yaml"),
                    ]), patch.object(module, "install") as installer:
                module.main()

            args, kwargs = installer.call_args
            skills_dir = kwargs.get("skills_dir")
            if skills_dir is None:
                skills_dir = args[3]
            self.assertEqual(Path(skills_dir), codex_home / "skills")

    def test_cli_defaults_host_config_inside_selected_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module_path = root / "install_release.py"
            module_path.write_bytes(
                (Path(__file__).parents[2] / "tools/install_release.py").read_bytes()
            )
            (root / "release.json").write_text(json.dumps({"version": "0.1.0"}))
            spec = importlib.util.spec_from_file_location("synthetic_install_release_host", module_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            prefix = root / "chosen prefix"

            with patch.dict(os.environ, {"CODEX_HOME": str(root / "codex")}), \
                    patch.object(sys, "argv", ["install_release.py", "--prefix", str(prefix)]), \
                    patch.object(module, "install") as installer:
                module.main()

            args, kwargs = installer.call_args
            host_config = kwargs.get("host_config")
            if host_config is None:
                host_config = args[2]
            self.assertEqual(Path(host_config), prefix / "config/host.yaml")

    def test_cli_create_vault_requires_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module_path = root / "install_release.py"
            module_path.write_bytes(
                (Path(__file__).parents[2] / "tools/install_release.py").read_bytes()
            )
            (root / "release.json").write_text(json.dumps({"version": "0.1.0"}))
            spec = importlib.util.spec_from_file_location("synthetic_install_release_vault", module_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with patch.object(sys, "argv", ["install_release.py", "--create-vault"]), \
                    self.assertRaises(SystemExit) as raised:
                module.main()
            self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
