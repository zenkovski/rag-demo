[Česky](../cs/decisions/ADR-006-deterministicke-kontroly.md)

# ADR-006: Deterministic answer checks alongside the LLM judge

**Status:** accepted · **Date:** 9 Oct 2026

## Context

The correctness of an answer is judged by an AI judge (DeepSeek), then by a second model against the text of the law and by the project owner. The judge was wrong: it overlooked wrong "I don't know" answers (questions 49, 51) and marked a correct answer about mzda and plat (wage and salary) as an error (38). Measuring quality only with another model is circular.

## Decision

Alongside the judge run **deterministic checks** (`tools/answer_checks.py`) that need no model:

1. the citation `[n]` points to a chunk the model received,
2. an answer that is not "I don't know" has at least one citation,
3. every number in the answer is in the text of the **cited** chunk (numbers written as words in the law are converted; derived values and wrongly assigned citations are distinguished).

## Result

On 66 answers in v3: no citation out of range, no answer without a citation, **3 suspicions** about numbers. Manual review: 2 derived sums and 1 **real wrong citation** ("11 hours" is in chunk [4], the answer cites [1]; factually correct). A judge comparing meaning would easily have overlooked this.

## What the check does NOT do (and why it reports a "suspicion")

- It does not determine whether the sentence **follows** from the chunk (that is a judgement, for a human or a judge).
- It does not verify numbers written as compounds and word forms beyond the basic forms (up to ninety).
- It is **not in the live chain**, only in measurement. Wiring it in before displaying the answer is a decision about product behaviour (discard the answer? show a warning?) that has not been made yet.

## Consequences

A measurable signal with no cost and no trust in another model. It is a **supplement**, not a replacement for judgement.
