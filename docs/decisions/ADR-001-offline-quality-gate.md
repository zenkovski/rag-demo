[Česky](../cs/decisions/ADR-001-offline-quality-gate.md)

# ADR-001: The quality gate replays stored results, it does not call the model

**Status:** accepted · **Date:** 9 Oct 2026

## Context

I want every pull request to reveal a regression in retrieval quality. Two things stand in the way:

1. Calling the model costs money (the live demo key has a cap of $0.75, of which ~$0.09 remains) and the result is not exactly the same when repeated.
2. CI that fails randomly stops being taken seriously and people ignore it.

## Decision

The quality gate (`tools/experiments.py --check`) **replays** retrieval from stored embeddings and stored model answers (`data/emb_cache.npz`, `data/llm_cache.json`) and compares the ranking of the correct chunks per question with `results/baseline.json`. It never calls the API (`RAG_OFFLINE=1`, a missing cache = an error, not a call).

The gate **guards the retrieval code**: BM25, RRF, paragraph rules, selection ordering. It is deterministic, takes tens of seconds and costs nothing. The tolerance is zero: any drop in the rank of a correct chunk is a code change, not noise.

**A change that alters the candidates** (e.g. a different RRF) also alters the input of the LLM selection. The stored answer then no longer fits. In that case the gate **fails with a clear message** ("cannot replay: verify only by live measurement") instead of guessing. Such a change must be measured live (`tools/evaluate.py`) and the baseline is regenerated deliberately (`--save-baseline`).

## Consequences

- (+) Repeatable, free, fast, no false alarms.
- (+) On a regression the gate prints the specific questions and the rank before and after.
- (−) **It does not guard the model's behaviour.** A worse prompt or a different model is not caught by the gate. For that there is the live measurement, manual and paid.
- (−) A change of candidates requires a live measurement, so CI cannot decide on its own.
- (−) The baseline also freezes errors: a rank "correct" means "same as before", not "correct in an absolute sense".

## Alternatives considered

| Alternative | Why not |
|---|---|
| Live measurement in CI on every PR | costs money, non-deterministic, would exhaust the key |
| Live measurement with a threshold "must not drop by 2 points" | on 56 questions 2 points is less than one question; the threshold would be indistinguishable from noise |
| A mocked model (fake answers) | tests the mock, not the system. Fake models are used in the *security* and *permission* tests, where the data flow matters, not quality |
