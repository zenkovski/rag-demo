# ADR-002: RRF místo váženého součtu skóre

**Stav:** přijato · **Datum:** 9. 10. 2026 (původní volba z 6. 10. 2026)

## Kontext

Hledání dává tři pořadí (význam původní otázky, význam přepsané, slova). Je potřeba je spojit. Dvě běžné cesty: **RRF** (reciprocal rank fusion, bere jen pořadí) a **vážený součet** normalizovaných skóre.

## Rozhodnutí

**RRF s k = 60.**

## Důkaz (z [benchmark-results.md](../benchmark-results.md))

Váha BM25 ve váženém součtu se ladila **jen na dev otázkách** (vyšla 0,05, tedy téměř vypnuté BM25).

| | Recall@5 | MRR |
|---|---|---|
| RRF | 0,86 | 0,71 |
| vážený součet | 0,88 | 0,76 |

Párový test: 2 otázky lepší RRF, 4 lepší vážený součet, **p = 0,69**. Rozdíl není rozlišitelný od náhody. Parametr k (10 až 100) výsledek také skoro nemění (intervaly se překrývají).

## Proč tedy RRF

- Nepotřebuje normalizaci skóre (embeddingy 0–1, BM25 0–∞) ani ladění vah, tedy nemá parametr, který by se dal přeladit na malou sadu.
- Při stejné kvalitě vyhrává jednodušší.

## Důsledky

- Kdyby nová sada (v4) ukázala, že vážený součet je lepší, rozhodnutí se změní. Na dnešních datech to nelze tvrdit.
- Optimální váha BM25 blízko nule je signál k ADR-004 (BM25 možná nepřispívá).
