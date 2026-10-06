# RAG asistent nad zákoníkem práce

Asistent odpovídá česky na otázky o zákoníku práce. Odpovídá jen z textu zákona a každou větu ocituje. Když v textu odpověď není, řekne „nevím“. Kvalitu měřím na 20 testovacích otázkách a výsledky ukazuji včetně chyb.

**Živá stránka:** https://lukas-rag.vercel.app
**Kód:** https://github.com/zenkovski/rag-demo

> **Není to právní porada.** Je to technická ukázka. Odpovědi můžou být chybné, a některé chybné jsou (viz níže).

Postaveno s AI (Claude Code). Kód jsem nepsal ručně; četl jsem ho, kontroloval a testoval. Rozbor každé části je v [INTERVIEW.md](INTERVIEW.md).

## Výsledky

| Měřítko | Výsledek |
|---|---|
| Odpověď správně (ruční kontrola všech 20) | **18 z 20** |
| Správný paragraf mezi prvními třemi nalezenými (hit@3) | **13 z 16** |
| Řekl „nevím“, když zdroj odpověď nemá | **4 z 4** |
| Řekl „nevím“, i když odpověď ve zdroji byla | 0 z 16 |
| AI soudce se shodl s ruční kontrolou | 19 z 20 |

Podrobně otázku po otázce: [RESULTS.md](RESULTS.md).

## Kde se mýlí

1. **Vyhledávání nerozumí laickým slovům.** „Firma mi nezaplatila výplatu, můžu hned odejít?“ Zákon píše „okamžitě zrušit“ a „nevyplatil mzdu“. Správný § 56 se mezi nalezené úseky nedostal, a odpověď je proto špatně. Stejný problém má ukázková otázka „Může mi dát výpověď, když jsem nemocný?“: § 53 (ochranná doba) se nenašel.
2. **Model si občas přidá nepravdu.** U dohody o pracovní činnosti správně napsal „max. 20 hodin týdně“, ale přidal „a ročně max. 300 hodin“. To platí pro DPP, ne pro DPČ. Odpověď citovala zdroj, ale zdroj přečetla obráceně. **AI soudce tuhle chybu nepoznal**, našla ji až ruční kontrola. Proto kontroluji ručně.
3. **Drobné nepřesnosti v citacích.** Dvakrát model ocitoval sousední úsek místo správného. Obsah odpovědi byl správně.

## Jak to funguje

```
otázka ─► embedding (e5) ─► 5 nejpodobnějších úseků ─► LLM: „odpověz jen z nich, cituj“ ─► odpověď [1] [2]
```

| Část | Jak | Soubor |
|---|---|---|
| Data | Zákoník práce, 5 témat (zkušební doba, výpověď a odstupné, DPP/DPČ, pracovní doba a přesčasy, dovolená), 84 paragrafů | `tools/chunk.py` |
| Dělení textu | 1 úsek = 1 odstavec paragrafu, ID typu `§ 51 odst. 2`, celkem 260 úseků | `tools/chunk.py` |
| Embeddingy | `intfloat/multilingual-e5-base` z Hugging Face, lokálně, zdarma | `tools/rag.py` |
| Vyhledávání | kosinová podobnost v numpy, top 5 | `tools/rag.py` |
| Odpověď | `nvidia/nemotron-3-super-120b-a12b` přes OpenRouter (free), teplota 0 | `tools/rag.py` |
| Měření | 20 otázek se zlatou odpovědí, hit@3, AI soudce + ruční kontrola | `tools/evaluate.py` |
| Web | statická stránka, D3 graf, předpočítané odpovědi v `data.json` | `site/`, `tools/build_data.py` |

## Jak měřím

- `data/testset.json`: 20 otázek. 16 má odpověď ve zdroji (snadné, střední, těžké), 4 záměrně ne (minimální mzda, mateřská, home office, nemocenská). U nich je správně jen „nevím“.
- **Vyhledávání:** je správný paragraf mezi prvními třemi nalezenými? (hit@3)
- **Odpověď:** AI soudce (stejný model) porovná odpověď se zlatou odpovědí a s úseky. Pak všech 20 odpovědí kontroluji ručně proti textu zákona. Ruční verdikt má přednost; poznámky jsou v `data/manual_review.json`.
- Odpovědi modelu se ukládají do `data/llm_cache.json`. Opakovaný běh dá stejná čísla a nic nestojí.

## Zdroj dat

Zákon č. 262/2006 Sb., zákoník práce, aktuální znění 29. 8. 2026 až 31. 12. 2026 (verze 63), z https://www.zakonyprolidi.cz/cs/2006-262, staženo 6. 10. 2026. Text zákona není chráněn autorským právem (§ 3 autorského zákona).

## Jak spustit

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
copy .env.example .env               # a doplň OPENROUTER_API_KEY

.venv/Scripts/python tools/chunk.py                  # stáhne a rozdělí zákon
.venv/Scripts/python tools/rag.py "Kolik mám dovolené?"   # vyzkouší vyhledávání
.venv/Scripts/python tools/evaluate.py               # měření -> RESULTS.md
.venv/Scripts/python tools/build_data.py             # data pro web -> site/data.json
cd site && python -m http.server 8000                # web na http://localhost:8000
```

## Bezpečnost

- API klíč je jen v `.env` (v `.gitignore`). Na webu žádný klíč není a web nevolá žádné API.
- Před commitem a nasazením jsem prošel repo i historii na `sk-`, `api_key`, `OPENROUTER`, `ANTHROPIC` a tokeny.

## Další kroky

- Hybridní vyhledávání (vektory + BM25) a přepsání laické otázky do jazyka zákona. Mířilo by to přesně na chyby výše.
- Reranker nad top 20 úseky.
- Větší testovací sada ze skutečných otázek lidí.
- Celý zákon a vektorová databáze (pgvector). Na 260 úseků stačí numpy.
