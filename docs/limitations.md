# Limity a co není hotové

Co projekt **neumí**, co **neměří** a co se **záměrně nedělalo**, s důvodem. Odděleně: změřené (v [benchmark-results.md](benchmark-results.md)), odhady a plány.

## Co v zadání „AI Knowledge Platform“ chybí a proč

| Oblast | Stav | Důvod |
|---|---|---|
| Ingest více typů dokumentů, deduplikace, verze dokumentů | **není** | zdroj je čistý text 4 zákonů s jasnou strukturou (snadný případ). PDF, tabulky a OCR by potřebovaly jiné dělení; závěry z tohoto projektu se na ně **nepřenášejí** |
| Reranking: cross-encoder × LLM | hotovo | rozdíl je neprůkazný (p = 0,125), viz [ADR-005](decisions/ADR-005-llm-vyber-misto-cross-encoderu.md) |
| Strategie dělení textu, velikosti úseků | **neděláno** | vyžaduje přepočet embeddingů přes placené API; dělení po odstavcích je zdůvodněné strukturou zákona, ne změřené proti alternativám |
| Další embedding modely, kvantizace | jen e5-base × e5-large | další modely = nová cache = peníze |
| **Distribuované tracing, p50/p95/p99 celé služby, propustnost** | **není změřeno** | vyžaduje živá volání proti placenému API a proti limitu 0,75 $ na klíči. Změřený je jen čas výpočtu hledání (p50 ≈ 7 ms, bez sítě). Zátěžový test by byl bez skutečných čísel jen text |
| Cache odpovědí | **není** | přínos by se musel měřit; bez cache není cesta úniku dat přes cache ([ADR-003](decisions/ADR-003-opravneni-v-hledani.md)) |
| Retry s backoffem, timeouty | částečně | `rag.llm` opakuje při 429 a 5xx a čeká; web funkce zkouší 3×. **Limit souběhu** a samostatné timeouty po krocích nejsou |
| Verzování promptů/modelů/indexu | otisky v záznamu o běhu | **přepínač verzí za běhu a automatický rollback nejsou**; návrat = git |
| Docker | **není** | spuštění je `pip install` + jeden příkaz; Docker by nepřidal nic, co by se dalo ověřit |
| Autorizace, izolace tenantů | vzor v hledání | web nemá uživatele; vzor `allow` je otestovaný, ale není zapojený do webu ([ADR-003](decisions/ADR-003-opravneni-v-hledani.md)) |
| **AI agent** | **záměrně není** | nemá úkol, u kterého by byl smysluplnější než jednoduchý řetězec. Kdo ho chce: nejdřív by musel porazit tento řetězec na stejné sadě otázek. Pro výpočty (výše odstupného z průměrného výdělku) by dávala smysl **kalkulačka jako nástroj**, to je kandidát, ne hotová věc |
| ML experiment mimo volání LLM API | **jen cross-encoder a e5-base lokálně** | trénování modelu (fine-tuning) se nedělalo: bez dostatku dat a bez hypotézy, kterou by měl ověřit, by to bylo jen „umíme fine-tuning“ |

## Co je změřené, ale slabé

- **Sady jsou malé.** 56 otázek s odpovědí, z toho 8 validation a 8 test. Rozdíly o 1–3 otázky nelze rozlišit od náhody, většina ablací dopadla právě takhle.
- **Dev číslo je nadsazené.** „66 z 66“ vzniklo ladění podle většiny otázek.
- **Jedna zmrazená sada v4 (24 otázek)** je napsaná, **ne spuštěná**. Do té doby neexistuje měření na otázkách, které systém nikdy neviděl, kromě 10 otázek 57–66.
- **Otázky a správné odpovědi vznikaly s AI asistentem**, ne nezávislým týmem. Kontrolovaly se proti textu zákona jedním dalším modelem a prošel je majitel projektu. Nezávislá právní kontrola neproběhla.
- **Odpovědi jsou z jednoho uloženého běhu.** Chování modelu mezi běhy kolísá (viz [HISTORY.md](../HISTORY.md): „levný model četl stejný odstavec jednou správně, jindy špatně“). Opakované běhy s rozptylem se nedělaly.
- **Kontrola čísel a citací není v živém řetězci**, jen v měření. Živá odpověď s citací mimo rozsah by se zobrazila; zachytí ji až měření.
- **Bez Content-Security-Policy a Subresource Integrity** na webu ([threat-model.md](../security/threat-model.md), T8 a T12).

## Známé chyby (neopravené)

Dvě ze 16 ukázkových otázek na webu jsou špatně. Nejhorší je výpověď v nemoci: web tvrdí, že ji dát lze, zatímco zákon to v ochranné době zakazuje. Příčina je změřená (přepis otázky odvedl hledání jinam), oprava ne: [failure-gallery.md](failure-gallery.md#otevřené-chyby-zatím-neopravené), [ADR-004](decisions/ADR-004-prepis-a-bm25-otevrena-otazka.md).

## Co se opravilo, ale není nasazeno

`site/api/hit.js` (počítadlo kliků) přijímá už jen připravené otázky. Oprava je v repozitáři a otestovaná, **na živém webu zatím neběží**.

## Provozní stav, který se může změnit

Klíč OpenRouteru pro živé demo má pevný limit 0,75 $ a k 9. 10. 2026 zbývá asi 0,09 $. Až se vyčerpá, web ukáže „Rozpočet na živé otázky je vyčerpaný“, předpočítané otázky fungují dál.
