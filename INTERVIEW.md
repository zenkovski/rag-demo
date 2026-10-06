# Tahák na pohovor

Pro každou část projektu: jak funguje (2–3 věty) a na co se můžou ptát. Odpovědi jsou krátké, ať je umím říct vlastními slovy.

## 1. Celý tok v jedné větě
Otázka → najdu 5 nejpodobnějších úseků zákona → pošlu je jazykovému modelu s pravidlem „odpovídej jen z nich a cituj“ → odpověď s čísly [1], [2] → změřím, jestli je správně.

## 2. Data a dělení textu (chunking) · `tools/chunk.py`
Stáhnu aktuální znění zákoníku práce ze zakonyprolidi.cz a vezmu pět témat (84 paragrafů). Jeden úsek = jeden odstavec paragrafu, např. `§ 51 odst. 2`. Písmena a), b), c) zůstávají u svého odstavce.

**Proč po odstavcích?** Zákon je tak napsaný. Odstavec je jedna myšlenka a má vlastní adresu, takže citace vede přesně na místo v zákoně. Pevné kousky po 500 znacích by roztrhly větu a citace by nedávala smysl.

**Co je slabina?** Některé odstavce na sebe odkazují („podle odstavce 2“). Model pak vidí jen půlku pravidla. Další krok: přidat k úseku i odkazovaný odstavec.

## 3. Embeddingy · `tools/rag.py`
Model `intfloat/multilingual-e5-base` z Hugging Face převede každý úsek na vektor 768 čísel. Podobný význam = vektory blízko sebe. Běží lokálně na PC, zdarma.

**Co je embedding?** Číselný otisk významu textu. „Výpověď“ a „ukončení pracovního poměru“ mají podobný otisk, i když jsou to jiná slova.

**Proč e5?** Je vícejazyčný, umí češtinu a je malý. E5 chce předponu `query:` u otázky a `passage:` u dokumentu, jinak hledá hůř.

## 4. Vyhledávání
Otázku převedu na vektor a spočítám kosinovou podobnost se všemi 260 úseky (jedno násobení matic v numpy). Vezmu 5 nejlepších.

**Proč ne vektorová databáze?** Na 260 úseků je zbytečná, numpy to spočítá za milisekundy. U statisíců dokumentů bych použil pgvector nebo Qdrant.

**Kde vyhledávání selhává?** Když laik mluví jinak než zákon. „Nezaplatili mi výplatu, můžu odejít?“ vs. zákon „okamžitě zrušit… nevyplatil mzdu“. Pomohlo by hybridní hledání (vektory + klíčová slova BM25) nebo přepsání otázky modelem před hledáním.

## 5. Odpověď s citacemi
Model dostane 5 úseků očíslovaných [1] až [5] a pravidla: odpovídej jen z nich, za každou větu citace, a když tam odpověď není, napiš „Nevím“. Model je `nemotron-3-super` od NVIDIA přes OpenRouter (free).

**Proč citace?** Uživatel si může odpověď ověřit jedním klikem. U práva a financí je to nutnost. A já poznám, ze kterého úseku model čerpal.

**Co když model halucinuje?** Tři pojistky: (1) prompt zakazuje vlastní znalosti, (2) citace jde zkontrolovat proti zdroji, (3) měřím to: AI soudce kontroluje, jestli se každé tvrzení opírá o dodané úseky. Ani tak to není 100 %, proto web píše „není to právní porada“.

**Proč „nevím“?** Špatná sebevědomá odpověď je horší než žádná. Testovací sada má 4 otázky, na které zdroj odpověď nemá, a měřím, jestli model přizná, že neví.

## 6. Měření kvality · `tools/evaluate.py`
20 testovacích otázek se zlatou odpovědí a správnými paragrafy. Měřím zvlášť vyhledávání (hit@3: je správný úsek mezi prvními třemi?) a odpověď (je správná a opřená o zdroj?). Odpověď hodnotí AI soudce a pak ji ručně kontroluji. Čísla jsou v `RESULTS.md`.

**Proč měřit zvlášť vyhledávání a odpověď?** Abych věděl, kde opravovat. Když vyhledávání nenajde správný úsek, lepší prompt nepomůže.

**Proč ruční kontrola, když mám AI soudce?** Soudce je taky model a může se mýlit. Zapisuju i to, jak často se shodne s člověkem. Pak vím, jestli mu můžu věřit u větší sady.

**Proč jen 20 otázek?** Je to demo. Na produkci bych chtěl stovky otázek ze skutečných dotazů uživatelů a sledovat čísla při každé změně (regresní test).

## 7. Web · `site/`
Statická stránka bez serveru. Všechny odpovědi jsou předpočítané v `data.json`. Graf (D3) ukazuje všech 260 úseků, vazby = sousední odstavce a nejpodobnější úseky. Po otázce se rozsvítí přesně ty úseky, které vyhledávání vrátilo; citované plně, necitované obrysem.

**Proč statický web?** Bezpečnost a cena. Na webu není API klíč, nikdo cizí mi nemůže utratit peníze. Nevýhoda: dá se ptát jen na předpočítané otázky.

## 8. Bezpečnost
Klíč je jen v `.env`, který je v `.gitignore`. Před každým commitem prohledám repo i historii na `sk-`, `api_key` a podobně.

## 9. Co bych udělal dál
- hybridní vyhledávání (BM25 + vektory) a reranker,
- větší testovací sada ze skutečných otázek,
- živý backend s limitem dotazů,
- celý zákon místo pěti témat, pgvector místo numpy.
