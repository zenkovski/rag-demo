# ADR-003: Oprávnění se vynucuje v hledací vrstvě, ne v promptu

**Stav:** přijato jako vzor, **v živém webu nezapojeno** · **Datum:** 9. 10. 2026

## Kontext

Kdyby systém hledal nad dokumenty s různými právy, hrozí dva způsoby úniku: model dostane text, který uživatel vidět nesmí, a pak ho (omylem nebo na žádost) zopakuje; nebo se text objeví v citacích či mezivýsledcích.

Obrana „v promptu je napsáno, že tohle nesmíš ukázat“ je **nespolehlivá**: prompt jde obejít (viz prompt injection) a model text už viděl.

## Rozhodnutí

Oprávnění se **vynucuje před modelem**, v hledání: `rag.search(question, allow={"ZP"})` dá nepovoleným předpisům nulové skóre ve všech třech pořadích, takže se nedostanou mezi kandidáty, do výběru, do pěti úseků pro model, do stopy ani do citací. Prompt o nepovolených dokumentech vůbec neví.

## Ověření

`tests/test_security.py` na 20 otázkách ověřuje, že s `allow={"ZP"}` nepovolený předpis **není** (a) ve výsledku, (b) v žádném mezikroku stopy, (c) v textu promptu, který by dostal model při výběru kandidátů. Falešný model zapisuje, co by dostal. Druhý test dokazuje, že filtr něco dělá (bez filtru se úsek z nemocenského pojištění objeví). Po vypnutí masky test selže (ověřeno).

## Důsledky a limity

- Filtr je podle **předpisu** (`law`), ne podle uživatele. Skutečný systém by potřeboval seznam povolených dokumentů na uživatele a jeho zdroj pravdy (IdP, databáze oprávnění). **Neimplementováno.**
- Webová funkce `allow` nepoužívá, protože nemá uživatele ani neveřejné dokumenty.
- **Cache odpovědí neexistuje.** Kdyby se přidala, klíč musí obsahovat množinu povolených dokumentů, jinak by odpověď pro jednoho uživatele mohla vyjít druhému.
- Neřeší únik přes **vektory**: embedding nepovoleného dokumentu je v indexu. Při hrubém úniku indexu by se z vektorů dal část textu odhadnout. Pro důvěrná data by byl potřeba oddělený index na tenanta.
