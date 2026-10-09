# -*- coding: utf-8 -*-
"""Deterministické kontroly odpovědi (bez LLM): proti nim se AI soudce nemůže splést a stojí 0 $.

Kontroluje se jen to, co jde ověřit pravidlem:
1. citace [n] míří na úsek, který model opravdu dostal (není [7], když dostal 5 úseků),
2. odpověď, která není „nevím“, má aspoň jednu citaci,
3. každé číslo v odpovědi (4 týdny, 60 %, 15 dnů) je v textu některého úseku (nebo v otázce).
Co NEkontroluje: jestli tvrzení opravdu vyplývá z úseku (to je úsudek, patří člověku nebo soudci), čísla slovy
(„čtyři týdny“) ani správnost citace u konkrétní věty. Kontrola 3 proto hlásí „podezření“, ne „chyba“.
"""
from __future__ import annotations

import re

NEVIM = "nevím"
CITE = re.compile(r"\[(\d+)\]")
NUM = re.compile(r"(?<![\w§])(\d+(?:[  ]\d{3})*(?:[.,]\d+)?)(?![\w§])")


def is_abstention(answer: str) -> bool:
    return answer.strip().lower().startswith(NEVIM)


def _norm_num(s: str) -> str:
    return re.sub(r"[  ]", "", s).replace(",", ".")


# zákon píše čísla slovy („patnáct dnů“), odpověď číslicemi („15 dnů“): slova se pro porovnání převedou na číslice
_LONG = [("jedenáct", 11), ("dvanáct", 12), ("třináct", 13), ("čtrnáct", 14), ("patnáct", 15), ("šestnáct", 16), ("sedmnáct", 17),
         ("osmnáct", 18), ("devatenáct", 19), ("dvacet", 20), ("třicet", 30), ("čtyřicet", 40), ("padesát", 50), ("šedesát", 60),
         ("sedmdesát", 70), ("osmdesát", 80), ("devadesát", 90)]        # skloňují se příponou: patnáct, patnácti, patnácté…
_SHORT = {"jeden": 1, "jedna": 1, "jedno": 1, "jedné": 1, "jednoho": 1, "dva": 2, "dvě": 2, "dvou": 2, "dvěma": 2,
          "tři": 3, "tří": 3, "třech": 3, "třem": 3, "třemi": 3, "čtyři": 4, "čtyř": 4, "čtyřech": 4, "čtyřem": 4,
          "pět": 5, "pěti": 5, "šest": 6, "šesti": 6, "sedm": 7, "sedmi": 7, "osm": 8, "osmi": 8, "devět": 9, "devíti": 9,
          "deset": 10, "deseti": 10}


def word_numbers(text: str) -> list[str]:
    """Čísla zapsaná slovy do devadesáti (včetně skloňovaných tvarů). Stovky a složeniny („dvacet pět“) se nehledají."""
    out = []
    for w in re.findall(r"[a-zěščřžýáíéúůďťň]+", text.lower()):
        if w in _SHORT:
            out.append(str(_SHORT[w]))
            continue
        for stem, val in _LONG:
            if (w.startswith(stem[:-1]) and len(w) <= len(stem) + 3) or re.match(stem + r"[ií]?(denn|týdenn|měsíčn|hodinov|let)", w):
                out.append(str(val))                       # i složeniny: „patnáctidenní výpovědní doba“
                break
    return out


def numbers(text: str) -> list[str]:
    """Čísla z textu bez čísel citací ([3]) a čísel paragrafů („§ 52“, „odst. 2“)."""
    cleaned = CITE.sub(" ", text)
    cleaned = re.sub(r"§\s*\d+\w*|odst\.\s*\d+|písm\.\s*\w", " ", cleaned)
    return [_norm_num(m.group(1)) for m in NUM.finditer(cleaned)]


def check(answer: str, supplied: list[str], question: str = "") -> dict:
    """supplied = texty úseků v pořadí, v jakém je model dostal ([1] = supplied[0]).
    Vrací {"abstained", "cited", "bad_citations", "no_citation", "unsupported_numbers", "misattributed_numbers", "numbers_in_no_chunk"}."""
    cited = sorted({int(n) for n in CITE.findall(answer)})
    abstained = is_abstention(answer)
    bad = [n for n in cited if not 1 <= n <= len(supplied)]
    pool = " ".join(supplied[n - 1] for n in cited if n not in bad) if cited else " ".join(supplied)
    known = lambda text: set(numbers(text)) | set(word_numbers(text))
    haystack = known(pool) | known(question)
    anywhere = known(" ".join(supplied)) | known(question)
    unsupported = [] if abstained else sorted({n for n in numbers(answer) if n not in haystack})
    # číslo, které je v jiném dodaném úseku než citovaném = špatná citace; číslo, které není v žádném = odvozené (součet, polovina) nebo vymyšlené
    return {"abstained": abstained, "cited": cited, "bad_citations": bad,
            "no_citation": (not abstained) and not cited, "unsupported_numbers": unsupported,
            "misattributed_numbers": [n for n in unsupported if n in anywhere],
            "numbers_in_no_chunk": [n for n in unsupported if n not in anywhere]}
