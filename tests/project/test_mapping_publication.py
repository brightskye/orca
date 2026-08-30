from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

import yaml

from orca_memory.project_mapping import (
    ProjectMappingPublisher,
    ProjectMappingRepairRequired,
    detect_project_mapping_repairs,
)
from orca_memory.projects import ProjectRecord, ProjectRegistry, prepare_registration, prepare_relink


NOW = datetime(2026, 8, 30, 10, tzinfo=timezone.utc)


def _host_config(path: Path) -> None:
    path.write_text(
        "schema_version: 1\n"
        "host_id: test-host\n"
        "runtime: wsl\n"
        "vault_path: /tmp/test-vault\n"
        "runtime_path: /tmp/test-runtime\n"
        "connectors:\n"
        "  codex:\n"
        "    rollout_store: /tmp/test-rollouts\n"
        "project_root_mappings: []\n",
        encoding="utf-8",
    )


class ProjectMappingPublicationTests(unittest.TestCase):
    def test_registration_recovers_same_identity_after_project_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            host = root / "host.yaml"
            _host_config(host)
            plan = prepare_registration(
                workspace,
                "Orca",
                ProjectRegistry(),
                project_id="proj_fixed",
                now=NOW,
            )
            publisher = ProjectMappingPublisher(root / "vault", root / "runtime")

            def stop(point: str) -> None:
                if point == "after-project":
                    raise OSError("simulated stop")

            with self.assertRaisesRegex(OSError, "simulated stop"):
                publisher.publish(
                    plan,
                    host_config_path=host,
                    operation_id="map-1",
                    fault=stop,
                )

            project = root / "vault/System/Orca Memory/shallow/projects/orca/project.md"
            self.assertIn("project_id: proj_fixed", project.read_text())
            self.assertNotIn(str(workspace), project.read_text())
            publisher.recover(publisher.pending_intents()[0])
            mappings = yaml.safe_load(host.read_text())["project_root_mappings"]
            self.assertEqual(
                mappings, [{"root": str(workspace.resolve()), "project_id": "proj_fixed"}]
            )
            self.assertEqual(publisher.pending_intents(), ())

    def test_relink_changes_only_host_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            host = root / "host.yaml"
            _host_config(host)
            record = ProjectRecord("proj_orca", "Orca", NOW, NOW)
            plan = prepare_relink(
                workspace, ProjectRegistry((record,)), project_id="proj_orca"
            )
            publisher = ProjectMappingPublisher(root / "vault", root / "runtime")

            publisher.publish(plan, host_config_path=host, operation_id="map-1")

            self.assertFalse((root / "vault").exists())
            mappings = yaml.safe_load(host.read_text())["project_root_mappings"]
            self.assertEqual(mappings[0]["project_id"], "proj_orca")

    def test_conflicting_partial_state_preserves_intent_for_owner_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            host = root / "host.yaml"
            _host_config(host)
            plan = prepare_registration(
                workspace,
                "Orca",
                ProjectRegistry(),
                project_id="proj_fixed",
                now=NOW,
            )
            publisher = ProjectMappingPublisher(root / "vault", root / "runtime")

            def stop(point: str) -> None:
                if point == "after-intent":
                    raise OSError("simulated stop")

            with self.assertRaises(OSError):
                publisher.publish(
                    plan,
                    host_config_path=host,
                    operation_id="map-1",
                    fault=stop,
                )
            host.write_text("project_root_mappings: []\nchanged: true\n")

            with self.assertRaisesRegex(ProjectMappingRepairRequired, "host-config"):
                publisher.recover(publisher.pending_intents()[0])
            self.assertEqual(len(publisher.pending_intents()), 1)

    def test_missing_intent_with_unlinked_record_exposes_content_free_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host = root / "host.yaml"
            _host_config(host)
            project = root / "vault/System/Orca Memory/shallow/projects/orca/project.md"
            project.parent.mkdir(parents=True)
            project.write_text(
                ProjectRecord("proj_orca", "Orca", NOW, NOW).render(),
                encoding="utf-8",
            )

            repairs = detect_project_mapping_repairs(root / "vault", host)

            self.assertEqual(len(repairs), 1)
            self.assertEqual(repairs[0].failure_class, "unlinked-project-record")
            self.assertEqual(repairs[0].project_id, "proj_orca")
            self.assertNotIn(str(root), repairs[0].locator)


if __name__ == "__main__":
    unittest.main()
