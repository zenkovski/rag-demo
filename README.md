# RAG asistent nad pracovním právem

Asistent odpovídá česky na otázky z pracovního práva. Prohledává **4 předpisy, 2 475 odstavců**:
- celý zákoník práce,
- zákon o zaměstnanosti (podpora v nezaměstnanosti),
- zákon o nemocenském pojištění,
- nařízení vlády o překážkách v práci (třeba volno na svatbu nebo pohřeb).

Odpovídá jen z textu předpisů a každou větu ocituje. Když v textu odpověď není, řekne „nevím“. Na webu jde položit vlastní otázku a v mapě předpisů sledovat, jak asistent hledá. Kvalitu měřím na otázkách se známou správnou odpovědí a ukazuji i chyby.

**Živá stránka:** https://lukas-rag.vercel.app
**Kód:** https://github.com/zenkovski/rag-demo

> **Není to právní porada.** Je to technická ukázka. Odpovědi můžou být chybné.

Postaveno s AI (Claude Code). Kód jsem nepsal ručně; četl jsem ho, kontroloval a testoval. Rozbor každé části je v [INTERVIEW.md](INTERVIEW.md).

## Výsledky

46 testovacích otázek ve 3 sadách. 40 má odpověď v předpisech, 6 záměrně ne (daně, nájem bytu…), tam je správně „nevím“. Každou odpověď jsem ručně zkontroloval proti textu zákona.

| Měřítko | v1 | v2 |
|---|---|---|
| **Odpověď správně** | 36 z 46 | **42 z 46** |
| z toho otázky s odpovědí v předpisech | 30 z 40 | 36 z 40 |
| z toho správně „nevím“ | 6 z 6 | 6 z 6 |
| Správný paragraf mezi 5 úseky, které dostane model | 33 z 40 | 39 z 40 |

| Sada | v1 | v2 |
|---|---|---|
| testovací (1–20), podle ní jsem v2 ladil | 16 z 20 | 19 z 20 |
| kontrolní (21–30), napsaná po návrhu v2 | 7 z 10 | 10 z 10 |
| **nové předpisy (31–46)**, napsaná po přidání zákonů, bez ladění | **13 z 16** | **13 z 16** |

Podrobně otázku po otázce: [RESULTS.md](RESULTS.md).

**Jak číst tato čísla (poctivě):**
- Na sadě, podle které jsem ladil, je v2 nadsazená.
- **Na nových otázkách k novým zákonům jsou v1 i v2 stejné (13 z 16).** v2 tam lépe hledá, ale chyby dělá jinde: plete si mzdu a plat.
- **10× větší zdroj hledání nezhoršil.** 24 otázek, které fungovaly nad 260 odstavci, najdou správný paragraf i nad 2 475 odstavci (24 z 24).
- **Přepis otázky není deterministický.** I s teplotou 0 vyjde nové volání stejně jen asi u 7 ze 46 otázek. Čísla platí pro jedno uložené spuštění (`data/llm_cache.json`).

## Kde se mýlí (v2)

1. **Mzda × plat.** Zákoník práce má zvlášť pravidla pro mzdu (soukromé firmy) a plat (stát). Model u noční práce napsal 20 % (plat) místo 10 % (mzda).
2. **Obrácený význam.** „Zaměstnavatel posudek nemusí vydat dřív“ → model napsal „nesmí“.
3. **Velký zákon, podobné odstavce.** Zákon o nemocenském pojištění má stovky podobných odstavců. U „Kolik dostanu na nemocenské?“ hledání nenašlo správný odstavec a model řekl „nevím“.
4. **Půl odpovědi.** U otcovské našel délku (2 týdny), ale ne výši (70 %).

## Co se změnilo ve v2 a proč

| Problém ve v1 | Úprava ve v2 |
|---|---|
| Lidé píšou „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. | **Přepis otázky** do jazyka zákona (LLM). |
| Hledání podle významu občas mine přesné slovo. | **BM25** (hledání podle slov) nad přepsanou otázkou, spojené metodou **RRF**. |
| Model si u DPČ přidal „300 hodin ročně“ (platí jen pro DPP). | **Přísnější pravidla** v promptu. |
| Model e5-base běží jen lokálně (1 GB), na webu ne. | **e5-large přes API** (OpenRouter), stejný model při měření i na webu. |
| v1 běžel na free `nemotron-3-super`. | v2 používá `deepseek-v4.1-flash` (levný). |

Hledání po krocích (správný paragraf mezi 5 úseky, 40 otázek): e5-base 33 → e5-large 37 → + BM25 nad laickou otázkou **32** (zhoršení: slova „výplata“ v zákoně nejsou) → + přepis otázky **39**.

## Jak to funguje

```
otázka ─► přepis do jazyka zákona (LLM) ─┬─► vektory e5-large (původní i přepsaná otázka) ─┐
                                          └─► BM25 nad přepsanou otázkou ────────────────────┴─► RRF ─► 5 úseků ─► LLM: „odpověz jen z nich, cituj“
```

