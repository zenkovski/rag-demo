# -*- coding: utf-8 -*-
"""Metriky hledání a pomocné statistiky. Čistý Python + numpy, bez sítě, každá funkce má test v tests/test_metrics.py.

Co která metrika říká (a co NEříká):
- Recall@k  = jaký podíl správných úseků je mezi prvními k. Neříká nic o pořadí uvnitř k a nic o tom, jestli model odpověděl dobře.
- hit@k     = je mezi prvními k aspoň jeden správný úsek? (starší ukazatel z RESULTS.md; u otázek s jedním správným úsekem = Recall@k)
- MRR       = průměr 1 / pořadí prvního správného úseku. Silně odměňuje 1. místo, o ostatních správných úsecích nic neví.
- nDCG@k    = pořadí s důrazem na horní místa, správné úseky mají stejnou váhu (0/1). Neříká, že úsek stačí k odpovědi.
Všechny metriky měří HLEDÁNÍ. Správnost odpovědi je jiná věc a měří se zvlášť (viz tools/experiments.py, sekce odpovědi).
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


# ---------- hledání ----------
def recall_at_k(ranked: Sequence[str], gold: Sequence[str], k: int) -> float:
    """Podíl správných úseků mezi prvními k. Bez správného úseku (otázka bez odpovědi) se metrika nepočítá."""
    if not gold:
        raise ValueError("otázka bez správného úseku nemá Recall")
    top = set(ranked[:k])
    return sum(g in top for g in gold) / len(gold)


def hit_at_k(ranked: Sequence[str], gold: Sequence[str], k: int) -> float:
    return float(any(g in ranked[:k] for g in gold))


def reciprocal_rank(ranked: Sequence[str], gold: Sequence[str]) -> float:
    for n, x in enumerate(ranked, 1):
        if x in gold:
            return 1.0 / n
    return 0.0


def ndcg_at_k(ranked: Sequence[str], gold: Sequence[str], k: int) -> float:
    """nDCG s binární relevancí: DCG = součet 1 / log2(pořadí + 1) přes správné úseky, děleno ideálním DCG."""
    dcg = sum(1.0 / math.log2(n + 1) for n, x in enumerate(ranked[:k], 1) if x in gold)
    ideal = sum(1.0 / math.log2(n + 1) for n in range(1, min(len(gold), k) + 1))
    return dcg / ideal if ideal else 0.0


def first_gold_rank(ranked: Sequence[str], gold: Sequence[str]) -> int | None:
    """Pořadí prvního správného úseku (1 = první) nebo None, když v seznamu není."""
    for n, x in enumerate(ranked, 1):
        if x in gold:
            return n
    return None


# ---------- nejistota ----------
def bootstrap_ci(values: Sequence[float], n_boot: int = 10_000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float, float]:
    """Průměr a percentilový interval spolehlivosti přes otázky (bootstrap: opakované losování otázek s vracením).
    Interval ukazuje, jak moc by se číslo změnilo s jinou sadou otázek stejného typu. Ne s jiným modelem."""
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    return float(v.mean()), float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Interval spolehlivosti podílu (Wilson). Na rozdíl od „p ± chyba“ funguje i pro 10 z 10: dá zhruba 0,72 až 1,00."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def sign_test(a: Sequence[float], b: Sequence[float]) -> dict:
    """Párový znaménkový test (přesný, oboustranný): na stejných otázkách porovná dva systémy.
    Počítají se jen otázky, kde se systémy liší. Když A vyhrál 5× a B 0×, p = 0,0625: i to je málo na jistotu.
    Test neříká, jak velký rozdíl je, jen jestli je pravděpodobné, že není náhoda."""
    wins = sum(x > y for x, y in zip(a, b))
    losses = sum(x < y for x, y in zip(a, b))
    n = wins + losses
    if n == 0:
        return {"a_better": 0, "b_better": 0, "ties": len(a), "p": 1.0}
    k = min(wins, losses)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"a_better": wins, "b_better": losses, "ties": len(a) - n, "p": p}


# ---------- souhrn jedné sady pořadí ----------
def summarize(rankings: dict[int, Sequence[str]], golds: dict[int, Sequence[str]], ks: Sequence[int] = (1, 3, 5, 10, 20), seed: int = 0) -> dict:
    """rankings[id] = pořadí ID úseků, golds[id] = správné úseky. Vrací průměry s intervaly + hodnoty po otázkách (pro párové testy)."""
    ids = sorted(i for i in golds if golds[i])
    per: dict[str, list[float]] = {}
    for k in ks:
        per[f"recall@{k}"] = [recall_at_k(rankings[i], golds[i], k) for i in ids]
    per["mrr"] = [reciprocal_rank(rankings[i], golds[i]) for i in ids]
    per["ndcg@5"] = [ndcg_at_k(rankings[i], golds[i], 5) for i in ids]
    per["ndcg@10"] = [ndcg_at_k(rankings[i], golds[i], 10) for i in ids]
    metrics: dict[str, dict] = {}
    for name, vals in per.items():
        m, lo, hi = bootstrap_ci(vals, seed=seed)
        metrics[name] = {"mean": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)]}
    return {"n": len(ids), "ids": ids, "metrics": metrics, "per_question": per}
