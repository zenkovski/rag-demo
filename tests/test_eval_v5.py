# -*- coding: utf-8 -*-
"""Měření v5 (134 otázek) se musí dát přehrát z uložených dat: stejných 5 úseků a stejná odpověď u každé otázky.
Bez sítě: vektory otázek z data/emb_cache_local.npz, odpovědi Clauda z data/llm_cache_claude.json."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import rag  # noqa: E402

STORED = ROOT / "results" / "eval_v5.json"


@pytest.fixture
def patched(monkeypatch):
    """eval_v5.install() přepisuje rag.llm a rag.embed_api; monkeypatch je po testu vrátí."""
    monkeypatch.setattr(rag, "llm", rag.llm)
    monkeypatch.setattr(rag, "embed_api", rag.embed_api)
    import eval_v5
    return eval_v5


@pytest.mark.skipif(not STORED.exists(), reason="results/eval_v5.json chybí")
def test_eval_v5_replays_from_cache(patched):
    stored = {r["id"]: r for r in json.loads(STORED.read_text(encoding="utf-8"))["rows"]}
    rows = patched.results()
    assert len(rows) == len(stored) == 134
    for r in rows:
        s = stored[r["id"]]
        assert r["top5"] == s["top5"], f"otázka {r['id']}: jiné úseky"
        assert r["answer"] == s["answer"], f"otázka {r['id']}: jiná odpověď"
        assert r["fast_top10"] == s["fast_top10"], f"otázka {r['id']}: jiné hledání fast"
