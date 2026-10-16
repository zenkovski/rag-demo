[Česky](docs/cs/HISTORY.md)

# Version history

What changed in each version, why, and whether it helped. Numbers question by question: [RESULTS.md](RESULTS.md).

Abbreviations: ZP = Labour Code, ZZ = Employment Act, ZNP = Sickness Insurance Act, NV 590 = Government Decree 590/2006. DPČ / DPP = the two kinds of work-outside-employment agreements under Czech law (agreement to perform a job / agreement to complete a job).

| Version | Main change | Correct (66 questions) | Correct § among 5 chunks (56) |
|---|---|---|---|
| v1 | e5-base locally, free model `nemotron-3-super` | 54 | 47 |
| v2 | question rewrite, BM25 + RRF, e5-large via API, `deepseek-v4.1-flash` | 60 | 53 |
| v3 | LLM picks 5 of 20 candidates, mzda × plat (wage × salary) note, follow-up lookup | 65 | 56 |
| v3.1 | the answer is written by `deepseek-v4-pro`, useful "I don't know" | 66 | 56 |

## v1 → v2: retrieval

| Problem in v1 | Change in v2 |
|---|---|
| People write „výplata“ ("pay") and „odejít“ ("to leave"), the law says „mzda“ ("wage") and „okamžitě zrušit“ ("terminate with immediate effect"). | **Question rewrite** into the language of the law (LLM). |
| Search by meaning sometimes misses the exact word. | **BM25** (word-based search) over the rewritten question, combined with **RRF**. |
| For DPČ the model added "300 hours a year" (that applies only to DPP). | **Stricter rules** in the prompt. |
| e5-base runs only locally (1 GB), not on the website. | **e5-large via API**, the same model in the measurements and on the website. |

Retrieval step by step (correct § among 5 chunks, 56 questions):

| Step | hit@5 |
|---|---|
| e5-base | 47 |
| e5-large | 50 |
| + BM25 over the lay question | **44** (worse: the word „výplata“ is not in the law) |
| + question rewrite, BM25 over the rewrite | 53 |
| + selection via LLM, paragraph 1 and references | 56 |

## v2 → v3: errors by step

Every error arises either in **retrieval** (the model did not get the correct paragraph) or in **reading** (it got it but used it wrongly).

| Error in v2 | Step | Fix |
|---|---|---|
| Sickness benefit: how much money | retrieval (§ 29 ZNP only 11th) | LLM picks 5 of 20 + lookup of "according to paragraph 2" |
| Paternity benefit: length and amount | retrieval (§ 38c only 10th) | LLM picks 5 of 20 |
| Night work 20 % instead of 10 % | reading (mzda × plat) | the chunk carries the note "applies to mzda / plat" |
| Assessment (posudek) "must not" instead of "need not" | reading | rule „není povinen“ ("is not obliged to") = need not; stable only with the Pro model (v3.1) |

Two fixed rules without AI:
- For a selected paragraph 2, 3… paragraph 1 of the same § is added. This fixed the regression on rest between shifts.
- Paragraphs that a chunk refers to ("in the amount according to paragraph 2") are looked up.

## v3 → v3.1: unstable reading and needless "I don't know"

- The cheap model read the same paragraph correctly once and wrongly another time. Changing the fifth chunk in the context was enough.
- It often said "I don't know" even though it had the answer in front of it („Mám nárok na lékaře?“ / "Am I entitled to a doctor?").
- Experiment on 5 problem questions: the new prompt alone fixed 3, a stronger model alone 3, both together 5.
- That is why `deepseek-v4-pro` writes the answer. The rewrite and selection are still done by the cheap Flash.
- Drawback: Pro cites less often, not after every sentence.

## Hidden reasoning of the model

Before answering, DeepSeek Flash silently "thought", up to 4 800 tokens in the chunk selection. The step took 30 s and cost 10× more. Since v3 it is turned off (`reasoning: {enabled: false}`): the step takes 1.5 s and quality did not get worse. Most of the total $0.66 was spent on this before I found it.

## A larger source

The first version had 5 topics of the Labour Code (260 paragraphs). Now 4 regulations (2 475 paragraphs). On the same 24 questions retrieval did not get worse (24 of 24). Measurement of the first version: `data/archive_5temat/`.
