# RAG asistent nad zákoníkem práce

Asistent odpovídá česky na otázky o zákoníku práce. Odpovídá jen z textu zákona a každou větu ocituje. Když v textu odpověď není, řekne „nevím“. Na webu jde položit vlastní otázku a v mapě zákona sledovat, jak asistent hledá. Kvalitu měřím na otázkách se známou správnou odpovědí a ukazuji i chyby.

**Živá stránka:** https://lukas-rag.vercel.app
**Kód:** https://github.com/zenkovski/rag-demo

> **Není to právní porada.** Je to technická ukázka. Odpovědi můžou být chybné.

Postaveno s AI (Claude Code). Kód jsem nepsal ručně; četl jsem ho, kontroloval a testoval. Rozbor každé části je v [INTERVIEW.md](INTERVIEW.md).

## Výsledky

| Měřítko | v1 | v2 |
|---|---|---|
| **Odpověď správně, 20 testovacích otázek** (ruční kontrola) | 18 z 20 | **20 z 20** |
| z toho otázky s odpovědí v zákoně | 14 z 16 | 16 z 16 |
| z toho správně „nevím“, když zákon odpověď nemá | 4 z 4 | 4 z 4 |
| Správný paragraf mezi 5 úseky, které dostane model | 15 z 16 | 16 z 16 |
| **Odpověď správně, 10 nových otázek** | 8 z 10 | **10 z 10** |

„20 z 20“ = 16 správných odpovědí + 4 správná „nevím“ u otázek, na které zákon neodpovídá. Podrobně: [RESULTS.md](RESULTS.md).

**Jak číst tato čísla (poctivě):**
- v2 jsem ladil podle chyb na 20 testovacích otázkách, takže tam je výsledek nadsazený.
- Proto jsem napsal 10 nových otázek. První verze v2 na nich měla 9 z 10. Pak jsem kvůli webu přešel na větší embeddingy (e5-large přes API) a vyšlo 10 z 10. Změna nebyla kvůli těm otázkám, ale nové otázky tím už nejsou úplně čisté. Další krok je třetí, nová sada.
- **Přepis otázky není deterministický.** I s teplotou 0 vyjde nové volání modelu stejně jen u 6 z 30 otázek. Čísla platí pro jedno uložené spuštění (`data/llm_cache.json`); při novém běhu se můžou mírně lišit.

## Co se změnilo ve v2 a proč

| Problém ve v1 | Úprava ve v2 |
|---|---|
| Lidé píšou „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. Správný § 56 byl až 28. | **Přepis otázky** do jazyka zákona (LLM). § 56 je teď 1. |
| Hledání podle významu občas mine přesné slovo. | **BM25** (hledání podle slov) nad přepsanou otázkou, spojené metodou **RRF**. |
| Model si u DPČ přidal „300 hodin ročně“ (platí jen pro DPP). | **Přísnější pravidla** v promptu: každé tvrzení z citovaného úseku, úseky o jiné situaci nepoužívat. |
| Model e5-base běží jen lokálně (1 GB), na webu ne. | **e5-large přes API** (OpenRouter), stejný model při měření i na webu. |
| v1 běžel na free `nemotron-3-super`. | v2 používá `deepseek-v4.1-flash` (levný). |

Měření hledání po krocích (správný paragraf mezi 5 úseky, 16 otázek): e5-base 15 → e5-large 15 → + BM25 nad laickou otázkou **14** (zhoršení: slova „výplata“ v zákoně nejsou) → + přepis otázky **16**.

## Kde se pořád mýlí

1. **„Může mi zaměstnavatel dát výpověď, když jsem nemocný?“** (ukázka): § 53 se nenašel, asistent řekl „nevím“. Bezpečné, ale neužitečné.
2. **Správný paragraf často není první.** Mezi první tři se dostane u 14 z 16 otázek. Další krok by byl reranker.
3. **Živé otázky** z webu neprošly měřením ani ruční kontrolou. Na webu jsou tak označené.

## Jak to funguje

```
otázka ─► přepis do jazyka zákona (LLM) ─┬─► vektory e5-large (původní i přepsaná otázka) ─┐
                                          └─► BM25 nad přepsanou otázkou ────────────────────┴─► RRF ─► 5 úseků ─► LLM: „odpověz jen z nich, cituj“
```

| Část | Jak | Soubor |
|---|---|---|
| Data | Zákoník práce, 5 témat (zkušební doba, výpověď a odstupné, DPP/DPČ, pracovní doba a přesčasy, dovolená), 84 paragrafů | `tools/chunk.py` |
| Dělení textu | 1 úsek = 1 odstavec paragrafu, ID typu `§ 51 odst. 2`, celkem 260 úseků | `tools/chunk.py` |
| Embeddingy | v1: `intfloat/multilingual-e5-base` lokálně (Hugging Face); v2: `multilingual-e5-large` přes OpenRouter | `tools/rag.py` |
| Hledání podle slov | BM25 bez knihovny, čeština bez diakritiky, kořen = prvních 5 písmen | `tools/rag.py` |
| Spojení | reciprocal rank fusion (RRF), top 5 | `tools/rag.py` |
| Odpověď a přepis | `deepseek/deepseek-v4.1-flash` přes OpenRouter, teplota 0 | `tools/rag.py` |
| **LangChain verze** | stejný postup v LCEL (langchain-core 1.x): retrievery, `RunnableParallel`, `ChatOpenAI` přes OpenRouter | `tools/rag_langchain.py` |
| Měření | 20 + 10 otázek, AI soudce + ruční kontrola, srovnání v1/v2 | `tools/evaluate.py` |
| Web | statická stránka + serverová funkce pro živé otázky, D3 mapa | `site/`, `site/api/ask.js`, `tools/build_data.py` |

