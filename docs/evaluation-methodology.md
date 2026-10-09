# Metodika měření

Jak se měří, co čísla znamenají a co z nich **nelze** vyvodit. Výsledky jsou v [benchmark-results.md](benchmark-results.md) (generované), chyby v [failure-gallery.md](failure-gallery.md).

## 1. Datová sada

**Schéma** (`data/testset*.json`, jeden záznam = jedna otázka):

| Pole | Význam |
|---|---|
| `id` | číslo otázky, v rámci projektu unikátní (1–66, nová sada 101–124) |
| `q` | otázka tak, jak by ji napsal laik |
| `gold` | věcně správná odpověď (ručně napsaná podle textu zákona) |
| `chunks` | ID správných odstavců (`ZP § 56 odst. 1`). **Prázdný seznam = v předpisech odpověď není a správně je „nevím“.** Při dvou správných odstavcích se Recall počítá jako podíl nalezených |
| `level`, `type` | obtížnost, u nové sady typ případu (přesný odkaz, více odstavců, nejednoznačná, zastaralá, injekce…) |
| `canary` | (jen útoky) řetězec, který se v odpovědi nesmí objevit |

**Původ dat.** Otázky a správné odpovědi vznikaly s AI asistentem (Claude Code) podle textu zákona, majitel projektu je prošel. U nové sady v4 se správné odstavce hledaly prostým prohledáním dat a čtením textu, **ne podle výstupu systému**; jejich správnost nemá nezávislou právní kontrolu. Správné odstavce se kontrolují testem (`test_gold_chunks_exist`: každý musí v datech být).

**Co v sadách je a není.** 66 otázek: 56 s odpovědí, 10 záměrně bez ní. Všechny jsou formulované jako otázky laika. **Chybí** přesné odkazy na paragrafy, otázky přes více odstavců a nejednoznačné otázky, tedy typy, kde se mají projevit rozdíly mezi BM25 a embeddingy. Proto je napsaná nová sada (viz 4).

## 2. Dev, validation, test a prevence úniku

**Problém.** Podle chyb na otázkách se systém opakovaně upravoval (v2, v3, v3.1). Číslo naměřené na otázkách, podle kterých se ladilo, je **nadsazené**: systém se mohl přizpůsobit právě jim. Tomu se říká únik (data leakage) a vyhnout se mu jde jen tak, že se sada, na které se číslo uvádí, předem zamkne.

**Pravidla** (`data/splits.json`, platí vůči *finální* verzi v3.1):

| Role | Definice | Sady | Otázek s odpovědí |
|---|---|---|---|
| **dev** | podle chyb na ní se kód, prompt nebo model měnil | 1–46 | 40 |
| **validation** | napsaná před spuštěním verze, ale její výsledky ovlivnily další změnu | 47–56 | 8 |
| **test** | napsaná před spuštěním finální verze, od té doby se podle ní nic neměnilo | 57–66 | 8 |
| **test v4** *(plánovaná)* | napsaná, zmrazená, **zatím nespuštěná**; pustí se jednou | 101–124 | 17 |

1. Role se přidělují při psaní sady a **nikdy zpětně**: sada, podle které se cokoli opravilo, už není test.
2. Důkaz, kdy sada vznikla: commit v gitu (sloupec `commit` v `splits.json`). Tím se dá ověřit pořadí „sada → verze“.
3. Vážený součet v ablaci se ladí **jen na dev** (`select_weight`), výsledek se hlásí na všech rolích zvlášť.
4. Jednorázovost sady v4 vynucuje `tools/run_heldout.py`: před prvním voláním zapíše zámek s otisky kódu a promptů; druhý běh odmítne.

**Poctivá oprava dřívějšího tvrzení.** README uvádělo „20 z 20 na otázkách napsaných před spuštěním verze“. Přesně vzato: otázky 47–56 byly napsané před spuštěním v3, ale jejich chyby ovlivnily v3.1 (silnější model, pravidlo před „nevím“). **Skutečně netknutých je 10 otázek (57–66)**, a 10 z 10 má dolní mez 95% intervalu spolehlivosti kolem 0,72. Číslo „66 z 66“ je nadsazené a tak je i označené.

## 3. Metriky

Podrobně v `tools/metrics.py` (každá funkce má test na ručně spočítaném příkladu).

