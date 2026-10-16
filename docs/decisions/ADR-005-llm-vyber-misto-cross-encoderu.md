[Česky](../cs/decisions/ADR-005-llm-vyber-misto-cross-encoderu.md)

# ADR-005: LLM selection instead of a cross-encoder

**Status:** accepted, to be reconsidered · **Date:** 9 Oct 2026 (original choice 6–7 Oct 2026)

## Context

The RRF fusion gives 20 candidates. The model gets only 5. Who picks the right ones? Three options on the same 56 questions and the same 20 candidates (stored results of `tools/rerank_compare.py`):

| Method | Hit@5 (95 %) | MRR@5 (95 %) | Cost and time |
|---|---|---|---|
| first 5 from RRF | 0.88 (0.79–0.95) | 0.70 | 0 |
| cross-encoder `bge-reranker-v2-m3`, local | 0.93 (0.86–0.98) | 0.81 | $0, ~15 s per question (CPU) |
| **LLM selection** (`deepseek-v4.1-flash`) | **1.00** | **0.96 (0.93–0.99)** | ~$0.0001, ~1.5 s |

## Decision

**LLM selection.**

## Reasons and honest reservations

- Highest MRR, the correct paragraph almost always in first place. The LLM sees **all 20 at once** and recognises that the answer needs two paragraphs (both the length and the amount of the benefit). The cross-encoder scores question–chunk pairs separately.
- **Reservation:** LLM versus cross-encoder: better on 4 questions, worse on 0, **p = 0.125**. "56 versus 52 of 56" shows a direction, but on 56 questions it cannot be considered proven.
- **Reservation:** LLM selection is the only component with a conclusive benefit over RRF without selection (9 : 0, p = 0.004). That it is better than the cross-encoder is not conclusive.
- LLM selection can drop the base rule and leave only exceptions: see the [incident](../incidents/2026-10-06-regrese-odpocinek.md). Fixed by a fixed rule.

## Consequences

- A cost for every query, non-determinism, dependence on the prompt. The cross-encoder is deterministic and free.
- Reconsider when: (a) the new set v4 brings a difference, or (b) the selection can be done by a cross-encoder on a GPU in tens of ms. A hybrid under consideration: the cross-encoder as a first filter and the LLM only for uncertain cases.
