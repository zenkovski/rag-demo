# -*- coding: utf-8 -*-
"""Pořadí úseků pro model: co vybere LLM, jde první. Přidáno po incidentu 2026-10-09 (docs/incidents/2026-10-09-rozbite-razeni.md):
„zjednodušení“ řazení ve search() dalo přednost pořadí z RRF a lint, typy i všechny dosavadní testy zůstaly zelené."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import datasets  # noqa: E402
import rag  # noqa: E402

Q = next(q for q in datasets.questions() if q["id"] == 4)["q"]          # otázka, jejíž embedding je v cache


class PickThirdThenFirst:
    """Falešný model: přepis = otázka beze změny, výběr = 3. a 1. kandidát."""
    def __call__(self, system, user, model=None, reasoning=True):
        if system == rag.RERANK:
            return "3, 1", {}
        return user, {}


def test_final_order_puts_llm_picks_first(monkeypatch):
    monkeypatch.setattr(rag, "llm", PickThirdThenFirst())
    hits, _, steps = rag.search(Q, mode="hybrid_rerank", trace=True)
    cands = [i for i, _ in steps["fused"]]
    assert hits[0][0] == cands[2], "první má být to, co vybral LLM (3. kandidát), ne 1. z RRF"
    assert cands[0] in [i for i, _ in hits], "zbytek se doplní z pořadí RRF"
    assert len(hits) == rag.TOP_K
