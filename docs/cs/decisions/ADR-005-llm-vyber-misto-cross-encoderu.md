# ADR-005: LLM výběr místo cross-encoderu

**Stav:** přijato, k přehodnocení · **Datum:** 9. 10. 2026 (původní volba 6.–7. 10. 2026)

## Kontext

Spojení RRF dává 20 kandidátů. Model dostane jen 5. Kdo vybere ty správné? Tři možnosti na stejných 56 otázkách a stejných 20 kandidátech (uložené výsledky `tools/rerank_compare.py`):

| Způsob | Hit@5 (95 %) | MRR@5 (95 %) | Cena a čas |
|---|---|---|---|
| prvních 5 z RRF | 0,88 (0,79–0,95) | 0,70 | 0 |
| cross-encoder `bge-reranker-v2-m3`, lokálně | 0,93 (0,86–0,98) | 0,81 | 0 $, ~15 s na otázku (CPU) |
| **LLM výběr** (`deepseek-v4.1-flash`) | **1,00** | **0,96 (0,93–0,99)** | ~0,0001 $, ~1,5 s |

## Rozhodnutí

**LLM výběr.**

## Důvody a poctivé výhrady

- Nejvyšší MRR, správný odstavec skoro vždy na prvním místě. LLM vidí **všech 20 najednou** a pozná, že odpověď potřebuje dva odstavce (délka i výše dávky). Cross-encoder hodnotí dvojice otázka–úsek zvlášť.
- **Výhrada:** LLM proti cross-encoderu: lepší u 4 otázek, horší u 0, **p = 0,125**. „56 proti 52 z 56“ ukazuje směr, ale na 56 otázkách ho nelze považovat za prokázané.
- **Výhrada:** výběr přes LLM je jediná komponenta s průkazným přínosem proti RRF bez výběru (9 : 0, p = 0,004). Že je lepší než cross-encoder, průkazné není.
- LLM výběr může zahodit základní pravidlo a nechat jen výjimky: viz [incident](../incidents/2026-10-06-regrese-odpocinek.md). Opraveno pevným pravidlem.

## Důsledky

- Cena za každý dotaz, nedeterminismus, závislost na promptu. Cross-encoder je deterministický a zdarma.
- Přehodnotit, když: (a) nová sada v4 přinese rozdíl, nebo (b) výběr půjde dělat cross-encoderem na GPU v desítkách ms. Zvažovaný hybrid: cross-encoder jako první síto a LLM jen pro nejisté případy.
