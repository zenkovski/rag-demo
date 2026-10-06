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

66 testovacích otázek v 5 sadách. 56 má odpověď v předpisech, 10 záměrně ne (daně, nájem bytu, důchod…), tam je správně „nevím“. Každou odpověď jsem ručně zkontroloval proti textu zákona.

| Měřítko | v1 | v2 | v3.1 |
|---|---|---|---|
| **Odpověď správně** | 54 z 66 | 60 z 66 | **66 z 66** |
| z toho otázky s odpovědí v předpisech | 44 z 56 | 50 z 56 | 56 z 56 |
| z toho správně „nevím“ | 10 z 10 | 10 z 10 | 10 z 10 |
| Správný paragraf mezi 5 úseky, které dostane model | 47 z 56 | 53 z 56 | 56 z 56 |
| „Nevím“, i když odpověď v předpisech byla | 5 | 3 | 0 |

| Sada | v1 | v2 | v3.1 |
|---|---|---|---|
| testovací (1–20), podle ní jsem v2 ladil | 16 z 20 | 19 z 20 | 20 z 20 |
| kontrolní (21–30), napsaná po návrhu v2 | 7 z 10 | 10 z 10 | 10 z 10 |
| nové předpisy (31–46), podle chyb v2 na nich jsem navrhl v3 | 13 z 16 | 13 z 16 | 16 z 16 |
| **po opravě (47–56)**, napsaná před prvním spuštěním v3 | **8 z 10** | **8 z 10** | **10 z 10** |
| **po v3.1 (57–66)**, napsaná před spuštěním v3.1 | 10 z 10 | 10 z 10 | 10 z 10 |

Podrobně otázku po otázce: [RESULTS.md](RESULTS.md).

**Jak číst tato čísla (poctivě):**
- **66 z 66 je nadsazené.** Každou verzi jsem ladil podle chyb, které jsem znal. Poctivé jsou jen sady napsané předem (47–66): v3.1 20 z 20, v2 18 z 20, v1 18 z 20.
- Sada 57–66 vyšla moc lehká: všechny verze 10 z 10, takže rozdíl neukazuje.
- **Ukázkové otázky mimo testy: 14 z 16.** Dvě chyby jsou vidět na webu: „výpověď, když jsem nemocný“ (hledání nenašlo § 53) a „normální pracovní doba“ (převrácená podmínka u mladistvých).
- **Živé otázky na webu nikdo nekontroluje.** Model se pořád může splést, proto má každá věta citaci.
- AI soudce přehlédl několik chybných „nevím“ a jednu správnou odpověď označil za chybu. Ruční kontrola je nutná.
- Přepis, výběr i odpověď dělá jazykový model, nové spuštění se může mírně lišit. Čísla platí pro jedno uložené spuštění (`data/llm_cache.json`).

## Kde se to pokazilo: hledání, nebo čtení

Každá chyba vznikne v jednom ze dvou kroků. Na webu je u chyby štítek a ten krok ve schématu zčervená.
- **Hledání:** mezi 5 úseky, které model dostal, nebyl odstavec s odpovědí. Model pak nemá z čeho odpovědět.
- **Čtení:** správný odstavec model měl, ale špatně ho použil.

| Chyba ve v2 | Krok | Oprava ve v3 | Výsledek |
|---|---|---|---|
| Nemocenská: kolik peněz | hledání (§ 29 ZNP byl až 11., § 192 odst. 2 chyběl) | LLM vybere 5 z 20 + dohledání odkazu „podle odstavce 2“ | opraveno |
| Otcovská: délka i výše | hledání (§ 38c byl až 10.) | LLM vybere 5 z 20 | opraveno |
| Noční práce 20 % místo 10 % | čtení (mzda × plat) | úsek nese poznámku „platí pro mzdu / plat“, model uvede obě varianty | opraveno |
| Posudek „nesmí“ místo „nemusí“ | čtení | pravidlo: „není povinen“ = nemusí, ne nesmí | opraveno, ale po další změně podkladů **znovu chyba** (jediná chyba v3) |

**Dvě pevná pravidla navíc (bez AI, zdarma):** k vybranému odstavci 2, 3… se vždy přidá odstavec 1 téhož paragrafu (oprava regrese u odpočinku mezi směnami) a dohledají se odstavce, na které úsek odkazuje („ve výši podle odstavce 2“).

**Co pravidlem opravit nejde: nestabilní čtení.** Levný model (DeepSeek v4.1 Flash) četl stejný odstavec jednou správně a jindy špatně. Stačilo, aby se změnil pátý, nejméně důležitý úsek v podkladech. A často zbytečně říkal „nevím“: u „Mám nárok na lékaře?“ měl správný bod nařízení před sebou.

**v3.1:** odpověď píše silnější **DeepSeek v4 Pro** (přepis a výběr dál dělá levný Flash) a zadání říká: než napíšeš „nevím“, projdi každý úsek a odpověz aspoň na část otázky. V pokusu na 5 problémových otázkách to spravila jen kombinace obou změn. Pasti („nájem bytu“, „daně“) dál dostanou „nevím“. Nevýhoda: silnější model dává citace méně často, ne za každou větu.

Navíc se v3 u nejasné otázky **doptá** („Myslel jste mzdu, nebo plat?“) a odpoví na každou možnost zvlášť.

