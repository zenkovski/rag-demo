# Rozhodnutí (ADR)

Každé významné rozhodnutí: kontext, rozhodnutí, důsledky, jaké byly alternativy. Stav „otevřené“ znamená, že data nestačí a rozhodnutí se odkládá na konkrétní měření.

| ADR | Rozhodnutí | Stav |
|---|---|---|
| [001](ADR-001-offline-quality-gate.md) | Quality gate přehrává uložené výsledky, nevolá model | přijato |
| [002](ADR-002-rrf-misto-vazeni.md) | RRF místo váženého součtu skóre | přijato |
| [003](ADR-003-opravneni-v-hledani.md) | Oprávnění se vynucuje v hledací vrstvě, ne v promptu | přijato (vzor, ne zapojeno) |
| [004](ADR-004-prepis-a-bm25-otevrena-otazka.md) | Přepis otázky a BM25: přínos není prokázán | **otevřené** |
| [005](ADR-005-llm-vyber-misto-cross-encoderu.md) | LLM výběr místo cross-encoderu | přijato, k přehodnocení |
| [006](ADR-006-deterministicke-kontroly.md) | Deterministické kontroly vedle LLM soudce | přijato |
