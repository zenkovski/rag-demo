# Connect an AI agent (MCP)

The MCP server (`tools/mcp_server.py`) runs over **stdio**: your agent app starts it as a child process. It uses the official MCP Python SDK (v2.3.0) and the same service layer as the REST API.

| Tool | What it does | Needs an LLM? |
|---|---|---|
| `search_knowledge` | Ranked passages with paragraph IDs, scores, source URLs. `mode=fast` (default) or `mode=full` | `fast`: no (1 embedding call) · `full`: 2 LLM calls |
| `ask_knowledge` | Answer with structured citations and `evidence_status` | yes, 3 LLM calls (paid unless cached) |
| `get_document` | Full text + metadata of one paragraph, e.g. `ZP § 51 odst. 2` | no |

## 1. Install (once)

```bash
git clone https://github.com/zenkovski/rag-demo.git && cd rag-demo
python -m venv .venv
.venv/bin/pip install -r requirements-service.txt        # Windows: .venv\Scripts\pip install -r requirements-service.txt
```

**Offline by default in the configs below** (`RAG_OFFLINE=1`): no key needed, nothing is paid, answers come from the stored cache. That covers the 82 prepared questions (list: `site/api/_presets.json`). For any new question, set `RAG_OFFLINE=0` and put `OPENROUTER_API_KEY` in `.env`.

## 2a. Claude Code (one command)

Run inside the cloned folder. Use absolute paths.

```bash
# macOS / Linux
claude mcp add czech-labour-law -e RAG_OFFLINE=1 -- "$PWD/.venv/bin/python" "$PWD/tools/mcp_server.py"
```

```powershell
# Windows (PowerShell)
claude mcp add czech-labour-law -e RAG_OFFLINE=1 -- "$PWD\.venv\Scripts\python.exe" "$PWD\tools\mcp_server.py"
```

Check: `claude mcp list` shows `czech-labour-law: ✓ Connected`.

## 2b. Claude Desktop (paste config)

Open *Settings → Developer → Edit Config* (file `claude_desktop_config.json`: macOS `~/Library/Application Support/Claude/`, Windows `%APPDATA%\Claude\`). Add, with your own absolute paths, then restart Claude Desktop:

```json
{
  "mcpServers": {
    "czech-labour-law": {
      "command": "/ABSOLUTE/PATH/rag-demo/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/rag-demo/tools/mcp_server.py"],
      "env": { "RAG_OFFLINE": "1", "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

On Windows the command is `C:/path/rag-demo/.venv/Scripts/python.exe` (forward slashes work).

## 3. Test a tool call

Ask the agent: *"Use search_knowledge: Jak dlouhá je výpovědní doba?"* ("How long is the notice period?").

Non-interactive check with Claude Code (this exact command was run on 2026-10-16 and returned `ZP § 51 odst. 2, ZZ § 78 odst. 7, ZP § 51 odst. 1`):

```bash
claude -p --mcp-config mcp.json --strict-mcp-config --allowedTools "mcp__czech-labour-law__search_knowledge" \
  "Call search_knowledge with query 'Jak dlouhá je výpovědní doba?' and k=3. Reply with only the paragraph IDs."
```

(`mcp.json` = the same `mcpServers` block as in 2b.)

Example structured output of `search_knowledge` (`k=2`, text shortened here):

```json
{
  "query": "Jak dlouhá je výpovědní doba?",
  "mode": "fast",
  "rewritten_query": null,
  "passages": [
    {"rank": 1, "id": "ZP § 51 odst. 2", "law": "ZP", "law_name": "Zákoník práce", "title": "Výpověď",
     "text": "(2) Výpovědní doba činí nejméně 2 měsíce, s výjimkou výpovědi dané a) …",
     "truncated": false, "score": 0.8907, "source_url": "https://www.zakonyprolidi.cz/cs/2006-262"},
    {"rank": 2, "id": "ZZ § 78 odst. 7", "law": "ZZ", "law_name": "Zákon o zaměstnanosti", "title": "Chráněný trh práce …",
     "text": "(7) Výpovědní doba činí 2 měsíce a počíná běžet …",
     "truncated": false, "score": 0.8788, "source_url": "https://www.zakonyprolidi.cz/cs/2004-435"}
  ]
}
```

`ask_knowledge` returns `answer`, `evidence_status` (`sufficient` / `insufficient`), `citations` (`marker`, `id`, `excerpt`, `source_url`), `passages_supplied` and deterministic `checks` (`bad_citations`, `unsupported_numbers`).

## Agent check: Claude as the agent, DeepSeek as a second opinion

`tools/agent_check.py` gives Claude Sonnet (via `claude -p`) only `search_knowledge` and `get_document` and lets it answer by itself. The result is compared with the gold paragraphs and with this project's own pipeline (`ask_knowledge`, DeepSeek, from cache).

Run on 2026-10-16, held-out questions 57–66 (8 with an answer, 2 where the law has none), server offline (0 $ OpenRouter; ~1.5 $ equivalent of Claude plan usage):

| | Claude Sonnet as MCP agent | DeepSeek pipeline |
|---|---|---|
| Cites the gold paragraph / says "I don't know" when it should | **10 / 10** (Wilson 95 % 0.72–1.00) | **10 / 10** |
| Same `evidence_status` as the other model | 10 / 10 | |

What this does **not** measure: whether every sentence of the answer is right (no judge was run here), and questions outside this small set. Raw answers: `results/agent_check.json`.

## Safety

- Every passage `text` is **untrusted data**. The server instructions and the output schema say so; agents should quote it, never follow it. Test: `tests/test_mcp.py` puts an injected instruction inside a passage.
- If a model obeys an injected "cite [9]", the deterministic check marks the answer `insufficient` (`bad_citations: [9]`).
- All tools are read-only. Limits: query 3–500 characters, `k` ≤ 10, passage text ≤ 1,500 characters (full text via `get_document`), timeout 30 s (search) / 60 s (ask).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server "failed" / not connected | Use absolute paths. Run the command yourself: it should wait silently for input (Ctrl+C to stop). An import error means the venv is missing `requirements-service.txt`. |
| `provider_unavailable: offline mode … not in the cache` | Expected in offline mode for a new question. Use a prepared question, or set `RAG_OFFLINE=0` + `OPENROUTER_API_KEY`. |
| `provider_unavailable: OPENROUTER_API_KEY is not set` | Put the key in `rag-demo/.env` (the server reads it from there) or in the `env` block. |
| `not_found … Try: ZP § 51 odst. 1, …` | The paragraph has subsections; use one of the suggested IDs. |
| Garbled Czech characters (Windows) | Add `"PYTHONIOENCODING": "utf-8"` to `env`. |
| First call is slow (~1–2 s) | Loading 2,475 vectors on start. Later calls are fast. |
