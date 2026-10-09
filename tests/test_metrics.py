# -*- coding: utf-8 -*-
"""Testy metrik na ručně spočítaných příkladech. Bez sítě."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import metrics as m  # noqa: E402

R = ["a", "b", "c", "d", "e", "f"]


def test_recall_single_and_multi_gold():
    assert m.recall_at_k(R, ["c"], 3) == 1.0
    assert m.recall_at_k(R, ["c"], 2) == 0.0
    assert m.recall_at_k(R, ["a", "f"], 3) == 0.5          # jeden ze dvou správných úseků je v top 3
    assert m.recall_at_k(R, ["a", "f"], 6) == 1.0


def test_recall_without_gold_is_an_error():
    with pytest.raises(ValueError):
        m.recall_at_k(R, [], 5)


def test_reciprocal_rank():
    assert m.reciprocal_rank(R, ["a"]) == 1.0
    assert m.reciprocal_rank(R, ["c"]) == pytest.approx(1 / 3)
    assert m.reciprocal_rank(R, ["x"]) == 0.0
    assert m.reciprocal_rank(R, ["d", "b"]) == 0.5          # počítá se první správný


def test_ndcg_perfect_and_worse():
    assert m.ndcg_at_k(R, ["a"], 5) == 1.0
    assert m.ndcg_at_k(R, ["c"], 5) == pytest.approx(1 / math.log2(4))
    assert m.ndcg_at_k(R, ["a", "b"], 5) == 1.0              # oba správné nahoře = ideál
    assert m.ndcg_at_k(R, ["x"], 5) == 0.0


def test_ndcg_ignores_results_after_k():
    assert m.ndcg_at_k(R, ["f"], 5) == 0.0


def test_first_gold_rank():
    assert m.first_gold_rank(R, ["c", "e"]) == 3
    assert m.first_gold_rank(R, ["z"]) is None


def test_bootstrap_ci_is_reproducible_and_brackets_mean():
    vals = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    a = m.bootstrap_ci(vals, seed=1)
    assert a == m.bootstrap_ci(vals, seed=1)                 # stejný seed = stejné číslo
    mean, lo, hi = a
    assert mean == pytest.approx(0.7) and lo <= mean <= hi and 0 <= lo and hi <= 1


def test_bootstrap_ci_of_constant_is_a_point():
    assert m.bootstrap_ci([1] * 20)[1:] == (1.0, 1.0)


def test_wilson_ten_of_ten_is_not_certainty():
    p, lo, hi = m.wilson_interval(10, 10)
    assert p == 1.0 and 0.70 < lo < 0.74 and hi == 1.0       # 10 z 10 ještě neznamená „vždy“


def test_sign_test_known_values():
    # A vyhrál 5×, B 0× -> p = 2 * 1/32 = 0,0625
    r = m.sign_test([1] * 5, [0] * 5)
    assert (r["a_better"], r["b_better"], r["ties"]) == (5, 0, 0) and r["p"] == pytest.approx(0.0625)
    assert m.sign_test([1, 0], [0, 1])["p"] == 1.0           # 1:1 = žádný rozdíl
    assert m.sign_test([1, 1], [1, 1])["p"] == 1.0           # samé remízy


def test_sign_test_needs_many_wins_for_significance():
    assert m.sign_test([1] * 10, [0] * 10)["p"] < 0.05
    assert m.sign_test([1] * 4 + [0], [0] * 4 + [1])["p"] > 0.05


def test_summarize_shapes():
    rk = {1: R, 2: ["x", "a", "b"]}
    gd = {1: ["a"], 2: ["a"], 3: []}                         # otázka 3 nemá odpověď a nepočítá se
    s = m.summarize(rk, gd, ks=(1, 3))
    assert s["n"] == 2 and s["metrics"]["recall@1"]["mean"] == 0.5 and s["metrics"]["recall@3"]["mean"] == 1.0
    assert s["metrics"]["mrr"]["mean"] == pytest.approx(0.75)
