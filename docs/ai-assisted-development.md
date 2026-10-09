# Vývoj s AI: kdo co udělal a kde se AI spletla

Projekt vznikl s asistentem Claude Code. Projekt se netváří, že kód psal člověk. Důležitější je, **co se ověřilo, kým a kde se přitom našla chyba**.

## Kdo co dělal

| Část | Kdo | Jak ověřeno |
|---|---|---|
| Kód řetězce (`tools/rag.py` atd.), web, počáteční sady otázek a měření (6.–7. 10. 2026) | Claude Code (Opus 5.5), řídil Lukáš Procházka | druhá kontrola všech odpovědí proti textu zákona jiným modelem, **výsledky prošel majitel projektu** |
| Měřicí vrstva, bezpečnostní testy, CI, dokumenty, zmrazená sada v4 (9. 10. 2026) | Claude Code (Sonnet 5.5) | testy, mutační kontroly obran a CI na GitHubu (viz níže) |
| Rozhodnutí o tom, co se bude dělat a co ne | Lukáš Procházka | – |

**Co nebylo uděláno:** práce z 9. 10. 2026 (metriky, ablace, bezpečnostní testy, dokumenty, nová sada) **nebyla před zveřejněním řádek po řádku zkontrolována majitelem projektu**. Tvrzení „ověřeno“ v dokumentech znamená „ověřeno spuštěním testu nebo skriptu“, ne „přečteno a schváleno člověkem“. Nová sada v4 a její správné odpovědi vznikly stejným způsobem a **nemají nezávislou právní kontrolu**.

## Kde AI navrhla špatně a co to odhalilo

| Kdy | Co se stalo | Co to odhalilo | Co se změnilo |
|---|---|---|---|
| 6. 10. | Skryté „přemýšlení“ modelu spálilo většinu rozpočtu; nikdo to nečekal, výstup byl krátký | cena a čas v `usage` | [incident](incidents/2026-10-06-skryte-premysleni.md), před dávkou se měří jedno volání |
| 6. 10. | Výběr přes LLM zahodil základní pravidlo (v3.0) | porovnání **po otázkách**, ne průměr | [incident](incidents/2026-10-06-regrese-odpocinek.md), pevné pravidlo + test |
| 6. 10. | AI soudce přehlédl chybná „nevím“ a jednu správnou odpověď označil za chybu | ruční kontrola proti zákonu | druhý verdikt, deterministické kontroly ([ADR-006](decisions/ADR-006-deterministicke-kontroly.md)) |
| 7. 10. | README tvrdilo „20 z 20 na otázkách napsaných předem“ | audit rolí sad podle gitu (9. 10.) | [opraveno](evaluation-methodology.md#2-dev-validation-test-a-prevence-úniku): skutečně netknutých je 10 |
| 9. 10. | První verze kontroly čísel označila „15 dnů“ za nepodložené; zákon píše „patnáctidenní“ | test na skutečné odpovědi | převod číslovek slovy, test |
| 9. 10. | První verze klasifikace chyb brala „aspoň jeden správný úsek“ jako nalezeno; u otázky se dvěma správnými odstavci (otcovská) to schovalo chybějící odstavec | čtení vygenerované galerie, ne metrik | „nalezeno“ = všechny správné úseky, test |
| 9. 10. | Text v dokumentu tvrdil „samé odvozené hodnoty“, ještě než se po opravě kontroly znovu spočítalo, co zbylo; ve skutečnosti zbyla i **špatná citace** | přepočet po opravě | tabulka podezření se generuje z dat, ruční komentář je přesný |
| 9. 10. | První verze quality gate při změně kandidátů spadla na chybějící klíč místo srozumitelné zprávy; hrozilo, že by lokálně volala placené API | úvaha o selhání, test | offline režim `RAG_OFFLINE`, chybějící cache = chyba, `tests/conftest.py` zakazuje síť |
| 9. 10. | Testovací skript vytvořil v repu adresář `%SystemDrive%` (podproces bez proměnných prostředí) | `git status` | adresář smazán, skript opraven |
| 9. 10. | Při přidání dalšího prohlížeče se ukázala chyba v **testu**, ne v produktu (QA projekt: test ve WebKitu četl seznam dřív, než se vykreslil) | opakování 10× | [QA repo](https://github.com/zenkovski/qa-portfolio#reliability) |

## Co z toho plyne pro další práci

1. Dokument s čísly se **generuje z dat** (`tools/make_docs.py`), ne píše z hlavy. Ručně napsané věty se po změně dat musí znovu zkontrolovat.
2. Obrana se považuje za otestovanou, až když se **rozbila** a test selhal (mutační kontrola).
3. Kdo projekt prezentuje, musí umět vysvětlit: proč RRF a ne vážený součet, proč se výsledky na dev nepočítají jako důkaz, co je Recall@k × MRR, co dokazuje a nedokazuje offline gate, proč je oprávnění v hledání a ne v promptu. Pokud to autor neumí vysvětlit, příslušné tvrzení patří z prezentace pryč.