**Tři implementace, stejné hledání.** Ruční Python (`rag.py`), LangChain (`rag_langchain.py`) a JavaScript na webu (`site/api/ask.js`) najdou při stejném přepisu otázky stejných 5 úseků ve stejném pořadí u **30 z 30** otázek. LangChain verzi jsem postavil na `langchain-core`, protože `langchain-community` (kde býval `BM25Retriever`) se ukončuje.

## Živé otázky na webu a ochrana proti zneužití

- Funkce `site/api/ask.js` běží na Vercelu. API klíč je jen v proměnné prostředí na Vercelu, ne v kódu ani na stránce.
- Max **10 otázek na IP za den**, strop 400 otázek denně na instanci, délka 8–300 znaků.
- **Proof of work:** prohlížeč musí před odesláním najít číslo, se kterým SHA-256 hash začíná čtyřmi nulami (~1–3 s). Pro člověka to nevadí, hromadné dotazy robotem to prodraží. Hash jde použít jen jednou.
- Požadavek musí přijít ze stránky (kontrola původu a hlavičky) a nesmí vyplnit skryté pole (past na roboty).
- **Nejtvrdší pojistka:** klíč má v OpenRouteru limit 0,50 $. Víc utratit nejde.
- Slabina: počítadla jsou v paměti funkce, ne v databázi. Při více instancích se dají obejít. Proti tomu je právě limit na klíči. Další krok: Upstash Redis nebo Vercel KV.

## Mapa zákona a „přemýšlení“

Po otázce mapa postupně ukáže skutečné mezivýsledky hledání: odstavce podobné významem (tyrkysové), odstavce se shodnými slovy (bílé), spojení RRF a nakonec citované odstavce. Kroky se přepínají i s vypnutými animacemi ve Windows. Při přiblížení se ukážou čísla paragrafů, při větším i jejich názvy.

## Jak měřím

- `data/testset.json`: 20 otázek, 16 s odpovědí v zákoně a 4 bez (minimální mzda, mateřská, home office, nemocenská). U nich je správně jen „nevím“.
- `data/testset_holdout.json`: 10 nových otázek, napsaných až po návrhu v2.
- **Hledání:** správný paragraf mezi prvními třemi (hit@3) a mezi pěti, které dostane model (hit@5).
- **Odpověď:** AI soudce porovná odpověď se zlatou odpovědí a s úseky. Pak všechny odpovědi kontroluji ručně proti textu zákona. Platí ruční verdikt (`data/manual_review*.json`). Ve v1 soudce jednu chybu přehlédl, proto kontroluji ručně.
- Cena: měření v2 asi 0,02 $, celý vývoj v2 0,13 $. Jedna živá otázka stojí zlomek centu.

## Zdroj dat

Zákon č. 262/2006 Sb., zákoník práce, aktuální znění 29. 8. 2026 až 31. 12. 2026 (verze 63), z https://www.zakonyprolidi.cz/cs/2006-262, staženo 6. 10. 2026. Text zákona není chráněn autorským právem (§ 3 autorského zákona).

## Jak spustit

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
copy .env.example .env                                  # a doplň OPENROUTER_API_KEY

.venv/Scripts/python tools/chunk.py                      # stáhne a rozdělí zákon
.venv/Scripts/python tools/rag.py "Nezaplatili mi výplatu, můžu odejít?"   # porovná způsoby hledání
.venv/Scripts/python tools/evaluate.py --retrieval       # měření hledání po krocích
.venv/Scripts/python tools/evaluate.py                   # měření v2 -> RESULTS.md
.venv/Scripts/python tools/evaluate.py --holdout         # 10 nových otázek, v1 i v2
.venv/Scripts/python tools/rag_langchain.py --compare    # LangChain verze = stejné výsledky?
.venv/Scripts/python tools/build_data.py                 # data pro web
```

## Bezpečnost

- Klíč je jen v `.env` (v `.gitignore`) a v proměnné prostředí na Vercelu.
- Před commitem a nasazením jsem prošel repo i historii na `sk-`, `api_key`, `OPENROUTER`, `ANTHROPIC` a tokeny.

## Další kroky

- Reranker (cross-encoder) nad top 20 úseky.
- Úseky s odkazy („podle odstavce 2“, „§ 54“) doplnit o odkazovaný odstavec.
- Třetí, čistá sada otázek a měření rozptylu (více běhů kvůli nedeterministickému přepisu).
- Počítadla limitů v Redis místo paměti funkce.
