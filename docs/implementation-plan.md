[Česky](cs/implementation-plan.md)

# Plan and audit

State as of 9 Oct 2026. First an audit (what really works, verified by running it), then a plan in small steps with completion criteria, finally the risks. What was done and what was not is in the **Status** column.

Abbreviations: ZP = Labour Code, ZZ = Employment Act, ZNP = Sickness Insurance Act, NV 590 = Government Decree 590/2006.

## 1. Audit of the starting state

Carried out before any change (commit `88ec093`). Every row is verified by a command, not taken from the README.

| Finding | Verified | Conclusion |
|---|---|---|
| 14 tests pass, no API | `pytest tests` → 14 passed in 1 s | works |
| Retrieval can be replayed from stored results without a key | all 56 questions through `rag.search`, `OPENROUTER_API_KEY` removed from the environment | works, **but 51 s** (the embedding cache was read from a 16 MB file on every query) |
| The replayed ranking matches the measurement | correct § among 5 chunks for 55 of 56 by the first correct chunk (README: 56 of 56 by any) | matches |
| README claims "20 of 20 on questions written in advance" | git: `testset_fresh.json` (47–56) was created before v3, but v3.1 was created based on its errors; `testset_fresh2.json` (57–66) before v3.1 | **inflated:** truly untouched are 10 questions, not 20 |
| No formal roles of sets (dev / validation / test) | `data/` | **missing** |
| Metrics: only hit@3, hit@5, MRR only in DESIGN.md for one ablation | `tools/evaluate.py` | Recall@k, nDCG, confidence intervals, paired tests missing |
| The question set has only layperson questions | 66 questions read | **missing:** exact references to sections, multiple paragraphs, ambiguous, outdated, injections |
| CI | `.github/workflows/tests.yml` | runs only pytest; no lint, types or comparison with a reference state |
| Secrets in the repo | key patterns via `git ls-files` | clean (`.env` in `.gitignore`, `.env.example` without a value) |
| Click counter `hit.js` | code reading | **writes an arbitrary string to Redis** (forgeable `Origin` header), the database could be filled up |
| Three copies of the search (Python, JS, LangChain) | `tests/test_rag.py::test_web_matches_python` | the duplication is justified and guarded by an equivalence test |
| Live demo key | OpenRouter `/key` (read only) | limit $0.75, ~$0.09 remaining → **do not run live measurements on it** |

## 2. Target architecture

The smallest useful one: no rewrite, no new services. To the chain were added a **measurement layer** (see [architecture.md](architecture.md)), security tests and CI gates. Everything that worked was kept.

## 3. Plan and status

| # | Step | Completion criterion | Status |
|---|---|---|---|
| 0 | Audit and this plan | the table above, every row verified | **done** |
| 1 | Roles of sets + methodology | `data/splits.json`, [evaluation-methodology.md](evaluation-methodology.md), README corrected | **done** |
| 2 | Metrics and statistics | Recall@k, MRR, nDCG, bootstrap, Wilson, paired test; every function tested on a hand-computed example | **done** |
| 3 | Ablations (P0) | 9 systems, RRF k, weighted sum, rewrite, reranking; run record (config, fingerprints, runtime, cost, regressions) | **done** (without chunking and further embeddings, see limitations) |
| 4 | Failure diagnostics | categories A–F, a gallery of real errors with cause, fix and proof | **done** |
| 5 | Quality gate in CI | lint + types + tests + comparison with baseline, a failure shows the questions | **done**, demonstration of a regression below |
| 6 | Security | [threat model](../security/threat-model.md), tests of web functions, permissions in the search, XSS, secrets | **done**; model behaviour under injection **not measured** (live set prepared) |
| 7 | New frozen set | 24 questions, all types from the brief, one-off run lock | **written**, **NOT run** (waiting for budget) |
| 8 | Incidents | ≥ 1 from symptom to proof of fix | **done** (3: two from history, one demonstration in CI) |
| 9 | ADRs | significant decisions with reasoning and open questions | **done** (6) |
| 10 | Clean start per README | fresh clone, install, tests, gate | **verified in CI** (GitHub Actions: ubuntu, clean virtualenv) |
| – | Per-step tracing, load test, cache, Docker, agent, model training | – | **deliberately not** (reasons in [limitations.md](limitations.md)) |

## 4. Risks and open items

| Risk | Impact | Status |
|---|---|---|
| Key budget (~$0.09) | the new set v4 and live injections cannot be run | **awaiting decision:** a separate key with ≥ $1 |
| Deploying the `hit.js` fix | the live website still has the old version | **awaiting approval** (nothing is deployed without it) |
| Small sets | differences of 1–3 questions cannot be distinguished | set v4 + repetition, see [ADR-004](decisions/ADR-004-prepis-a-bm25-otevrena-otazka.md) |
| The baseline freezes errors | "same as before" ≠ "correct" | described in [ADR-001](decisions/ADR-001-offline-quality-gate.md) |
| Open error "notice of termination during illness" | a misleading answer on the live website | diagnosed, **not fixed** |

## 5. Order of work and what changed from the first idea

The brief assumed an "AI Knowledge Platform" (ingestion, retrieval, generation, evaluation, observability, security, web). After the audit, **modules were not added just to match a technology list**. Evaluation and security are new; ingestion, retrieval and generation already existed and work; observability is the weakest spot and is described as such.
