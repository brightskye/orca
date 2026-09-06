---
type: research
status: informational
updated: 2026-08-28
---

# Measuring interaction preferences

> [!WARNING]
> Archived research evidence. Current interaction behavior is owned by the
> [Interaction Preference Specification](../../specifications/interaction-preferences.md)
> and [Interaction Guidance Specification](../../specifications/interaction-guidance.md).

This note asks whether psychology, psychometrics, linguistics, or HCI
provides an accepted way to rank one person's conversational and presentation
preferences for Orca dimensions such as detail, structure, question frequency,
technical depth, tone, and progress updates.

Sources are original instrument papers, first-party manuals, official
standards, or first-party institutional sources. The conclusions below are
about measurement for a personal assistant, not clinical or employment
assessment.

## Verdict

There is **no universal, validated standard that ranks a person's preferred
assistant response style across these dimensions**. There are useful adjacent
instruments, but each measures a narrower construct, population, task, or
outcome:

- Psychometric standards explain how to validate a measure; they do not supply
  a ready-made interaction-preference scale.
- Communication-style inventories measure reported or observed communication
  behavior, not necessarily the response style a person wants from an agent.
- Linguistic tools measure features of language use. They should not be used
  to infer a durable preference from wording alone.
- HCI scales measure usability, workload, or satisfaction in a specified
  context, rather than a stable personal preference.
- Pairwise-comparison models can rank explicitly chosen response alternatives,
  but the ranking is a local preference model, not a personality score.

Therefore Orca should **rank response options, not rank the human**. It should
store scoped, evidence-backed interaction observations and use them as
noncanonical presentation guidance. It must not infer personality, ability,
mental state, or a general communication identity.

## Relevant primary precedents

