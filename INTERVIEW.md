# Tahák na pohovor

Pro každou část projektu: jak funguje (2–3 věty) a na co se můžou ptát. Odpovědi jsou krátké, ať je umím říct vlastními slovy.

## 1. Celý tok v jedné větě
Otázka → model ji přeloží do jazyka zákona → najdu 20 kandidátů (podle významu i podle slov) → model z nich vybere 5, které k otázce patří → pošlu je jazykovému modelu s pravidlem „odpovídej jen z nich a cituj“ → odpověď s čísly [1], [2] → změřím, jestli je správně.

## 2. Data a dělení textu (chunking) · `tools/chunk.py`
Stáhnu aktuální znění 4 předpisů ze zakonyprolidi.cz: celý zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění a nařízení o překážkách v práci. Celkem 2 475 úseků. Jeden úsek = jeden odstavec paragrafu, např. `ZP § 51 odst. 2`. Zkratka zákona je v ID, protože § 26 je v každém zákoně jiný. U nařízení je úsek jeden bod přílohy (`NV 590 příloha bod 5` = svatba).

**Proč po odstavcích?** Zákon je tak napsaný. Odstavec je jedna myšlenka a má vlastní adresu, takže citace vede přesně na místo v zákoně.

**Co jsem vyhodil?** Závěrečná ustanovení: seznamy zrušených zákonů, účinnost, směrnice EU a katalog platových tříd. K otázkám lidí nic nepřidají, jen dělají šum. Pár obřích výčtů zkracuji na 6 000 znaků.

**Co mě překvapilo?** Nařízení o minimální mzdě je od roku 2025 zrušené. Výši teď vyhlašuje ministerstvo sdělením, které v zákonech není. Proto je otázka „Jaká je minimální mzda v roce 2026?“ dál test „nevím“.

**Co je slabina?** Odstavce na sebe odkazují („podle § 26“). Model pak vidí jen půlku pravidla. Další krok: přidat k úseku i odkazovaný odstavec.

## 3. Embeddingy · `tools/rag.py`
Model e5 z Hugging Face převede každý úsek na vektor čísel. Podobný význam = vektory blízko sebe. Ve v1 `multilingual-e5-base` lokálně (768 čísel), ve v2 `multilingual-e5-large` přes API OpenRouteru (1024 čísel).

**Proč přes API?** Lokální model má 1 GB a na Vercelu neběží. Web používá přesně ten model, který jsem změřil. Vektory všech 2 475 úseků stály asi 0,001 $.

**Proč int8?** 2 475 × 1024 čísel ve float32 je 10 MB, to je na serverovou funkci moc. Každý vektor uložím jako celá čísla −127 až 127 a jedno měřítko: 4× menší soubor. Python, LangChain i web převádějí zpátky stejně a vektor znovu normalizují. Bez normalizace se LangChain (kosinová podobnost) lišil u 11 ze 46 otázek, protože zaokrouhlený vektor nemá přesně délku 1.

**Co je embedding?** Číselný otisk významu textu. „Výpověď“ a „ukončení pracovního poměru“ mají podobný otisk, i když jsou to jiná slova.

**Proč e5?** Je vícejazyčný a umí češtinu. Chce předponu `query:` u otázky a `passage:` u dokumentu, jinak hledá hůř.

## 4. Vyhledávání (v2: hybridní)
Tři seznamy pořadí: (1) podle významu z původní otázky, (2) podle významu z přepsané otázky, (3) podle slov (BM25) z přepsané otázky. Spojím je metodou RRF a vezmu 5 nejlepších. Kosinová podobnost je jedno násobení matic v numpy.

**Co je BM25?** Klasické hledání podle slov, jak ho mají vyhledávače. Bere v úvahu, jak často se slovo v úseku objevuje a jak vzácné je v celém zákoně. Češtinu zjednoduším: malá písmena, bez diakritiky a jen prvních 5 písmen slova („mzda“, „mzdu“ i „mzdy“ jsou pak skoro stejné).

