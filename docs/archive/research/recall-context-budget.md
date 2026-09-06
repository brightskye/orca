---
type: research
status: informational
updated: 2026-08-28
---

# Recall and processor context budget

> [!WARNING]
> Archived research evidence. Current recall budgets are owned by the
> [Retrieval Contract](../../specifications/retrieval.md) and
> [Configuration Specification](../../specifications/configuration.md).

This note answers two questions for Orca:

1. Does the local handoff skill define a token limit that Orca should copy?
2. What context and recall budgets are reasonable across popular open-weight
   models used locally or self-hosted?

Sources are first-party model cards, vendor documentation, or the skill file
itself. A model's advertised maximum is a capability ceiling, not a reason to
fill every request to that size.

## Short answer

A locally installed Codex handoff skill (`handoff/SKILL.md`) was reviewed as a
source. It defines the purpose and contents of a handoff, but **does not define
a numeric token or character limit**. It says to summarize, reference existing
artifacts, and redact sensitive information. Orca therefore needs its own
bounded contract.

The current Orca defaults remain reasonable and should become configuration:

```yaml
context:
  model_window_tokens: 32768       # supplied by the selected runtime
  processor_input_tokens: 20000
  processor_output_tokens: 4000
  conversation_handoff_tokens: 2000
  recall_total_tokens: 4000
  recall_per_document_tokens: 1500
  recall_max_results: 6
```

**Inference:** This is a portable starting point for a 32K local model. A
2,000-token handoff is roughly 1,300–1,600 words of ordinary prose; a
4,000-token recall package is roughly 2,800–3,200 words. Code, YAML, tables,
and identifiers consume more tokens.

## First-party context-window evidence

| Family or representative model | Official native/default context | Optional or variant-specific extension | Local-use implication |
|---|---:|---:|---|
| [Meta Llama 3.1/3.3](https://github.com/meta-llama/llama-models) | 128K | Llama 4 Scout: 10M; Maverick: 1M | 128K is already common in the local Llama ecosystem. Llama 4's very large limits do not justify larger Orca injections. |
| [Qwen3](https://huggingface.co/Qwen/Qwen3-32B) | 32,768 | 131,072 validated with YaRN | YaRN requires serving configuration; Qwen warns that static scaling can affect shorter contexts. Treat 32K as the portable baseline for Qwen3. |
| [Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) | 262,144 | Up to 1,010,000 with YaRN | A newer variant has a larger native window, but deployment memory and model choice still govern the usable limit. |
| [Gemma 3](https://ai.google.dev/gemma/docs/core/model_card_3) | 128K for 4B/12B/27B; 32K for 1B/270M | None needed for the stated limits | Small local deployments may use the 32K variants, so Orca should not assume 128K. |
| [Mistral Ministral 3](https://docs.mistral.ai/resources/known-limitations) | 256K for 3B/8B/14B | Not required for the documented limit | The advertised window is large, but the selected inference runtime can still lower it to preserve memory. |
| [DeepSeek-V3 / R1](https://github.com/deepseek-ai/DeepSeek-V3) / [R1 model card](https://huggingface.co/deepseek-ai/DeepSeek-R1) | 128K | No extension required in the official model information | The flagship checkpoints are very large; their context limit is not a practical local-hardware target for most Phase 1 WSL installations. |

The vendor sources also show why these numbers must not be treated as a single
universal guarantee:

- Meta lists different limits by Llama generation and model variant.
- Qwen distinguishes native pretraining length from YaRN extension and says
  scaling can affect shorter contexts.
- Gemma has different limits even within one family.
- Mistral states that input and output tokens both count against the context
  window and that requests beyond the limit fail.

The runtime's effective value is therefore the lower of the model's supported
window and the serving configuration's limit. Orca should discover or receive
that value rather than infer it from the model family name.

## Budget recommendation

### Recall into an active agent conversation

Keep the existing default of **4,000 tokens total**, with **1,500 tokens per
document** and at most six results. On a 32K model, the complete package is
about 12.5% of the nominal context window, leaving most of the window for the
live discussion, system instructions, tools, and the answer. On 128K or larger
models it is a small fraction of the window.

This is intentionally a fixed initial budget across 32K, 128K, and 256K
models. Increasing recall merely because a model advertises a larger window
would increase latency and token cost, and would make results less focused.

### Conversation Continuation Summary

Keep the existing default of **2,000 tokens**. It is large enough for current
state, important outcomes, unresolved questions, next steps, and artifact
references, while remaining small enough to include during later processing.
It is a living current-state view, not a transcript. The handoff skill's lack
of a numeric limit means there is no external value to inherit.

### Processor call

The accepted Phase 1 ceiling of **20,000 input tokens plus 4,000 output tokens**
fits within a 32K context window at 24,000 planned tokens, leaving 8,000 for
runtime-specific framing and safety margin. The processor must still enforce
the combined request budget, because some runtimes count input and output
together.

If the selected runtime reports a smaller window, Orca should derive a lower
per-call budget rather than truncate silently. If it reports a larger window,
Orca should retain the defaults until recall-quality or processing measurements
show that more context is needed.

## Configuration profiles

Configuration should allow the Owner to set the model window and explicit
budgets, while validating that every request fits:

| Runtime profile | Processor input | Processor output | Handoff | Recall total / per document |
|---|---:|---:|---:|---:|
| 16K constrained | 10K | 2K | 1.5K | 2K / 1K |
| 32K baseline (recommended) | 20K | 4K | 2K | 4K / 1.5K |
| 64K+ | 20K | 4K | 2K | 4K / 1.5K |

These are profiles, not promises that every model will perform equally well
at its maximum. **Inference:** The 32K profile is the useful compatibility
target because it covers Qwen3 and the smaller Gemma variants while remaining
well below the 128K–256K windows common in newer models.

The validation rule should be equivalent to:

```text
fixed instructions
+ selected evidence and memory inputs
+ requested output ceiling
<= configured model_window_tokens
```

When the inequality fails, reduce the lowest-priority related records and then
split new evidence at turn boundaries. Never silently cut a turn or pretend
that an optional long-context extension is available.

## Sources

- [Orca handoff skill](/mnt/c/Users/kyh82/.codex/skills/handoff/SKILL.md)
- [Meta Llama model overview](https://github.com/meta-llama/llama-models)
- [Meta Llama 4 announcement](https://ai.meta.com/blog/llama-4-multimodal-intelligence/)
- [Qwen3 model card](https://huggingface.co/Qwen/Qwen3-32B)
- [Qwen3 context concepts](https://github.com/QwenLM/Qwen3/blob/main/docs/source/getting_started/concepts.md)
- [Qwen3.6 model card](https://huggingface.co/Qwen/Qwen3.6-27B)
- [Google Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3)
- [Mistral context-window limitations](https://docs.mistral.ai/resources/known-limitations)
- [DeepSeek-V3 official repository](https://github.com/deepseek-ai/DeepSeek-V3)
- [DeepSeek-R1 official model card](https://huggingface.co/deepseek-ai/DeepSeek-R1)
