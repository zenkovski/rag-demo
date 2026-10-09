# Výsledky měření

Generuje `tools/experiments.py` + `tools/make_docs.py`. Běh z commitu `175c84b` (necommitované změny), 2026-10-09T20:10:17, offline replay z cache (0 $), trval 45.6 s, cena 0.00 $. Python 3.13.14, numpy 2.5.3, Windows AMD64.

**Co je změřené a co ne.** Hledání se tu přehrává z uložených embeddingů a uložených odpovědí LLM (přepis, výběr). Kód hledání je tedy ověřený a běh je opakovatelný, ale **žádné nové volání modelu se neprovedlo**. Odpovědi (sekce 4) jsou z dřívějších měření s ruční kontrolou. Co to neříká, je u každé sekce.

## 0. Data

66 otázek, z toho 56 s odpovědí v zákonech a 10 záměrně bez ní (správně je „nevím“). Role sad (dev / validation / test) a důkaz, kdy vznikly: [`data/splits.json`](../data/splits.json), pravidla v [evaluation-methodology.md](evaluation-methodology.md).

| Role | Otázek s odpovědí | Sady |
|---|---|---|
| dev | 40 | 1–46 (podle nich se ladilo) |
| validation | 8 | 47–56 |
| test | 8 | 57–66 |

Otisky dat: `chunks.json` 69dc954d11e7e746, `splits.json` ab3dc5d7ab7be314, `testset.json` 9c5101df30878390, `testset_holdout.json` 2fa82168ef1ad3c8, `testset_new.json` ab77c9c8cafbb6b7, `testset_fresh.json` b15f4dac0c42b161, `testset_fresh2.json` 28d11cd9e9e9d9ad, `testset_heldout_v4.json` ef5733a4f6fc453e

Konfigurace: embedding `intfloat/multilingual-e5-large` (v1 `intfloat/multilingual-e5-base`), přepis a výběr `deepseek/deepseek-v4.1-flash`, odpověď `deepseek/deepseek-v4-pro`, 20 kandidátů, 5 úseků pro model, RRF k = 60. Otisky promptů: rewrite `59d04c8035fa`, rerank `401e96680d68`, answer_v3 `e0cfc865f7c2`.

## 1. Hledání

Správný úsek mezi prvními k, na všech 56 otázkách s odpovědí. V závorce 95% interval spolehlivosti (bootstrap přes otázky, 10 000 losování). U otázek se dvěma správnými úseky Recall počítá podíl nalezených.

| Systém | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Recall@20 | MRR | nDCG@5 |
|---|---|---|---|---|---|---|---|
| e5-base, význam otázky (lokálně) | 0.43 | 0.71 | 0.80 (0.71–0.89) | 0.88 | 0.90 | 0.62 (0.52–0.72) | 0.64 |
| e5-large, význam otázky | 0.58 | 0.80 | 0.86 (0.77–0.94) | 0.92 | 0.97 | 0.74 (0.65–0.83) | 0.75 |
| BM25, laická otázka | 0.18 | 0.51 | 0.58 (0.46–0.70) | 0.60 | 0.70 | 0.38 (0.29–0.47) | 0.41 |
| BM25, přepsaná otázka | 0.43 | 0.68 | 0.76 (0.64–0.86) | 0.83 | 0.83 | 0.58 (0.48–0.68) | 0.60 |
| RRF: e5-large + BM25 (bez přepisu) | 0.45 | 0.66 | 0.75 (0.63–0.86) | 0.83 | 0.91 | 0.61 (0.51–0.71) | 0.63 |
| RRF: e5-large (otázka + přepis), bez BM25 | 0.59 | 0.81 | 0.88 (0.80–0.96) | 0.97 | 0.99 | 0.74 (0.65–0.83) | 0.76 |
| RRF: e5-large (otázka + přepis) + BM25 nad přepisem (v2) | 0.54 | 0.79 | 0.86 (0.77–0.94) | 0.92 | 0.96 | 0.71 (0.62–0.80) | 0.73 |
| vážený součet místo RRF | 0.60 | 0.83 | 0.88 (0.80–0.96) | 0.96 | 0.99 | 0.76 (0.68–0.85) | 0.77 |
| v3: v2 + LLM vybere 5 z 20 + pravidla odstavců (finální) | 0.85 | 0.98 | 0.99 (0.96–1.00) | – | – | 0.96 (0.93–0.99) | 0.96 |

