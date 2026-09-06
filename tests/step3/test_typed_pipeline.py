from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orca_memory.conversation import ConversationBatch, NormalizedTurn
from orca_memory.memory import ProjectSummary, RecordProposal, parse_record
from orca_memory.pipeline import Step3Pipeline
from orca_memory.processor import ContinuationSummary, ProcessingProposal, Processor
from orca_memory.storage import MemoryScope, Storage


class MutableProvider:
    name = "fake-semantic-provider/typed"

    def __init__(self, proposal: ProcessingProposal) -> None:
        self.proposal = proposal
        self.calls = 0

    def distill(self, request):
        self.calls += 1
        return self.proposal


def _batch(turn_id: str, *, conversation_id: str = "conversation-typed") -> ConversationBatch:
    turn = NormalizedTurn(
        connector_id="codex-local",
        conversation_id=conversation_id,
        turn_id=turn_id,
        occurred_at="2026-08-30T10:00:00Z",
        source_uri=f"codex://session/{conversation_id}/event/{turn_id}",
        text=f"Owner evidence for {turn_id}.",
        content_sha256=hashlib.sha256(f"Owner evidence for {turn_id}.".encode()).hexdigest(),
    )
    return ConversationBatch("codex-local", conversation_id, (turn,))


def _add(*, scope: str = "general", scope_id: str = "general") -> RecordProposal:
    return RecordProposal(
        operation="add",
        kind="decision",
        subject="Processed source index",
        scope=scope,
        scope_id=scope_id,
        current="Use the durable processed-source index.",
        context="The index is a rebuildable projection.",
        workstreams=("phase-1",) if scope == "project" else (),
        source_segment_refs=("turn-add#1",),
    )


