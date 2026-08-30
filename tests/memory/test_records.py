import hashlib
import unittest

from orca_memory.memory import (
    MEMORY_KINDS,
    MemoryRecord,
    MemoryValidationError,
    ProjectSummary,
    RecordProposal,
    apply_update,
    kind_directory,
    materialize_record,
    parse_project_summary,
    parse_record,
    record_filename,
    render_project_summary,
    render_record,
    scope_directory,
    semantic_slug,
    short_id,
    validate_operation,
)


class MemoryRecordTests(unittest.TestCase):
    def _record(self, **overrides):
        values = {
            "memory_id": "mem_example",
            "kind": "decision",
            "subject": "Processed source index",
            "scope": "project",
            "scope_id": "proj_orca",
            "status": "current",
            "source_updated_at": "2026-08-30T10:15:00Z",
            "created_at": "2026-08-30T10:20:00Z",
            "updated_at": "2026-08-30T10:20:00Z",
            "current": "Use the durable processed-source index.",
            "context": "It is a rebuildable projection.",
            "implications": "Replay can avoid a semantic call.",
            "workstreams": ("phase-1",),
        }
        values.update(overrides)
        return MemoryRecord(**values)

    def test_all_controlled_kinds_have_contract_directories(self):
        expected = {
            "workstream-summary": "workstreams",
            "decision": "decisions",
            "knowledge": "knowledge",
            "entity": "entities",
            "identity": "identities",
            "goal": "goals",
            "constraint": "constraints",
            "open-question": "open-questions",
            "lesson": "lessons",
            "topic": "topics",
        }
        self.assertEqual(MEMORY_KINDS, set(expected))
        for kind, directory in expected.items():
            self.assertEqual(kind_directory(kind), directory)

    def test_scopes_require_fixed_or_project_identity(self):
        self.assertEqual(
            scope_directory("project", "Orca Memory" ).as_posix(),
            "System/Orca Memory/shallow/projects/orca-memory",
        )
        self.assertEqual(
            scope_directory("general").as_posix(), "System/Orca Memory/shallow/general"
        )
        self.assertEqual(
            scope_directory("unassigned").as_posix(),
            "System/Orca Memory/shallow/unassigned",
        )
        for values in (
            {"scope": "general", "scope_id": "proj_x"},
            {"scope": "unassigned", "scope_id": "general"},
            {"scope": "project", "scope_id": "general"},
        ):
            with self.assertRaises(MemoryValidationError):
                self._record(**values, workstreams=())
        with self.assertRaises(MemoryValidationError):
            scope_directory("project")

    def test_current_record_requires_current_and_only_none_review(self):
        record = self._record()
        self.assertEqual(record.authority, "noncanonical")
        self.assertEqual(record.review_state, "none")
        with self.assertRaises(MemoryValidationError):
            self._record(current=None)
        with self.assertRaises(MemoryValidationError):
            self._record(final="A final position", closure="done")
        with self.assertRaises(MemoryValidationError):
            self._record(authority="canonical")
        with self.assertRaises(MemoryValidationError):
            self._record(review_state="required")

    def test_closed_record_uses_final_and_closure(self):
        record = self._record(
            status="closed",
            current=None,
            context=None,
            implications=None,
            final="The migration completed.",
            closure="Closed after successful verification.",
            workstreams=(),
        )
        rendered = render_record(record)
        self.assertIn("## Final\n", rendered)
        self.assertIn("## Closure\n", rendered)
        self.assertNotIn("## Current\n", rendered)
        self.assertEqual(parse_record(rendered), record)
        with self.assertRaises(MemoryValidationError):
            self._record(status="conflict")

    def test_timestamps_are_utc_and_monotonic_storage_values(self):
        normalized = self._record(
            created_at="2026-08-30T10:20:00+00:00",
            updated_at="2026-08-30T10:21:00+00:00",
        )
        self.assertEqual(normalized.created_at, "2026-08-30T10:20:00Z")
        self.assertEqual(normalized.updated_at, "2026-08-30T10:21:00Z")
        with self.assertRaises(MemoryValidationError):
            self._record(created_at="2026-08-30T10:20:00+08:00")
        with self.assertRaises(MemoryValidationError):
            self._record(
                created_at="2026-08-30T10:21:00Z", updated_at="2026-08-30T10:20:00Z"
            )

    def test_subject_slug_is_human_readable_portable_and_bounded(self):
        self.assertEqual(semantic_slug("Build / Business_knowledge!"), "build-business-knowledge")
        self.assertEqual(semantic_slug("Café — rollout"), "café-rollout")
        self.assertLessEqual(len(semantic_slug(("word " * 100).strip())), 72)
        for subject in (
            "memory",
            "decision-final",
            "CON",
            "",
            "api_key=real-looking-value",
        ):
            with self.assertRaises(MemoryValidationError):
                semantic_slug(subject)

    def test_short_id_and_filename_are_deterministic(self):
        expected = hashlib.sha256("mem_example".encode()).hexdigest()[:12]
        self.assertEqual(short_id("mem_example"), expected)
        self.assertEqual(
            record_filename("Processed source index", "mem_example"),
            f"processed-source-index--{expected}.md",
        )
        self.assertEqual(self._record().filename, record_filename("Processed source index", "mem_example"))

    def test_render_parse_round_trip_has_exact_frontmatter_and_no_provenance(self):
        rendered = render_record(self._record())
        self.assertEqual(rendered.splitlines()[0], "---")
        self.assertIn("schema: orca-memory/0.2", rendered)
        self.assertIn("workstreams: [\"phase-1\"]", rendered)
        self.assertNotIn("source_refs", rendered)
        self.assertNotIn("content_hash", rendered)
        self.assertEqual(parse_record(rendered), self._record())

    def test_parser_rejects_extra_fields_bad_schema_and_body_sections(self):
        rendered = render_record(self._record())
        for invalid in (
            rendered.replace("schema: orca-memory/0.2", "schema: orca-memory/0.3"),
            rendered.replace("updated_at: 2026-08-30T10:20:00Z", "memory_id: mem_other\nupdated_at: 2026-08-30T10:20:00Z"),
            rendered.replace("## Context", "## Conflict"),
        ):
            with self.assertRaises(MemoryValidationError):
                parse_record(invalid)

    def test_proposals_cannot_assign_storage_owned_fields(self):
        proposal = RecordProposal(
            operation="add",
            kind="knowledge",
            subject="Codex rollout storage",
            scope="general",
            scope_id="general",
            current="The storage is local and rebuildable.",
        )
        record = materialize_record(
            proposal,
            memory_id="mem_new",
            created_at="2026-08-30T10:00:00Z",
        )
        self.assertEqual(record.memory_id, "mem_new")
        self.assertEqual(record.created_at, record.updated_at)
        with self.assertRaises(MemoryValidationError):
            RecordProposal.from_mapping(
                {
                    "operation": "add",
                    "kind": "knowledge",
                    "subject": "Safe subject",
                    "scope": "general",
                    "scope_id": "general",
                    "current": "Meaning",
                    "memory_id": "mem_provider_owned",
                }
            )

    def test_add_support_update_operations_enforce_scope_and_identity(self):
        existing = self._record()
        support = RecordProposal(
            operation="support",
            target_memory_id=existing.memory_id,
            kind=existing.kind,
            subject=existing.subject,
            scope=existing.scope,
            scope_id=existing.scope_id,
            source_updated_at=existing.source_updated_at,
            current=existing.current,
            context=existing.context,
            implications=existing.implications,
            workstreams=existing.workstreams,
        )
        self.assertTrue(validate_operation("support", existing=existing, proposal=support))
        with self.assertRaises(MemoryValidationError):
            validate_operation(
                "support",
                existing=existing,
                proposal=RecordProposal(
                    operation="support",
                    target_memory_id=existing.memory_id,
                    kind=existing.kind,
                    subject=existing.subject,
                    scope=existing.scope,
                    scope_id=existing.scope_id,
                    current="Changed meaning",
                ),
            )
        update = RecordProposal(
            operation="update",
            target_memory_id=existing.memory_id,
            kind=existing.kind,
            subject="Processed source index",
            scope=existing.scope,
            scope_id=existing.scope_id,
            source_updated_at="2026-08-30T11:00:00Z",
            current="Use the updated durable source index.",
            workstreams=existing.workstreams,
        )
        updated = apply_update(existing, update, updated_at="2026-08-30T11:01:00Z")
        self.assertEqual(updated.memory_id, existing.memory_id)
        self.assertEqual(updated.created_at, existing.created_at)
        self.assertEqual(updated.updated_at, "2026-08-30T11:01:00Z")
        with self.assertRaises(MemoryValidationError):
            validate_operation("update", existing=existing, proposal={
                "operation": "update", "target_memory_id": "mem_other", "kind": "decision",
                "subject": "Processed source index", "scope": "project", "scope_id": "proj_orca",
                "current": "No", "source_updated_at": "2026-08-30T11:00:00Z",
            })

    def test_conflict_and_supersede_are_explicitly_deferred(self):
        for operation in ("conflict", "supersede"):
            with self.assertRaises(MemoryValidationError):
                RecordProposal(
                    operation=operation,
                    kind="decision",
                    subject="A decision subject",
                    scope="general",
                    scope_id="general",
                    current="A position",
                )


