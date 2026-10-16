[Česky](../cs/incidents/2026-10-06-regrese-odpocinek.md)

# Incident: LLM selection dropped the base rule (rest between shifts)

**Status:** fixed, guarded by a test and the quality gate. **Found:** 6 Oct 2026, by measurement after introducing v3. **Where it broke:** chunk selection (the step between retrieval and the answer).

Abbreviation: ZP = Labour Code. Chunk IDs like `ZP § 90 odst. 1` mean Labour Code, section 90, paragraph 1.

## Symptom

After introducing the selection "the LLM picks 5 of 20 candidates" (commit `458bb46`, v3.0) the overall result improved (v2 50 → v3 54 of 56), but one question that v2 had right stopped working:

> **„Kolik hodin odpočinku musím mít mezi dvěma směnami?“ ("How many hours of rest must I have between two shifts?")** Correct: an uninterrupted daily rest of at least 11 hours (§ 90 odst. 1 ZP).

In v3.0 the answer did not state the basic number at all:

> "The basic rule is only hinted at in the chunks (paragraph 1 is cited but not given), so we cannot determine the exact basic length of rest from the supplied chunks. What is certain is that under the stated conditions it may be shortened…"

The answer was safe ("I don't know") but useless. No error in the log, no exception. Just a worse answer.

## How it was found

Not by reading the answers, but by **comparing per question** (v2 → v3) after every change: hit@5 dropped on a single question from "yes" to "no", even though the whole improved. Had only the average been watched (54 of 56 is better than 50), the regression would have vanished in the sum.

## Cause (measurable)

The correct paragraph **is** among the 20 candidates. The selection step decided:

| Step | § 90 odst. 1 (the rule) | § 90 odst. 2, 3 (the exceptions) |
|---|---|---|
| Candidates from RRF (20) | yes | yes |
| **LLM selection (v3.0)** | **dropped** | selected |
| Five chunks for the model | missing | `ZP § 90 odst. 3`, `odst. 2`, `§ 90a`, … |

The LLM picked chunks that "answer the question about shortening the rest", and the exceptions look more relevant than the basic rule. The error is not in the model or in the prompt as such, it is in the fact that **an exception cannot be read correctly without its rule**. Category by the [failure gallery](../failure-gallery.md): **B – found, but dropped**. A better prompt or better retrieval would not fix it for certain; only a fixed rule fixes it reliably.

Evidence from the data (`data/eval.json`, commit `458bb46`, question 10): the five chunks for the model were `ZP § 90 odst. 3`, `odst. 2`, `§ 90a`, `§ 85 odst. 3`, `§ 100 odst. 2`. Paragraph 1 was missing.

## Fix

A fixed rule **without AI** (`rag.with_odst1`, commit `1e76718`): to a selected paragraph 2, 3… paragraph 1 of the same section is always added, even if it was not among the candidates.

Why a rule and not "forbid the LLM from omitting paragraph 1": the LLM is unstable and a new prompt wording would only move the error. A rule is deterministic and can be tested.

## Proof that the fix helped and broke nothing

- Question 10 after the fix: five chunks `ZP § 90 odst. 3`, **`odst. 1`**, `odst. 2`, … Answer: "…an uninterrupted daily rest of at least 11 hours… for a juvenile at least 12 hours, or 14 hours" (correct).
- Overall hit@5 on the first 48 questions with an answer: **47 → 48**. After the fix, **all** questions were measured again, not just that one: no other got worse.

## What became permanent

1. **Unit test** `tests/test_rag.py::test_with_odst1_adds_base_rule`: an exception (§ 90 odst. 2) gets paragraph 1 added after it.
2. **Quality gate** (`python tools/experiments.py --check`): the rank of the correct chunk for every question is in `results/baseline.json`; if someone removed the rule, it fails on this question, not only in the average.
3. **Procedure:** after every change, compare per question (`transitions` in [benchmark-results.md](../benchmark-results.md)), not only the sum.

## What would have prevented it sooner

Per-question measurement with the very first version of the selection. The average (54 of 56) looked like a success and the fix came only after inspecting individual questions.
