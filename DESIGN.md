[Česky](docs/cs/DESIGN.md)

# System design: decisions and why

Every decision in the project, why it was made, and what backs it up. The numbers come from the measurements in [RESULTS.md](RESULTS.md); the version history is in [HISTORY.md](HISTORY.md).

Abbreviations used below: ZP = Labour Code (zákoník práce), ZZ = Employment Act (zákon o zaměstnanosti), ZNP = Sickness Insurance Act (zákon o nemocenském pojištění), NV 590 = Government Decree 590/2006. Chunk IDs such as `ZP § 56 odst. 1` mean Labour Code, section 56, paragraph 1.

## 1. The whole flow

```
question ─► rewrite into the language of the law (LLM)
         ─► search by meaning (e5-large: original + rewritten question) + by words (BM25: rewritten question)
         ─► RRF ─► 20 candidates ─► LLM picks 5 ─► + paragraph 1 of the same § + referenced paragraphs
         ─► answer only from these 5 chunks, with citations, or "I don't know"
```

Every step can be measured on its own. Because of that, for every error I know whether it arose in **retrieval** (the correct paragraph never reached the model) or in **reading** (the model had it and used it wrongly). The fix is different for each type: a better prompt does not fix retrieval, and better retrieval does not fix reading.

## 2. Data and chunking · `tools/chunk.py`

- 4 regulations from zakonyprolidi.cz, **2 475 chunks**. One chunk = one paragraph of a section, with an ID like `ZP § 56 odst. 1`.
- **Why by paragraph:** that is how the law is written. A paragraph is one idea with its own address, so a citation points exactly to the place in the law. A fixed window (e.g. 500 tokens) would cut rules in half.
- **Law abbreviation in the ID:** § 26 is a different section in every law.
- **Dropped:** lists of repealed regulations, entry into force, EU directives, the catalogue of pay grades. Just noise. A few huge enumerations are truncated to 6 000 characters.
- **Metadata:** law, section, area (notice of termination, holiday…) and, for the Labour Code, a note "applies to mzda / plat" (wage in the private sector / salary in the public sector; see § 6).

## 3. Embeddings · `tools/rag.py`

- **Model:** `multilingual-e5-large` via API. It handles Czech, and the same model runs in the measurements and on the website. The local e5-base (v1) found the correct § among 5 for 47 of 56 questions, e5-large for 50.
- **Prefixes `query:` and `passage:`:** e5 was trained that way. A question and a document are different kinds of text, and the prefix tells the model which is which.
- **Normalisation to length 1:** cosine similarity is then a plain dot product. The whole search is one multiplication of a 2 475 × 1 024 matrix.
- **int8:** float32 vectors take 10 MB, too much for a serverless function. I store each vector as integers −127…127 plus one scale factor: 4× smaller. Measured impact on 301 queries: similarity of float × int8 vector at least 0.9999, top 20 agrees on average in 19.8 of 20, top 5 in the same order for 81 %. All numbers in RESULTS.md already include int8.
- **A trap I found:** a rounded vector does not have length exactly 1. LangChain computes cosine and Python a dot product, so they differed on 11 of 46 questions. Fix: re-normalise the vector after converting back, identically in all three versions.

## 4. Retrieval · `tools/rag.py`

| Step | Why | Measured (correct § among 5, out of 56) |
|---|---|---|
| e5-large | meaning, even in different words | 50 |
| + BM25 over the lay question | exact terms | **44**: worse, the word „výplata“ ("pay") is not in the law |
| + question rewrite, BM25 over the rewrite | „výplata“ → „mzda“ ("pay" → "wage") | 53 |
| + LLM picks 5 of 20, paragraph 1, references | reads the candidates and chooses | 56 |

