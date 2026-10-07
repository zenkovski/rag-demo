# -*- coding: utf-8 -*-
"""Výběr 5 z 20 kandidátů: LLM (v3) proti lokálnímu cross-encoderu, plus metriky hledání po krocích.
Nic neplatí: přepisy, výběry LLM i embeddingy jsou v cache. Bez klíče v prostředí každé nové volání API spadne,
takže se nic nezaplatí omylem.
  OPENROUTER_API_KEY= .venv/Scripts/python tools/rerank_compare.py   -> data/rerank_compare.json
Cross-encoder: BAAI/bge-reranker-v2-m3 (vícejazyčný, ~2,3 GB, běží lokálně na CPU)."""
import json, os, time
import numpy as np
import rag
from evaluate import tests

CE_MODEL = "BAAI/bge-reranker-v2-m3"


def rank_of(gold, ids):
    """Pořadí prvního správného úseku (1 = první), None když chybí."""
    return next((n for n, i in enumerate(ids, 1) if i in gold), None)


def summary(ranks, n):
    found = [r for r in ranks if r is not None and r <= n]
    return {"hit": len(found), "of": len(ranks), "mrr": round(sum(1 / r for r in found) / len(ranks), 3)}


def main():
    assert not os.environ.get("OPENROUTER_API_KEY"), "spusť s prázdným OPENROUTER_API_KEY (jen z cache)"
    from sentence_transformers import CrossEncoder
    chunks = rag.load_chunks()
    ID = {c["id"]: n for n, c in enumerate(chunks)}
    ce = CrossEncoder(CE_MODEL, max_length=512)
    qs = [t for t in tests() if t["chunks"]]
    rows, ce_time = [], []
    for t in qs:
        gold = {ID[g] for g in t["chunks"]}
        hits, rewritten, steps = rag.search(t["q"], trace=True)
        cands = [i for i, _ in steps["fused"]]
        t0 = time.perf_counter()
        scores = ce.predict([(f"{t['q']} {rewritten}", f"{chunks[i]['id']} {chunks[i]['title']}. {chunks[i]['text']}") for i in cands])
        ce_time.append(time.perf_counter() - t0)
        ce_pick = [cands[j] for j in np.argsort(-scores, kind="stable")[:rag.TOP_K]]
        # stejná pevná pravidla jako u LLM, ať se srovnává jen výběr
        ce_final = rag.with_refs(rag.with_odst1(ce_pick, cands))
        rows.append({"id": t["id"], "set": t["set"],
                     "rrf20": rank_of(gold, cands), "rrf5": rank_of(gold, cands[:rag.TOP_K]),
                     "llm": rank_of(gold, [i for i, _ in hits]), "ce": rank_of(gold, ce_final)})
    out = {
        "n": len(rows),
        "kandidati_20": summary([r["rrf20"] for r in rows], 20),
        "rrf_top5": summary([r["rrf5"] for r in rows], 5),
        "llm_vyber_5": summary([r["llm"] for r in rows], 5),
        "cross_encoder_5": summary([r["ce"] for r in rows], 5),
        "cross_encoder_s_na_otazku_cpu": round(float(np.median(ce_time)), 2),
        "chyby_cross_encoder": [r["id"] for r in rows if not r["ce"]],
        "chyby_llm": [r["id"] for r in rows if not r["llm"]],
        "rows": rows,
    }
    (rag.ROOT / "data" / "rerank_compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
