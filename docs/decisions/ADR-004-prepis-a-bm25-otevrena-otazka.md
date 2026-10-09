# ADR-004: Přepis otázky a BM25: přínos není prokázán

**Stav:** **otevřené** · **Datum:** 9. 10. 2026

## Kontext

v2 přidala (a) přepis laické otázky do jazyka zákona a (b) BM25 nad přepsanou otázkou, spojené RRF. Původní zdůvodnění: BM25 vyhraje u přesných termínů a čísel, přepis překládá „výplatu“ na „mzdu“.

## Co ukazují data

Offline ablace na 56 otázkách s odpovědí ([benchmark-results.md](../benchmark-results.md)):

| Systém | Recall@5 | Recall@20 |
|---|---|---|
| jen e5-large (význam) | 0,86 | 0,97 |
| RRF: e5-large nad otázkou i přepisem, **bez BM25** | **0,88** | **0,99** |
| RRF + BM25 nad přepisem (v2, současný stav) | 0,86 | 0,96 |

- **BM25 hledání nezlepšilo**, nepatrně zhoršilo. Párový test je neprůkazný (3 : 5, p = 0,73), ale **směr je opačný, než se čekalo**. Optimální váha BM25 ve váženém součtu vyšla 0,05.
- **Přepis pomáhá BM25** (laická otázka 0,58 → přepsaná 0,76), ale **embeddingy přepis nepotřebují** (jen e5-large 0,86, s přepisem 0,88; neprůkazné).

## Skutečná chyba, která s tím souvisí

Web na otázku „Může mi zaměstnavatel dát výpověď, když jsem nemocný?“ odpovídá zavádějícím způsobem ([galerie chyb](../failure-gallery.md#otevřené-chyby-zatím-neopravené)). Správný odstavec (ZP § 53 odst. 1, zákaz výpovědi v ochranné době) je v pořadí:

| Pořadí | Místo správného odstavce |
|---|---|
| význam, **původní** otázka | **12.** |
| význam, **přepsaná** otázka | 219. |
| BM25, přepsaná otázka | 106. |
| BM25, laická otázka | 10. |

Přepis („…rozvázat pracovní poměr výpovědí, nachází-li se zaměstnanec v dočasné pracovní neschopnosti?“) odvedl hledání k obecným odstavcům o skončení poměru. Po spojení RRF skončil správný odstavec na 45. místě, tedy mimo 20 kandidátů.

## Zkoumané varianty (offline, jen kandidáti: Recall@20)

| Spojení | Recall@20 (56 otázek) | pořadí § 53 v demu |
|---|---|---|
| současné (otázka, přepis, BM25 přepisu) | 0,964 | 45 |
| + BM25 laické otázky | 0,973 | 23 |
| otázka + přepis, bez BM25 | 0,991 | 31 |
| otázka + BM25 laické + přepis | 0,987 | **14** (uvnitř 20) |

## Rozhodnutí

**Zatím neměnit.** Varianty výše **nejdou poctivě posoudit na těchto datech**: vznikly podle chyby, kterou už znám, a posuzují se na týchž otázkách, podle kterých se už jednou ladilo. Na dev, validation i test sadě jsou rozdíly o 1–2 otázky.

## Co rozhodne

Zmrazená sada v4 ([testset_heldout_v4.json](../../data/testset_heldout_v4.json)) obsahuje **přesné odkazy na paragrafy a čísla**, přesně ten případ, kde má BM25 vyhrát, a **nejednoznačné a chybně napsané otázky**, kde má pomoci přepis. Postup:

1. Před spuštěním se zafixuje seznam variant výše (nic dalšího se nepřidá).
2. Varianty se pustí **živě jednou** na v4 (vyžaduje ~0,03 $ na variantu, nový klíč).
3. Změna se přijme jen když zlepší Recall@20 **bez zhoršení** Recall@5 a MRR a rozdíl vyjde průkazně, nebo když aspoň není horší a je jednodušší.

Do té doby zůstává otevřená chyba „výpověď v nemoci“ zapsaná jako známá.

## Důsledky

- Přiznáno, že část architektury (BM25) není podložená měřením. Důvod, proč tu je: původní předpoklad a úspěch u přesných termínů, který tato sada nemá jak ukázat.
