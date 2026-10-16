[Česky](cs/limitations.md)

# Limitations and what is not finished

What the project **cannot do**, what it **does not measure** and what was **deliberately not done**, with the reason. Kept apart: what is measured (in [benchmark-results.md](benchmark-results.md)), estimates and plans.

Abbreviations: ZP = Labour Code, ZZ = Employment Act, ZNP = Sickness Insurance Act, NV 590 = Government Decree 590/2006.

## What is missing from the "AI Knowledge Platform" brief, and why

| Area | Status | Reason |
|---|---|---|
| Ingest of multiple document types, deduplication, document versions | **not present** | the source is plain text of 4 laws with a clear structure (an easy case). PDFs, tables and OCR would need different chunking; conclusions from this project **do not transfer** to them |
| Reranking: cross-encoder × LLM | done | the difference is inconclusive (p = 0.125), see [ADR-005](decisions/ADR-005-llm-vyber-misto-cross-encoderu.md) |
| Text chunking strategies, chunk sizes | **not done** | requires recomputing embeddings via a paid API; chunking by paragraph is justified by the structure of the law, not measured against alternatives |
| Further embedding models, quantisation | only e5-base × e5-large | more models = a new cache = money |
| **Distributed tracing, p50/p95/p99 of the whole service, throughput** | **not measured** | requires live calls against the paid API and against the $0.75 limit on the key. Only the search compute time is measured (p50 ≈ 7 ms, without network). A load test without real numbers would be just text |
| Answer cache | **not present** | the benefit would have to be measured; without a cache there is no data-leak path through the cache ([ADR-003](decisions/ADR-003-opravneni-v-hledani.md)) |
| Retry with backoff, timeouts | partial | `rag.llm` retries on 429 and 5xx and waits; the web function tries 3×. Since 2026-10-16 the service layer (`tools/service.py`) has a total deadline per request (30 s search via MCP, 60 s ask) and maps failures to 503/504. A **concurrency limit** and separate per-step timeouts are not present; a timed-out thread keeps running in the background |
| Versioning of prompts/models/index | fingerprints in the run record | **a runtime version switch and automatic rollback are not present**; returning = git |
| Docker | **present since 2026-10-16** | `Dockerfile` + `docker-compose.yml` for the REST API (offline by default). Verified only in CI (job `docker`: build, healthy, `/health`, search, 401); not run on the development PC |
| Authorisation, tenant isolation | API key + pattern in the search | the website has no users. The REST API (2026-10-16) requires an `X-API-Key` (keys in `RAG_API_KEYS`); there are no per-user rights and **no rate limit**. The `allow` (law filter) pattern is exposed as `laws` in API and MCP, but it is a filter, not tenant isolation ([ADR-003](decisions/ADR-003-opravneni-v-hledani.md)) |
| **AI agent** | **external agents via MCP (2026-10-16); no own multi-step agent** | the project does not run its own agent loop: a simple chain answers better per dollar. Instead, external agents (Claude Desktop / Claude Code) use the MCP server (`tools/mcp_server.py`). Claude Sonnet as such an agent cited the gold paragraph or correctly declined on 10/10 held-out questions ([mcp.md](mcp.md)). A **calculator as a tool** (severance from average earnings) is still only a candidate |
| ML experiment beyond LLM API calls | **only the cross-encoder and e5-base locally** | model training (fine-tuning) was not done: without enough data and without a hypothesis for it to verify, it would be just "we can do fine-tuning" |

## What is measured but weak

- **The sets are small.** 56 questions with an answer, of which 8 validation and 8 test. Differences of 1–3 questions cannot be distinguished from chance, and most ablations turned out exactly like that.
- **The dev number is inflated.** "66 of 66" came from tuning on most of the questions.
- **One frozen set v4 (24 questions)** is written, **not run**. Until then there is no measurement on questions the system has never seen, except for the 10 questions 57–66.
- **The questions and correct answers were created with an AI assistant**, not by an independent team. They were checked against the text of the law by one additional model and reviewed by the project owner. No independent legal review took place.
- **The answers are from one stored run.** The model's behaviour fluctuates between runs (see [HISTORY.md](../HISTORY.md): "the cheap model read the same paragraph correctly once and wrongly another time"). Repeated runs with variance were not done.
- **The number and citation check is not in the live chain**, only in measurement. A live answer with a citation out of range would be displayed; only the measurement catches it.
- **No Content-Security-Policy and Subresource Integrity** on the website ([threat-model.md](../security/threat-model.md), T8 and T12).

## Known errors (not fixed)

Two of the 16 sample questions on the website are wrong. The worst is notice of termination during illness: the website claims it can be given, whereas the law forbids it during the protection period. The cause is measured (the question rewrite led the search elsewhere), the fix is not: [failure-gallery.md](failure-gallery.md#open-failures-not-fixed-yet), [ADR-004](decisions/ADR-004-prepis-a-bm25-otevrena-otazka.md).

## What was fixed but is not deployed

`site/api/hit.js` (the click counter) now accepts only prepared questions. The fix is in the repository and tested, but **is not running on the live website yet**.

## Operational state that may change

The OpenRouter key for the live demo has a hard limit of $0.75 and as of 9 Oct 2026 about $0.09 remains. Once it is used up, the website shows "The budget for live questions is exhausted" („Rozpočet na živé otázky je vyčerpaný“); the precomputed questions keep working.