**Co je RRF?** Reciprocal rank fusion: každý seznam dá úseku body podle pořadí (1/(60 + pořadí)) a body se sečtou. Vyhraje úsek, který je vysoko ve více seznamech. Nemusím ladit váhy a nevadí, že skóre embeddingů a BM25 mají jiné stupnice.

**Proč přepis otázky?** Laik píše „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. Model otázku nejdřív přeloží do jazyka zákona. U otázky o výplatě se tím správný § 56 dostal z 28. místa mezi nalezené.

**Proč BM25 jen nad přepsanou otázkou?** Změřil jsem to. BM25 nad laickou otázkou hledá slova, která v zákoně nejsou, a přidává šum: samotné BM25 zhoršilo výsledek z 15 na 14 z 16. Nad přepsanou otázkou pomáhá.

**Proč ne vektorová databáze?** Na 2 475 úseků je zbytečná: 2,5 milionu násobení zvládne numpy i JavaScript za milisekundy. U statisíců dokumentů bych použil pgvector nebo Qdrant.

**Co udělal 10× větší zdroj?** Měřil jsem to. 24 otázek, které měly odpověď už nad 260 odstavci, najdou správný paragraf i nad 2 475 odstavci (24 z 24). Celkem v2 najde správný paragraf mezi 5 u 39 ze 40 otázek.

**Co je výběr přes LLM (v3)?** Reranker. RRF dá 20 kandidátů a jazykový model si je přečte a vybere 5, které k otázce opravdu patří. U otcovské byl odstavec s výší dávky až 10., výběr ho dostal do pětky. Cena: jedno volání navíc, asi 1,5 s. Levnější varianta je cross-encoder, malý model, který jen boduje dvojici otázka–úsek.

**Kde vyhledávání pořád selhává?** Zákon o nemocenském pojištění má stovky podobných odstavců („nemocenské“, „podpůrčí doba“, „vyměřovací základ“). U „Kolik peněz dostanu na nemocenské?“ se správný odstavec nenašel. Další krok: reranker (cross-encoder), který přečte otázku a úsek spolu a seřadí je přesněji.

## 5. Odpověď s citacemi
Model dostane 5 úseků očíslovaných [1] až [5] a pravidla: odpovídej jen z nich, za každou větu citace, a když tam odpověď není, napiš „Nevím“. Ve v1 to byl `nemotron-3-super` od NVIDIA (free), ve v2 `deepseek-v4.1-flash` přes OpenRouter. Celé měření v2 stálo asi 0,04 $.

**Co se změnilo v promptu ve v2?** Každé tvrzení musí plynout z citovaného úseku, a úseky o jiné situaci se nesmí použít. Důvod: ve v1 model u DPČ napsal „300 hodin ročně“, protože viděl úsek o DPP.

**Proč citace?** Uživatel si může odpověď ověřit jedním klikem. U práva a financí je to nutnost. A já poznám, ze kterého úseku model čerpal.

**Co když model halucinuje?** Tři pojistky: (1) prompt zakazuje vlastní znalosti, (2) citace jde zkontrolovat proti zdroji, (3) měřím to: AI soudce kontroluje, jestli se každé tvrzení opírá o dodané úseky. Ani tak to není 100 %, proto web píše „není to právní porada“.

**Proč „nevím“?** Špatná sebevědomá odpověď je horší než žádná. Testovací sady mají 6 otázek mimo předpisy (daně, nájem bytu, rodičovský příspěvek…) a měřím, jestli model přizná, že neví. Obě verze: 6 z 6.

**Nejčastější chyba v2?** Mzda × plat (ve v3 opravené). Zákoník práce má zvlášť pravidla pro mzdu (soukromé firmy) a plat (stát). U noční práce model napsal 20 % (plat) místo 10 % (mzda). Řešení ve v3: úsek v podkladech nese poznámku „platí pro mzdu / pro plat“ a pravidlo říká: když otázka neříká, která skupina platí, uveď obě varianty. U nejasné otázky se model doptá.

