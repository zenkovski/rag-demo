[Česky](cs/evaluation-methodology.md)

# Evaluation methodology

How measurement is done, what the numbers mean and what they **cannot** be used to conclude. The results are in [benchmark-results.md](benchmark-results.md) (generated), the errors in [failure-gallery.md](failure-gallery.md).

Abbreviations: ZP = Labour Code, ZZ = Employment Act, ZNP = Sickness Insurance Act, NV 590 = Government Decree 590/2006. Chunk IDs like `ZP § 56 odst. 1` mean Labour Code, section 56, paragraph 1.

## 1. The dataset

**Schema** (`data/testset*.json`, one record = one question):

| Field | Meaning |
|---|---|
| `id` | question number, unique within the project (1–66, new set 101–124) |
| `q` | the question as a layperson would write it |
| `gold` | the factually correct answer (written by hand from the text of the law) |
| `chunks` | IDs of the correct paragraphs (`ZP § 56 odst. 1`). **An empty list = the regulations do not contain the answer and the correct reply is "I don't know" („nevím“).** With two correct paragraphs, Recall is computed as the share found |
| `level`, `type` | difficulty; for the new set the type of case (exact reference, multiple paragraphs, ambiguous, outdated, injection…) |
| `canary` | (attacks only) a string that must not appear in the answer |

**Origin of the data.** The questions and correct answers were created with an AI assistant (Claude Code) from the text of the law, and the project owner went through them. For the new set v4, the correct paragraphs were found by plainly searching the data and reading the text, **not from the system's output**; their correctness has no independent legal review. The correct paragraphs are checked by a test (`test_gold_chunks_exist`: each must be in the data).

**What the sets contain and do not contain.** 66 questions: 56 with an answer, 10 deliberately without one. All are phrased as a layperson's questions. **Missing** are exact references to sections, questions spanning several paragraphs and ambiguous questions, i.e. the types where differences between BM25 and embeddings should show up. That is why a new set has been written (see 4).

## 2. Dev, validation, test and leakage prevention

**The problem.** The system was repeatedly changed based on errors on questions (v2, v3, v3.1). A number measured on the questions it was tuned on is **inflated**: the system could have adapted to exactly those. This is called data leakage, and it can be avoided only by locking in advance the set on which the number is reported.

**Rules** (`data/splits.json`, valid with respect to the *final* version v3.1):

| Role | Definition | Sets | Questions with an answer |
|---|---|---|---|
| **dev** | code, prompt or model was changed based on errors on it | 1–46 | 40 |
| **validation** | written before the version was run, but its results influenced the next change | 47–56 | 8 |
| **test** | written before the final version was run, nothing was changed based on it since | 57–66 | 8 |
| **test v4** *(planned)* | written, frozen, **not yet run**; will be run once | 101–124 | 17 |

1. Roles are assigned when a set is written and **never retroactively**: a set based on which anything was fixed is no longer a test.
2. Proof of when a set was created: a git commit (the `commit` column in `splits.json`). This makes the order "set → version" verifiable.
3. The weighted sum in the ablation is tuned **only on dev** (`select_weight`), and the result is reported on each role separately.
4. The one-off nature of set v4 is enforced by `tools/run_heldout.py`: before the first call it writes a lock with fingerprints of the code and prompts; a second run is refused.

**An honest correction of an earlier claim.** The README stated "20 of 20 on questions written before the version was run". Strictly speaking: questions 47–56 were written before v3 was run, but their errors influenced v3.1 (a stronger model, a rule before "I don't know"). **Truly untouched are 10 questions (57–66)**, and 10 of 10 has a lower bound of the 95 % confidence interval of about 0.72. The number "66 of 66" is inflated and is labelled as such.

## 3. Metrics

Details in `tools/metrics.py` (every function has a test on a hand-computed example).

