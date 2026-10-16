[Česky](../cs/decisions/ADR-002-rrf-misto-vazeni.md)

# ADR-002: RRF instead of a weighted sum of scores

**Status:** accepted · **Date:** 9 Oct 2026 (original choice from 6 Oct 2026)

## Context

The retrieval produces three rankings (meaning of the original question, meaning of the rewritten one, words). They need to be combined. Two common ways: **RRF** (reciprocal rank fusion, uses only the rank) and a **weighted sum** of normalised scores.

## Decision

**RRF with k = 60.**

## Evidence (from [benchmark-results.md](../benchmark-results.md))

The BM25 weight in the weighted sum was tuned **only on the dev questions** (it came out at 0.05, i.e. BM25 almost switched off).

| | Recall@5 | MRR |
|---|---|---|
| RRF | 0.86 | 0.71 |
| weighted sum | 0.88 | 0.76 |

Paired test: RRF better on 2 questions, weighted sum better on 4, **p = 0.69**. The difference is indistinguishable from chance. The parameter k (10 to 100) also hardly changes the result (the intervals overlap).

## Why RRF then

- It needs no score normalisation (embeddings 0–1, BM25 0–∞) and no weight tuning, so it has no parameter that could be over-tuned to a small set.
- With equal quality, the simpler one wins.

## Consequences

- If the new set (v4) showed that the weighted sum is better, the decision would change. On today's data that cannot be claimed.
- An optimal BM25 weight close to zero is a signal pointing to ADR-004 (BM25 may not contribute).
