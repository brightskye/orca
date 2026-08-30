from __future__ import annotations

import hashlib
import unittest

from orca_memory.conversation import NormalizedTurn
from orca_memory.interaction import (
    AdaptiveProfile,
    InteractionObservation,
    InteractionScope,
    ObservationAbstention,
    ObservationProposal,
    ProfileEntry,
    admit_observation,
    compile_guidance,
    consolidate_profile,
    owner_resolved_entry,
)
from orca_memory.segmentation import segment_turn


def _turn(turn_id: str, role: str, occurred_at: str, text: str = "synthetic"):
    turn = NormalizedTurn(
        connector_id="codex-local",
        conversation_id="conversation-feedback",
        turn_id=turn_id,
        occurred_at=occurred_at,
        source_uri=f"codex://session/conversation-feedback/event/{turn_id}",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        source_role=role,
    )
    return segment_turn(turn, max_segment_tokens=8_000)[0]


def _observation(
    observation_id: str,
    conversation_id: str,
    occurred_at: str,
    *,
    value: str | None = "concise",
    direction: str | None = None,
    scope: InteractionScope | None = None,
    lasting: bool = False,
    evidence_class: str = "direct-correction",
    replaces_prior: bool = False,
) -> InteractionObservation:
    return InteractionObservation(
        observation_id=observation_id,
        dimension="detail",
        context="status-update" if not lasting else "general",
        scope=scope or InteractionScope("agent", agent_id="codex"),
        evidence_class=evidence_class,
        conversation_id=conversation_id,
        feedback_turn_id=f"feedback-{conversation_id}",
        evaluated_assistant_turn_ids=(f"answer-{conversation_id}",),
        preceding_request_turn_id=f"request-{conversation_id}",
        occurred_at=occurred_at,
        value=value,
        direction=direction,
        lasting=lasting,
        replaces_prior=replaces_prior,
    )


class ObservationTests(unittest.TestCase):
    def _proposal(self, **values) -> ObservationProposal:
        fields = dict(
            dimension="detail",
            value="concise",
            context="status-update",
            scope=InteractionScope("agent", agent_id="codex"),
            evidence_class="direct-correction",
            feedback_turn_id="feedback",
            evaluated_assistant_turn_ids=("answer",),
            preceding_request_turn_id="request",
        )
        fields.update(values)
        return ObservationProposal(**fields)

    def test_complete_feedback_context_admits_content_free_deterministic_observation(self) -> None:
        segments = (
            _turn("request", "owner", "2026-08-30T10:00:00Z", "Give a status."),
            _turn("answer", "assistant", "2026-08-30T10:01:00Z", "A long status."),
            _turn("feedback", "owner", "2026-08-30T10:02:00Z", "Shorter."),
        )
        first = admit_observation(self._proposal(), segments)
        second = admit_observation(self._proposal(), segments)
        self.assertIsInstance(first, InteractionObservation)
        self.assertEqual(first, second)
        self.assertEqual(first.occurred_at, "2026-08-30T10:02:00Z")
        encoded = str(first.value_dict())
        self.assertNotIn("Give a status", encoded)
        self.assertNotIn("A long status", encoded)
        self.assertNotIn("Shorter", encoded)

    def test_missing_or_reversed_context_abstains_without_classification(self) -> None:
        missing = admit_observation(
            self._proposal(),
            (_turn("request", "owner", "2026-08-30T10:00:00Z"),),
        )
        self.assertIsInstance(missing, ObservationAbstention)
        self.assertEqual(missing.abstention_reason, "missing-evaluated-response")
        reversed_context = admit_observation(
            self._proposal(),
            (
                _turn("answer", "assistant", "2026-08-30T10:01:00Z"),
                _turn("request", "owner", "2026-08-30T10:00:00Z"),
                _turn("feedback", "owner", "2026-08-30T10:02:00Z"),
            ),
        )
        self.assertEqual(reversed_context.abstention_reason, "ambiguous-target")

    def test_controlled_values_and_general_context_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            self._proposal(dimension="personality")
        with self.assertRaises(ValueError):
            self._proposal(value=None, direction=None)
        with self.assertRaises(ValueError):
            self._proposal(context="general")
        with self.assertRaises(ValueError):
            self._proposal(lasting=True)


