# Orca quality

This area explains how Orca is verified and which evidence supports Phase 1
acceptance.

- [Acceptance](acceptance.md) owns the required scenarios, thresholds, and
  accepted Phase 1 verdict.
- [Test Strategy](test-strategy.md) owns test levels, fixtures, suite coverage,
  evaluation boundaries, and the canonical regression command.
- Executable evaluation cases and evaluation-only runners live with other
  repeatable checks under `tests/evals/`; they are not installed Orca runtime
  modules.
- Private retained results live under the ignored `.local/evidence/` area and
  are not public project authority.

Current capability and verification claims belong in
[Project Record: Current](../project-record/current.md).
