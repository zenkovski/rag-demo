# Tahák na pohovor

Pro každou část projektu: jak funguje (2–3 věty) a na co se můžou ptát. Odpovědi jsou krátké, ať je umím říct vlastními slovy.

## 1. Celý tok v jedné větě
Otázka → model ji přeloží do jazyka zákona → najdu 5 úseků (podle významu i podle slov) → pošlu je jazykovému modelu s pravidlem „odpovídej jen z nich a cituj“ → odpověď s čísly [1], [2] → změřím, jestli je správně.

## 2. Data a dělení textu (chunking) · `tools/chunk.py`
Stáhnu aktuální znění zákoníku práce ze zakonyprolidi.cz a vezmu pět témat (84 paragrafů). Jeden úsek = jeden odstavec paragrafu, např. `§ 51 odst. 2`. Písmena a), b), c) zůstávají u svého odstavce.

**Proč po odstavcích?** Zákon je tak napsaný. Odstavec je jedna myšlenka a má vlastní adresu, takže citace vede přesně na místo v zákoně. Pevné kousky po 500 znacích by roztrhly větu a citace by nedávala smysl.

**Co je slabina?** Některé odstavce na sebe odkazují („podle odstavce 2“). Model pak vidí jen půlku pravidla. Další krok: přidat k úseku i odkazovaný odstavec.

## 3. Embeddingy · `tools/rag.py`
Model `intfloat/multilingual-e5-base` z Hugging Face převede každý úsek na vektor 768 čísel. Podobný význam = vektory blízko sebe. Běží lokálně na PC, zdarma.

**Co je embedding?** Číselný otisk významu textu. „Výpověď“ a „ukončení pracovního poměru“ mají podobný otisk, i když jsou to jiná slova.

**Proč e5?** Je vícejazyčný, umí češtinu a je malý. E5 chce předponu `query:` u otázky a `passage:` u dokumentu, jinak hledá hůř.

## 4. Vyhledávání (v2: hybridní)
Tři seznamy pořadí: (1) podle významu z původní otázky, (2) podle významu z přepsané otázky, (3) podle slov (BM25) z přepsané otázky. Spojím je metodou RRF a vezmu 5 nejlepších. Kosinová podobnost je jedno násobení matic v numpy.

**Co je BM25?** Klasické hledání podle slov, jak ho mají vyhledávače. Bere v úvahu, jak často se slovo v úseku objevuje a jak vzácné je v celém zákoně. Češtinu zjednoduším: malá písmena, bez diakritiky a jen prvních 5 písmen slova („mzda“, „mzdu“ i „mzdy“ jsou pak skoro stejné).

**Co je RRF?** Reciprocal rank fusion: každý seznam dá úseku body podle pořadí (1/(60 + pořadí)) a body se sečtou. Vyhraje úsek, který je vysoko ve více seznamech. Nemusím ladit váhy a nevadí, že skóre embeddingů a BM25 mají jiné stupnice.

**Proč přepis otázky?** Laik píše „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. Model otázku nejdřív přeloží do jazyka zákona. U otázky o výplatě se tím správný § 56 dostal z 28. místa mezi nalezené.

**Proč BM25 jen nad přepsanou otázkou?** Změřil jsem to. BM25 nad laickou otázkou hledá slova, která v zákoně nejsou, a přidává šum: samotné BM25 zhoršilo výsledek z 15 na 14 z 16. Nad přepsanou otázkou pomáhá.

**Proč ne vektorová databáze?** Na 260 úseků je zbytečná, numpy to spočítá za milisekundy. U statisíců dokumentů bych použil pgvector nebo Qdrant.

**Kde vyhledávání pořád selhává?** „Do kdy si musím vybrat dovolenou?“: správný § 218 odst. 1 se nenašel ani ve v2. A správný paragraf často není první, jen mezi pěti. Další krok: reranker (cross-encoder), který přečte otázku a úsek spolu a seřadí je přesněji.