| Metrika | Co měří | Co z ní NEvyplývá |
|---|---|---|
| **Recall@k** | jaký podíl správných odstavců je mezi prvními k | nic o pořadí uvnitř k; že odstavec stačí k odpovědi |
| **hit@k** | je mezi prvními k aspoň jeden správný odstavec | u otázky se dvěma správnými odstavci skryje, že jeden chybí (starší ukazatel v RESULTS.md) |
| **MRR** | průměr 1 / pořadí prvního správného odstavce | silně odměňuje 1. místo; o druhém správném odstavci neví |
| **nDCG@k** | pořadí s důrazem na horní místa, správné odstavce stejně důležité | nerozlišuje „stačí“ a „potřebné“ |
| **Správnost odpovědi** | věcná shoda se `gold`, ruční kontrola proti textu zákona | je to úsudek; AI soudce se mýlí (viz galerii), proto platí druhý verdikt a moje kontrola |
| **Správné „nevím“ / zbytečné „nevím“ / odpověď bez zdroje** | odmítnutí tam, kde zdroj mlčí / odmítnutí, i když zdroj byl / odpověď na otázku, kterou zákon neřeší | „nevím“ samo není úspěch: systém, který vždy odmítne, má 100 % správných odmítnutí |
| **Kontrola citací a čísel** (`answer_checks.py`) | citace míří na dodaný úsek, číslo v odpovědi je v citovaném úseku | netvrdí, že věta z úseku vyplývá; hlásí **podezření**, ne chybu (odvozené součty jsou správně, ale nedoložené) |
| **Kontext** (pokrytí, relevance, duplicity) | – | **neměří se.** Pokrytí by šlo spočítat z `chunks`, duplicity ne. Neimplementováno. |
| **Latence, cena** | cena z uložených odpovědí OpenRouteru; čas výpočtu hledání z cache | **p50/p95 celé služby nejsou změřené**, protože by to vyžadovalo živá volání; viz [limitations.md](limitations.md) |

**Proč ne samotný LLM-as-a-judge.** Soudce (DeepSeek) přehlédl několik chybných „nevím“ a občas označil správnou odpověď za chybu. Proto se každá odpověď ještě jednou porovná s textem zákona (Claude Opus 5.5), tento verdikt prošel majitel projektu, a vedle toho jsou deterministické kontroly, které žádný model nepotřebují. Soudce tedy **není zdroj pravdy**, je to první filtr.

## 4. Statistika a nejistota

- **Interval spolehlivosti (95 %).** Bootstrap přes otázky (10 000 losování, pevný seed). Ukazuje, jak by se číslo změnilo s jinou sadou podobných otázek. **Neukazuje** náhodnost modelu.
- **Wilson** pro podíly (správných odpovědí): funguje i u 10 z 10 (≈ 0,72–1,00).
- **Párový znaménkový test** pro porovnání dvou systémů na stejných otázkách: počítají se jen otázky, kde se liší. Rozdíl 5 : 0 dává p = 0,0625, tedy ještě **ne** významné. Rozdíl 9 : 0 (výběr LLM proti RRF) dává p = 0,004.
- **Co se neříká.** U rozdílu o 1–3 otázky z 56 se netvrdí „lepší“, jen „neprůkazný rozdíl“. Takhle dopadly BM25, přepis, vážený součet i srovnání e5-base a e5-large.
- **Opakované běhy stochastických částí.** LLM volání mají teplotu 0, ale ani tak není nové volání vždy stejné. Čísla odpovědí platí pro **jeden uložený běh**. Opakované běhy s rozptylem se **nedělaly** (stály by peníze). Slabina je zapsaná v [limitations.md](limitations.md).

## 5. Experimenty (ablace)

Spouští se jedním příkazem (`python tools/experiments.py`), běží offline z uložených výsledků a **nestojí nic**. Každý běh uloží konfiguraci, otisky dat a promptů, verze modelů, metriky, runtime, cenu a seznam regresí.

| Otázka z ablace | Jak se zkoumá | Stav |
|---|---|---|
| dense × BM25 × hybrid | 9 systémů, Recall@k, MRR, nDCG, CI | hotovo |
| RRF × vážený součet | váha ladí jen dev; párový test | hotovo |
| parametr k v RRF | k = 10, 30, 60, 100 | hotovo |
| přepis otázky zapnutý/vypnutý | `rrf_dense_bm25` × `rrf_v2` | hotovo |
| bez výběru × cross-encoder × LLM | z uložených výsledků | hotovo |
| e5-base × e5-large | lokálně přes `sentence-transformers` | hotovo (jen lokálně, CI přeskakuje) |
| **velikost a strategie dělení** | – | **neděláno**: vyžaduje znovu spočítat embeddingy (placené API) |
| **jiné embedding modely, kvantizace** | – | **neděláno**, stejný důvod; int8 kvantizace je ověřená jinde (DESIGN.md §3) |

## 6. Co se pouští živě a kdy

| Měření | Příkaz | Cena | Kdy |
|---|---|---|---|
| celá sada v1–v3 s odpověďmi a soudcem | `tools/evaluate.py` | ~0,07 $ | po změně promptu nebo modelu |
| **nová zmrazená sada v4** | `tools/run_heldout.py --live` | ~0,03 $ | **jednou**, na zmrazeném kódu |
| bezpečnostní injekce | `tools/security_eval.py --live` | ~0,02 $ | po změně promptu nebo funkce; **zatím nespuštěno** |

Všechno ostatní běží zdarma a při každém pushi.

## 7. Co by změnilo závěry

- Dostatek otázek na **přesné odkazy** a **čísla paragrafů**: BM25 by tu mohl vyhrát a tabulka v sekci 2 benchmarku by se musela přepsat (ADR-004 je vedený jako otevřený).
- Víc než 56 otázek s odpovědí: intervaly se zúží, rozdíly o 1–3 otázky by se daly rozlišit.
- Jiný zdroj než zákon (PDF s tabulkami, verze dokumentů): závěry o dělení textu a hledání se nepřenesou (viz [DESIGN.md §11](../DESIGN.md#11-co-by-chybělo-do-provozu)).
