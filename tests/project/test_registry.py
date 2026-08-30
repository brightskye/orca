from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from orca_memory.projects import (
    ProjectRecord,
    ProjectRegistry,
    RootMapping,
    WorktreeEvidence,
    allocate_project_id,
    prepare_registration,
    prepare_relink,
    project_alias_slug,
    resolve_project,
    validate_project_record,
)


NOW = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)


def _record(project_id: str = "proj_orca", alias: str = "Orca") -> ProjectRecord:
    return ProjectRecord(project_id, alias, NOW, NOW)


class ProjectRecordTests(unittest.TestCase):
    def test_renders_and_parses_exact_identity_record_without_local_evidence(self) -> None:
        record = _record()
        rendered = record.render()

        self.assertEqual(validate_project_record(rendered), record)
        self.assertEqual(
            rendered,
            "---\n"
            "schema_version: orca-project/0.1\n"
            "project_id: proj_orca\n"
            "project_alias: Orca\n"
            "authority: noncanonical\n"
            "registration_method: owner-confirmed\n"
            "created_at: 2026-08-30T10:00:00Z\n"
            "updated_at: 2026-08-30T10:00:00Z\n"
            "---\n"
            "# Orca\n\n"
            "Project registry identity record.\n",
        )
        self.assertNotIn("/workspace", rendered)
        self.assertNotIn("git", rendered.lower())

    def test_rejects_identity_mutation_and_extra_frontmatter(self) -> None:
        rendered = _record().render()
        with self.assertRaises(ValueError):
            validate_project_record(rendered.replace("authority: noncanonical", "authority: canonical"))
        with self.assertRaises(ValueError):
            validate_project_record(rendered.replace("updated_at:", "root: /private\nupdated_at:"))
        with self.assertRaises(ValueError):
            validate_project_record(rendered.replace("# Orca", "# Other"))

    def test_alias_and_slug_are_case_insensitive_and_reserved_scopes_rejected(self) -> None:
        self.assertEqual(project_alias_slug("My_Project"), "my-project")
        registry = ProjectRegistry((_record(alias="My Project"),))
        with self.assertRaisesRegex(ValueError, "collision"):
            prepare_registration(
                Path("/tmp/new-project"),
                "my_project",
                registry,
                project_id="proj_second",
                now=NOW,
            )
        for alias in ("General", "unassigned"):
            with self.assertRaises(ValueError):
                ProjectRecord("proj_x", alias, NOW, NOW)

    def test_allocation_uses_storage_input_and_skips_existing_ids(self) -> None:
        values = iter(("proj_orca", "proj_next"))
        self.assertEqual(
            allocate_project_id(lambda: next(values), existing_ids={"proj_orca"}),
            "proj_next",
        )
        with self.assertRaises(ValueError):
            allocate_project_id(lambda: "not-a-project-id")


class ProjectResolutionTests(unittest.TestCase):
    def test_exact_mapping_returns_mapped_without_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            result = resolve_project(root, (RootMapping(root, "proj_orca"),), ProjectRegistry((_record(),)))

            self.assertEqual(result.status, "mapped")
            self.assertEqual(result.project_id, "proj_orca")
            self.assertIsNone(result.mapping_plan)
            self.assertTrue(result.allows_project_processing)

    def test_missing_identity_is_an_error_and_unknown_root_needs_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            missing = resolve_project(root, ((str(root), "proj_missing"),), ProjectRegistry())
            self.assertEqual(missing.status, "error")
            unknown = resolve_project(root, (), ProjectRegistry())
            self.assertEqual(unknown.status, "owner-choice-required")
            unassigned = resolve_project(root, (), ProjectRegistry(), owner_choice="unassigned")
            self.assertEqual(unassigned.status, "unassigned")
            self.assertIsNone(unassigned.mapping_plan)

    def test_exact_common_directory_reuses_one_nonconflicting_mapped_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            current = base / "current"
            mapped = base / "mapped"
            current.mkdir()
            mapped.mkdir()
            common = base / ".git-common"
            common.mkdir()
            result = resolve_project(
                current,
                (RootMapping(mapped, "proj_orca"),),
                ProjectRegistry((_record(),)),
                git_root=current,
                git_common_dir=common,
                mapped_worktrees=(WorktreeEvidence(mapped, common),),
            )

            self.assertEqual(result.status, "worktree-reused")
            self.assertEqual(result.project_alias, "Orca")
            self.assertIsNotNone(result.mapping_plan)
            self.assertEqual(result.mapping_plan.action, "worktree-reuse")
            self.assertEqual(result.mapping_plan.git_common_dir, common.resolve())

    def test_conflicting_common_directory_candidates_do_not_auto_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            current = base / "current"
            first = base / "first"
            second = base / "second"
            for path in (current, first, second):
                path.mkdir()
            common = base / ".git-common"
            common.mkdir()
            records = ProjectRegistry((_record(), _record("proj_other", "Other")))
            result = resolve_project(
                current,
                (RootMapping(first, "proj_orca"), RootMapping(second, "proj_other")),
                records,
                git_root=current,
                git_common_dir=common,
                mapped_worktrees=(WorktreeEvidence(first, common), WorktreeEvidence(second, common)),
            )

            self.assertEqual(result.status, "owner-choice-required")
            self.assertEqual(result.candidate_project_ids, ("proj_orca", "proj_other"))
            self.assertIsNone(result.mapping_plan)

    def test_registration_and_relink_return_fixed_local_plans_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            registry = ProjectRegistry((_record(),))
            registration = prepare_registration(
                root,
                "New Project",
                registry,
                project_id="proj_new",
                now=NOW,
            )
            self.assertEqual(registration.action, "register")
            self.assertEqual(registration.project_record.project_id, "proj_new")
            self.assertIn("project_alias: New Project", registration.project_record.render())
            relink = prepare_relink(root, registry, project_alias="orca")
            self.assertEqual(relink.action, "relink")
            self.assertEqual(relink.project_id, "proj_orca")
            self.assertFalse((root / "project.md").exists())


if __name__ == "__main__":
    unittest.main()