Finální systém vrací jen 5 úseků (tolik dostane model), proto u něj chybí Recall@10 a @20.

### Po rolích sad (Recall@5 a MRR)

| Systém | dev (n=40) R@5 | MRR | validation (n=8) R@5 | MRR | test (n=8) R@5 | MRR |
|---|---|---|---|---|---|---|
| e5-base, význam otázky (lokálně) | 0.79 | 0.61 | 0.69 | 0.47 | 1.00 | 0.77 |
| e5-large, význam otázky | 0.89 | 0.76 | 0.56 | 0.58 | 1.00 | 0.79 |
| BM25, laická otázka | 0.60 | 0.42 | 0.44 | 0.28 | 0.62 | 0.29 |
| BM25, přepsaná otázka | 0.76 | 0.58 | 0.75 | 0.49 | 0.75 | 0.68 |
| RRF: e5-large + BM25 (bez přepisu) | 0.76 | 0.63 | 0.56 | 0.41 | 0.88 | 0.73 |
| RRF: e5-large (otázka + přepis), bez BM25 | 0.90 | 0.75 | 0.69 | 0.72 | 1.00 | 0.74 |
| RRF: e5-large (otázka + přepis) + BM25 nad přepisem (v2) | 0.86 | 0.71 | 0.81 | 0.64 | 0.88 | 0.82 |
| vážený součet místo RRF | 0.90 | 0.78 | 0.81 | 0.72 | 0.88 | 0.72 |
| v3: v2 + LLM vybere 5 z 20 + pravidla odstavců (finální) | 0.98 | 0.95 | 1.00 | 1.00 | 1.00 | 1.00 |

**Pozor na velikost.** Test má 8 a validation 8 otázek. Rozdíl o jednu otázku je 12 procentních bodů, intervaly spolehlivosti jsou široké a u 8 z 8 je dolní mez ~0,68 (Wilson). Dev číslo je nadsazené: podle něj se ladilo. Role „test“ tu slouží jako kontrola, ne jako důkaz.

## 2. Co která část přináší (ablace)

Párové porovnání na stejných otázkách. „A lepší / B lepší“ = u kolika otázek měl A, resp. B vyšší Recall@5. p je přesný oboustranný znaménkový test: p pod 0,05 říká, že rozdíl pravděpodobně není náhoda. Nad tím je to jen pozorování.

| Porovnání | A lepší | B lepší | shoda | p |
|---|---|---|---|---|
| RRF v2 × jen e5-large | 4 | 5 | 47 | 1.000 |
| RRF v2 × RRF bez přepisu | 8 | 3 | 45 | 0.227 |
| RRF v2 × RRF bez BM25 | 3 | 5 | 48 | 0.727 |
| RRF v2 × vážený součet | 2 | 4 | 50 | 0.688 |
| v3 (výběr LLM) × RRF v2 | 9 | 0 | 47 | 0.004 |
| jen e5-large × e5-base | 5 | 2 | 49 | 0.453 |

Co z toho plyne (čísla jsou z tabulek výše):

- **Výběr přes LLM je jediná komponenta s jasným přínosem.** Recall@1 0.54 → 0.85, MRR 0.71 → 0.96, lepší u 9 otázek, horší u 0.
- **BM25 se v těchto otázkách nevyplatilo.** RRF bez BM25 má Recall@5 0.88 a Recall@20 0.99, RRF s BM25 0.86 a 0.96. Rozdíl není statisticky průkazný, ale směr je opačný, než se čekalo. Sada neobsahuje otázky na přesná čísla paragrafů a identifikátory, tedy přesně to, v čem má být BM25 silné. Rozhodnutí se proto odkládá na novou sadu (viz [limitations.md](limitations.md)).
- **Přepis otázky bez BM25 nevadí.** Samotný e5-large: Recall@5 0.86; s přepisem: 0.88. Rozdíl zhruba o dvě otázky, nepůjde rozlišit od náhody.
- **e5-large proti e5-base:** Recall@5 0.86 proti 0.80.
- **Laická otázka do BM25 škodí:** 0.58 proti 0.76 po přepisu. Tady přepis zjevně pomáhá (zákon říká „mzda“, ne „výplata“).

