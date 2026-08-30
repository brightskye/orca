import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from orca_memory.retrieval import (
    AdapterHit,
    AgentCairnRetrievalAdapter,
    MAX_DOCUMENT_TOKENS,
    MAX_RESULTS,
    MAX_TOTAL_TOKENS,
    ProjectionIndex,
    ProjectionSource,
    RecallRequest,
    RecallService,
    RetrievalUnavailable,
    RetrievalValidationError,
    build_projection,
    projection_from_conversation,
    load_projection_index,
    rebuild_projection_index,
    projections_from_conflict,
)


def _source(
    projection_id: str,
    meaning: str,
    *,
    path: str | None = None,
    artifact_kind: str = "typed-memory-record",
    authority: str = "noncanonical",
    scope: str = "project",
    scope_id: str = "proj_orca",
    status: str = "current",
    visibility: str = "owner",
    memory_id: str | None = None,
    structural_id: str | None = None,
    source_updated_at: str | None = None,
    stale: bool = False,
) -> ProjectionSource:
    return ProjectionSource(
        path=path or f"System/Orca Memory/{projection_id}.md",
        source_text=f"# Source {projection_id}\n\n{meaning}\n",
        meaning=meaning,
        artifact_kind=artifact_kind,
        authority=authority,
        scope=scope,
        scope_id=scope_id,
        status=status,
        projection_id=projection_id,
        memory_id=memory_id,
        visibility=visibility,
        structural_id=structural_id,
        source_updated_at=source_updated_at,
        stale=stale,
    )


class RecordingAdapter:
    version = "test-adapter/1"

    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self.scores = scores or {}
        self.seen: tuple[str, ...] = ()

    def rank(self, query, projections, limit):
        self.seen = tuple(item.projection_id for item in projections)
        return tuple(
            AdapterHit(item.projection_id, self.scores.get(item.projection_id, 1.0))
            for item in projections
        )


