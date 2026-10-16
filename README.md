# Czech Labour Law Knowledge Service

**English** · [Česky](README.cs.md)

[![tests](https://github.com/zenkovski/rag-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/zenkovski/rag-demo/actions/workflows/tests.yml)

**A cited-answer RAG service over 4 Czech labour laws, usable by people (web), programs (REST API) and AI agents (MCP).**
Live demo: **[lukas-rag.vercel.app](https://lukas-rag.vercel.app)** (Czech UI; English toggle in the repo, not deployed yet)

![Question, cited answer and a map of the laws where the retrieved paragraphs light up](docs/demo.webp)

## What it does

- Searches **2,475 paragraphs** of 4 Czech labour laws. Every result has a paragraph ID like `ZP § 52 odst. 1` and a source link.
- Answers only from the retrieved text, with citations. When the law does not say, it answers "I don't know" and marks `evidence_status: insufficient`.
- One shared core, three doors: web UI, REST API (FastAPI) and MCP server (official SDK). Same results everywhere.
- Measured, not guessed: held-out questions, confidence intervals, offline quality gate in CI.

```
Human ──────── Web UI (Vercel) ──────┐
AI agent ───── MCP server (stdio) ───┼──> tools/service.py ──> tools/rag.py (retrieval pipeline)
Programs ───── REST API (FastAPI) ───┘
```

## Connect your agent (MCP)

```bash
git clone https://github.com/zenkovski/rag-demo.git && cd rag-demo
python -m venv .venv && .venv/bin/pip install -r requirements-service.txt
claude mcp add czech-labour-law -e RAG_OFFLINE=1 -- "$PWD/.venv/bin/python" "$PWD/tools/mcp_server.py"
```

Claude Desktop config, Windows paths and troubleshooting: **[docs/mcp.md](docs/mcp.md)**. `RAG_OFFLINE=1` = no API key needed, nothing is paid, answers come from the cache (82 prepared questions).

Tools: `search_knowledge` (no LLM in `mode=fast`), `ask_knowledge` (cited answer), `get_document` (full paragraph). Ask your agent: *"Use search_knowledge: Jak dlouhá je výpovědní doba?"* ("How long is the notice period?"). Real output (text shortened):

```json
{
  "query": "Jak dlouhá je výpovědní doba?",
  "mode": "fast",
  "passages": [
    {"rank": 1, "id": "ZP § 51 odst. 2", "law": "ZP", "title": "Výpověď",
     "text": "(2) Výpovědní doba činí nejméně 2 měsíce, s výjimkou výpovědi dané a) …",
     "score": 0.8907, "source_url": "https://www.zakonyprolidi.cz/cs/2006-262"}
  ]
}
```

`ask_knowledge` adds `answer`, `evidence_status`, `citations` (`marker`, `id`, `excerpt`, `source_url`) and deterministic `checks`. Passage text is returned as untrusted data, never as instructions (tested with an injected instruction).

## REST API quick start

```bash
export RAG_API_KEYS=my-local-key     # or put it in .env
docker compose up --build            # offline by default; docs at http://localhost:8000/docs

curl -s -X POST localhost:8000/api/v1/search -H "X-API-Key: my-local-key" -H "Content-Type: application/json" \
  -d '{"query": "Jak dlouhá je výpovědní doba?", "k": 3}'
curl -s -X POST localhost:8000/api/v1/ask -H "X-API-Key: my-local-key" -H "Content-Type: application/json" \
  -d '{"question": "Jak dlouhá je výpovědní doba?"}'
curl -s "localhost:8000/api/v1/documents/ZP%20%C2%A7%2051%20odst.%202" -H "X-API-Key: my-local-key"
```

Without Docker: `pip install -r requirements-service.txt`, then `RAG_OFFLINE=1 RAG_API_KEYS=my-local-key uvicorn api:app --app-dir tools`. Errors are structured (`401`, `404`, `413`, `422`, `503` provider down, `504` timeout) and carry a request ID. On Windows, send Czech text from a UTF-8 file: `--data-binary @query.json`.

## Key results

Measured on **134 questions the system was never tuned on** (sets v4 + v5, frozen in git before the run; 112 answerable, 22 where the law has no answer). Details and caveats: [docs/evaluation-v5.md](docs/evaluation-v5.md).

| Measure | Result |
|---|---|
| Correct paragraph among the 5 passages the model reads | **111 / 112** (95 % Wilson 0.95–1.00) |
| Correct answers, judged against hand-checked gold answers | **108 / 112** (0.91–0.99) |
| "I don't know" when the law has no answer | **21 / 22** (0.78–0.99) |

Honest scope: in this run the LLM steps (rewrite, pick, answer) were done by **Claude Sonnet with the same prompts**, not by the DeepSeek models of the live site, to spend no API credits; questions and judges are also Claude, with a 15-answer spot check. Without any LLM, the `fast` search alone finds the gold paragraph in the top 5 for 101/112. Older measurements (66 questions, ablations with p-values) are in [docs/benchmark-results.md](docs/benchmark-results.md); method in [docs/evaluation-methodology.md](docs/evaluation-methodology.md); known failures in [docs/failure-gallery.md](docs/failure-gallery.md); limits in [docs/limitations.md](docs/limitations.md).

## How it works

```
question
  → rewrite into legal language            ("výplata" → "mzda")             LLM (DeepSeek v4.1 Flash)
  → semantic + keyword search              (e5-large + BM25, fused by RRF) → 20 candidates
  → LLM picks 5 passages                   (+ deterministic rules: paragraph 1, in-section references)
  → answer only from those 5, with [n] citations                            LLM (DeepSeek v4 Pro)
  → deterministic checks                   (citation range, numbers present in the cited text)
```

The same retrieval exists in Python, LangChain (LCEL) and JavaScript (live site); parity tests keep them identical. The service layer and both APIs call the Python version and do not copy it.

## Run the checks

```bash
pip install -r requirements-service.txt -r requirements-dev.txt
python -m pytest tests                                  # 165 tests, offline, network blocked
ruff check . && mypy
python tools/experiments.py --check --no-base           # quality gate: retrieval vs results/baseline.json
```

CI runs the same: lint + types, tests, quality gate, and a Docker build with a smoke test.

## Documentation

[Engineering audit](docs/engineering-audit.md) · [MCP guide](docs/mcp.md) · [Architecture](docs/architecture.md) · [Design decisions](DESIGN.md) · [ADRs](docs/decisions/) · [Incidents](docs/incidents/) · [Threat model](security/threat-model.md) · [History v1 → v3.1](HISTORY.md) · [AI-assisted development](docs/ai-assisted-development.md). Most lab documents are in Czech.

## Authorship

I designed the system and directed the build with Claude Code; I verified it with tests, evaluations and code reviews. Not legal advice: a technical demo. Law texts from zakonyprolidi.cz, downloaded 2026-10-06 (262/2006, 435/2004, 187/2006, 590/2006 Sb.).
