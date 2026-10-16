[Česky](../cs/incidents/2026-10-06-skryte-premysleni.md)

# Incident: hidden model "reasoning" burned most of the budget

**Status:** fixed (turned off), lesson recorded. **Found:** 6 Oct 2026 while introducing v3, after most of the total ~$0.66 had been spent.

## Symptom

The step "LLM picks 5 of 20 candidates" took **around 30 s** per question and the whole measurement cost several times more than the estimate. The answers looked normal, no error, no timeout.

## Cause

The model `deepseek-v4.1-flash` via OpenRouter silently generates "reasoning" tokens before answering, which do not appear in the answer but are **paid for and take time**. In the chunk selection it was up to **4 800 tokens** per call, while the answer was a few characters ("3, 1, 7").

Nobody expected it, because the output was short. The cost and time were hidden in the `usage` field, which was not being checked.

## Fix

`reasoning: {"enabled": false}` for the steps that do not need it (rewrite, selection; in the code the parameter `reasoning=False`, distinguished in the cache key by the suffix `|noreason`, so old stored answers are not mixed up with new ones).

| | With reasoning | Without |
|---|---|---|
| Time of the selection step | ~30 s | ~1.5 s |
| Cost of the step | ~10× more | baseline |
| Quality of the selection | – | **did not get worse** (per the note in [HISTORY.md](../../HISTORY.md); I do not keep a separate before/after comparison) |

(Source of the numbers: [HISTORY.md](../../HISTORY.md#hidden-reasoning-of-the-model). Time and cost are estimates from the time of the incident; the measured before/after difference was not saved in the data, which is a weakness.)

## Lesson (and what changed)

1. **Before a bulk run, measure one call**, including time and the token count from `usage`, not just the length of the output.
2. Every run stores the cost (`cost_usd` in `data/eval.json`) and from now on also in the run record (`results/…json`, field `ops.cost_per_question_usd`).
3. Model answers are **cached by input**, so repeated measurement costs nothing. That is why it is now possible to run the measurement and the quality gate for free (see [ADR-001](../decisions/ADR-001-offline-quality-gate.md)).
4. A **hard limit on the key** at the provider ($0.75) is the toughest safeguard. This incident did not trigger it, but it showed why it must be there.

## What this does NOT prove

That reasoning is always unnecessary. For answering hard questions it may help; that was not tried here (the answer is written by a stronger model without reasoning and the quality is measured). The decision was made on the measured time, cost and quality on these 56 questions.