### RRF: parametr k

| k | Recall@5 | MRR |
|---|---|---|
| 10 | 0.89 (0.81–0.96) | 0.72 (0.63–0.81) |
| 30 | 0.89 (0.81–0.96) | 0.71 (0.62–0.80) |
| 60 (použito) | 0.86 (0.77–0.94) | 0.71 (0.62–0.80) |
| 100 | 0.85 (0.75–0.94) | 0.71 (0.62–0.80) |

Hodnota k se na výsledku skoro nepozná: intervaly se překrývají. Proto zůstává výchozí 60.

### RRF proti váženému součtu skóre

Váha BM25 se vybírala jen na dev otázkách (podle MRR): **0.05**. Na všech otázkách má vážený součet Recall@5 0.88 a MRR 0.76, RRF 0.86 a 0.71. Rozdíl je neprůkazný (p = 0.69). RRF zůstává, protože nepotřebuje ladit váhu a normalizaci skóre. Optimální váha BM25 vyšla velmi nízká, což je stejný signál jako výše: slova hledání moc nepomáhají.

## 3. Výběr 5 z 20: žádný, cross-encoder, LLM

Stejných 56 otázek, stejných 20 kandidátů z RRF. Uložené výsledky z `tools/rerank_compare.py` (cross-encoder běžel lokálně na CPU, 15.23 s na otázku). Hit@5 = je mezi pěti vybranými aspoň jeden správný úsek.

| Způsob | Hit@5 | MRR@5 |
|---|---|---|
| bez výběru (prvních 5 z RRF) | 0.88 (0.79–0.95) | 0.70 (0.60–0.80) |
| cross-encoder bge-reranker-v2-m3 | 0.93 (0.86–0.98) | 0.81 (0.72–0.89) |
| LLM výběr (deepseek-v4.1-flash) | 1.00 (1.00–1.00) | 0.96 (0.93–0.99) |

LLM proti cross-encoderu: lepší u 4 otázek, horší u 0, p = 0.125. Číslo 56 proti 52 z README tedy ukazuje směr, ale na 56 otázkách ho nejde považovat za prokázané. LLM navíc vidí všech 20 kandidátů najednou a platí se za každý dotaz. Cross-encoder je zdarma, deterministický, ale na CPU pomalý.

## 4. Odpovědi

Zdroj: uložené běhy v1, v2, v3 (v3 = finální) a ruční kontrola proti textu zákona (druhý verdikt modelu Claude Opus 5.5, který prošel majitel projektu). Správnost je úsudek, nelze ji spočítat pravidlem. Proto je vedle AI soudce a ruční kontroly přidaná deterministická kontrola (sloupce vpravo), která soudce nepotřebuje.

| Verze | Sada | Správně (95% interval) | Zbytečné „nevím“ | Správné „nevím“ | Odpověděl bez zdroje | Čísla mimo citované úseky |
|---|---|---|---|---|---|---|
| v1 | všechny | 54 z 66 (0.71–0.89) | 5 z 56 | 10 z 10 | 0 z 10 | 5 |
| v1 | dev | 36 z 46 (0.64–0.88) | 4 z 40 | 6 z 6 | 0 z 6 | 3 |
| v1 | validation | 8 z 10 (0.49–0.94) | 1 z 8 | 2 z 2 | 0 z 2 | 0 |
| v1 | test | 10 z 10 (0.72–1.00) | 0 z 8 | 2 z 2 | 0 z 2 | 2 |
| v2 | všechny | 60 z 66 (0.82–0.96) | 3 z 56 | 10 z 10 | 0 z 10 | 3 |
| v2 | dev | 42 z 46 (0.80–0.97) | 1 z 40 | 6 z 6 | 0 z 6 | 3 |
| v2 | validation | 8 z 10 (0.49–0.94) | 2 z 8 | 2 z 2 | 0 z 2 | 0 |
| v2 | test | 10 z 10 (0.72–1.00) | 0 z 8 | 2 z 2 | 0 z 2 | 0 |
| v3 | všechny | 66 z 66 (0.94–1.00) | 0 z 56 | 10 z 10 | 0 z 10 | 3 |
| v3 | dev | 46 z 46 (0.92–1.00) | 0 z 40 | 6 z 6 | 0 z 6 | 3 |
| v3 | validation | 10 z 10 (0.72–1.00) | 0 z 8 | 2 z 2 | 0 z 2 | 0 |
| v3 | test | 10 z 10 (0.72–1.00) | 0 z 8 | 2 z 2 | 0 z 2 | 0 |