| Area | Primary precedent | What it measures | Relevance and limitation for Orca |
|---|---|---|---|
| Psychometrics | [AERA/APA/NCME, *Standards for Educational and Psychological Testing* (2014)](https://www.aera.net/Publications/Books/Standards-for-Educational-Psychological-Testing-2014-Edition?Tags=63064) | Validity, reliability, fairness, and responsible interpretation of tests | The governing measurement framework. A custom Orca score would need evidence for its intended use and population; the Standards do not provide weights for conversational preferences. |
| Communication style | [de Vries et al., *The Communication Styles Inventory*](https://doi.org/10.1177/0093650211413571) | Self-reported communication behavior: expressiveness, preciseness, questioningness, emotionality, and related domains | Directly overlaps with structure, concision, and questioning. The reported instrument has domain reliabilities above .80, but it measures the person's style, not what an assistant should output, and its context/population cannot be assumed for Orca. |
| Technology-mediated communication preference | [Parker, Chignell, and Ruppenthal, *Communication Preferences Inventory* (CPI)](https://doi.org/10.1145/782115.782123) | Preferences concerning technology-mediated communication and collaboration; the paper reports a 62-item inventory, factor analysis, and preliminary behavior prediction | The closest conceptual precedent. It is an early, domain-specific instrument with a small validation sample (110 for the reported factor structure) and explicitly presents normalization and further validation as future work. It is a precedent, not a drop-in Orca standard. |
| Context-specific communication preference | [Farin, Gramm, and Kosiol, KOPRA questionnaire](https://pubmed.ncbi.nlm.nih.gov/20219317/) | Patient preferences for physician communication across four scales | Demonstrates that direct preference questionnaires can be reliable in a defined domain; reported physician-version alphas were .80–.92. Medical role and context make it inappropriate as a general assistant style scale. |
| Information preference | [Ho, Hagmann, and Loewenstein, *Measuring Information Preferences*](https://doi.org/10.1287/mnsc.2019.3543) | Desire to obtain or avoid potentially unpleasant information | Useful evidence that information preference can be domain-specific and can predict behavior. It does not measure answer length, tone, or formatting, so it should not be generalized to those dimensions. |
| Cognitive/detail-adjacent trait | [Viswanathan, *Individual Differences in Need for Precision*](https://doi.org/10.1177/0146167297237005) | Preference for relatively fine-grained processing | Shows that a precision-related preference can be operationalized and validated, including reliability and behavioral validity evidence. It is a processing preference, not a validated measure of desired assistant response detail. |
| Linguistic analysis | [Pennebaker, Francis, and Booth, *LIWC-22 Development and Psychometrics Manual*](https://www.liwc.app/static/documents/LIWC-22%20Manual%20-%20Development%20and%20Psychometrics.pdf) | Dictionary-based language categories and summary measures, with reliability/validity studies | Suitable for describing language samples. The manual emphasizes that self-report and behavioral measures can reflect different constructs and that language varies strongly by context. Do not infer a durable presentation preference from word counts or style alone. |
| HCI usability | [ISO 9241-11:2018](https://www.iso.org/standard/63500.html) | Usability as an outcome of use in a specified context | Provides the useful idea that effectiveness, efficiency, and satisfaction are context-bound outcomes. It is not a personal communication-preference inventory and does not prescribe an aggregation rule. |
| HCI workload | [NASA Task Load Index (NASA-TLX)](https://www.nasa.gov/human-systems-integration-division/nasa-task-load-index-tlx/) | Subjective workload across mental, physical, temporal, performance, effort, and frustration dimensions | Could evaluate whether an answer format imposes too much effort or frustration in a task. It cannot tell Orca that a person has a general preference for concise or detailed answers. |
| Explicit preference ranking | [Thurstone, “A Law of Comparative Judgment”](https://doi.org/10.1037/h0070288); [Bradley and Terry, “Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons”](https://doi.org/10.1093/biomet/39.3-4.324) | Relative ordering of alternatives from pairwise judgments | A sound method for asking “which response do you prefer, A or B?” and estimating a local ranking with uncertainty. It ranks alternatives under a defined task; it does not validate a latent personality or permanent preference. |

## What the precedents imply for Orca

### 1. Define a narrow construct before scoring it

“Likes detail” is not one measurable construct. It can mean at least:

- preferred answer length;
- desired explanatory depth;
- tolerance for technical terminology;
- preference for examples or citations;
- desire for exhaustive alternatives; or
- willingness to spend time reading.

Orca should keep separate dimensions such as `detail`, `structure`,
`question_frequency`, `technical_depth`, `tone`, and `progress_updates`. Each
observation should describe the desired assistant behavior in a defined
context, not a trait of the Owner.

### 2. Direct elicitation is stronger than passive language inference

The most defensible signal is an explicit Owner statement or a direct choice
between controlled response examples. For example:

```text
For project reviews, which default do you prefer?
A. A short conclusion with only necessary detail
B. A detailed explanation with alternatives and tradeoffs
```

Several pairwise choices can produce an ordinal preference model for that
dimension. A single choice should remain scoped to its task unless the Owner
explicitly marks it as general. The model should retain uncertainty and the
examples/context used for the choice.

### 3. Corrections are evidence, not a personality diagnosis

“That answer is too long” is strong evidence about the preceding answer in
that context. It may support a broader preference after repeated, aligned
corrections across comparable contexts, but it is not proof of a stable trait.
The same Owner may prefer concise status updates and detailed technical design
reviews. Current instructions must always override any stored profile.

### 4. Language behavior is context-sensitive

LIWC's own manual reports that language measures vary across corpora and that
self-report and behavioral measures may reflect different constructs. A short
Owner message may reflect urgency, device constraints, or the current task,
not a preference for short assistant replies. Observed message length,
vocabulary, punctuation, or question count can be supporting evidence only;
they must not activate a durable Orca preference by themselves.

### 5. Utility can be measured without inferring a trait

For product evaluation, Orca can compare response variants using explicit
Owner feedback such as “too short / right / too detailed,” task completion,
follow-up repair requests, and occasional pairwise choices. These are
interaction outcomes. They should be reported as evidence that a format worked
in a context, not as a psychological diagnosis.

## Assessment of the proposed 4/2/1 weights

The proposed weights—explicit lasting preference = 4, direct correction = 2,
positive feedback = 1—have **no established scientific or psychometric basis
found in the primary sources reviewed**. They are acceptable as an Orca policy
heuristic if clearly named and versioned as such, but they must not be called a
validated confidence score or measurement standard.

The main risk is false precision: a score of 4 is not demonstrably twice as
strong as a score of 2, and a positive reaction is not necessarily half as
informative as a correction. Context, scope, recency, repeated exposure, and
the quality of the response being judged matter more than arbitrary arithmetic.

If Orca keeps numeric bookkeeping for implementation simplicity, use it only
as an internal evidence ledger:

```yaml
dimension: detail
observation: prefer-concise
evidence_class: explicit_general | direct_correction | positive_feedback | indirect_behavior
scope: global | agent | project | conversation
source_turn_id: ...
observed_at: ...
policy_version: interaction-evidence/1
```

Do not expose the sum as “the Owner's preference strength.” Prefer the
following conservative states for automatic behavior:

```text
not_observed → provisional → confirmed_by_owner
                         ↘ conflicting / inactive
```

- `explicit_general` may become confirmed for its stated scope immediately.
- `direct_correction` may create a provisional scoped observation; repeated
  aligned corrections can trigger an Owner confirmation request.
- `positive_feedback` supports a provisional observation but should rarely
  activate one alone.
- `indirect_behavior` may be retained for analysis but must not activate a
  durable profile.
- Any materially conflicting evidence should suppress automatic guidance for
  that dimension until the Owner resolves it.

This state model is easier to explain and safer to audit than treating 4, 2,
and 1 as interval-scale measurements.

## Recommended Orca measurement contract

1. **Measure only presentation behavior.** Do not infer personality, emotion,
   intelligence, motives, health, protected traits, or a global communication
   identity.
2. **Prefer direct evidence.** Accept explicit scope-marked instructions and
   optional pairwise comparisons. Treat corrections and positive feedback as
   observations tied to the judged output.
3. **Keep scope and context.** Store whether the observation is global,
   agent-specific, project-specific, or conversation-specific, along with the
   task context and source turn timestamp.
4. **Use provisional states.** Aggregate only comparable observations. Require
   explicit confirmation before promoting an inferred cross-context pattern to
   durable automatically loaded guidance.
5. **Fail closed on conflict.** Do not choose between incompatible styles by
   recency alone. Ask the Owner or keep both as context-specific preferences.
6. **Evaluate empirically.** Track correction rate, explicit satisfaction,
   repair turns, and task success by dimension. Use those metrics to revise
   Orca policy, not to make claims about the Owner's psychology.
7. **Respect psychometric limits.** If Orca later claims a validated scale, it
   would need a documented construct definition, item design, target
   population, reliability, validity, fairness, and test-retest evaluation in
   line with the AERA/APA/NCME Standards. Phase 1 should make no such claim.

## Bottom line

Existing research supports borrowing methods and vocabulary—not importing a
universal score. The closest useful precedents are communication-preference
questionnaires and pairwise comparative judgment. For Orca, a small,
Owner-controlled, context-scoped evidence model is more defensible than
passively ranking the human or treating the 4/2/1 heuristic as psychometrics.