class RetrievalTests(unittest.TestCase):
    def test_projection_hash_is_deterministic_and_stale_or_secret_sources_fail_closed(self):
        source = _source("mem_one", "The project uses deterministic indexing.")
        projection = build_projection(source)
        assert projection is not None
        self.assertEqual(
            projection.source_sha256,
            hashlib.sha256(source.source_text.encode()).hexdigest(),
        )
        self.assertIsNone(build_projection(_source("mem_stale", "old", stale=True)))
        with self.assertRaises(RetrievalValidationError):
            build_projection(_source("mem_secret", "api_key=not-a-safe-value"))
        with self.assertRaises(RetrievalValidationError):
            build_projection(
                _source(
                    "candidate",
                    "candidate text",
                    artifact_kind="knowledge-candidate",
                )
            )

    def test_conflict_projection_keeps_each_active_variant_without_a_winner(self):
        conflict = SimpleNamespace(
            status="conflict",
            authority="noncanonical",
            scope="project",
            scope_id="proj_orca",
            memory_id="mem_conflict",
            kind="decision",
            variants=(
                SimpleNamespace(variant_id="v1", label="Earlier policy", position="Use policy one"),
                SimpleNamespace(variant_id="v2", label="Later policy", position="Use policy two"),
            ),
            render=lambda: "# conflict source",
        )
        projections = projections_from_conflict(conflict, path="records/conflict.md")
        self.assertEqual(tuple(item.projection_id for item in projections), ("mem_conflict:v1", "mem_conflict:v2"))
        self.assertEqual({item.status for item in projections}, {"conflict"})
        self.assertEqual({item.authority for item in projections}, {"noncanonical"})
        self.assertIn("Earlier policy", projections[0].meaning)
        self.assertIn("Later policy", projections[1].meaning)

    def test_hard_filters_are_applied_before_adapter_ranking(self):
        sources = (
            _source("allowed", "deployment policy for Orca", memory_id="mem_allowed"),
            _source(
                "wrong-project",
                "deployment policy for another project",
                scope_id="proj_other",
                memory_id="mem_other",
            ),
            _source(
                "private",
                "deployment policy private",
                visibility="private",
                memory_id="mem_private",
            ),
            _source(
                "closed",
                "deployment policy closed",
                status="closed",
                memory_id="mem_closed",
            ),
            _source(
                "canonical",
                "deployment policy canonical",
                authority="canonical",
                memory_id="mem_canonical",
            ),
        )
        index = ProjectionIndex.rebuild(sources)
        adapter = RecordingAdapter()
        response = RecallService(index, adapter).recall(
            RecallRequest(
                question="deployment policy",
                project_id="proj_orca",
                allowed_authorities=frozenset({"noncanonical"}),
            )
        )
        self.assertEqual(adapter.seen, ("allowed",))
        self.assertEqual([item.memory_id for item in response.results], ["mem_allowed"])
        self.assertNotIn("mem_private", str(response))
        self.assertNotIn("wrong-project", str(response))

    def test_canonical_first_only_within_relevance_tie(self):
        sources = (
            _source("shallow-strong", "deployment policy strong shallow"),
            _source(
                "canonical-tie",
                "deployment policy canonical tie",
                authority="canonical",
            ),
            _source(
                "canonical-weak",
                "deployment policy canonical weak",
                authority="canonical",
            ),
        )
        adapter = RecordingAdapter(
            {"shallow-strong": 0.95, "canonical-tie": 0.93, "canonical-weak": 0.20}
        )
        response = RecallService(ProjectionIndex.rebuild(sources), adapter).recall(
            RecallRequest(question="deployment policy")
        )
        self.assertEqual(
            [item.path for item in response.results],
            [
                "System/Orca Memory/canonical-tie.md",
                "System/Orca Memory/shallow-strong.md",
                "System/Orca Memory/canonical-weak.md",
            ],
        )
        self.assertEqual(response.results[0].authority, "canonical")
        # A materially stronger shallow result is still ranked ahead of weak
        # canonical content even though canonical is labelled separately.
        self.assertGreater(response.results[1].score, response.results[2].score)

    def test_duplicate_identity_and_strong_overlap_collapse_before_result_limit(self):
        sources = (
            _source("first", "same deterministic deployment policy", memory_id="mem_dup"),
            _source("second", "same deterministic deployment policy", memory_id="mem_dup"),
            _source("overlap", "same deterministic deployment policy", memory_id="mem_overlap"),
            *tuple(_source(f"extra-{index}", f"unique deployment detail {index}") for index in range(8)),
        )
        adapter = RecordingAdapter({source.projection_id: 1.0 for source in sources})
        response = RecallService(ProjectionIndex.rebuild(sources), adapter).recall(
            RecallRequest(question="deployment policy")
        )
        self.assertLessEqual(len(response.results), MAX_RESULTS)
        self.assertIn("duplicate identity", response.omitted)
        self.assertIn("strongly overlapping result", response.omitted)
        self.assertIn("result-count limit", response.omitted)

    def test_exact_conversation_includes_only_associated_project_material(self):
        exact = projection_from_conversation(
            conversation_id="conversation_one",
            structural_id="conv:orca--abc123",
            path="System/Orca Memory/conversation-summaries/conversation_one.md",
            source_text="# Conversation\n\nRecall deployment decisions.",
            meaning="Recall deployment decisions from this conversation.",
            scope="project",
            scope_id="proj_orca",
        )
        summary_source = _source(
            "project-summary:proj_orca",
            "Orca project deployment summary",
            path="System/Orca Memory/project-summary.md",
            artifact_kind="project-summary",
            structural_id="project-summary:proj_orca",
        )
        record_source = _source(
            "record-orca",
            "Orca deployment decision",
            path="System/Orca Memory/orca-record.md",
            memory_id="mem_orca",
        )
        other_source = _source(
            "record-other",
            "Other deployment decision",
            path="System/Orca Memory/other-record.md",
            scope_id="proj_other",
            memory_id="mem_other",
        )
        summary = build_projection(summary_source)
        record = build_projection(record_source)
        other = build_projection(other_source)
        assert summary is not None and record is not None and other is not None
        adapter = RecordingAdapter()
        response = RecallService(
            ProjectionIndex((exact, summary, record, other)), adapter
        ).recall(RecallRequest(question="conv:orca--abc123"))
        self.assertEqual(
            set(adapter.seen), {exact.projection_id, summary.projection_id, record.projection_id}
        )
        self.assertNotIn(other.projection_id, adapter.seen)
        self.assertLessEqual(len(response.results[0].excerpt.split()), 2000)
        self.assertTrue(any(item.artifact_kind == "project-summary" for item in response.results))
        self.assertEqual(response.results[0].structural_id, "conv:orca--abc123")

    def test_agentcairn_adapter_is_replaceable_and_cannot_return_ineligible_items(self):
        projection = build_projection(_source("allowed", "safe deployment policy"))
        assert projection is not None
        calls = []

        def ranker(query, projections, limit):
            calls.append((query, tuple(item.projection_id for item in projections), limit))
            return (("allowed", 0.8),)

        adapter = AgentCairnRetrievalAdapter(ranker)
        response = RecallService(ProjectionIndex((projection,)), adapter).recall(
            RecallRequest(question="deployment policy")
        )
        self.assertEqual(response.results[0].path, projection.path)
        self.assertEqual(calls, [("deployment policy", ("allowed",), 1)])

        def malicious(query, projections, limit):
            return (AdapterHit("not-allowed", 1.0),)

        with self.assertRaises(RetrievalValidationError):
            RecallService(
                ProjectionIndex((projection,)), AgentCairnRetrievalAdapter(malicious)
            ).recall(RecallRequest(question="deployment policy"))

    def test_governed_local_agentcairn_ranks_only_prefiltered_projections(self):
        allowed = build_projection(_source("allowed-local", "deployment policy for Orca"))
        excluded = build_projection(
            _source(
                "excluded-local", "deployment policy secret project",
                scope_id="proj_other",
            )
        )
        assert allowed is not None and excluded is not None
        response = RecallService(
            ProjectionIndex((allowed, excluded)),
            AgentCairnRetrievalAdapter.local(),
        ).recall(
            RecallRequest(question="deployment policy", project_id="proj_orca")
        )
        self.assertEqual([item.path for item in response.results], [allowed.path])
        self.assertNotIn("excluded-local", str(response))

    def test_budgets_bound_ordinary_results_and_never_scan_when_index_unavailable(self):
        meaning = "deployment " + " ".join(f"detail{index}" for index in range(2200))
        projection = build_projection(_source("large", meaning))
        assert projection is not None
        response = RecallService(
            ProjectionIndex((projection,)), RecordingAdapter()
        ).recall(RecallRequest(question="deployment"))
        self.assertEqual(len(response.results), 1)
        self.assertLessEqual(len(response.results[0].excerpt.split()), MAX_DOCUMENT_TOKENS)
        self.assertLessEqual(len(response.results[0].excerpt.split()) + 12, MAX_TOTAL_TOKENS)

        unavailable_adapter = RecordingAdapter()
        with self.assertRaises(RetrievalUnavailable):
            RecallService(
                ProjectionIndex((projection,), available=False), unavailable_adapter
            ).recall(RecallRequest(question="deployment"))
        self.assertEqual(unavailable_adapter.seen, ())

    def test_project_alias_must_resolve_without_guessing(self):
        projection = build_projection(_source("allowed", "deployment policy"))
        assert projection is not None
        service = RecallService(
            ProjectionIndex((projection,)),
            RecordingAdapter(),
            project_alias_resolver=lambda alias: "proj_orca" if alias.casefold() == "orca" else None,
        )
        response = service.recall(RecallRequest(question="deployment", project_alias="ORCA"))
        self.assertEqual(response.applied_filters["project_id"], "proj_orca")
        with self.assertRaises(RetrievalValidationError):
            service.recall(RecallRequest(question="deployment", project_alias="unknown"))

    def test_disposable_index_rebuild_load_and_hash_drift_fail_without_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vault = root / "vault"
            runtime = root / "runtime"
            relative = "System/Orca Memory/shallow/general/knowledge/safe.md"
            source_path = vault / relative
            source_path.parent.mkdir(parents=True)
            source = _source("persisted", "deployment policy", path=relative)
            source_path.write_text(source.source_text, encoding="utf-8")

            rebuilt = rebuild_projection_index((source,), runtime_root=runtime)
            loaded = load_projection_index(runtime, vault)

            self.assertEqual(loaded, rebuilt)
            index_path = runtime / "retrieval/index.json"
            self.assertEqual(index_path.stat().st_mode & 0o077, 0)
            source_path.write_text("changed deployment policy", encoding="utf-8")
            with self.assertRaisesRegex(RetrievalUnavailable, "hash is stale"):
                load_projection_index(runtime, vault)
            index_path.unlink()
            with self.assertRaisesRegex(RetrievalUnavailable, "unavailable"):
                load_projection_index(runtime, vault)


if __name__ == "__main__":
    unittest.main()