| Metric | What it measures | What does NOT follow from it |
|---|---|---|
| **Recall@k** | what share of the correct paragraphs is among the first k | nothing about the order within k; that a paragraph is sufficient for the answer |
| **hit@k** | whether at least one correct paragraph is among the first k | for a question with two correct paragraphs, it hides that one is missing (an older indicator in RESULTS.md) |
| **MRR** | mean of 1 / rank of the first correct paragraph | strongly rewards 1st place; knows nothing about a second correct paragraph |
| **nDCG@k** | ranking with emphasis on the top places, correct paragraphs equally important | does not distinguish "sufficient" from "needed" |
| **Answer correctness** | factual agreement with `gold`, manual check against the text of the law | it is a judgement; the AI judge is wrong at times (see the gallery), so the second verdict and my check apply |
| **Correct "I don't know" / needless "I don't know" / answer without a source** | refusal where the source is silent / refusal although the source was there / an answer to a question the law does not address | "I don't know" alone is not a success: a system that always refuses has 100 % correct refusals |
| **Citation and number check** (`answer_checks.py`) | the citation points to a supplied chunk, the number in the answer is in the cited chunk | does not claim that the sentence follows from the chunk; reports a **suspicion**, not an error (derived sums are correct but not documented) |
| **Context** (coverage, relevance, duplicates) | – | **not measured.** Coverage could be computed from `chunks`, duplicates could not. Not implemented. |
| **Latency, cost** | cost from stored OpenRouter responses; search compute time from the cache | **p50/p95 of the whole service are not measured**, because that would require live calls; see [limitations.md](limitations.md) |

**Why not an LLM-as-a-judge alone.** The judge (DeepSeek) overlooked several wrong "I don't know" answers and at times marked a correct answer as an error. That is why every answer is compared once more with the text of the law (Claude Opus 5.5), this verdict was reviewed by the project owner, and alongside it there are deterministic checks that need no model. The judge is therefore **not the source of truth**, it is a first filter.

## 4. Statistics and uncertainty

- **Confidence interval (95 %).** Bootstrap over questions (10 000 draws, fixed seed). It shows how the number would change with a different set of similar questions. It does **not** show the randomness of the model.
- **Wilson** for proportions (correct answers): works even for 10 of 10 (≈ 0.72–1.00).
- **Paired sign test** for comparing two systems on the same questions: only questions where they differ are counted. A difference of 5 : 0 gives p = 0.0625, so still **not** significant. A difference of 9 : 0 (LLM selection versus RRF) gives p = 0.004.
- **What is not claimed.** For a difference of 1–3 questions out of 56, "better" is not claimed, only "inconclusive difference". That is how BM25, the rewrite, the weighted sum and the comparison of e5-base and e5-large turned out.
- **Repeated runs of the stochastic parts.** The LLM calls have temperature 0, but even so a new call is not always the same. The answer numbers apply to **one stored run**. Repeated runs with variance were **not done** (they would cost money). The weakness is recorded in [limitations.md](limitations.md).

## 5. Experiments (ablations)

Run with one command (`python tools/experiments.py`), offline from stored results, and it **costs nothing**. Every run saves the configuration, fingerprints of data and prompts, model versions, metrics, runtime, cost and a list of regressions.

| Question from the ablation | How it is examined | Status |
|---|---|---|
| dense × BM25 × hybrid | 9 systems, Recall@k, MRR, nDCG, CI | done |
| RRF × weighted sum | weight tuned on dev only; paired test | done |
| parameter k in RRF | k = 10, 30, 60, 100 | done |
| question rewrite on/off | `rrf_dense_bm25` × `rrf_v2` | done |
| no selection × cross-encoder × LLM | from stored results | done |
| e5-base × e5-large | locally via `sentence-transformers` | done (local only, CI skips it) |
| **chunk size and strategy** | – | **not done**: requires recomputing embeddings (paid API) |
| **other embedding models, quantisation** | – | **not done**, same reason; int8 quantisation is verified elsewhere (DESIGN.md §3) |

## 6. What is run live and when

| Measurement | Command | Cost | When |
|---|---|---|---|
| the whole set v1–v3 with answers and judge | `tools/evaluate.py` | ~$0.07 | after changing a prompt or model |
| **the new frozen set v4** | `tools/run_heldout.py --live` | ~$0.03 | **once**, on the frozen code |
| security injections | `tools/security_eval.py --live` | ~$0.02 | after changing a prompt or function; **not yet run** |

Everything else runs for free and on every push.

## 7. What would change the conclusions

- Enough questions on **exact references** and **section numbers**: BM25 might win there and the table in section 2 of the benchmark would have to be rewritten (ADR-004 is kept as open).
- More than 56 questions with an answer: the intervals would narrow, differences of 1–3 questions could be distinguished.
- A source other than a law (PDFs with tables, document versions): the conclusions about chunking and retrieval do not transfer (see [DESIGN.md §11](../DESIGN.md#11-what-would-be-missing-for-production)).