class TypedPipelineTests(unittest.TestCase):
    def _storage(self, root: Path, *, identifiers, fault=None) -> Storage:
        values = iter(identifiers)
        return Storage(
            root / "vault",
            root / "runtime",
            clock=lambda: datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
            id_factory=lambda: next(values),
            publication_fault=fault,
        )

    def test_add_materializes_storage_identity_and_joined_manifest_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = MutableProvider(ProcessingProposal(None, (_add(),)))
            result = Step3Pipeline(
                Processor(provider),
                self._storage(root, identifiers=("run-add", "memory-add")),
            ).run(_batch("turn-add"), scope=MemoryScope("general", "general"))

            self.assertEqual(result.status, "success")
            self.assertEqual(len(result.output_paths), 1)
            record = parse_record(result.output_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(record.memory_id, "mem_memory-add")
            self.assertEqual(record.created_at, "2026-08-30T12:00:00Z")
            manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
            operation = manifest["operations"][0]
            output = manifest["outputs"][0]
            self.assertEqual(operation["artifact_id"], record.memory_id)
            self.assertEqual(operation["source_refs"], ["src-001"])
            self.assertEqual(operation["output_refs"], [output["output_ref"]])
            self.assertEqual(output["artifact_id"], record.memory_id)

    def test_support_preserves_bytes_and_update_preserves_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identifiers = ("run-add", "memory-add", "run-support", "run-update")
            storage = self._storage(root, identifiers=identifiers)
            provider = MutableProvider(ProcessingProposal(None, (_add(),)))
            pipeline = Step3Pipeline(Processor(provider), storage)
            first = pipeline.run(
                _batch("turn-add"), scope=MemoryScope("general", "general")
            )
            original_path = first.output_paths[0]
            original_payload = original_path.read_bytes()
            existing = parse_record(original_payload.decode("utf-8"))

            provider.proposal = ProcessingProposal(
                None,
                (
                    RecordProposal(
                        operation="support",
                        target_memory_id=existing.memory_id,
                        kind=existing.kind,
                        subject=existing.subject,
                        scope=existing.scope,
                        scope_id=existing.scope_id,
                        status=existing.status,
                        source_updated_at=existing.source_updated_at,
                        workstreams=existing.workstreams,
                        current=existing.current,
                        context=existing.context,
                        implications=existing.implications,
                        source_segment_refs=("turn-support#1",),
                    ),
                ),
            )
            supported = pipeline.run(
                _batch("turn-support"), scope=MemoryScope("general", "general")
            )
            self.assertEqual(original_path.read_bytes(), original_payload)
            support_manifest = json.loads(supported.manifest_path.read_text())
            self.assertEqual(support_manifest["operations"][0]["outcome"], "supported")
            self.assertEqual(support_manifest["operations"][0]["output_refs"], [])

            provider.proposal = ProcessingProposal(
                None,
                (
                    RecordProposal(
                        operation="update",
                        target_memory_id=existing.memory_id,
                        kind=existing.kind,
                        subject="Processed source receipt index",
                        scope=existing.scope,
                        scope_id=existing.scope_id,
                        current="Use the durable receipt-backed processed-source index.",
                        source_segment_refs=("turn-update#1",),
                    ),
                ),
            )
            updated = pipeline.run(
                _batch("turn-update"), scope=MemoryScope("general", "general")
            )
            self.assertFalse(original_path.exists())
            self.assertEqual(len(updated.output_paths), 2)
            new_path = next(path for path in updated.output_paths if path.exists())
            new_record = parse_record(new_path.read_text(encoding="utf-8"))
            self.assertEqual(new_record.memory_id, existing.memory_id)
            self.assertEqual(new_record.created_at, existing.created_at)
            self.assertEqual(new_record.updated_at, "2026-08-30T12:00:00Z")

    def test_project_change_requires_and_publishes_linked_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proposal = _add(scope="project", scope_id="proj_orca")
            provider = MutableProvider(
                ProcessingProposal(
                    None,
                    (proposal,),
                    ProjectSummary(
                        project_id="proj_orca",
                        purpose="Orca Phase 1",
                        current_state="The processed-source index is selected.",
                        relevant_memory_ids=("mem_memory-add",),
                    ),
                )
            )
            result = Step3Pipeline(
                Processor(provider),
                self._storage(root, identifiers=("run-add", "memory-add")),
            ).run(
                _batch("turn-add"),
                scope=MemoryScope("project", "proj_orca", "Orca"),
            )

            summary = root / "vault/System/Orca Memory/shallow/projects/orca/summary.md"
            self.assertTrue(summary.is_file())
            self.assertIn(
                "[mem_memory-add](System/Orca Memory/shallow/projects/orca/decisions/",
                summary.read_text(encoding="utf-8"),
            )
            manifest = json.loads(result.manifest_path.read_text())
            self.assertEqual(
                [operation["artifact_kind"] for operation in manifest["operations"]],
                ["typed-memory-record", "project-summary"],
            )

    def test_support_keeps_project_summary_and_still_saves_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = _add(scope="project", scope_id="proj_orca")
            summary = ProjectSummary("proj_orca", "Orca Phase 1", "Index selected.")
            provider = MutableProvider(ProcessingProposal(None, (record,), summary))
            pipeline = Step3Pipeline(
                Processor(provider),
                self._storage(root, identifiers=("run-add", "memory-add", "run-support")),
            )
            scope = MemoryScope("project", "proj_orca", "Orca")
            pipeline.run(_batch("turn-add"), scope=scope)
            path = root / "vault/System/Orca Memory/shallow/projects/orca/summary.md"
            original = path.read_bytes()
            provider.proposal = ProcessingProposal(
                ContinuationSummary("Continue index work", "Keep the existing decision."),
                (replace(record, operation="support", target_memory_id="mem_memory-add",
                         source_segment_refs=("turn-support#1",)),),
                replace(summary, current_state="An unnecessary rewrite.", body=None),
            )
            result = pipeline.run(_batch("turn-support"), scope=scope)
            self.assertEqual(result.status, "success")
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(any(p.parent.name == "conversation-summaries" for p in result.output_paths))
            manifest = json.loads(result.manifest_path.read_text())
            self.assertNotIn("project-summary", [op["artifact_kind"] for op in manifest["operations"]])

    def test_project_summary_resolves_storage_assigned_memory_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proposal = _add(scope="project", scope_id="proj_orca")
            provider = MutableProvider(
                ProcessingProposal(
                    None,
                    (proposal,),
                    ProjectSummary(
                        project_id="proj_orca",
                        purpose="Orca Phase 1",
                        current_state="The new record is ready.",
                    ),
                )
            )
            result = Step3Pipeline(
                Processor(provider),
                self._storage(root, identifiers=("run-add", "unpredictable-memory-id")),
            ).run(
                _batch("turn-add"),
                scope=MemoryScope("project", "proj_orca", "Orca"),
            )

            summary = (root / "vault/System/Orca Memory/shallow/projects/orca/summary.md").read_text()
            self.assertIn("mem_unpredictable-memory-id", summary)
            self.assertEqual(
                json.loads(result.manifest_path.read_text())["operations"][0]["artifact_id"],
                "mem_unpredictable-memory-id",
            )

    def test_composed_pipeline_passes_current_same_scope_record_to_next_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = _add()

            class ContextProvider(MutableProvider):
                def __init__(self) -> None:
                    super().__init__(ProcessingProposal(None, (first,)))
                    self.requests = []

                def distill(self, request):
                    self.requests.append(request)
                    if len(self.requests) == 1:
                        return self.proposal
                    target = request.related_records[0]
                    return ProcessingProposal(
                        None,
                        (
                            RecordProposal(
                                operation="support",
                                target_memory_id=target.memory_id,
                                kind=target.kind,
                                subject=target.subject,
                                scope=target.scope,
                                scope_id=target.scope_id,
                                status=target.status,
                                source_updated_at=target.source_updated_at,
                                workstreams=target.workstreams,
                                current=target.current,
                                context=target.context,
                                implications=target.implications,
                                source_segment_refs=("turn-support#1",),
                            ),
                        ),
                    )

            provider = ContextProvider()
            pipeline = Step3Pipeline(
                Processor(provider),
                self._storage(root, identifiers=("run-add", "memory-add", "run-support")),
            )
            pipeline.run(_batch("turn-add"), scope=MemoryScope("general", "general"))
            result = pipeline.run(_batch("turn-support"), scope=MemoryScope("general", "general"))

            self.assertEqual(len(provider.requests[1].related_records), 1)
            self.assertEqual(provider.requests[1].related_records[0].memory_id, "mem_memory-add")
            operation = json.loads(result.manifest_path.read_text())["operations"][0]
            self.assertEqual((operation["operation"], operation["outcome"]), ("support", "supported"))

    def test_manifest_binds_operation_to_only_the_cited_owner_segment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = _batch("turn-first").turns[0]
            second_text = "The second Owner turn supports this decision."
            second = NormalizedTurn(
                "codex-local",
                "conversation-typed",
                "turn-second",
                "2026-08-30T10:01:00Z",
                "codex://session/conversation-typed/event/turn-second",
                second_text,
                hashlib.sha256(second_text.encode()).hexdigest(),
            )
            proposal = RecordProposal(
                operation="add",
                kind="decision",
                subject="Cited second turn",
                scope="general",
                scope_id="general",
                current="Use only the second turn as support.",
                source_segment_refs=("turn-second#1",),
            )
            provider = MutableProvider(ProcessingProposal(None, (proposal,)))
            result = Step3Pipeline(
                Processor(provider),
                self._storage(root, identifiers=("run-add", "memory-add")),
            ).run(
                ConversationBatch("codex-local", "conversation-typed", (first, second)),
                scope=MemoryScope("general", "general"),
            )
            manifest = json.loads(result.manifest_path.read_text())
            self.assertEqual(manifest["operations"][0]["source_refs"], ["src-002"])

    def test_project_change_without_summary_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = MutableProvider(
                ProcessingProposal(None, (_add(scope="project", scope_id="proj_orca"),))
            )
            with self.assertRaisesRegex(ValueError, "requires a Project Summary"):
                Step3Pipeline(
                    Processor(provider),
                    self._storage(root, identifiers=("run-add", "memory-add")),
                ).run(
                    _batch("turn-add"),
                    scope=MemoryScope("project", "proj_orca", "Orca"),
                )
            self.assertFalse((root / "vault").exists())

    def test_partial_publication_recovers_without_second_provider_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            provider = MutableProvider(ProcessingProposal(None, (_add(),)))
            stopped = False

            def fault(point: str) -> None:
                nonlocal stopped
                if point == "after-output:out-001" and not stopped:
                    stopped = True
                    raise OSError("simulated stop")

            pipeline = Step3Pipeline(
                Processor(provider),
                self._storage(
                    root,
                    identifiers=("run-add", "memory-add"),
                    fault=fault,
                ),
            )
            batch = _batch("turn-add")
            with self.assertRaisesRegex(OSError, "simulated stop"):
                pipeline.run(batch, scope=MemoryScope("general", "general"))

            result = pipeline.run(batch, scope=MemoryScope("general", "general"))
            self.assertEqual(result.status, "replay")
            self.assertEqual(provider.calls, 1)
            self.assertEqual(
                len(list((root / "vault").glob("**/manifests/**/*.json"))), 1
            )


if __name__ == "__main__":
    unittest.main()
