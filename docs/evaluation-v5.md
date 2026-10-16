# Evaluation v5: 134 held-out questions (2026-10-16)

The earlier honest numbers rested on 10 untouched questions. This run adds **110 new questions (set v5)** plus the **24 frozen questions of set v4**: 134 questions the system was never tuned on, 112 with an answer in the law and 22 without one.

## How the questions were made

1. Three Claude Sonnet subagents wrote 110 questions from the law text only (different parts of the 4 laws, lay wording, ~10 % exact references, multi-paragraph, ambiguous, 15 questions outside these laws). They never saw system outputs.
2. A fourth subagent reviewed every question against the paragraph text: 105 ok, 5 fixed (`.tmp` review, applied before freezing).
3. The set was **committed before the first run** (`1e80187`, `data/testset_v5.json`). No code, prompt or model was changed after looking at the results.

## What was run, and what differs from production

| Step | Production (live site) | This run | Why |
|---|---|---|---|
| Query vector | e5-large via OpenRouter | e5-large **locally** (`sentence-transformers`) | free. Same model: cosine 0.9999999 vs. API vectors, identical top 5 on 66/66 old questions |
| Passage vectors | from API (`data/emb_cache.npz`) | same | – |
| BM25, RRF, paragraph-1 and reference rules | `tools/rag.py` | same code | – |
| Rewrite, pick 5 of 20, answer | DeepSeek v4.1 Flash / v4 Pro | **Claude Sonnet** as a Claude Code subagent, **same prompts** | no API credits spent |
| Judge | DeepSeek + Claude second opinion | Claude Sonnet (3 judges), spot check by Claude Opus | – |

So the answer numbers describe **"the v3 chain with Claude as the LLM"**, not the DeepSeek production chain. Retrieval numbers for `fast` and `hybrid` contain no LLM and apply to production as is. Cost: 0 USD of API; Claude plan usage only. Runner: `tools/eval_v5.py` (export tasks → subagent → import, three rounds, then judge). Replay from cache is tested in `tests/test_eval_v5.py`.

## Results (n = 134; 112 answerable, 22 unanswerable)

### Retrieval (answerable questions)

| System | Recall@5 (95 % bootstrap) | MRR@5 | Gold paragraph in top 5 (Wilson 95 %) |
|---|---|---|---|
| `fast`: e5-large only, no LLM | 0.84 (0.78–0.89) | 0.71 | 101/112 (0.83–0.94) |
| `hybrid`: e5-large + BM25, no rewrite, no LLM | 0.68 (0.60–0.76) | 0.57 | 82/112 (0.64–0.81) |
| 20 candidates after rewrite (before the pick) | Recall@20 0.97 (0.94–1.00) | – | 110/112 |
| **v3: Claude picks 5 of 20** | **0.97 (0.94–0.99)** | **0.97** | **111/112 (0.95–1.00)** |

### Answers

| Measure | Result |
|---|---|
| Correct answers (judge) | **108 / 112** (Wilson 95 % 0.91–0.99); 2 partial, 2 wrong |
| Correct "I don't know" where the law has no answer (rule: answer starts with „Nevím“ / "I don't know") | **21 / 22** (0.78–0.99) |
| False "I don't know" on answerable questions | 1 |
| Deterministic checks: citation out of range / answer without citation / number not in cited text | 0 / 0 / 1 |

**Judge reliability.** One judge batch marked 44/44 correct within half a minute, so the verdicts were checked: (a) no answer judged correct lacks a gold paragraph in its passages; (b) Claude Opus re-read 15 random "correct" answers against the gold: 15/15 agreed. This lowers, but does not remove, the risk of a lenient judge from the same model family as the answerer.

### Failures

| Id | Question (Czech) | What went wrong | Where |
|---|---|---|---|
| 276 | Smím si při nemocenské přivydělat prací u stejného zaměstnavatele? | ZNP § 16 not among the passages → „Nevím“ | retrieval |
| 291 | Dostanu nějaké peníze, když se budu rekvalifikovat, a kolik? | gave 0.4× average wage (ZZ § 51 odst. 2, special cases) instead of 80 % of net earnings | reading |
| 274 | Jsem na neschopence a chci odjet k rodičům… | right rule, but the 14-day condition for telling the employer is vague | reading (partial) |
| 232 | Kolik peněz navíc dostanu, když musím makat o víkendu? | judged partial (no overtime part). **Gold error found after the run:** the gold omits ZP § 118 odst. 1 (wages: at least 10 %); the system's answer (10 % wages, 25 % salary) matches the law. Kept as partial in the numbers; not re-scored | gold |

## What this does not show

- **Not the production model.** DeepSeek answers on these 134 questions are **not run** (would cost API credits).
- **Same-family judging.** Questions, answers and judges are all Claude. Independent (human or legal) review: not done.
- **Question style.** Written by an LLM from the law text, so wording may sit closer to the law than real user questions. 15 v5 + 7 v4 unanswerable questions are a small sample for refusals.
- **One run.** Subagent outputs are not perfectly deterministic; no repeated runs. In 4 of 134 rerank tasks the subagent reported reading only ~260 of the 400 characters shown per passage.
- Set v4 was planned to be run once on the DeepSeek chain. It has now been seen by this Claude-chain run; no change was made because of it, so it still serves as a held-out set for the DeepSeek chain, but it is no longer unseen by people.

Data: `data/testset_v5.json`, `data/llm_cache_claude.json`, `data/emb_cache_local.npz`, `data/judge_v5_claude.json`, `results/eval_v5.json`.
