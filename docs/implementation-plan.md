# Plán a audit

Stav k 9. 10. 2026. Nejdřív audit (co opravdu funguje, ověřeno spuštěním), potom plán po malých krocích s kritérii dokončení, nakonec rizika. Co se udělalo a co ne, je ve sloupci **Stav**.

## 1. Audit výchozího stavu

Provedeno před jakoukoli změnou (commit `88ec093`). Každý řádek je ověřený příkazem, ne převzatý z README.

| Zjištění | Ověřeno | Závěr |
|---|---|---|
| 14 testů prochází, bez API | `pytest tests` → 14 passed za 1 s | funguje |
| Hledání jde přehrát z uložených výsledků bez klíče | všech 56 otázek přes `rag.search`, `OPENROUTER_API_KEY` odstraněn z prostředí | funguje, **ale 51 s** (embedding cache se četla ze souboru 16 MB při každém dotazu) |
| Přehrané pořadí odpovídá měření | správný § mezi 5 úseky u 55 z 56 podle prvního správného úseku (README: 56 z 56 podle kteréhokoli) | sedí |
| README tvrdí „20 z 20 na otázkách napsaných předem“ | git: `testset_fresh.json` (47–56) vznikla před v3, ale podle jejích chyb vznikla v3.1; `testset_fresh2.json` (57–66) před v3.1 | **nadsazené:** skutečně netknutých je 10 otázek, ne 20 |
| Žádná formální role sad (dev / validation / test) | `data/` | **chybí** |
| Metriky: jen hit@3, hit@5, MRR jen v DESIGN.md u jedné ablace | `tools/evaluate.py` | chybí Recall@k, nDCG, intervaly spolehlivosti, párové testy |
| Sada otázek má jen laické otázky | 66 otázek přečteno | **chybí** přesné odkazy na paragrafy, více odstavců, nejednoznačné, zastaralé, injekce |
| CI | `.github/workflows/tests.yml` | spouští jen pytest; bez lintu, typů a srovnání s referenčním stavem |
| Tajemství v repu | vzory klíčů přes `git ls-files` | čisté (`.env` v `.gitignore`, `.env.example` bez hodnoty) |
| Počítadlo kliků `hit.js` | čtení kódu | **zapisuje do Redisu libovolný řetězec** (padělatelná hlavička `Origin`), šlo zaplnit databázi |
| Tři kopie hledání (Python, JS, LangChain) | `tests/test_rag.py::test_web_matches_python` | duplicita je zdůvodněná a hlídaná testem ekvivalence |
| Klíč živého dema | OpenRouter `/key` (jen čtení) | limit 0,75 $, zbývá ~0,09 $ → **živá měření na něm nespouštět** |

## 2. Cílová architektura

Nejmenší užitečná: žádný přepis, žádné nové služby. K řetězci přibyla **měřicí vrstva** (viz [architecture.md](architecture.md)), bezpečnostní testy a CI brány. Zachováno vše, co fungovalo.

## 3. Plán a stav

| # | Krok | Kritérium dokončení | Stav |
|---|---|---|---|
| 0 | Audit a tento plán | tabulka výše, každý řádek ověřen | **hotovo** |
| 1 | Role sad + metodika | `data/splits.json`, [evaluation-methodology.md](evaluation-methodology.md), README opraveno | **hotovo** |
| 2 | Metriky a statistika | Recall@k, MRR, nDCG, bootstrap, Wilson, párový test; každá funkce testovaná na ručně spočítaném příkladu | **hotovo** |
| 3 | Ablace (P0) | 9 systémů, RRF k, vážený součet, přepis, reranking; záznam o běhu (config, otisky, runtime, cena, regrese) | **hotovo** (bez dělení textu a dalších embeddingů, viz limity) |
| 4 | Diagnostika selhání | kategorie A–F, galerie skutečných chyb s příčinou, opravou a důkazem | **hotovo** |
| 5 | Quality gate v CI | lint + typy + testy + srovnání s baseline, selhání ukáže otázky | **hotovo**, demonstrace regrese níže |
| 6 | Bezpečnost | [model hrozeb](../security/threat-model.md), testy webových funkcí, oprávnění v hledání, XSS, tajemství | **hotovo**; chování modelu pod injekcí **nezměřeno** (živá sada připravená) |
| 7 | Nová zmrazená sada | 24 otázek, všechny typy ze zadání, zámek jednorázového běhu | **napsáno**, **NEspuštěno** (čeká na rozpočet) |
| 8 | Incidenty | ≥ 1 od symptomu po důkaz opravy | **hotovo** (3: dva z historie, jeden ukázkový v CI) |
| 9 | ADR | významná rozhodnutí se zdůvodněním a otevřenými otázkami | **hotovo** (6) |
| 10 | Čistý start podle README | nový klon, instalace, testy, gate | **ověřeno v CI** (GitHub Actions: ubuntu, čistý virtualenv) |
| – | Tracing po krocích, load test, cache, Docker, agent, trénování modelu | – | **záměrně ne** (důvody v [limitations.md](limitations.md)) |

## 4. Rizika a otevřené věci

| Riziko | Dopad | Stav |
|---|---|---|
| Rozpočet klíče (~0,09 $) | nelze pustit novou sadu v4 ani živé injekce | **čeká na rozhodnutí:** samostatný klíč s ≥ 1 $ |
| Nasazení opravy `hit.js` | živý web má stále starou verzi | **čeká na schválení** (nic se nenasazuje bez něj) |
| Malé sady | rozdíly o 1–3 otázky nejde rozlišit | sada v4 + opakování, viz [ADR-004](decisions/ADR-004-prepis-a-bm25-otevrena-otazka.md) |
| Baseline zamrzne chyby | „stejně jako dřív“ ≠ „správně“ | popsáno v [ADR-001](decisions/ADR-001-offline-quality-gate.md) |
| Otevřená chyba „výpověď v nemoci“ | zavádějící odpověď na živém webu | diagnostikováno, **neopraveno** |

## 5. Pořadí práce a co se změnilo oproti první představě

Zadání počítalo s „AI Knowledge Platform“ (ingestion, retrieval, generation, evaluation, observability, security, web). Po auditu se **nepřidávaly moduly kvůli seznamu technologií**. Evaluace a bezpečnost jsou nové; ingestion, retrieval a generation už existovaly a fungují; observability je nejslabší místo a je popsané jako takové.
