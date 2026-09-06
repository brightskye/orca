from __future__ import annotations

from dataclasses import FrozenInstanceError
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

from orca_memory.configuration import ConfigurationError, load_configuration
from orca_memory.projects import ProjectRecord, project_alias_slug


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTERED_ADAPTER = "replace-with-registered-adapter-id"


class ConfigurationTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, dict, dict]:
        vault = root / "vault"
        runtime = root / "runtime"
        rollout_store = root / "rollouts"
        vault.mkdir()
        runtime.mkdir()
        rollout_store.mkdir()

        host = yaml.safe_load(
            (REPOSITORY_ROOT / "config" / "host.example.yaml").read_text(encoding="utf-8")
        )
        host["vault_path"] = str(vault)
        host["runtime_path"] = str(runtime)
        host["connectors"]["codex"]["rollout_store"] = str(rollout_store)
        host_path = root / "host.yaml"
        host_path.write_text(yaml.safe_dump(host, sort_keys=False), encoding="utf-8")

        vault_config = yaml.safe_load(
            (REPOSITORY_ROOT / "config" / "orca-memory.example.yaml").read_text(
                encoding="utf-8"
            )
        )
        config_path = vault / "System" / "Orca Memory" / "orca-memory.yaml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(yaml.safe_dump(vault_config, sort_keys=False), encoding="utf-8")
        return host_path, host, vault_config

    def _write_host(self, path: Path, value: dict) -> None:
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    def _write_vault(self, host: dict, value: dict) -> None:
        path = Path(host["vault_path"]) / "System" / "Orca Memory" / "orca-memory.yaml"
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    def _load(self, host_path: Path, *, environ: dict[str, str] | None = None):
        return load_configuration(
            host_path,
            environ={} if environ is None else environ,
            registered_provider_adapters={REGISTERED_ADAPTER},
        )

    def test_safe_examples_produce_immutable_idempotent_value_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, _, _ = self._fixture(root)
            before = _tree_snapshot(root)

            first = self._load(host_path)
            second = self._load(host_path)

            self.assertEqual(second, first)
            self.assertEqual(_tree_snapshot(root), before)
            self.assertEqual(first.host.schema_version, 1)
            self.assertEqual(first.host.runtime, "wsl")
            self.assertEqual(first.vault.schema_version, "orca-memory-config/0.1")
            self.assertFalse(first.vault.lifecycle.enabled)
            self.assertEqual(first.vault.cadence.catch_up_minutes, 15)
            self.assertEqual(first.vault.retry.max_attempts, 3)
            self.assertEqual(first.vault.budgets.processor.input_tokens, 20_000)
            self.assertEqual(first.vault.budgets.recall.max_results, 6)
            self.assertEqual(first.vault.budgets.interaction.auto_load_tokens, 500)
            processing = first.vault.budgets.processor.as_processing_budget()
            self.assertEqual(processing.preceding_turn_tokens, 1_000)
            self.assertEqual(processing.related_record_count, 5)
            with self.assertRaises(FrozenInstanceError):
                first.host.host_id = "changed"

    def test_lifecycle_defaults_off_and_requires_an_exact_boolean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)

            vault.pop("lifecycle")
            self._write_vault(host, vault)
            self.assertFalse(self._load(host_path).vault.lifecycle.enabled)

            vault["lifecycle"] = {"enabled": True}
            self._write_vault(host, vault)
            self.assertTrue(self._load(host_path).vault.lifecycle.enabled)

            for invalid in ("true", 1, None):
                with self.subTest(invalid=invalid):
                    vault["lifecycle"] = {"enabled": invalid}
                    self._write_vault(host, vault)
                    with self.assertRaisesRegex(
                        ConfigurationError, "lifecycle.enabled must be a boolean"
                    ):
                        self._load(host_path)

    def test_vault_path_precedence_file_environment_and_normalized_equality(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, _ = self._fixture(root)
            vault = Path(host["vault_path"])

            self.assertEqual(self._load(host_path).host.vault_path, vault.resolve())

            host.pop("vault_path")
            self._write_host(host_path, host)
            self.assertEqual(
                self._load(host_path, environ={"ORCA_VAULT_PATH": str(vault)}).host.vault_path,
                vault.resolve(),
            )

            host["vault_path"] = str(vault)
            self._write_host(host_path, host)
            equivalent = vault / ".." / vault.name
            self.assertEqual(
                self._load(
                    host_path, environ={"ORCA_VAULT_PATH": str(equivalent)}
                ).host.vault_path,
                vault.resolve(),
            )

    def test_conflicting_vault_sources_fail_without_echoing_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, _, _ = self._fixture(root)
            other = root / "other-vault"
            other.mkdir()

            with self.assertRaises(ConfigurationError) as caught:
                self._load(host_path, environ={"ORCA_VAULT_PATH": str(other)})

            message = str(caught.exception)
            self.assertIn("conflicts", message)
            self.assertNotIn(str(root), message)

    def test_missing_relative_inaccessible_and_cross_location_paths_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, _ = self._fixture(root)

            with self.assertRaisesRegex(ConfigurationError, "required host configuration"):
                self._load(root / "missing.yaml")

            cases = (
                ("vault_path", "relative/vault", "absolute path"),
                ("vault_path", str(root / "missing-vault"), "inaccessible"),
                ("runtime_path", "relative/runtime", "absolute path"),
            )
            for field, value, expected in cases:
                with self.subTest(field=field, value=value):
                    changed = yaml.safe_load(yaml.safe_dump(host))
                    changed[field] = value
                    self._write_host(host_path, changed)
                    with self.assertRaisesRegex(ConfigurationError, expected):
                        self._load(host_path)

            changed = yaml.safe_load(yaml.safe_dump(host))
            inside_runtime = Path(host["vault_path"]) / "runtime"
            inside_runtime.mkdir()
            changed["runtime_path"] = str(inside_runtime)
            self._write_host(host_path, changed)
            with self.assertRaisesRegex(ConfigurationError, "outside the vault"):
                self._load(host_path)

            changed = yaml.safe_load(yaml.safe_dump(host))
            inside_rollouts = Path(host["vault_path"]) / "rollouts"
            inside_rollouts.mkdir()
            changed["connectors"]["codex"]["rollout_store"] = str(inside_rollouts)
            self._write_host(host_path, changed)
            with self.assertRaisesRegex(ConfigurationError, "outside the vault"):
                self._load(host_path)

    def test_vault_and_rollouts_must_be_outside_configured_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)
            project = root / "project"
            project.mkdir()

            nested_vault = project / "private-vault"
            (nested_vault / "System/Orca Memory").mkdir(parents=True)
            (nested_vault / "System/Orca Memory/orca-memory.yaml").write_text(
                yaml.safe_dump(vault, sort_keys=False), encoding="utf-8"
            )
            host["vault_path"] = str(nested_vault)
            host["project_root_mappings"] = [
                {"root": str(project), "project_id": "proj_test"}
            ]
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "vault_path must be outside"):
                self._load(host_path)

            outside_vault = Path(host["vault_path"]).parent.parent / "outside-vault"
            (outside_vault / "System/Orca Memory").mkdir(parents=True)
            (outside_vault / "System/Orca Memory/orca-memory.yaml").write_text(
                yaml.safe_dump(vault, sort_keys=False), encoding="utf-8"
            )
            host["vault_path"] = str(outside_vault)
            host["connectors"]["codex"]["rollout_store"] = str(project / "rollouts")
            (project / "rollouts").mkdir()
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "rollout_store must be outside"):
                self._load(host_path)

    def test_vault_inside_symlinked_or_detected_git_worktree_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)
            project = root / "project"
            project.mkdir()

            actual_vault = project / "actual-vault"
            (actual_vault / "System/Orca Memory").mkdir(parents=True)
            (actual_vault / "System/Orca Memory/orca-memory.yaml").write_text(
                yaml.safe_dump(vault, sort_keys=False), encoding="utf-8"
            )
            symlinked_vault = root / "vault-link"
            symlinked_vault.symlink_to(actual_vault, target_is_directory=True)
            host["vault_path"] = str(symlinked_vault)
            host["project_root_mappings"] = [
                {"root": str(project), "project_id": "proj_test"}
            ]
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "vault_path must be outside"):
                self._load(host_path)

            subprocess.run(
                ["git", "init", "--quiet", str(project / "git-root")],
                check=True,
                capture_output=True,
                text=True,
            )
            git_root = project / "git-root"
            nested_git_vault = git_root / "private-vault"
            (nested_git_vault / "System/Orca Memory").mkdir(parents=True)
            (nested_git_vault / "System/Orca Memory/orca-memory.yaml").write_text(
                yaml.safe_dump(vault, sort_keys=False), encoding="utf-8"
            )
            host["vault_path"] = str(nested_git_vault)
            host["project_root_mappings"] = []
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "vault_path must be outside"):
                self._load(host_path)

            partial_root = project / "partial-root"
            (partial_root / ".git").mkdir(parents=True)
            (partial_root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            partial_vault = partial_root / "private-vault"
            (partial_vault / "System/Orca Memory").mkdir(parents=True)
            (partial_vault / "System/Orca Memory/orca-memory.yaml").write_text(
                yaml.safe_dump(vault, sort_keys=False), encoding="utf-8"
            )
            host["vault_path"] = str(partial_vault)
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "ambiguous Git worktree marker"):
                self._load(host_path)

            linked_root = project / "linked-root"
            linked_root.mkdir()
            linked_gitdir = root / "linked-gitdir"
            linked_gitdir.mkdir()
            (linked_root / ".git").write_text(
                f"gitdir: {linked_gitdir}\n", encoding="utf-8"
            )
            linked_vault = linked_root / "private-vault"
            (linked_vault / "System/Orca Memory").mkdir(parents=True)
            (linked_vault / "System/Orca Memory/orca-memory.yaml").write_text(
                yaml.safe_dump(vault, sort_keys=False), encoding="utf-8"
            )
            host["vault_path"] = str(linked_vault)
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "vault_path must be outside"):
                self._load(host_path)

    def test_runtime_may_remain_inside_detected_git_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, _ = self._fixture(root)
            git_root = root / "git-root"
            subprocess.run(
                ["git", "init", "--quiet", str(git_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            runtime = git_root / ".runtime"
            runtime.mkdir()
            host["runtime_path"] = str(runtime)
            self._write_host(host_path, host)
            self.assertEqual(self._load(host_path).host.runtime_path, runtime.resolve())

    def test_vault_configuration_symlink_cannot_escape_the_vault(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, _ = self._fixture(root)
            config_path = (
                Path(host["vault_path"])
                / "System"
                / "Orca Memory"
                / "orca-memory.yaml"
            )
            outside = root / "outside-config.yaml"
            config_path.replace(outside)
            config_path.symlink_to(outside)

            with self.assertRaisesRegex(ConfigurationError, "inside the vault"):
                self._load(host_path)

    def test_unknown_duplicate_and_unsupported_schema_keys_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)

            changed_host = yaml.safe_load(yaml.safe_dump(host))
            changed_host["unknown"] = True
            self._write_host(host_path, changed_host)
            with self.assertRaisesRegex(ConfigurationError, "unknown key"):
                self._load(host_path)

            changed_host = yaml.safe_load(yaml.safe_dump(host))
            changed_host["schema_version"] = 2
            self._write_host(host_path, changed_host)
            with self.assertRaisesRegex(ConfigurationError, "host schema_version"):
                self._load(host_path)

            changed_host["schema_version"] = 1.0
            self._write_host(host_path, changed_host)
            with self.assertRaisesRegex(ConfigurationError, "host schema_version"):
                self._load(host_path)

            self._write_host(host_path, host)
            changed_vault = yaml.safe_load(yaml.safe_dump(vault))
            changed_vault["schema_version"] = "orca-memory-config/9"
            self._write_vault(host, changed_vault)
            with self.assertRaisesRegex(ConfigurationError, "vault schema_version"):
                self._load(host_path)

            changed_vault = yaml.safe_load(yaml.safe_dump(vault))
            changed_vault["budgets"]["recall"]["unknown"] = 1
            self._write_vault(host, changed_vault)
            with self.assertRaisesRegex(ConfigurationError, "unknown key"):
                self._load(host_path)

            self._write_vault(host, vault)
            host_path.write_text(
                host_path.read_text(encoding="utf-8") + "host_id: duplicate\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigurationError, "duplicate key"):
                self._load(host_path)

    def test_provider_and_exact_policies_validate_without_calling_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)

            with self.assertRaisesRegex(ConfigurationError, "not registered"):
                load_configuration(host_path, environ={}, registered_provider_adapters=set())

            policy_cases = (
                ("privacy", "redaction_policy"),
                ("processing", "processor_policy"),
                ("interaction", "observation_policy"),
                ("interaction", "aggregation_policy"),
                ("interaction", "guidance_policy"),
            )
            for group, field in policy_cases:
                with self.subTest(group=group, field=field):
                    changed = yaml.safe_load(yaml.safe_dump(vault))
                    changed[group][field] = "unsupported/version"
                    self._write_vault(host, changed)
                    with self.assertRaisesRegex(ConfigurationError, f"unsupported {group}"):
                        self._load(host_path)

    def test_defaults_and_lower_cadence_retry_and_budgets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)
            vault.pop("cadence")
            vault.pop("retry")
            vault["budgets"] = {
                "processor": {"input_tokens": 10_000, "new_evidence_tokens": 4_000},
                "recall": {"max_results": 3},
                "interaction": {"auto_load_tokens": 250},
            }
            self._write_vault(host, vault)

            result = self._load(host_path)

            self.assertEqual(result.vault.cadence.catch_up_minutes, 15)
            self.assertEqual(result.vault.retry.retention_hours, 72)
            self.assertEqual(result.vault.budgets.processor.input_tokens, 10_000)
            self.assertEqual(result.vault.budgets.processor.output_tokens, 4_000)
            self.assertEqual(result.vault.budgets.recall.max_results, 3)
            self.assertEqual(result.vault.budgets.interaction.auto_load_tokens, 250)

    def test_raised_nonpositive_and_inconsistent_budgets_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, vault = self._fixture(root)

            changes = (
                ("processor", "new_evidence_tokens", 8_001, "accepted ceiling"),
                ("recall", "max_results", 7, "accepted ceiling"),
                ("interaction", "auto_load_tokens", 501, "accepted ceiling"),
                ("processor", "input_tokens", 0, "positive integer"),
                ("recall", "total_tokens", True, "positive integer"),
            )
            for group, field, value, expected in changes:
                with self.subTest(group=group, field=field):
                    changed = yaml.safe_load(yaml.safe_dump(vault))
                    changed["budgets"][group][field] = value
                    self._write_vault(host, changed)
                    with self.assertRaisesRegex(ConfigurationError, expected):
                        self._load(host_path)

            changed = yaml.safe_load(yaml.safe_dump(vault))
            changed["budgets"]["processor"]["model_window_tokens"] = 20_000
            self._write_vault(host, changed)
            with self.assertRaisesRegex(ConfigurationError, "do not fit model_window_tokens"):
                self._load(host_path)

            changed = yaml.safe_load(yaml.safe_dump(vault))
            changed["budgets"]["recall"]["total_tokens"] = 1_000
            self._write_vault(host, changed)
            with self.assertRaisesRegex(ConfigurationError, "per_document_tokens"):
                self._load(host_path)

            changed = yaml.safe_load(yaml.safe_dump(vault))
            changed["retry"]["max_attempts"] = 4
            self._write_vault(host, changed)
            with self.assertRaisesRegex(ConfigurationError, "accepted ceiling"):
                self._load(host_path)

    def test_project_mappings_require_unique_roots_and_existing_registry_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host_path, host, _ = self._fixture(root)
            workspace = root / "workspace"
            workspace.mkdir()
            host["project_root_mappings"] = [
                {"root": str(workspace), "project_id": "proj_orca"}
            ]
            self._write_host(host_path, host)

            with self.assertRaisesRegex(ConfigurationError, "unknown project_id"):
                self._load(host_path)

            record = ProjectRecord(
                "proj_orca",
                "Orca",
                "2026-08-30T00:00:00Z",
                "2026-08-30T00:00:00Z",
            )
            project_path = (
                Path(host["vault_path"])
                / "System"
                / "Orca Memory"
                / "shallow"
                / "projects"
                / project_alias_slug(record.project_alias)
                / "project.md"
            )
            project_path.parent.mkdir(parents=True)
            project_path.write_text(record.render(), encoding="utf-8")
            self.assertEqual(
                self._load(host_path).host.project_root_mappings[0].project_id,
                "proj_orca",
            )

            host["project_root_mappings"].append(
                {"root": str(workspace / ".." / workspace.name), "project_id": "proj_orca"}
            )
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "duplicate normalized"):
                self._load(host_path)

            host["project_root_mappings"] = [
                {
                    "root": str(Path(host["vault_path"]) / "project"),
                    "project_id": "proj_orca",
                }
            ]
            self._write_host(host_path, host)
            with self.assertRaisesRegex(ConfigurationError, "outside the vault"):
                self._load(host_path)

    def test_local_private_and_generated_paths_are_git_ignored(self) -> None:
        candidates = (
            "config/host.yaml",
            ".runtime/checkpoint.json",
            ".venv/dependency",
            "src/orca_memory/__pycache__/configuration.cpython-312.pyc",
        )
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=REPOSITORY_ROOT,
            input="\n".join(candidates) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tuple(result.stdout.splitlines()), candidates)


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


if __name__ == "__main__":
    unittest.main()