- **BM25** is classic word-based search. It wins on exact terms and numbers („§ 52“, „DPČ“ (agreement to perform a job), „odstupné“ (severance pay)), where an embedding blurs the meaning. Written without a library: Czech without diacritics, and stem = first 5 letters.
- **RRF instead of weighting scores:** the embedding scores (0–1) and BM25 (0–∞) have different scales. A weighted sum would need tuned weights and normalisation. RRF takes only the rank (1/(60 + rank)) and nothing is tuned.
- **Why no vector database:** 2 475 chunks take under 10 ms in numpy. A database would add a service, but not quality. The threshold is around hundreds of thousands of chunks (see § 11).

## 5. Choosing 5 of 20: LLM or cross-encoder?

The selection cannot find what is not among the 20 candidates. That is why I measure the ceiling (candidates) and the selection separately. `tools/rerank_compare.py`, from cache, free:

| Step (56 questions with an answer) | Correct § | MRR | Time and cost per question |
|---|---|---|---|
| Ceiling: among the 20 RRF candidates | 55 of 56 | | |
| No selection: first 5 from RRF | 49 of 56 | 0.70 | 0 |
| Cross-encoder `bge-reranker-v2-m3`, local | 52 of 56 | 0.81 | 15 s on CPU, $0 |
| **LLM selection (`deepseek-v4.1-flash`)** | **56 of 56** | **0.96** | 1.5 s, ~$0.0001 |

MRR (mean reciprocal rank) = how high the first correct chunk ranks: 1 = always first, 0.5 = second on average. The fixed rules (paragraph 1, references) are the same for both selections.

- **Why 56 when the ceiling is 55:** for „odpočinek mezi směnami“ ("rest between shifts") the rule (§ 90 odst. 1) was missing even among the 20 candidates. The LLM picked the exception (odst. 2) and the paragraph 1 rule added the base rule. Here the rule helped, not the selection.
- **Why the LLM:** 4 more correct chunks and the correct chunk almost always in first place. The cross-encoder knows only a question–chunk pair. The LLM sees all 20 at once and recognises that the answer needs two paragraphs (both the length and the amount of the benefit).
- **Drawbacks of the LLM:** you pay for every query, it depends on the prompt, and a new call need not return the same thing. The cross-encoder is deterministic and with a GPU would take tens of ms.
- **In production I would try:** the cross-encoder on a GPU as a first filter and the LLM only for uncertain cases. Or fine-tune the cross-encoder on question–section pairs from the logs.

## 6. The answer

- **Rules in the prompt:** answer only from the chunks, a citation [n] after each claim, do not use a chunk about a different situation, „je povinen“ ("is obliged to") = must, „není povinen“ ("is not obliged to") = need not (not "must not"), copy numbers exactly. When there is nothing in the chunks: „Nevím“ ("I don't know").
- **Mzda × plat (wage × salary):** the Labour Code has separate rules for companies (mzda) and the state (plat). The model confused 10 % and 20 % for night work. A chunk therefore carries a note saying who it applies to, and the model states both variants when the question does not say.
- **Model:** the rewrite and selection are done by the cheap `deepseek-v4.1-flash`, the answer by `deepseek-v4-pro`. Flash read the same paragraph correctly once and wrongly another time, and said "I don't know" needlessly. Experiment on 5 problem questions: a better prompt alone fixed 3, a stronger model alone 3, both together 5.
- **Hidden reasoning turned off:** Flash "thought" up to 4 800 tokens per step, 30 s and 10× the cost. Turned off: 1.5 s, quality did not get worse.
- **Cost:** the whole measurement of 66 questions including the AI judge $0.07, so about $0.001 per question.

## 7. Measurement · `tools/evaluate.py`

- **66 questions in 5 sets.** 56 have an answer in the regulations (with correct sections), 10 are traps where the correct answer is "I don't know".
- **Test leakage:** based on the errors on a set I each time designed the next version, so that version is favoured on that set. That is why I wrote a new set, with correct answers, before running v3 and v3.1. The honest number: **20 of 20 (previous version 18 of 20)**. The overall 66 of 66 is inflated, and it says so.
- **Retrieval:** hit@3 and hit@5 (correct § among the first 3 / 5) and MRR (how high the correct § ranks).
- **Answer:** an AI judge (correct? grounded in the chunks?), then a second check of every answer against the text of the law (Claude Opus 5.5), which I went through and approved. The second verdict applies. The judge overlooked several wrong "I don't know" answers.
- **Outside the tests:** 16 sample questions on the website, 14 correct. Both errors are visible on the website.
- **Repeatability:** the rewrite is done by an LLM and even at temperature 0 a new call is not always identical. The numbers apply to one stored run (`data/llm_cache.json`). Properly, several runs and the variance would be measured. For a demo with a $0.75 limit I do not do that.
- **66 questions is few.** The difference 18 vs 20 of 20 is an indicator, not statistical proof.

