# -*- coding: utf-8 -*-
"""Vrstva služby (tools/service.py): stejné výsledky jako při měření, kontrola vstupu, chyby, bezpečný zápis cache.
Vše z cache, bez sítě (tests/conftest.py zapíná RAG_OFFLINE=1)."""
import json
import sys
import threading
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import datasets  # noqa: E402
import metrics as M  # noqa: E402
import rag  # noqa: E402
import service  # noqa: E402

BASE = json.loads((ROOT / "results" / "baseline.json").read_text(encoding="utf-8"))["per_question_first_gold_rank"]
QS = {q["id"]: q for q in datasets.questions()}
Q4 = QS[4]["q"]                                                    # „výpovědní doba“: hledání i odpověď jsou v cache
UNANSWERABLE = next(q["q"] for q in QS.values() if not q["chunks"])


# ---------- výsledky se nezměnily ----------
def test_full_search_matches_baseline():
    """mode=full = finální v3: pořadí prvního správného úseku musí být u všech 56 otázek stejné jako v baseline."""
    for qid, expected in BASE["v3_llm_rerank"].items():
        q = QS[int(qid)]
        ids = [p.id for p in service.search(q["q"], k=5, mode="full").passages]
        assert M.first_gold_rank(ids, q["chunks"]) == expected, f"otázka {qid}"


def test_fast_search_matches_baseline():
    """mode=fast = jen e5-large (bez LLM): v top 10 stejné pořadí jako dense_large v baseline."""
    for qid, expected in BASE["dense_large"].items():
        q = QS[int(qid)]
        ids = [p.id for p in service.search(q["q"], k=10, mode="fast").passages]
        assert M.first_gold_rank(ids, q["chunks"]) == (expected if expected is not None and expected <= 10 else None), f"otázka {qid}"


def test_fast_search_needs_no_llm(monkeypatch):
    def no_llm(*a, **kw):
        raise AssertionError("mode=fast nesmí volat jazykový model")
    monkeypatch.setattr(rag, "llm", no_llm)
    r = service.search(Q4, mode="fast")
    assert r.rewritten_query is None and len(r.passages) == 5


# ---------- tvar výstupu ----------
def test_search_result_shape():
    r = service.search(Q4, k=3)
    assert [p.rank for p in r.passages] == [1, 2, 3]
    p = r.passages[0]
    assert p.id.startswith(("ZP §", "ZZ §", "ZNP §", "NV 590 §")) and p.source_url.startswith("https://") and p.text


def test_laws_filter():
    r = service.search(Q4, k=10, laws=["ZZ"])
    assert r.passages and all(p.law == "ZZ" for p in r.passages)


def test_long_passage_is_truncated_and_full_text_in_document():
    chunks = rag.load_chunks()
    long_id = max(chunks, key=lambda c: len(c["text"]))["id"]
    assert len(service.get_document(long_id).text) > service.MAX_PASSAGE_CHARS
    i = next(n for n, c in enumerate(chunks) if c["id"] == long_id)
    p = service._passage(1, i, 0.5)
    assert p.truncated and len(p.text) == service.MAX_PASSAGE_CHARS


def test_ask_sufficient_with_citations():
    a = service.ask(Q4)
    assert a.evidence_status == "sufficient"
    assert a.citations and all(c.id in a.passages_supplied for c in a.citations)
    assert all(f"[{c.marker}]" in a.answer for c in a.citations)


def test_ask_insufficient_when_law_does_not_say():
    a = service.ask(UNANSWERABLE)
    assert a.evidence_status == "insufficient" and a.citations == []
    assert a.answer.startswith("Nevím")


def test_get_document_and_suggestions():
    d = service.get_document("ZP  §  51 odst. 2")                   # mezery navíc nevadí
    assert d.id == "ZP § 51 odst. 2" and d.paragraph == "51" and d.subsection == "2" and d.law_number == "262/2006 Sb."
    with pytest.raises(service.NotFound) as e:
        service.get_document("ZP § 51")
    assert "ZP § 51 odst. 1" in e.value.details["suggestions"]


# ---------- vstup ----------
@pytest.mark.parametrize("kwargs", [
    {"query": ""}, {"query": "ab"}, {"query": "x" * 501}, {"query": Q4, "k": 0}, {"query": Q4, "k": 11},
    {"query": Q4, "mode": "slow"}, {"query": Q4, "laws": ["GDPR"]},
])
def test_search_rejects_bad_input(kwargs):
    with pytest.raises(service.InvalidInput):
        service.search(**kwargs)


# ---------- chyby poskytovatele ----------
def test_cache_miss_offline_is_provider_unavailable():
    with pytest.raises(service.ProviderUnavailable):
        service.search("Otázka, která v cache určitě není: kolik stojí rohlík?", mode="fast")


def test_network_error_is_provider_unavailable(monkeypatch):
    def down(*a, **kw):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(rag, "search", down)
    with pytest.raises(service.ProviderUnavailable):
        service.search(Q4)


def test_slow_provider_is_timeout(monkeypatch):
    monkeypatch.setattr(rag, "search", lambda *a, **kw: time.sleep(1))
    with pytest.raises(service.ProviderTimeout):
        service.search(Q4, timeout=0.05)


# ---------- cache ----------
def test_llm_cache_concurrent_writes_keep_valid_file(tmp_path, monkeypatch):
    """Riziko 1 z auditu: souběžné zápisy nesmí ztratit záznam ani nechat rozbitý JSON."""
    f = tmp_path / "llm_cache.json"
    f.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(rag, "LLM_CACHE", f)
    monkeypatch.setattr(rag, "_llm_cache", None)
    threads = [threading.Thread(target=rag._llm_cache_put, args=(f"k{i}", {"text": str(i), "usage": {}})) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert set(json.loads(f.read_text(encoding="utf-8"))) == {f"k{i}" for i in range(30)}
