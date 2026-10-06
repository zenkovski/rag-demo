# RAG asistent nad zákoníkem práce

Asistent odpovídá česky na otázky o zákoníku práce. Odpovídá jen z textu zákona a každou větu ocituje. Když v textu odpověď není, řekne „nevím“. Kvalitu měřím na otázkách se známou správnou odpovědí a výsledky ukazuji včetně chyb. Projekt má dvě verze: v1 (základ) a v2 (vylepšené vyhledávání), obě změřené stejně.

**Živá stránka:** https://lukas-rag.vercel.app
**Kód:** https://github.com/zenkovski/rag-demo

> **Není to právní porada.** Je to technická ukázka. Odpovědi můžou být chybné, a některé chybné jsou (viz níže).

Postaveno s AI (Claude Code). Kód jsem nepsal ručně; četl jsem ho, kontroloval a testoval. Rozbor každé části je v [INTERVIEW.md](INTERVIEW.md).

## Výsledky

| Měřítko | v1 | v2 |
|---|---|---|
| **Odpověď správně, 20 testovacích otázek** (ruční kontrola) | 18 z 20 | **20 z 20** |
| z toho otázky s odpovědí v zákoně | 14 z 16 | 16 z 16 |
| z toho správně „nevím“, když zákon odpověď nemá | 4 z 4 | 4 z 4 |
| Správný paragraf mezi 5 úseky, které dostane model | 15 z 16 | 16 z 16 |
| **Odpověď správně, 10 nových otázek** (kontrola přeučení) | 8 z 10 | **9 z 10** |

„20 z 20“ znamená: 16 otázek, na které zákon odpovídá, model zodpověděl správně, a u 4 otázek, na které zákon neodpovídá, správně řekl „nevím“. Podrobně otázku po otázce: [RESULTS.md](RESULTS.md).

**Pozor na 20 z 20.** Úpravy v2 jsem navrhl podle chyb na těchto 20 otázkách, takže tam je výsledek nadsazený. Proto jsem až potom napsal 10 nových otázek a změřil na nich v1 i v2 beze změn. Tam je zlepšení menší (8 → 9 z 10). Tohle je poctivější číslo.

## Co se změnilo ve v2 a proč

| Problém ve v1 | Úprava ve v2 |
|---|---|
| Lidé píšou „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. Hledání podle významu správný § 56 nenašlo. | **Přepis otázky:** jazykový model nejdřív přeloží otázku do jazyka zákona. |
| Hledání podle významu občas mine přesné slovo. | **BM25** (hledání podle slov) nad přepsanou otázkou. Výsledky obou hledání se spojí metodou RRF. |
| Model si u DPČ přidal „300 hodin ročně“, což platí jen pro DPP. | **Přísnější pravidla** v promptu: každé tvrzení musí plynout z citovaného úseku; úseky o jiné situaci nepoužívat. |
| v1 běžel na free modelu `nemotron-3-super`. | v2 používá `deepseek-v4.1-flash` (levný, ~0,05 $ za milion vstupních tokenů). |

Zajímavost z měření: samotné BM25 nad laickou otázkou nepomohlo (15 → 14 z 16), protože slova „výplata“ v zákoně nejsou. Zabralo až spolu s přepisem otázky (16 z 16).

## Kde se v2 pořád mýlí

1. **„Do kdy si musím vybrat dovolenou?“** (nová otázka 28): správný § 218 odst. 1 se nenašel ani po přepisu. Odpověď cituje jen pravidlo o 30. červnu a hlavní zásadu vynechá.
2. **„Může mi dát výpověď, když jsem nemocný?“** (ukázka): v2 už najde § 53 (ochranná doba), ale závěr „během nemoci výpověď dostat nemůžete“ je moc silný. § 54 má výjimky a ten se nenašel.
3. **Správný paragraf často není první.** Mezi první tři se dostane u 13 z 16 otázek, model ho ale dostane mezi pěti. Další krok by byl reranker.

## Jak to funguje

```
otázka ─► přepis do jazyka zákona (LLM) ─► embeddingy + BM25 ─► RRF ─► 5 úseků ─► LLM: „odpověz jen z nich, cituj“ ─► odpověď [1] [2]
```

