# Incident (ukázkový): „zjednodušení“ řazení rozbilo výběr, lint ani unit testy nic nehlásily

**Stav:** opraveno, hlídáno novým testem. **Druh:** záměrně vyrobený incident pro doložení CI (rozbitou změnu napsal AI asistent, aby se ukázalo, co CI zachytí). Příznaky, diagnóza a oprava jsou skutečné, opravdu proběhly v CI.

| | Odkaz |
|---|---|
| Rozbitá změna (commit `2d71aaa`) | [PR #1](https://github.com/zenkovski/rag-demo/pull/1), větev `incident/rozbite-razeni` |
| CI na rozbité změně: **červená** | [run 37971647801](https://github.com/zenkovski/rag-demo/actions/runs/37971647801) |
| Oprava (commit `9a6afce`) | stejná větev |
| CI po opravě: **zelená** | [run 37971901553](https://github.com/zenkovski/rag-demo/actions/runs/37971901553) |

## Symptom

Změna v `rag.search()` vypadala jako úklid: pořadí z RRF má přednost a vybrané úseky se jen „doplní“. CI ukázala:

| Brána | Výsledek |
|---|---|
| lint (ruff) | **zelená** |
| typy (mypy) | **zelená** |
| testy (112) | **zelená** |
| **quality gate** | **červená** |

Žádná výjimka, žádný pád, odpovědi pořád vypadaly rozumně. Systém jen odpovídal horší.

## Detekce a diagnóza

Quality gate porovnal pořadí správného úseku **po otázkách** s `results/baseline.json` a vypsal 23 otázek:

```
REGRESE:
  - otázka 10: správný úsek byl v 5 úsecích pro model a teď tam není (pořadí 2 -> None)
  - otázka 12: správný úsek byl v 5 úsecích pro model a teď tam není (pořadí 1 -> None)
  - otázka 15: správný úsek klesl z pořadí 1 na 3
  - otázka 19: správný úsek klesl z pořadí 1 na 4
  …
  - all: v3 recall@5 0.9866 -> 0.8616
  - all: v3 mrr 0.9643 -> 0.7006
```

Z výpisu se dala vyvodit příčina, než se otevřel jediný soubor:

1. **Skoro všechny otázky klesaly z 1. místa.** Chyba se tedy netýká toho, jestli se správný úsek najde, ale **jak se seřadí**.
2. **Gate neskončil hláškou „nelze přehrát“** (viz [ADR-001](../decisions/ADR-001-offline-quality-gate.md)). Kandidáti pro výběr LLM zůstali stejní, protože uložené odpovědi modelu seděly. Tím se vyloučilo hledání (BM25, RRF, embeddingy) a zbylo to, co se děje **po výběru**.
3. **Šest otázek vypadlo z pěti úseků úplně**, ostatní jen klesly. To odpovídá tomu, že se výběr LLM přestal respektovat a prvních pět se bere z pořadí RRF.
4. Mezi vypadlými je **otázka 10** (odpočinek mezi směnami) z [incidentu 6. 10.](2026-10-06-regrese-odpocinek.md): znovu se ztratil základní odstavec, tentokrát jiným mechanismem.

## Příčina

```diff
-        order = [(i, 0.0) for i in picked] + [(i, s) for i, s in fused if i not in picked]
+        order = fused + [(i, 0.0) for i in picked if i not in dict(fused)]   # „zjednodušení“
```

Původní řádek dává **vybrané úseky první a zbytek doplní z RRF**. „Zjednodušená“ verze dá první RRF a vybrané se přidají za něj (a většinou tam už jsou, protože je mezi kandidáty). Výběr LLM tak přestal ovlivňovat, co model dostane.

## Proč to unit testy nezachytily

112 testů zkoumá **jednotlivé části** (RRF, BM25, `parse_pick`, odstavec 1, odkazy…), ne jejich **složení** do finálního pořadí. Všechny části byly správně; špatné bylo jejich spojení. K tomu je potřeba kontrola celku proti něčemu, co víme, že je správně: u quality gate jsou to pořadí z měření.

## Oprava a důkaz

Vráceno beze zbytku (`git revert`). CI po opravě je zelená ve všech třech branách a `v3 recall@5 0.9866 / mrr 0.9643` je zase přesně baseline.

## Co se z toho stalo trvalé

1. **Nový unit test** `tests/test_search_order.py::test_final_order_puts_llm_picks_first`: falešný model vybere 3. a 1. kandidáta, první pro model musí být 3. Ověřeno: **na rozbité verzi selže, na opravené projde.** Chyba se tak příště zachytí už mezi unit testy za sekundy.
2. Quality gate zůstává jako druhá síť pro chyby, které nikdo předem nenapadne.

## Co tato ukázka NEdokazuje

- Že gate zachytí **každou** regresi. Hlídá kód hledání a řazení nad uloženými odpověďmi modelu; **horší prompt nebo jiný model nezachytí** (to je živé měření, ruční a placené).
- Že by tuhle chybu AI asistent neudělala sám. Naopak: je to přesně ten typ „vypadá to jako úklid“ změny, kterou umí napsat i nesledovaný asistent.