class ProjectSummaryTests(unittest.TestCase):
    def _summary(self, **overrides):
        values = {
            "project_id": "proj_orca",
            "purpose": "Orca Phase 1",
            "current_state": "The local implementation is progressing.",
            "active_workstreams": ("memory",),
            "important_outcomes": ("Capture handoff is validated.",),
            "open_questions": ("Which retrieval adapter is next?",),
            "next_steps": ("Implement explicit recall.",),
            "relevant_memory_ids": ("mem_example",),
        }
        values.update(overrides)
        return ProjectSummary(**values)

    def test_project_summary_has_separate_schema_and_validated_links(self):
        summary = self._summary()
        rendered = render_project_summary(
            summary,
            memory_paths={"mem_example": "System/Orca Memory/shallow/projects/orca/decisions/example.md"},
        )
        self.assertIn("schema_version: orca-project-summary/1", rendered)
        self.assertIn("kind: project-summary", rendered)
        self.assertNotIn("memory_id:", rendered)
        self.assertIn("[mem_example](System/Orca Memory/shallow/projects/orca/decisions/example.md)", rendered)
        self.assertEqual(parse_project_summary(rendered), summary)

    def test_project_summary_defaults_to_stable_ids_and_rejects_bad_relationships(self):
        rendered = render_project_summary(self._summary())
        self.assertIn("- `mem_example`", rendered)
        self.assertEqual(parse_project_summary(rendered), self._summary())
        with self.assertRaises(MemoryValidationError):
            render_project_summary(self._summary(), memory_paths={})
        with self.assertRaises(MemoryValidationError):
            self._summary(authority="canonical")
        with self.assertRaises(MemoryValidationError):
            self._summary(relevant_memory_ids=("../../secret",))


if __name__ == "__main__":
    unittest.main()
