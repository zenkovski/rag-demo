# Návrh systému: rozhodnutí a proč

Každé rozhodnutí v projektu, proč padlo a čím je podložené. Čísla jsou z měření v [RESULTS.md](RESULTS.md), vývoj verzí v [HISTORY.md](HISTORY.md).

## 1. Celý tok

```
otázka ─► přepis do jazyka zákona (LLM)
        ─► hledání podle významu (e5-large: původní + přepsaná otázka) + podle slov (BM25: přepsaná otázka)
        ─► RRF ─► 20 kandidátů ─► LLM vybere 5 ─► + odstavec 1 téhož § + odkazované odstavce
        ─► odpověď jen z těchto 5 úseků, s citacemi, nebo „nevím“
```

Každý krok jde měřit zvlášť. Díky tomu u každé chyby vím, jestli vznikla v **hledání** (správný odstavec se k modelu nedostal), nebo ve **čtení** (model ho měl a špatně použil). Oprava je pro každý typ jiná: lepší prompt nespraví hledání a lepší hledání nespraví čtení.

## 2. Data a dělení textu · `tools/chunk.py`

- 4 předpisy ze zakonyprolidi.cz, **2 475 úseků**. Jeden úsek = jeden odstavec paragrafu, ID typu `ZP § 56 odst. 1`.
- **Proč po odstavcích:** zákon je tak napsaný. Odstavec je jedna myšlenka s vlastní adresou, citace pak vede přesně na místo v zákoně. Pevné okno (např. 500 tokenů) by trhalo pravidla v půlce.
- **Zkratka zákona v ID:** § 26 je v každém zákoně jiný.
- **Vyhozené:** seznamy zrušených předpisů, účinnost, směrnice EU, katalog platových tříd. Jen šum. Pár obřích výčtů je zkrácených na 6 000 znaků.
- **Metadata:** zákon, paragraf, oblast (výpověď, dovolená…) a u zákoníku práce poznámka „platí pro mzdu / plat“ (viz § 6).

## 3. Embeddingy · `tools/rag.py`

- **Model:** `multilingual-e5-large` přes API. Umí češtinu a stejný model běží při měření i na webu. Lokální e5-base (v1) našel správný § mezi 5 u 47 z 56 otázek, e5-large u 50.
- **Předpony `query:` a `passage:`:** e5 byl tak trénovaný. Otázka a dokument jsou jiné druhy textu a předpona modelu řekne, který je který.
- **Normalizace na délku 1:** kosinová podobnost je pak obyčejný skalární součin. Celé hledání je jedno násobení matice 2 475 × 1 024.
- **int8:** vektory ve float32 mají 10 MB, na serverovou funkci moc. Každý vektor ukládám jako celá čísla −127…127 plus jedno měřítko: 4× menší. Změřený dopad na 301 dotazech: podobnost float × int8 vektoru min. 0,9999, top 20 se shoduje v průměru 19,8 z 20, top 5 ve stejném pořadí u 81 %. Všechna čísla v RESULTS.md jsou už s int8.
- **Past, kterou jsem našel:** zaokrouhlený vektor nemá přesně délku 1. LangChain počítá kosinus, Python skalární součin, takže se lišily u 11 ze 46 otázek. Oprava: po převodu zpět vektor znovu normalizovat, ve všech třech verzích stejně.

## 4. Hledání · `tools/rag.py`

| Krok | Proč | Změřeno (správný § mezi 5, ze 56) |
|---|---|---|
| e5-large | význam, i jinými slovy | 50 |
| + BM25 nad laickou otázkou | přesné termíny | **44**: zhoršení, slovo „výplata“ v zákoně není |
| + přepis otázky, BM25 nad přepisem | „výplata“ → „mzda“ | 53 |
| + LLM výběr 5 z 20, odstavec 1, odkazy | přečte kandidáty a vybere | 56 |

- **BM25** je klasické hledání podle slov. Vyhraje u přesných termínů a čísel („§ 52“, „DPČ“, „odstupné“), kde embedding rozmaže význam. Napsaný bez knihovny: čeština bez diakritiky a kořen = prvních 5 písmen.
- **RRF místo vážení skóre:** skóre embeddingů (0–1) a BM25 (0–∞) mají jiné stupnice. Vážený součet by potřeboval ladit váhy a normalizaci. RRF bere jen pořadí (1/(60 + pořadí)) a nic se neladí.
- **Proč ne vektorová databáze:** 2 475 úseků je pod 10 ms v numpy. Databáze by přidala službu, ale ne kvalitu. Hranice je kolem statisíců úseků (viz § 11).

