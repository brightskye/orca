# Orca semantic provider rules v0.1

This is the one-pass runtime projection of the accepted Orca semantic boundary
in `../../docs/governance/memory-system-contract.md`. It deliberately exposes only the
fields needed by the Cairn integration adapter. It does not grant canonical
authority and does not perform Curator governance.

Given normalized authored conversation events, return one JSON object with a
`decisions` array. Each decision may select one event by its zero-based
`event_index` and propose one atomic provisional memory unit with:

- `content`: concise, durable meaning grounded only in that event;
- `intent`: `explicit` only when the authored event clearly asks to remember,
  save, capture, or preserve the meaning; otherwise `implicit`;
- `candidate_type`: one of `project_state`, `decision`, `preference`,
  `procedure`, `lesson`, `person_context`, `working_context`, or
  `general_knowledge`;
- `proposed_scope`: `project-specific`, `owner-global`, or `general`.

Rules:

1. Prefer no decision when usefulness, attribution, current meaning, or support
   is uncertain. A miss is safer than a wrong durable memory.
2. Preserve the proposition's polarity, attribution, temporal meaning,
   qualifiers, and applicability. Do not turn a question, hypothetical,
   historical preference, third-party report, or rejected statement into a
   current assertion by Owner.
3. Do not extract routine instructions for the immediate task, acknowledgments,
   raw logs, plugin/system envelopes, secrets, credential-adjacent material,
   or unsupported conclusions.
4. `project-specific` requires evidence that the meaning applies to the named
   or observed project. Observed project is provenance, not automatic scope.
5. `owner-global` is only for an explicit cross-project Owner preference or
   operating rule. Use `general` only for impersonal reusable knowledge.
6. Keep content provisional and atomic. Do not emit lifecycle, authority,
   canonical destination, promotion, verification, or Curator fields.
7. Do not invent relations or provenance. Harness, session, event, source URI,
   artifact path, and source-text hash are intentionally withheld from the
   model and bound locally by the deterministic adapter after this pass.
8. Evaluate each event independently. Do not suppress a grounded unit because
   another event expresses similar meaning; exact retry deduplication and
   identity are deterministic adapter responsibilities.
9. This v0.1 provider selects at most one atomic unit per event. When an event
   contains multiple meanings and no single unit can preserve them safely,
   abstain rather than merge claims.
10. Return only JSON matching the supplied response schema. Return an empty
   `decisions` array when nothing is safely memory-worthy.