**Vypnuté skryté přemýšlení modelu.** DeepSeek v4.1 Flash před odpovědí „přemýšlí“: u výběru úseků až 4 800 skrytých slov. Každý krok pak trval 30 s a stál desetkrát víc. Ve v3 je přemýšlení vypnuté (`reasoning: {enabled: false}`). Krok trvá 1,5 s a kvalita je podle měření lepší.

## Co se změnilo ve v2 a proč

| Problém ve v1 | Úprava ve v2 |
|---|---|
| Lidé píšou „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. | **Přepis otázky** do jazyka zákona (LLM). |
| Hledání podle významu občas mine přesné slovo. | **BM25** (hledání podle slov) nad přepsanou otázkou, spojené metodou **RRF**. |
| Model si u DPČ přidal „300 hodin ročně“ (platí jen pro DPP). | **Přísnější pravidla** v promptu. |
| Model e5-base běží jen lokálně (1 GB), na webu ne. | **e5-large přes API** (OpenRouter), stejný model při měření i na webu. |
| v1 běžel na free `nemotron-3-super`. | v2 používá `deepseek-v4.1-flash` (levný). |

Hledání po krocích (správný paragraf mezi 5 úseky, 56 otázek): e5-base 47 → e5-large 50 → + BM25 nad laickou otázkou **44** (zhoršení: slova „výplata“ v zákoně nejsou) → + přepis otázky 53 → + výběr přes LLM, odstavec 1 a odkazy **56** (z 56).

## Jak to funguje

```
otázka ─► přepis do jazyka zákona (LLM) ─┬─► vektory e5-large (původní i přepsaná otázka) ─┐
                                          └─► BM25 nad přepsanou otázkou ────────────────────┴─► RRF ─► 20 kandidátů
    ─► LLM vybere 5, které k otázce patří (+ odstavec 1 téhož §) ─► LLM: „odpověz jen z nich, cituj, rozliš mzdu a plat“
```

| Část | Jak | Soubor |
|---|---|---|
| Data | 4 předpisy ze zakonyprolidi.cz, 2 475 odstavců. Závěrečná ustanovení a seznamy zrušených zákonů vynechané. | `tools/chunk.py` |
| Dělení textu | 1 úsek = 1 odstavec, ID typu `ZP § 51 odst. 2`, `ZNP § 26 odst. 1`, `NV 590 příloha bod 5` | `tools/chunk.py` |
| Embeddingy | v1: `multilingual-e5-base` lokálně; v2: `multilingual-e5-large` přes OpenRouter, uložené jako int8 (4× menší) | `tools/rag.py` |
| Hledání podle slov | BM25 bez knihovny, čeština bez diakritiky, kořen = prvních 5 písmen | `tools/rag.py` |
| Spojení a výběr | reciprocal rank fusion (RRF) → 20 kandidátů → LLM vybere 5 (v3) | `tools/rag.py` |
| Odpověď | `deepseek/deepseek-v4-pro` (v3.1), přepis a výběr `deepseek-v4.1-flash`, teplota 0, skryté přemýšlení vypnuté | `tools/rag.py` |
| **LangChain verze** | stejný postup v LCEL (langchain-core 1.x) | `tools/rag_langchain.py` |
| Měření | 66 otázek, AI soudce + ruční kontrola, v1, v2 i v3.1 | `tools/evaluate.py` |
| Web | statická stránka + serverová funkce, D3 mapa s rozložením spočítaným předem v Pythonu | `site/`, `site/api/ask.js`, `tools/build_data.py` |

**Tři implementace, stejné hledání.** Ruční Python (`rag.py`), LangChain (`rag_langchain.py`) a JavaScript na webu (`site/api/ask.js`) najdou při stejném přepisu otázky stejných 20 kandidátů a při stejném výběru stejných 5 úseků ve stejném pořadí u **66 z 66** otázek. Zaokrouhlené vektory (int8) se ve všech třech verzích převádějí zpět stejně a znovu normalizují. Bez toho se LangChain (kosinová podobnost) lišil u 11 otázek.

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

- `data/testset.json` (1–20), `data/testset_holdout.json` (21–30), `data/testset_new.json` (31–46), `data/testset_fresh.json` (47–56, napsané před spuštěním v3), `data/testset_fresh2.json` (57–66, napsané před spuštěním v3.1).
- Šest otázek, které měly v první verzi (jen 5 témat zákoníku práce) správnou odpověď „nevím“, má teď odpověď v předpisech (mateřská, home office, svatba…). Dostaly novou zlatou odpověď, původní je v poli `gold_5temat`.
- **Hledání:** správný paragraf mezi prvními třemi (hit@3) a mezi pěti (hit@5).
- **Odpověď:** AI soudce + ruční kontrola všech odpovědí. Platí ruční verdikt (`data/manual_review.json`, `data/demo_review.json`).
- Cena: celý projekt asi 0,65 $ (limit klíče jsem zvedl z 0,50 na 0,75 $). Většinu spolklo skryté přemýšlení modelu, než jsem ho ve v3 vypnul. Měření v3.1 od nuly stojí asi 0,07 $.
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

- Levnější a stabilnější reranker (cross-encoder) místo LLM.
- Úseky s odkazy („podle § 26“) doplnit o odkazovaný odstavec.
- Měření rozptylu (více běhů kvůli nedeterministickému přepisu).
- Počítadla limitů v Redis místo paměti funkce.
