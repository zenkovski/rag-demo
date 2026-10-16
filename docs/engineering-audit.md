# Engineering audit: RAG demo → agent-ready knowledge service

Date: 2026-10-16 · commit `c6a6955` · scope: [upgrade brief](#plan-and-acceptance-criteria) (service layer, REST, MCP).
Every row below was checked by running a command, not copied from the docs.

## Baseline (run locally, Windows, Python 3.13.14)

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check .` | clean |
| Types | `mypy` (5 typed modules) | clean |
| Tests | `pytest tests -q` (offline, network blocked) | **113 passed**, 12.6 s |
| Quality gate | `python tools/experiments.py --check --no-base` | v3 recall@5 0.9866, MRR 0.9643, n=56, no regressions |
| Docker | `docker --version` | **not installed on this PC** → Docker will be verified in CI only |

## What works

- One pipeline (`tools/rag.py`): query rewrite → e5-large + BM25 → RRF → LLM picks 5 of 20 → deterministic rules (paragraph 1, in-section references) → answer with `[n]` citations.
- Offline replay: embeddings (`data/emb_cache.npz`) and LLM answers (`data/llm_cache.json`) are cached, `RAG_OFFLINE=1` turns a cache miss into an error instead of a paid call.
- Deterministic answer checks (`tools/answer_checks.py`): citation range, missing citation, numbers not in the sources.
- Permission filter inside retrieval (`rag.search(allow=...)`), tested.

## What is duplicated

- Retrieval exists 3× (Python, LangChain LCEL, JS on Vercel). Justified (measure in Python, serve on Vercel, show LCEL) and guarded by parity tests. **The new service must not become copy no. 4**: it calls `rag.search`, it does not re-implement it.
- Prompts are copied into `site/api/_index.json` by `tools/build_data.py` (generated, not hand-edited). OK.
- `rag.load_chunks()` parses `chunks.json` again on every call (only cached indirectly). Cheap fix in the service layer.

## Three biggest risks

1. **LLM cache is not safe for a server.** `rag.llm()` reads and rewrites the whole 1 MB `llm_cache.json` on every call. Two concurrent requests can lose a write or leave broken JSON. Fix: load once, write under a lock, same cache keys (so stored answers stay valid and free).
2. **"Search without an LLM" does not exist yet.** The v3 search makes 2 LLM calls (rewrite, rerank) + 1 embedding call. Measured options without an LLM (baseline, n=56): `dense_large` recall@5 **0.857** (MRR 0.741); `rrf_dense_bm25` 0.750. So `mode="fast"` = existing `dense_large` path (1 embedding call, no LLM); `mode="full"` = v3 (0.987). Both are existing code paths with existing numbers. Note: "fast" still needs the embedding API for a new query.
3. **Law text goes to external agents.** Through MCP, retrieved text lands in another model's context. A poisoned passage could carry instructions. Mitigation: passages are returned as data fields (never merged into instructions), tool descriptions say so, plus a test with an injected instruction inside a passage.

Smaller: `ask` costs money (3 LLM calls; measured cost incl. AI judge ~0.0011 $ per question, baseline `ops`); tests use the cache only. Open bug "výpověď v nemoci" (ZP § 53 not among the 20 candidates) cannot be fixed for free: any retrieval change invalidates the cached rerank call.

## Plan and acceptance criteria

| Phase | Deliverable | Done when |
|---|---|---|
| B | `tools/service.py`: `search()`, `ask()`, `get_document()` with typed results; cache-safe `llm()` | `search(mode="full")` returns exactly `rag.search` hits for all 56 cached questions (new test); quality gate unchanged |
| C | `api/` FastAPI: `POST /api/v1/search`, `POST /api/v1/ask`, `GET /api/v1/documents/{id}`, `/health`, API key, request ID, limits | integration tests: 200, 422, 401, 503/504 provider down (mocked); `/docs` renders; Dockerfile builds in CI |
| D | `mcp_server.py` (official MCP SDK, stdio): `search_knowledge`, `ask_knowledge`, `get_document` | real SDK client over stdio lists 3 tools and gets citations from `search_knowledge`; injection test green |
| E | English README (30 s), `README.cs.md`, `docs/explain-for-lukas.md`, GitHub About | links work; no caveat deleted, only moved to `docs/` |

Out of scope (agreed): tracing, run records, `/runs`, dashboard, new experiments, remote MCP transport, queues, UI rewrite.

## Next steps (if the session ends early)

Status is updated here at the end of each phase.

- [x] Phase A: audit
- [x] Phase B: service layer (`tools/service.py`, baseline equality test for 56 questions in both modes)
- [x] Phase C: REST API (`tools/api.py`, 26 integration tests, Docker verified in CI run 38828365259)
- [x] Phase D: MCP server (`tools/mcp_server.py`, stdio e2e test with the SDK client; Claude Code connected and called `search_knowledge` on 2026-10-16, see [mcp.md](mcp.md))
- [x] Phase E: English README, `README.cs.md`, [explain-for-lukas.md](explain-for-lukas.md), GitHub About set. Bad preset "výpověď v nemoci": already not among the quick-question buttons (repo and live site checked 2026-10-16); it stays visible, marked wrong, in the question list and the failure gallery. No fix: any retrieval change invalidates the cached rerank call (not free).
- [x] Agent check (`tools/agent_check.py`): Claude Sonnet via MCP 10/10 on questions 57–66, DeepSeek pipeline 10/10, agreement 10/10 ([mcp.md](mcp.md#agent-check-claude-as-the-agent-deepseek-as-a-second-opinion)).

### Not done / open
- Docker not run on the dev PC (no Docker installed); verified only in CI.
- `ask` latency and cost with live calls: not run (offline only).
- Live demo still runs the old `hit.js`; deploy needs approval.
