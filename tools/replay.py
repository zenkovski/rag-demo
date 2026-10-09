# -*- coding: utf-8 -*-
"""Přehraje hledání nad uloženými výsledky (embeddingy a odpovědi LLM jsou v data/*cache*), takže běh je offline,
stojí 0 $ a dá pokaždé stejné pořadí. Vrací pořadí úseků pro každý „systém“ (způsob hledání) a každou otázku.

Co to dokazuje a co ne: že KÓD hledání (BM25, RRF, pravidla odstavce 1 a odkazů) dává stejné pořadí jako při měření.
Neříká nic o tom, jak by dopadly NOVÉ otázky nebo nové odpovědi modelu: ty cache nezná.
"""
from __future__ import annotations

import time

import numpy as np

import rag

DEPTH = 50
SYSTEMS = {
    "dense_base":        "e5-base (lokálně), jen význam otázky",
    "dense_large":       "e5-large, jen význam otázky",
    "bm25_raw":          "BM25 nad laickou otázkou",
    "bm25_rewrite":      "BM25 nad přepsanou otázkou",
    "rrf_dense_bm25":    "RRF: e5-large + BM25 nad laickou otázkou (bez přepisu)",
    "rrf_dense_rewrite": "RRF: e5-large nad otázkou a přepisem (bez BM25)",
    "rrf_v2":            "RRF: e5-large nad otázkou i přepisem + BM25 nad přepisem (v2)",
    "weighted_v2":       "vážený součet skóre (min-max) místo RRF, váhy z dev sad",
    "v3_llm_rerank":     "v2 + LLM vybere 5 z 20, odstavec 1 a odkazy (v3 = finální)",
}


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x)


def components(q: str, allow=None) -> dict:
    """Jednotlivá skóre pro otázku: význam (původní i přepsaná), slova, přepis. Vše z cache."""
    mask = rag.allow_mask(allow)
    m = 1 if mask is None else mask
    rewritten = rag.rewrite(q, reasoning=False)
    return {
        "rewritten": rewritten,
        "d_q": rag.dense_scores(q) * m,
        "d_rw": rag.dense_scores(rewritten) * m,
        "b_raw": rag.bm25_scores(q) * m,
        "b_rw": rag.bm25_scores(rewritten) * m,
    }


def weighted(c: dict, w_bm25: float) -> list[int]:
    """Vážený součet normalizovaných skóre: (1 - w) * průměr významů + w * BM25."""
    dense = 0.5 * _minmax(c["d_q"]) + 0.5 * _minmax(c["d_rw"])
    return rag.top((1 - w_bm25) * dense + w_bm25 * _minmax(c["b_rw"]), DEPTH)


def rankings_for(q: str, w_bm25: float, rrf_k: int = 60, with_base: bool = True, allow=None) -> dict[str, list[int]]:
    """Pořadí (indexy úseků) pro každý systém. v3 = skutečný rag.search (včetně výběru LLM z cache)."""
    c = components(q, allow)
    t = lambda s: rag.top(s, DEPTH)
    out = {
        "dense_large": t(c["d_q"]),
        "bm25_raw": t(c["b_raw"]),
        "bm25_rewrite": t(c["b_rw"]),
        "rrf_dense_bm25": [i for i, _ in rag.rrf([t(c["d_q"]), t(c["b_raw"])], rrf_k)][:DEPTH],
        "rrf_dense_rewrite": [i for i, _ in rag.rrf([t(c["d_q"]), t(c["d_rw"])], rrf_k)][:DEPTH],
        "rrf_v2": [i for i, _ in rag.rrf([t(c["d_q"]), t(c["d_rw"]), t(c["b_rw"])], rrf_k)][:DEPTH],
        "weighted_v2": weighted(c, w_bm25),
    }
    try:
        hits, _ = rag.search(q, mode="hybrid_rerank", allow=allow)
        out["v3_llm_rerank"] = [i for i, _ in hits]                  # jen 5 úseků: tolik dostane model
    except rag.OfflineCacheMiss as e:                                # kód změnil kandidáty: uložená odpověď modelu se nehodí
        out["_cache_miss"] = str(e)
    if with_base:
        try:
            d = rag.dense_scores(q, "base")
            out["dense_base"] = t(d * (1 if allow is None else rag.allow_mask(allow)))
        except Exception:                                            # bez torch / sentence-transformers / modelu
            pass
    return out


def stage_trace(q: str, allow=None) -> dict:
    """Mezivýsledky pro diagnostiku: co našel význam, co slova, co spojení, co vybral LLM, co dostal model."""
    hits, rewritten, steps = rag.search(q, mode="hybrid_rerank", trace=True, allow=allow)
    return {"rewritten": rewritten, "steps": steps, "final": [i for i, _ in hits]}


def retrieval_latency(queries: list[str], repeat: int = 5) -> dict:
    """Čas samotného výpočtu hledání (matice × vektor, BM25, RRF) po načtení cache. Bez volání API.
    Skutečná odezva služby je v řádu sekund a skládá se hlavně z volání LLM, které se tu nepočítá."""
    comps = [components(q) for q in queries]            # přepis i embeddingy z cache, sem se nezapočítávají
    times = []
    for _ in range(repeat):
        for c in comps:
            t0 = time.perf_counter()
            r = [rag.top(c["d_q"]), rag.top(c["d_rw"]), rag.top(rag.bm25_scores(c["rewritten"]))]
            rag.rrf(r)
            times.append((time.perf_counter() - t0) * 1000)
    a = np.array(times)
    return {"calls": len(a), "p50_ms": round(float(np.percentile(a, 50)), 2), "p95_ms": round(float(np.percentile(a, 95)), 2),
            "max_ms": round(float(a.max()), 2)}
