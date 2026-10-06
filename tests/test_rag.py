# -*- coding: utf-8 -*-
"""Testy bez API: nic nestojí, běží za pár sekund. Spuštění: python -m pytest tests"""
import json, shutil, subprocess, sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import rag  # noqa: E402

CHUNKS = rag.load_chunks()
ID = {c["id"]: n for n, c in enumerate(CHUNKS)}


# ---------- data ----------
def test_chunks_unique_and_bounded():
    assert len(CHUNKS) == 2475
    assert len(ID) == len(CHUNKS), "ID úseků se nesmí opakovat"
    assert max(len(c["text"]) for c in CHUNKS) <= 6100, "úsek je moc dlouhý (strop 6 000 znaků)"


def test_gold_chunks_exist():
    """Každý správný úsek v testovacích sadách musí v datech opravdu být (jinak je měření hledání špatně)."""
    for f in sorted((ROOT / "data").glob("testset*.json")):
        for q in json.loads(f.read_text(encoding="utf-8")):
            for g in q["chunks"]:
                assert g in ID, f"{f.name} #{q['id']}: {g} v datech není"


# ---------- BM25 ----------
def test_tokens_strip_diacritics_and_stem():
    assert rag.tokens("Výplata mzdy, můžu odejít?") == ["vypla", "mzdy", "odeji"]


def test_tokens_drop_stopwords_and_short_words():
    assert rag.tokens("a je to v práci") == ["praci"]


def test_bm25_finds_exact_term():
    best = rag.top(rag.bm25_scores("odstupné"), 5)
    assert any("odstupn" in CHUNKS[i]["text"].lower() for i in best)


# ---------- spojení a výběr ----------
def test_rrf_prefers_agreement():
    # úsek 7 je druhý ve dvou pořadích, úsek 1 první jen v jednom -> vyhraje 7
    assert rag.rrf([[1, 7], [9, 7]])[0][0] == 7


def test_top_skips_zero_scores_and_is_stable():
    assert rag.top(np.array([0.0, 2.0, 1.0, 2.0])) == [1, 3, 2]


def test_parse_pick_ignores_invalid_and_duplicates():
    assert rag.parse_pick("3, 1, 3, 99, 0", 20) == [2, 0]
    assert len(rag.parse_pick("1 2 3 4 5 6 7", 20)) == rag.TOP_K


def test_with_odst1_adds_base_rule():
    """Výběr vzal výjimku (§ 90 odst. 2), pravidlo přidá základ (odst. 1) hned za ni."""
    assert rag.with_odst1([ID["ZP § 90 odst. 2"]], []) == [ID["ZP § 90 odst. 2"], ID["ZP § 90 odst. 1"]]


def test_with_refs_follows_reference():
    """§ 192 odst. 1 říká „ve výši podle odstavce 2“ -> dohledá odstavec 2, kde je číslo 60 %."""
    hits = rag.with_refs([ID["ZP § 192 odst. 1"]])
    assert ID["ZP § 192 odst. 2"] in hits and len(hits) <= rag.TOP_K


# ---------- vektory ----------
def test_quantize_roundtrip():
    rng = np.random.default_rng(0)
    v = rng.normal(size=(50, 1024)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    q, scale = rag.quantize(v)
    back = rag.dequantize(q, scale)
    assert q.dtype == np.int8
    assert np.allclose(np.linalg.norm(back, axis=1), 1, atol=1e-5)
    assert (np.sum(back * v, axis=1) > 0.999).all(), "int8 nesmí změnit směr vektoru"


# ---------- odpověď ----------
def test_note_marks_wage_vs_salary():
    para = lambda law, p: {"law": law, "para": p}
    assert "mzdu" in rag.note(para("ZP", "115"))
    assert "plat" in rag.note(para("ZP", "125"))
    assert rag.note(para("ZNP", "115")) == ""


def test_cited_numbers():
    assert rag.cited("Ano [1]. Lhůta je 15 dnů [3][1].") == [1, 3]


# ---------- web = Python ----------
@pytest.mark.skipif(not shutil.which("node"), reason="chybí Node.js")
def test_web_matches_python():
    """Webová funkce (JavaScript) musí hledat stejně jako Python, na kterém se měří."""
    texts = ["Zaměstnavatel nevyplatil zaměstnanci mzdu", "výpověď ve zkušební době", "dovolená na zotavenou"]
    cases = {"texts": texts, "rankings": [[1, 7, 3], [9, 7, 1], [3, 2]], "pick": "4, 2, 2, 30, 1",
             "picked": [ID["ZP § 90 odst. 2"]], "hits": [ID["ZP § 192 odst. 1"], ID["ZP § 56 odst. 1"]]}
    js = json.loads(subprocess.run(["node", str(ROOT / "tests" / "js_core.cjs")], input=json.dumps(cases),
                                   capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    assert js["tokens"] == [rag.tokens(t) for t in texts]
    assert js["bm25"] == [rag.top(rag.bm25_scores(t), 10) for t in texts]
    assert js["rrf"] == [i for i, _ in rag.rrf(cases["rankings"])]
    assert js["pick"] == rag.parse_pick(cases["pick"], 20)
    assert js["odst1"] == rag.with_odst1(cases["picked"], [])
    assert js["refs"] == rag.with_refs(cases["hits"])