## 5. Výběr 5 z 20: LLM, nebo cross-encoder?

Výběr nemůže najít, co mezi 20 kandidáty není. Proto měřím zvlášť strop (kandidáti) a výběr. `tools/rerank_compare.py`, z cache, zdarma:

| Krok (56 otázek s odpovědí) | Správný § | MRR | Čas a cena na otázku |
|---|---|---|---|
| Strop: mezi 20 kandidáty z RRF | 55 z 56 | | |
| Bez výběru: prvních 5 z RRF | 49 z 56 | 0,70 | 0 |
| Cross-encoder `bge-reranker-v2-m3`, lokálně | 52 z 56 | 0,81 | 15 s na CPU, 0 $ |
| **LLM výběr (`deepseek-v4.1-flash`)** | **56 z 56** | **0,96** | 1,5 s, ~0,0001 $ |

MRR (mean reciprocal rank) = jak vysoko je první správný úsek: 1 = vždy první, 0,5 = v průměru druhý. Pevná pravidla (odstavec 1, odkazy) mají oba výběry stejná.

- **Proč 56, když strop je 55:** u „odpočinku mezi směnami“ chybělo pravidlo (§ 90 odst. 1) i mezi 20 kandidáty. LLM vybral výjimku (odst. 2) a pravidlo odstavce 1 doplnilo základ. Tady pomohlo pravidlo, ne výběr.
- **Proč LLM:** o 4 správné úseky víc a správný úsek skoro vždy na prvním místě. Cross-encoder zná jen dvojici otázka–úsek. LLM vidí všech 20 najednou a pozná, že odpověď potřebuje dva odstavce (délku i výši dávky).
- **Nevýhody LLM:** platí se za každý dotaz, závisí na promptu a nové volání nemusí vrátit totéž. Cross-encoder je deterministický a s GPU by trval desítky ms.
- **V provozu bych zkusil:** cross-encoder na GPU jako první síto a LLM jen pro nejisté případy. Nebo cross-encoder doladit na párech otázka–paragraf z logů.

## 6. Odpověď

- **Pravidla v promptu:** odpovídej jen z úseků, za tvrzení citace [n], úsek o jiné situaci nepoužívej, „je povinen“ = musí, „není povinen“ = nemusí (ne „nesmí“), čísla opiš přesně. Když v úsecích nic není: „Nevím“.
- **Mzda × plat:** zákoník práce má zvlášť pravidla pro firmy (mzda) a stát (plat). Model zaměnil 10 % a 20 % u noční práce. Úsek proto nese poznámku, komu platí, a model uvede obě varianty, když to otázka neříká.
- **Model:** přepis a výběr dělá levný `deepseek-v4.1-flash`, odpověď `deepseek-v4-pro`. Flash četl stejný odstavec jednou správně a jindy špatně a zbytečně říkal „nevím“. Pokus na 5 problémových otázkách: lepší prompt sám spravil 3, silnější model sám 3, oba dohromady 5.
- **Skryté přemýšlení vypnuté:** Flash „přemýšlel“ až 4 800 tokenů na krok, 30 s a 10× dráž. Vypnuté: 1,5 s, kvalita se nezhoršila.
- **Cena:** celé měření 66 otázek včetně AI soudce 0,07 $, tedy asi 0,001 $ na otázku.

## 7. Měření · `tools/evaluate.py`

- **66 otázek v 5 sadách.** 56 má odpověď v předpisech (se správnými paragrafy), 10 je past, kde je správně „nevím“.
- **Únik testu (leakage):** podle chyb na sadě jsem pokaždé navrhl další verzi, takže na ní je ta verze zvýhodněná. Proto jsem před spuštěním v3 i v3.1 napsal novou sadu i se správnými odpověďmi. Poctivé číslo: **20 z 20 (předchozí verze 18 z 20)**. Celkových 66 z 66 je nadsazené a tak je to i napsané.
- **Hledání:** hit@3 a hit@5 (správný § mezi prvními 3 / 5) a MRR (jak vysoko správný § je).
- **Odpověď:** AI soudce (správně? opírá se o úseky?), pak druhá kontrola každé odpovědi proti textu zákona (Claude Opus 5.5), kterou jsem prošel a schválil. Platí druhý verdikt. Soudce přehlédl několik chybných „nevím“.
- **Mimo testy:** 16 ukázkových otázek na webu, 14 správně. Obě chyby jsou na webu vidět.
- **Opakovatelnost:** přepis dělá LLM a ani s teplotou 0 není nové volání vždy stejné. Čísla platí pro jeden uložený běh (`data/llm_cache.json`). Správně by se měřilo víc běhů a rozptyl. Pro demo s limitem 0,75 $ to nedělám.
- **66 otázek je málo.** Rozdíl 18 vs 20 z 20 je ukazatel, ne statistický důkaz.