## 6. Měření kvality · `tools/evaluate.py`
46 otázek ve 3 sadách, každá se zlatou odpovědí a správnými paragrafy. 6 otázek nemá odpověď v předpisech (správně je „nevím“). Měřím zvlášť vyhledávání (hit@3, hit@5) a odpověď. Odpověď hodnotí AI soudce a pak ji ručně kontroluji. Výsledek: v1 44 z 56, v2 50 z 56, v3 55 z 56.

**Proč tři sady?**
- testovací (1–20): podle chyb na nich jsem navrhl v2, takže tam je v2 nadsazená (19 z 20),
- kontrolní (21–30): napsané až po návrhu v2 (10 z 10),
- nové předpisy (31–46): napsané po přidání zákonů. v1 i v2 tam měly 13 z 16. Podle těch chyb jsem navrhl v3 (16 z 16, ale zvýhodněné),
- po opravě (47–56): 10 otázek i se zlatými odpověďmi napsaných **před** prvním spuštěním v3. **v3 10 z 10, v2 8 z 10.** To je nejpoctivější číslo a na pohovoru ho říkám první.

**Co se stalo se starými „nevím“ otázkami?** V první verzi (jen 5 témat zákoníku práce) byla „Jak dlouho trvá mateřská?“ test „nevím“. Teď je mateřská v předpisech, takže otázka dostala novou zlatou odpověď. Původní je uložená v poli `gold_5temat`. Kdybych to neudělal, „nevím“ by se počítalo jako správně, i když odpověď v zákoně je.

**Je výsledek opakovatelný?** Ne úplně. Přepis otázky dělá jazykový model a i s teplotou 0 vyjde nové volání stejně jen asi u 7 ze 46 otázek. Odpovědi ukládám do cache, takže moje čísla jdou zopakovat, ale nové spuštění se může mírně lišit. Správně by se mělo měřit víc běhů a uvádět rozptyl.

**Proč měřit zvlášť vyhledávání a odpověď?** Abych věděl, kde opravovat. Když vyhledávání nenajde správný úsek, lepší prompt nepomůže. A naopak: 3 ze 4 chyb v2 jsou při správně nalezeném paragrafu, tam pomůže prompt nebo metadata, ne lepší hledání.

**Proč ruční kontrola, když mám AI soudce?** Soudce je taky model. S vypnutým přemýšlením přehlédl 3 chybná „nevím“ (odpověď v zákoně byla, a on dal „správně“). Proto kontroluju i ukázkové otázky na webu (14 z 16 správně).

## 7. LangChain verze · `tools/rag_langchain.py`
Stejný postup napsaný idiomaticky v LangChainu 1.x: `Document`, vlastní `Embeddings` pro e5, `InMemoryVectorStore`, dva retrievery (`BaseRetriever`), LCEL řetěz s `RunnableParallel` (tři hledání najednou), RRF a `ChatOpenAI` napojený na OpenRouter.

**Proč dvě verze?** Ruční verze ukazuje, že vím, co se děje uvnitř. LangChain verze ukazuje, že umím framework, který firmy používají. Změřil jsem, že při stejném přepisu otázky najdou obě (a JavaScript na webu) stejných 5 úseků u 56 z 56 otázek (při stejném přepisu a stejném výběru). Napoprvé to bylo jen 35 z 46: `InMemoryVectorStore` počítá kosinovou podobnost a zaokrouhlené vektory neměly přesně délku 1. Opravil jsem to normalizací ve všech třech verzích.

**Proč ne `langchain-community`?** Při instalaci hlásil, že se ukončuje. `BM25Retriever` a `EnsembleRetriever` tam byly, teď je to roztroušené. Proto jsem retrievery napsal jako malé vlastní třídy nad `langchain-core`.