| Část | Jak | Soubor |
|---|---|---|
| Data | 4 předpisy ze zakonyprolidi.cz, 2 475 odstavců. Závěrečná ustanovení a seznamy zrušených zákonů vynechané. | `tools/chunk.py` |
| Dělení textu | 1 úsek = 1 odstavec, ID typu `ZP § 51 odst. 2`, `ZNP § 26 odst. 1`, `NV 590 příloha bod 5` | `tools/chunk.py` |
| Embeddingy | v1: `multilingual-e5-base` lokálně; v2: `multilingual-e5-large` přes OpenRouter, uložené jako int8 (4× menší) | `tools/rag.py` |
| Hledání podle slov | BM25 bez knihovny, čeština bez diakritiky, kořen = prvních 5 písmen | `tools/rag.py` |
| Spojení | reciprocal rank fusion (RRF), top 5 | `tools/rag.py` |
| Odpověď a přepis | `deepseek/deepseek-v4.1-flash` přes OpenRouter, teplota 0 | `tools/rag.py` |
| **LangChain verze** | stejný postup v LCEL (langchain-core 1.x) | `tools/rag_langchain.py` |
| Měření | 46 otázek, AI soudce + ruční kontrola, v1 i v2 | `tools/evaluate.py` |
| Web | statická stránka + serverová funkce, D3 mapa s rozložením spočítaným předem v Pythonu | `site/`, `site/api/ask.js`, `tools/build_data.py` |

**Tři implementace, stejné hledání.** Ruční Python (`rag.py`), LangChain (`rag_langchain.py`) a JavaScript na webu (`site/api/ask.js`) najdou při stejném přepisu otázky stejných 5 úseků ve stejném pořadí u **46 z 46** otázek. Zaokrouhlené vektory (int8) se ve všech třech verzích převádějí zpět stejně a znovu normalizují. Bez toho se LangChain (kosinová podobnost) lišil u 11 otázek.

## Živé otázky na webu a ochrana proti zneužití

- Funkce `site/api/ask.js` běží na Vercelu. API klíč je jen v proměnné prostředí na Vercelu.
- Max **10 otázek na IP za den**, strop 400 otázek denně na instanci, délka 8–300 znaků.
- **Proof of work:** prohlížeč musí najít číslo, se kterým SHA-256 začíná čtyřmi nulami (~1–3 s). Hash jde použít jen jednou.
- Požadavek musí přijít ze stránky a nesmí vyplnit skryté pole (past na roboty).
- **Nejtvrdší pojistka:** klíč má v OpenRouteru limit 0,50 $.
- Slabina: počítadla jsou v paměti funkce, ne v databázi. Další krok: Upstash Redis.

## Mapa předpisů a „přemýšlení“

2 475 teček, každá je jeden odstavec. Barva = oblast (výpověď, dovolená, nemoc, nezaměstnanost…). Vazby = sousední odstavce a dva nejpodobnější odstavce podle embeddingů. Rozložení se počítá předem v Pythonu (silový algoritmus jako v D3), v prohlížeči by trvalo dlouho. Po otázce mapa ukáže skutečné mezivýsledky hledání: podle významu, podle slov, spojení RRF a citované odstavce. Funguje i s vypnutými animacemi.

## Jak měřím

- `data/testset.json` (1–20), `data/testset_holdout.json` (21–30), `data/testset_new.json` (31–46).
- Šest otázek, které měly v první verzi (jen 5 témat zákoníku práce) správnou odpověď „nevím“, má teď odpověď v předpisech (mateřská, home office, svatba…). Dostaly novou zlatou odpověď, původní je v poli `gold_5temat`.
- **Hledání:** správný paragraf mezi prvními třemi (hit@3) a mezi pěti (hit@5).
- **Odpověď:** AI soudce + ruční kontrola všech odpovědí. Platí ruční verdikt (`data/manual_review.json`, `data/demo_review.json`).
- Cena měření v2: 0,04 $. Celý projekt zatím asi 0,20 $.
- Měření první verze (5 témat, 260 odstavců) je v `data/archive_5temat/`.

## Zdroje dat

Ze zakonyprolidi.cz, staženo 6. 10. 2026:
- 262/2006 Sb., zákoník práce, znění 29. 8. 2026 (verze 63)
- 435/2004 Sb., zákon o zaměstnanosti, znění 1. 7. 2026 (verze 87)
- 187/2006 Sb., zákon o nemocenském pojištění, znění 1. 7. 2026 (verze 66)
- 590/2006 Sb., nařízení vlády o překážkách v práci, znění 1. 6. 2025 (verze 2)

Nařízení o minimální mzdě (567/2006) je od roku 2025 zrušené. Výši minimální mzdy teď vyhlašuje ministerstvo sdělením, proto ji asistent nezná. Text zákonů není chráněn autorským právem (§ 3 autorského zákona).

## Jak spustit

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
copy .env.example .env                                  # a doplň OPENROUTER_API_KEY

.venv/Scripts/python tools/chunk.py                      # stáhne a rozdělí předpisy
.venv/Scripts/python tools/rag.py "Nezaplatili mi výplatu, můžu odejít?"
.venv/Scripts/python tools/evaluate.py --retrieval       # měření hledání po krocích
.venv/Scripts/python tools/evaluate.py                   # měření v2 i v1 -> RESULTS.md
.venv/Scripts/python tools/rag_langchain.py --compare    # LangChain verze = stejné výsledky?
.venv/Scripts/python tools/build_data.py                 # data pro web (rozložení mapy ~3 min)
```

## Bezpečnost

- Klíč je jen v `.env` (v `.gitignore`) a v proměnné prostředí na Vercelu.
- Před commitem a nasazením jsem prošel repo i historii na `sk-`, `api_key`, `OPENROUTER`, `ANTHROPIC` a tokeny.

## Další kroky

- Rozlišit mzdu a plat: k úseku přidat, pro koho platí, a filtrovat podle toho.
- Reranker (cross-encoder) nad top 20 úseky.
- Úseky s odkazy („podle § 26“) doplnit o odkazovaný odstavec.
- Měření rozptylu (více běhů kvůli nedeterministickému přepisu).
- Počítadla limitů v Redis místo paměti funkce.