| Část | Jak | Soubor |
|---|---|---|
| Data | Zákoník práce, 5 témat (zkušební doba, výpověď a odstupné, DPP/DPČ, pracovní doba a přesčasy, dovolená), 84 paragrafů | `tools/chunk.py` |
| Dělení textu | 1 úsek = 1 odstavec paragrafu, ID typu `§ 51 odst. 2`, celkem 260 úseků | `tools/chunk.py` |
| Embeddingy | `intfloat/multilingual-e5-base` z Hugging Face, lokálně, zdarma | `tools/rag.py` |
| Hledání podle slov | BM25 bez knihovny, čeština bez diakritiky, kořen = prvních 5 písmen | `tools/rag.py` |
| Spojení | reciprocal rank fusion (RRF), top 5 | `tools/rag.py` |
| Odpověď a přepis | `deepseek/deepseek-v4.1-flash` přes OpenRouter, teplota 0 | `tools/rag.py` |
| Měření | 20 + 10 otázek se zlatou odpovědí, AI soudce + ruční kontrola, srovnání v1/v2 | `tools/evaluate.py` |
| Web | statická stránka, D3 graf, předpočítané odpovědi v `data.json` | `site/`, `tools/build_data.py` |

## Jak měřím

- `data/testset.json`: 20 otázek. 16 má odpověď v zákoně (snadné, střední, těžké), 4 záměrně ne (minimální mzda, mateřská, home office, nemocenská). U nich je správně jen „nevím“.
- `data/testset_holdout.json`: 10 nových otázek, napsaných až po návrhu v2.
- **Vyhledávání:** je správný paragraf mezi prvními třemi nalezenými (hit@3) a mezi pěti, které dostane model (hit@5)?
- **Odpověď:** AI soudce porovná odpověď se zlatou odpovědí a s úseky. Pak všechny odpovědi kontroluji ručně proti textu zákona. Ruční verdikt má přednost; poznámky jsou v `data/manual_review*.json`. Ve v1 soudce jednu chybu přehlédl (DPČ a 300 hodin), proto kontroluji ručně.
- Odpovědi modelu se ukládají do `data/llm_cache.json`. Opakovaný běh dá stejná čísla a nic nestojí.
- Cena: měření v2 asi 0,02 $, celý vývoj v2 (všechny pokusy, přepisy, ukázky) 0,065 $.

## Zdroj dat

Zákon č. 262/2006 Sb., zákoník práce, aktuální znění 29. 8. 2026 až 31. 12. 2026 (verze 63), z https://www.zakonyprolidi.cz/cs/2006-262, staženo 6. 10. 2026. Text zákona není chráněn autorským právem (§ 3 autorského zákona).

## Jak spustit

```bash
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
copy .env.example .env                                # a doplň OPENROUTER_API_KEY

.venv/Scripts/python tools/chunk.py                    # stáhne a rozdělí zákon
.venv/Scripts/python tools/rag.py "Nezaplatili mi výplatu, můžu odejít?"   # porovná 3 způsoby hledání
.venv/Scripts/python tools/evaluate.py --retrieval     # měření hledání (v1 / BM25 / v2)
.venv/Scripts/python tools/evaluate.py                 # měření v2 -> RESULTS.md
.venv/Scripts/python tools/evaluate.py --holdout       # 10 nových otázek, v1 i v2
.venv/Scripts/python tools/build_data.py               # data pro web -> site/data.json
cd site && python -m http.server 8000                  # web na http://localhost:8000
```

## Bezpečnost

- API klíč je jen v `.env` (v `.gitignore`). Na webu žádný klíč není a web nevolá žádné API.
- Před commitem a nasazením jsem prošel repo i historii na `sk-`, `api_key`, `OPENROUTER`, `ANTHROPIC` a tokeny.

## Další kroky

- Reranker (cross-encoder) nad top 20 úseky, aby správný paragraf byl častěji první.
- Úseky s odkazy („podle odstavce 2“) doplnit o odkazovaný odstavec. Pomohlo by to u § 53 a § 54.
- Větší testovací sada ze skutečných otázek lidí.
- Celý zákon a vektorová databáze (pgvector). Na 260 úseků stačí numpy.
