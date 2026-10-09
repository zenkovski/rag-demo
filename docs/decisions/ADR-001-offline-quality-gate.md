# ADR-001: Quality gate přehrává uložené výsledky, nevolá model

**Stav:** přijato · **Datum:** 9. 10. 2026

## Kontext

Chci, aby každý pull request odhalil regresi kvality hledání. Dvě věci tomu brání:

1. Volání modelu stojí peníze (klíč živého dema má strop 0,75 $, z toho zbývá ~0,09 $) a výsledek není při opakování přesně stejný.
2. CI, které selhává náhodně, se přestane brát vážně a lidé ho ignorují.

## Rozhodnutí

Quality gate (`tools/experiments.py --check`) **přehrává** hledání z uložených embeddingů a uložených odpovědí modelu (`data/emb_cache.npz`, `data/llm_cache.json`) a porovnává pořadí správných úseků po otázkách s `results/baseline.json`. Nikdy nevolá API (`RAG_OFFLINE=1`, chybějící cache = chyba, ne volání).

Gate **hlídá kód hledání**: BM25, RRF, pravidla odstavců, řazení výběru. Je deterministický, trvá desítky sekund a nestojí nic. Tolerance je nulová: jakýkoli pokles pořadí správného úseku je změna kódu, ne šum.

**Změna, která změní kandidáty** (např. jiné RRF), změní i vstup výběru LLM. Uložená odpověď se pak nehodí. Gate v tom případě **selže s jasnou zprávou** („nelze přehrát: ověřit jen živým měřením“) místo aby hádal. Taková změna se musí změřit živě (`tools/evaluate.py`) a baseline se přegeneruje vědomě (`--save-baseline`).

## Důsledky

- (+) Opakovatelné, zdarma, rychlé, bez falešných poplachů.
- (+) Při regresi gate vypíše konkrétní otázky a pořadí před a po.
- (−) **Nehlídá chování modelu.** Horší prompt nebo jiný model gate nezachytí. Na to je živé měření, ruční a placené.
- (−) Změna kandidátů vyžaduje živé měření, takže u ní CI nemůže rozhodnout sám.
- (−) Baseline zamrzne i chyby: pořadí „správně“ znamená „stejně jako dřív“, ne „správně v absolutním smyslu“.

## Zvažované alternativy

| Alternativa | Proč ne |
|---|---|
| Živé měření v CI při každém PR | stojí peníze, nedeterministické, vyčerpalo by klíč |
| Živé měření s prahem „nesmí klesnout o 2 body“ | na 56 otázkách je 2 body méně než jedna otázka; práh by nebyl rozlišitelný od šumu |
| Mockovaný model (falešné odpovědi) | testuje mock, ne systém. Falešné modely se používají v testech *bezpečnosti* a *oprávnění*, kde jde o tok dat, ne o kvalitu |