class ProfileTests(unittest.TestCase):
    scope = InteractionScope("agent", agent_id="codex")

    def test_three_distinct_conversations_activate_and_duplicates_count_once(self) -> None:
        observations = (
            _observation("obs-1", "c1", "2026-08-01T10:00:00Z"),
            _observation("obs-2", "c2", "2026-08-02T10:00:00Z"),
            _observation("obs-3", "c3", "2026-08-03T10:00:00Z"),
            _observation("obs-4", "c3", "2026-08-04T10:00:00Z"),
        )
        profile = consolidate_profile(
            observations, scope=self.scope, as_of="2026-08-30T10:00:00Z"
        )
        self.assertEqual(len(profile.entries), 1)
        entry = profile.entries[0]
        self.assertEqual(entry.status, "active")
        self.assertEqual(entry.supporting_conversations, 3)
        self.assertEqual(entry.last_evidence_at, "2026-08-04T10:00:00Z")
        self.assertTrue(entry.expires_at.startswith("2027-01-31"))

    def test_one_or_two_pending_and_expired_evidence_create_no_entry(self) -> None:
        two = tuple(
            _observation(f"obs-{index}", f"c{index}", f"2026-08-0{index}T10:00:00Z")
            for index in (1, 2)
        )
        self.assertEqual(
            consolidate_profile(two, scope=self.scope, as_of="2026-08-30T10:00:00Z").entries,
            (),
        )
        old = two + (_observation("obs-3", "c3", "2026-08-03T10:00:00Z"),)
        self.assertEqual(
            consolidate_profile(old, scope=self.scope, as_of="2027-03-01T10:00:00Z").entries,
            (),
        )

    def test_explicit_lasting_activates_immediately_without_expiry(self) -> None:
        explicit = _observation(
            "obs-explicit",
            "c1",
            "2026-08-20T10:00:00Z",
            lasting=True,
            evidence_class="explicit-general",
        )
        entry = consolidate_profile(
            (explicit,), scope=self.scope, as_of="2026-08-30T10:00:00Z"
        ).entries[0]
        self.assertEqual(entry.basis, "explicit")
        self.assertIsNone(entry.expires_at)
        self.assertIsNone(entry.supporting_conversations)

    def test_two_qualified_outcomes_become_conflicting_and_compile_nothing(self) -> None:
        observations = tuple(
            _observation(f"obs-a-{index}", f"a{index}", f"2026-08-0{index}T10:00:00Z")
            for index in (1, 2, 3)
        ) + tuple(
            _observation(
                f"obs-b-{index}",
                f"b{index}",
                f"2026-08-1{index}T10:00:00Z",
                value="detailed",
            )
            for index in (1, 2, 3)
        )
        profile = consolidate_profile(
            observations, scope=self.scope, as_of="2026-08-30T10:00:00Z"
        )
        self.assertEqual(profile.entries[0].status, "conflicting")
        self.assertEqual(
            compile_guidance((profile,), context="status-update", agent_id="codex"),
            "",
        )

    def test_incompatible_explicit_evidence_conflicts_until_clear_replacement(self) -> None:
        first = _observation(
            "obs-a", "c1", "2026-08-01T10:00:00Z", lasting=True,
            evidence_class="explicit-general", value="concise",
        )
        second = _observation(
            "obs-b", "c2", "2026-08-02T10:00:00Z", lasting=True,
            evidence_class="explicit-general", value="detailed",
        )
        profile = consolidate_profile(
            (first, second), scope=self.scope, as_of="2026-08-30T10:00:00Z"
        )
        self.assertEqual(profile.entries[0].status, "conflicting")
        replacement = _observation(
            "obs-c", "c3", "2026-08-03T10:00:00Z", lasting=True,
            evidence_class="explicit-general", value="balanced", replaces_prior=True,
        )
        replaced = consolidate_profile(
            (first, second, replacement), scope=self.scope, as_of="2026-08-30T10:00:00Z"
        )
        self.assertEqual((replaced.entries[0].status, replaced.entries[0].value), ("active", "balanced"))

    def test_owner_resolution_is_explicit_and_nonexpiring(self) -> None:
        entry = owner_resolved_entry(
            dimension="detail",
            context="status-update",
            value="concise",
            resolved_at="2026-08-30T10:00:00Z",
        )
        self.assertEqual(entry.basis, "owner-resolution")
        self.assertIsNone(entry.expires_at)

    def test_profile_render_is_byte_deterministic_and_noncanonical(self) -> None:
        profile = consolidate_profile(
            tuple(
                _observation(f"obs-{index}", f"c{index}", f"2026-08-0{index}T10:00:00Z")
                for index in (1, 2, 3)
            ),
            scope=self.scope,
            as_of="2026-08-30T10:00:00Z",
        )
        self.assertEqual(profile.render(), profile.render())
        self.assertIn("authority: noncanonical", profile.render())
        self.assertNotIn("feedback_turn", profile.render())


class GuidanceTests(unittest.TestCase):
    def _profile(self, scope, value, *, status="active", context="implementation"):
        entry = ProfileEntry(
            f"detail--{context}",
            "detail",
            context,
            status,
            value=value if status == "active" else None,
            basis="explicit" if status == "active" else None,
            last_evidence_at="2026-08-30T10:00:00Z" if status == "active" else None,
            candidates=() if status == "active" else (),
        )
        return AdaptiveProfile(scope, (entry,))

    def test_exact_template_and_more_specific_scope_replaces_broader(self) -> None:
        global_profile = self._profile(InteractionScope("global"), "detailed")
        agent_profile = self._profile(
            InteractionScope("agent", agent_id="codex"), "concise"
        )
        compiled = compile_guidance(
            (global_profile, agent_profile),
            context="implementation",
            agent_id="codex",
        )
        self.assertEqual(
            compiled,
            "During implementation work, keep the response concise and omit nonessential background.",
        )

    def test_owner_override_removes_profile_key_and_budget_never_truncates(self) -> None:
        profile = self._profile(InteractionScope("agent", agent_id="codex"), "detailed")
        self.assertEqual(
            compile_guidance(
                (profile,),
                context="implementation",
                agent_id="codex",
                overridden_keys=frozenset({("implementation", "detail")}),
            ),
            "",
        )
        self.assertEqual(
            compile_guidance(
                (profile,), context="implementation", agent_id="codex", token_budget=10
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