## 8. Jak hledám příčinu chyby

1. Je správný § mezi 20 kandidáty? Ne → chyba v hledání (embeddingy, BM25, přepis). Výběr ani prompt nepomůžou.
2. Je mezi 5 úseky pro model? Ne → chyba ve výběru (reranker).
3. Model ho měl a odpověděl špatně → chyba ve čtení (prompt, model, metadata úseku).
4. Po každé opravě měřím znovu všechno, ne jen opravenou otázku. Takhle jsem našel regresi: výběr ve v3 vzal u „odpočinku mezi směnami“ jen výjimky (§ 90 odst. 2, 3) bez pravidla (odst. 1). Oprava je pevné pravidlo bez AI: k odstavci 2, 3… vždy přidat odstavec 1.

Příklad: hit@5 je 56 z 56, ale odpověď u posudku byla špatně → problém je ve čtení, ne v hledání. Pomohl přesnější prompt a silnější model.

## 9. Proč je hledání napsané třikrát

- **Python** (`rag.py`): na něm se měří.
- **JavaScript** (`site/api/ask.js`): web běží jako serverová funkce v Node.js na Vercelu. Jedna služba bez dalšího serveru, zdarma.
- **LangChain** (`rag_langchain.py`): ukázka, že stejný postup umím ve frameworku, který firmy používají.

Riziko tří kopií je, že se rozejdou. Proto test v `tests/` spustí JavaScript a porovná ho s Pythonem. V provozu bych měl jednu implementaci (Python API) a web by jen zobrazoval výsledky.

## 10. Web a ochrana · `site/`

- Klíč jen v proměnné prostředí na Vercelu. Max 10 otázek na IP za den, strop 400 za den, proof of work (prohlížeč spočítá hash se 4 nulami, 1–3 s), kontrola původu, skryté pole proti robotům. Pevný limit 0,75 $ na klíči.
- Ukázkové otázky jsou předpočítané a zkontrolované, nic nestojí.
- Mapa ukazuje skutečné mezivýsledky hledání, ne animaci. Rozložení 2 475 bodů se počítá předem v Pythonu.
- Slabina: počítadla jsou v paměti funkce. Při víc instancích by se limit dal obejít. Řešení: Redis.

## 11. Co by chybělo do provozu

Pro demo to není potřeba. Pro skutečné nasazení:

- **Aktualizace zákonů:** denně porovnat verzi předpisu, při změně znovu rozdělit jen ten předpis, přepočítat embeddingy změněných odstavců (cache podle textu to umí), spustit měření a nasadit, jen když výsledek neklesne.
- **Testovací sada z provozu:** 10 000 otázek ručně nikdo nenapíše. Vzorek skutečných dotazů z logů rozdělený podle oblastí, k tomu otázky generované z odstavců a ruční kontrola vzorku. Těžké případy (podobné paragrafy, mzda × plat) do stálé regresní sady. Testovací sadu brát z pozdějšího období než ladicí, ať se neladí na test.
- **Měření v provozu:** latence, cena na dotaz, podíl „nevím“, kliky na citace a palec nahoru / dolů.
- **Víc dat:** při statisících úseků pgvector nebo Qdrant místo numpy a fulltext v Postgresu místo vlastního BM25. Postup zůstane stejný.
- **Jiné dokumenty:** zákon je čistý text s jasnou strukturou, to je pro RAG snadný případ. PDF s tabulkami, skeny nebo dokumenty v několika verzích by potřebovaly jiné dělení, OCR, filtrování podle metadat a práva přístupu.
- **Kdy RAG nestačí:** když odpověď vyžaduje výpočet (výše odstupného z průměrného výdělku) nebo spojení mnoha paragrafů. Tam by pomohl nástroj (kalkulačka) nebo agent, který hledá víckrát.

## 12. Testy · `tests/`

14 testů bez volání API, běží pod 1 s: dělení slov pro BM25, RRF, výběr čísel z odpovědi modelu, pravidla odstavce 1 a odkazů, převod int8 tam a zpět, poznámka mzda × plat a kontrola, že správné úseky z testovacích sad v datech opravdu jsou. Jeden test spustí kód webu v Node.js a ověří, že hledá stejně jako Python. GitHub je spouští po každém nahrání.
