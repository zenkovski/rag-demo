# -*- coding: utf-8 -*-
"""Kde v řetězci se odpověď pokazila. Každé selhání dostane kategorii podle toho, KTERÝ krok selhal:

  A  nenalezeno      správný úsek není ani mezi 20 kandidáty (chyba hledání: embeddingy, BM25, přepis, spojení)
  B  vyřazeno        správný úsek mezi kandidáty byl, ale do 5 úseků pro model se nedostal (chyba výběru / ořezu)
  C  špatně přečteno model správný úsek dostal, ale odpověděl špatně (chyba čtení: prompt, model, mzda × plat)
  D  bez opory       odpověď obsahuje tvrzení, které soudce nebo kontrola čísel nepodporuje (i když může být výsledek správně)
  E  měl odmítnout   v zákoně odpověď není a systém přesto odpověděl (halucinace)
  F  zbytečné „nevím“ odpověď v zákoně byla a systém odmítl

Kategorie A/B/C se vylučují, D se může přidat ke kterékoli, E a F jsou o odmítnutí. Rozdíl A × B × C určuje, KDE opravovat:
lepší prompt nespraví hledání a lepší hledání nespraví čtení.
"""
from __future__ import annotations

CATEGORIES = {
    "A": "relevantní úsek nebyl nalezen (hledání)",
    "B": "úsek byl nalezen, ale vyřazen před odpovědí (výběr)",
    "C": "správný kontext dodán, model ho špatně použil (čtení)",
    "D": "tvrzení bez dostatečné opory v úsecích",
    "E": "měl odmítnout odpovědět a neodmítl",
    "F": "odmítl, i když odpověď v zákoně byla",
}


def classify(*, answerable: bool, correct: bool, said_nevim: bool, gold_in_final: bool, gold_in_candidates: bool,
             grounded: bool = True, unsupported_numbers: bool = False) -> list[str]:
    """Vrací seznam kategorií (prázdný = bez nálezu)."""
    out: list[str] = []
    if not answerable:
        if not said_nevim:
            out.append("E")
    else:
        if said_nevim:
            out.append("F")
        if not gold_in_final:
            out.append("A" if not gold_in_candidates else "B")
        elif not correct and not said_nevim:
            out.append("C")
    if not said_nevim and (not grounded or unsupported_numbers) and not correct:
        out.append("D")                      # D jen u chybných odpovědí; u správných jde o „podezření“, ne o selhání
    return out


def primary(cats: list[str]) -> str:
    """Hlavní příčina pro tabulku: nejdřív kde se řetěz přerušil (A, B, C), pak odmítnutí (E, F), nakonec D."""
    for c in "ABCEFD":
        if c in cats:
            return c
    return "-"
