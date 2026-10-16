[Česky](../cs/incidents/2026-10-09-rozbite-razeni.md)

# Incident (demonstration): a "simplification" of the ordering broke the selection, lint and unit tests reported nothing

**Status:** fixed, guarded by a new test. **Kind:** a deliberately manufactured incident to demonstrate CI (the broken change was written by an AI assistant to show what CI catches). The symptoms, diagnosis and fix are real, they really happened in CI.

| | Link |
|---|---|
| Broken change (commit `2d71aaa`) | [PR #1](https://github.com/zenkovski/rag-demo/pull/1), branch `incident/rozbite-razeni` |
| CI on the broken change: **red** | [run 37971647801](https://github.com/zenkovski/rag-demo/actions/runs/37971647801) |
| Fix (commit `9a6afce`) | same branch |
| CI after the fix: **green** | [run 37971901553](https://github.com/zenkovski/rag-demo/actions/runs/37971901553) |

## Symptom

The change in `rag.search()` looked like a cleanup: the RRF order takes precedence and the selected chunks are merely "added". CI showed:

| Gate | Result |
|---|---|
| lint (ruff) | **green** |
| types (mypy) | **green** |
| tests (112) | **green** |
| **quality gate** | **red** |

No exception, no crash, the answers still looked reasonable. The system just answered worse.

## Detection and diagnosis

The quality gate compared the rank of the correct chunk **per question** with `results/baseline.json` and listed 23 questions (the output lines are verbatim from the tool, in Czech: "otázka" = question, "správný úsek" = correct chunk, "pořadí" = rank):

```
REGRESE:
  - otázka 10: správný úsek byl v 5 úsecích pro model a teď tam není (pořadí 2 -> None)
  - otázka 12: správný úsek byl v 5 úsecích pro model a teď tam není (pořadí 1 -> None)
  - otázka 15: správný úsek klesl z pořadí 1 na 3
  - otázka 19: správný úsek klesl z pořadí 1 na 4
  …
  - all: v3 recall@5 0.9866 -> 0.8616
  - all: v3 mrr 0.9643 -> 0.7006
```

From the output the cause could be inferred before a single file was opened:

1. **Almost all questions dropped from 1st place.** So the error is not about whether the correct chunk is found, but **how it is ordered**.
2. **The gate did not end with the message "cannot replay"** (see [ADR-001](../decisions/ADR-001-offline-quality-gate.md)). The candidates for the LLM selection stayed the same, because the stored model answers fit. This ruled out retrieval (BM25, RRF, embeddings) and left what happens **after the selection**.
3. **Six questions dropped out of the five chunks entirely**, the others only fell. This matches the LLM selection no longer being respected and the first five being taken from the RRF order.
4. Among those that dropped out is **question 10** (rest between shifts) from the [incident of 6 Oct](2026-10-06-regrese-odpocinek.md): the base paragraph was lost again, this time by a different mechanism.

## Cause

```diff
-        order = [(i, 0.0) for i in picked] + [(i, s) for i, s in fused if i not in picked]
+        order = fused + [(i, 0.0) for i in picked if i not in dict(fused)]   # "simplification"
```

The original line puts the **selected chunks first and fills the rest from RRF**. The "simplified" version puts RRF first and the selected ones are added after it (and mostly they are already there, since they are among the candidates). The LLM selection thus stopped influencing what the model receives.

## Why the unit tests did not catch it

The 112 tests examine **individual parts** (RRF, BM25, `parse_pick`, paragraph 1, references…), not their **composition** into the final order. All the parts were correct; the wrong thing was their joining. For that you need a check of the whole against something known to be correct: for the quality gate, that is the ranks from the measurement.

## Fix and proof

Reverted completely (`git revert`). CI after the fix is green on all three gates and `v3 recall@5 0.9866 / mrr 0.9643` is again exactly the baseline.

## What became permanent

1. **A new unit test** `tests/test_search_order.py::test_final_order_puts_llm_picks_first`: a fake model picks the 3rd and 1st candidate, the first one for the model must be the 3rd. Verified: **it fails on the broken version, passes on the fixed one.** The error will thus be caught next time already among the unit tests in seconds.
2. The quality gate stays as a second net for errors nobody thinks of in advance.

## What this demonstration does NOT prove

- That the gate catches **every** regression. It guards the retrieval and ordering code over stored model answers; **a worse prompt or a different model it does not catch** (that is the live measurement, manual and paid).
- That an AI assistant would not have made this error on its own. On the contrary: it is exactly the type of "looks like a cleanup" change that even an unsupervised assistant can write.