**Změny po otázkách.** v1 → v2: opraveno 8, zhoršeno 2 (otázky 40, 49). v2 → v3: opraveno 6, zhoršeno 0.

**Co z toho nevyplývá.** 66 z 66 u v3 je nadsazené: ladilo se podle 56 z těchto otázek. Poctivá kontrola je řádek „test“ (10 otázek, dolní mez intervalu ~0,72) a ten sám o sobě nedokazuje, že systém na nových otázkách dopadne stejně. Proto je připravená nová sada, která se pustí jednou (viz [evaluation-methodology.md](evaluation-methodology.md)).

**Kontrola čísel.** Sloupec „čísla mimo citované úseky“ je podezření, ne chyba: číslo v odpovědi, které není v textu žádného citovaného úseku. Kontrola rozlišuje dva případy: číslo, které je v jiném dodaném úseku než citovaném (špatná citace), a číslo, které není v žádném (odvozená hodnota, např. součet nebo polovina, nebo vymyšlené). Čísla zapsaná v zákoně slovy („patnáctidenní“) se převádějí na číslice.

Podezření u v3 (3 odpovědí):

| Otázka | Číslo v jiném dodaném úseku (špatná citace) | Číslo v žádném úseku (odvozené?) | Citované úseky |
|---|---|---|---|
| 7: Kolik hodin týdně můžu pracovat na dohodu o pracovní činnosti? | 20 | – | [1, 3, 4] |
| 20: Kolik peněz dostanu, když budu na nemocenské? | – | 15 | [1, 2, 3, 4] |
| 21: Kolik hodin volna v kuse musím mít aspoň jednou za týden? | 11 | 35 | [1, 2, 3, 5] |

Ruční projití těchto odpovědí: součet (24 + 11 = 35 hodin), polovina (20 hodin z 40) a „od 15. dne“ po 14 dnech jsou správné odvozené hodnoty, které odpověď sama vysvětluje, ale nejdou doložit citací. **Jedna skutečná chyba v citaci:** u otázky 21 je „11 hodin“ v úseku [4], odpověď ho cituje jako [1]. Odpověď je věcně správně, jen odkaz míří jinam. Tohle by AI soudce, který porovnává smysl, snadno přehlédl.

## 5. Provoz

| Verze | Cena na otázku při měření |
|---|---|
| v1 | 0.00071 $ |
| v2 | 0.00157 $ |
| v3 | 0.00112 $ |

Cena zahrnuje volání odpovědi i AI soudce při měření; ceny z odpovědí OpenRouteru uložených v cache. Celý projekt vyšel asi na 0,66 $ včetně chyb (viz [incident skrytého přemýšlení](incidents/2026-10-06-skryte-premysleni.md)).

Čas samotného výpočtu hledání (matice × vektor, BM25, RRF) z cache: **p50 7.33 ms, p95 14.08 ms**, max 16.58 ms (100 volání, tento počítač). Jen výpočet hledání z cache (matice × vektor, BM25, RRF). Volání LLM a embedding API tu nejsou: p50/p95 celé služby se offline změřit nedá.

p50/p95/p99 celé služby, propustnost a chybovost pod zátěží **nejsou změřené**. Zátěžový test by běžel proti placenému API a proti limitu 0,75 $ na klíči, takže se nedělal (viz [limitations.md](limitations.md)).

## 6. Regrese proti referenčnímu stavu

Žádné. Pořadí správných úseků u finálního systému je stejné nebo lepší než v `results/baseline.json`.