## 5. Odpověď s citacemi
Model dostane 5 úseků očíslovaných [1] až [5] a pravidla: odpovídej jen z nich, za každou větu citace, a když tam odpověď není, napiš „Nevím“. Ve v1 to byl `nemotron-3-super` od NVIDIA (free), ve v2 `deepseek-v4.1-flash` přes OpenRouter. Celé měření v2 stálo asi 0,02 $.

**Co se změnilo v promptu ve v2?** Každé tvrzení musí plynout z citovaného úseku, a úseky o jiné situaci se nesmí použít. Důvod: ve v1 model u DPČ napsal „300 hodin ročně“, protože viděl úsek o DPP.

**Proč citace?** Uživatel si může odpověď ověřit jedním klikem. U práva a financí je to nutnost. A já poznám, ze kterého úseku model čerpal.

**Co když model halucinuje?** Tři pojistky: (1) prompt zakazuje vlastní znalosti, (2) citace jde zkontrolovat proti zdroji, (3) měřím to: AI soudce kontroluje, jestli se každé tvrzení opírá o dodané úseky. Ani tak to není 100 %, proto web píše „není to právní porada“.

**Proč „nevím“?** Špatná sebevědomá odpověď je horší než žádná. Testovací sada má 4 otázky, na které zdroj odpověď nemá, a měřím, jestli model přizná, že neví.

## 6. Měření kvality · `tools/evaluate.py`
20 testovacích otázek se zlatou odpovědí a správnými paragrafy, z toho 4 bez odpovědi v zákoně (správně je „nevím“). Měřím zvlášť vyhledávání (hit@3, hit@5) a odpověď (je správná a opřená o zdroj?). Odpověď hodnotí AI soudce a pak ji ručně kontroluji. Výsledek: v1 18 z 20, v2 20 z 20. Čísla jsou v `RESULTS.md`.

**Co znamená „20 z 20“, když 4 odpovědi jsou „nevím“?** U těch 4 otázek zákon odpověď nemá, takže „nevím“ je správně. 20 z 20 = 16 správných odpovědí + 4 správná „nevím“.

**Není 20 z 20 podezřelé?** Je. Úpravy v2 jsem navrhl podle chyb na stejných otázkách, takže je to nadsazené (přeučení na testovací sadu). Proto jsem potom napsal 10 nových otázek a změřil obě verze beze změn: v1 8 z 10, v2 9 z 10. Tohle číslo je poctivější a na pohovoru ho říkám jako první.

**Proč měřit zvlášť vyhledávání a odpověď?** Abych věděl, kde opravovat. Když vyhledávání nenajde správný úsek, lepší prompt nepomůže.

**Proč ruční kontrola, když mám AI soudce?** Soudce je taky model a může se mýlit. Zapisuju i to, jak často se shodne s člověkem. Pak vím, jestli mu můžu věřit u větší sady.

**Proč jen 20 otázek?** Je to demo. Na produkci bych chtěl stovky otázek ze skutečných dotazů uživatelů a sledovat čísla při každé změně (regresní test).

## 7. Web · `site/`
Statická stránka bez serveru. Všechny odpovědi jsou předpočítané v `data.json`. Graf (D3) ukazuje všech 260 úseků, vazby = sousední odstavce a nejpodobnější úseky. Po otázce se rozsvítí přesně ty úseky, které vyhledávání vrátilo; citované plně, necitované obrysem.

**Proč statický web?** Bezpečnost a cena. Na webu není API klíč, nikdo cizí mi nemůže utratit peníze. Nevýhoda: dá se ptát jen na předpočítané otázky.

## 8. Bezpečnost
Klíč je jen v `.env`, který je v `.gitignore`. Před každým commitem prohledám repo i historii na `sk-`, `api_key` a podobně.

## 9. Co bych udělal dál
- reranker (cross-encoder) nad top 20 úseky,
- úseky s odkazy („podle odstavce 2“) doplnit o odkazovaný odstavec,
- větší testovací sada ze skutečných otázek,
- živý backend s limitem dotazů,
- celý zákon místo pěti témat, pgvector místo numpy.