**Co je LCEL?** LangChain Expression Language: kroky se skládají operátorem `|` jako roura (prompt | model | parser). `RunnableParallel` spustí víc kroků najednou, `RunnablePassthrough.assign` přidá výsledek ke vstupu.

## 8. Web a živé otázky · `site/`, `site/api/ask.js`
Stránka + jedna serverová funkce na Vercelu pro vlastní otázky. Připravené otázky s měřením jsou předpočítané v `data.json`. Funkce dělá totéž co Python, jen v JavaScriptu (přepis → embeddingy → BM25 → RRF → odpověď).

**Jak bráníš zneužití?** Klíč jen na serveru; 10 otázek na IP za den; proof of work (prohlížeč musí spočítat hash se 4 nulami, robotům to prodraží hromadné dotazy); kontrola původu požadavku; skryté pole jako past; a hlavně pevný limit 0,50 $ na klíči. Slabina: počítadla jsou v paměti funkce, ne v databázi.

**Co je ta animace v mapě?** Skutečné mezivýsledky hledání: nejdřív kandidáti podle významu, pak podle slov, pak spojení RRF, nakonec citované odstavce. Žádná vymyšlená animace. Graf (D3) ukazuje všech 2 475 úseků, barva = oblast, vazby = sousední odstavce a nejpodobnější úseky. Rozložení počítám předem v Pythonu (numpy, stejný silový algoritmus jako d3-force, ~3 min), v prohlížeči by to trvalo dlouho. Všechny vazby kreslím jako jednu SVG cestu, ať je mapa plynulá. Po otázce se rozsvítí přesně ty úseky, které vyhledávání vrátilo; citované plně, necitované obrysem.

**Proč předpočítané otázky?** Bezpečnost a cena: změřené otázky nic nestojí a jsou ručně zkontrolované. Vlastní otázky jdou přes funkci s limity.

## 9. Bezpečnost
Klíč je jen v `.env`, který je v `.gitignore`. Před každým commitem prohledám repo i historii na `sk-`, `api_key` a podobně.

## 10. Jak jsem opravoval chyby (v3)
Každou chybu jsem zařadil do kroku, kde vznikla:
- **hledání:** správný odstavec nebyl mezi 5 úseky pro model (nemocenská, otcovská),
- **čtení:** model ho měl, ale špatně použil (mzda × plat, „nemusí“ × „nesmí“).

Opravy: výběr přes LLM z 20 kandidátů (hledání), poznámka u úseku „platí pro mzdu / plat“ a přesnější pravidla (čtení). Pak jsem napsal 10 nových otázek **dřív**, než jsem v3 spustil, ať neladím na test. v3 má na nich 10 z 10, v2 8 z 10.

**Co se rozbilo?** Jedna otázka, která ve v2 fungovala („odpočinek mezi směnami“): výběr vzal odstavce o zkrácení odpočinku a vyhodil základní pravidlo. Proto měřím všechno znovu, ne jen opravené otázky. Regrese se jinak nepozná. Opravil jsem to deterministicky: k vybranému odstavci 2, 3… se vždy přidá odstavec 1 téhož paragrafu. Poctivě: tahle druhá oprava už nebyla ověřená na nových otázkách.

**Co mě stálo nejvíc?** Skryté přemýšlení modelu (reasoning). DeepSeek u každého kroku „přemýšlel“ tisíce slov: krok trval 30 s a měření stálo desetkrát víc. Vypnul jsem ho přes `reasoning: {enabled: false}`: krok trvá 1,5 s. Poučení: u každého modelu hlídat počet výstupních tokenů, ne jen cenu za token.

## 11. Co bych udělal dál
- cross-encoder místo LLM pro výběr (levnější, stabilnější),
- úseky s odkazy („podle § 26“) doplnit o odkazovaný odstavec,
- větší testovací sada ze skutečných otázek a měření rozptylu,
- počítadla limitů v Redis, pgvector místo numpy při dalším růstu.