## 8. How I find the cause of an error

1. Is the correct § among the 20 candidates? No → retrieval error (embeddings, BM25, rewrite). Neither the selection nor the prompt will help.
2. Is it among the 5 chunks for the model? No → selection error (reranker).
3. The model had it and answered wrongly → reading error (prompt, model, chunk metadata).
4. After every fix I measure everything again, not just the fixed question. That is how I found a regression: in v3 the selection for „odpočinek mezi směnami“ took only the exceptions (§ 90 odst. 2, 3) without the rule (odst. 1). The fix is a fixed rule without AI: for paragraph 2, 3… always add paragraph 1.

Example: hit@5 is 56 of 56, but the answer about the posudek (assessment) was wrong → the problem is in reading, not retrieval. A more precise prompt and a stronger model helped.

## 9. Why the retrieval is written three times

- **Python** (`rag.py`): this is what is measured.
- **JavaScript** (`site/api/ask.js`): the website runs as a serverless function in Node.js on Vercel. One service with no extra server, free.
- **LangChain** (`rag_langchain.py`): a demonstration that I can do the same procedure in a framework companies use.

The risk of three copies is that they drift apart. That is why a test in `tests/` runs the JavaScript and compares it with Python. In production I would have one implementation (a Python API) and the website would only display results.

## 10. Website and protection · `site/`

- The key lives only in an environment variable on Vercel. Max 10 questions per IP per day, a cap of 400 per day, proof of work (the browser computes a hash with 4 zeros, 1–3 s), origin check, a hidden field against bots. A hard $0.75 limit on the key.
- The sample questions are precomputed and checked, they cost nothing.
- The map shows the real intermediate results of the search, not an animation. The layout of the 2 475 points is computed in advance in Python.
- Weakness: the counters are in the function's memory. With several instances the limit could be bypassed. Fix: Redis.

## 11. What would be missing for production

Not needed for the demo. For a real deployment:

- **Updating the laws:** compare the regulation version daily; on a change, re-chunk only that regulation, recompute embeddings of the changed paragraphs (a cache keyed by text can do this), run the measurement and deploy only if the result does not drop.
- **A test set from production:** nobody writes 10 000 questions by hand. A sample of real queries from the logs split by area, plus questions generated from paragraphs and a manual check of a sample. Hard cases (similar sections, mzda × plat) go into a permanent regression set. Take the test set from a later period than the tuning set so that nothing is tuned to the test.
- **Measurement in production:** latency, cost per query, share of "I don't know", clicks on citations and thumbs up / down.
- **More data:** at hundreds of thousands of chunks, pgvector or Qdrant instead of numpy and Postgres full-text instead of my own BM25. The procedure stays the same.
- **Other documents:** a law is plain text with a clear structure, which is an easy case for RAG. PDFs with tables, scans or documents in several versions would need different chunking, OCR, metadata filtering and access rights.
- **When RAG is not enough:** when the answer requires a calculation (the amount of severance pay from average earnings) or combining many sections. There a tool (calculator) or an agent that searches several times would help.

## 12. Tests · `tests/`

14 tests with no API calls, running in under 1 s: word splitting for BM25, RRF, extracting numbers from the model's answer, the paragraph 1 and references rules, int8 conversion back and forth, the mzda × plat note, and a check that the correct chunks from the test sets are really in the data. One test runs the website code in Node.js and verifies that it searches the same as Python. GitHub runs them after every push.
