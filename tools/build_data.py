# -*- coding: utf-8 -*-
"""Předpočítá vše pro web -> site/data.json (úseky, hrany grafu, odpovědi v2, výsledky měření v1 i v2).
Spuštění (až po tools/evaluate.py, --holdout a --retrieval):  .venv/Scripts/python tools/build_data.py"""
import json
import numpy as np
import rag
import evaluate as E

ROOT = rag.ROOT

# 10 ukázkových otázek navíc (mimo obě testovací sady)
DEMO = [
    "Musí mi zaměstnavatel dát výpověď písemně?",
    "Kolik hodin týdně je normální pracovní doba?",
    "Může mi šéf určit dovolenou, kdy se mu to hodí?",
    "Může mi zaměstnavatel krátit dovolenou?",
    "Jak dlouhá je zkušební doba u vedoucího zaměstnance?",
    "Jak skončí pracovní poměr, když se se šéfem dohodneme?",
    "Kdy mi musí zaměstnavatel vyplatit odstupné?",
    "Kdy může zaměstnavatel okamžitě zrušit pracovní poměr?",
    "Musím mít na DPP písemný rozvrh směn?",
    "Může mi zaměstnavatel dát výpověď, když jsem nemocný?",
]

# ruční kontrola ukázkových odpovědí v2 (nejsou v testovacích sadách, ale na webu je vidět i tohle)
DEMO_REVIEW = {
    "Může mi zaměstnavatel dát výpověď, když jsem nemocný?":
        (False, "Řekl „nevím“, i když odpověď v zákoně je: § 53 odst. 1 (ochranná doba) se mezi 5 nalezených úseků nedostal. Bezpečné, ale neužitečné. V jedné dřívější verzi v2 se § 53 našel, ale závěr byl zase moc silný (§ 54 má výjimky)."),
}

def edges(vecs, chunks, k=2):
    """Hrany grafu: sousední odstavce téhož § + k nejpodobnějších úseků (podle embeddingů)."""
    out = set()
    for a in range(len(chunks) - 1):
        if chunks[a]["para"] == chunks[a + 1]["para"]:
            out.add((a, a + 1))
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, -1)
    for a in range(len(chunks)):
        for b in np.argsort(-sims[a])[:k]:
            out.add((min(a, int(b)), max(a, int(b))))
    return sorted(out)

def main():
    meta = json.loads((ROOT / "data" / "chunks.json").read_text(encoding="utf-8"))
    chunks = meta["chunks"]
    ids = {c["id"]: n for n, c in enumerate(chunks)}
    v2, v1 = E.load("eval.json"), E.load("eval_v1.json")
    m2, m1 = E.load("manual_review.json"), E.load("manual_review_v1.json")
    s2, s1 = E.summarize(v2, m2), E.summarize(v1, m1)
    ho, mh = E.load("eval_holdout.json"), E.load("manual_review_holdout.json")
    rc = E.load("retrieval_compare.json")
    v1rows = {r["id"]: r for r in v1["rows"]}

    def test_q(r, set_name, manual, v1_ok=None, v1_answer=None):
        m = manual.get(str(r["id"]), {})
        top = [t["id"] if isinstance(t, dict) else t for t in r["top"]]
        hits, _, trace = rag.search(r["q"], trace=True)   # stejné pořadí jako při měření (přepis je v cache)
        assert [chunks[i]["id"] for i, _ in hits] == top, r["id"]
        return {"q": r["q"], "answer": r["answer"], "rewritten": r.get("rewritten"),
                "hits": [[i, round(s, 3)] for i, s in hits], "trace": trace,
                "test": {"set": set_name, "id": r["id"], "level": r["level"], "gold": r["gold"],
                         "gold_chunks": r["chunks"], "hit3": r["hit3"],
                         "correct": m.get("correct", r["judge"]["correct"]), "judge": r["judge"]["correct"],
                         "note": m.get("note") or r["judge"]["reason"], "v1_correct": v1_ok, "v1_answer": v1_answer}}

    questions = [test_q(r, "test", m2, s1["final"][r["id"]], v1rows[r["id"]]["answer"]) for r in v2["rows"]]
    h1 = {r["id"]: r for r in ho["v1"]}
    for r in ho["v2"]:
        ok1 = mh.get("v1", {}).get(str(r["id"]), {}).get("correct", h1[r["id"]]["judge"]["correct"])
        questions.append(test_q(r, "holdout", mh.get("v2", {}), ok1, h1[r["id"]]["answer"]))
    for q in DEMO:
        hits, rw, trace = rag.search(q, trace=True)
        text, _ = rag.answer(q, hits, chunks)
        ok, note = DEMO_REVIEW.get(q, (True, "Ručně ověřeno proti textu zákona."))
        questions.append({"q": q, "answer": text, "rewritten": rw, "hits": [[i, round(s, 3)] for i, s in hits],
                          "trace": trace, "test": None, "review": {"ok": ok, "note": note}})
        print("demo", q, flush=True)

    def hold(name):
        rows, man = ho[name], mh.get(name, {})
        return {"correct": sum(man.get(str(r["id"]), {}).get("correct", r["judge"]["correct"]) for r in rows),
                "n": len(rows), "hit5": sum(r["hit5"] for r in rows if r["chunks"]),
                "n_answerable": sum(1 for r in rows if r["chunks"])}
    strip = lambda s: {k: v for k, v in s.items() if k != "final"}
    data = {"source": meta["source"], "version": meta["version"], "downloaded": meta["downloaded"],
            "llm": rag.LLM_MODEL, "llm_v1": E.V1["model"], "embeddings": rag.EMB_MODEL, "top_k": rag.TOP_K,
            "v1": strip(s1), "v2": strip(s2), "holdout": {"v1": hold("v1"), "v2": hold("v2")},
            "retrieval": {m: {"hit3": rc[m]["hit3"], "hit5": rc[m]["hit5"], "n": rc[m]["n"]} for m in rag.MODES},
            "cost_usd": v2.get("cost_usd_new_calls"),
            "chunks": [{k: c[k] for k in ("id", "title", "topic", "text")} for c in chunks],
            "edges": edges(rag.index(), chunks), "questions": questions}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # data pro živou funkci (site/api/ask.js): texty úseků, jejich vektory a prompty; žádná tajemství
    import base64
    vecs = rag.index().astype("<f4")
    live = {"emb_model": rag.EMB_MODEL, "llm": rag.LLM_MODEL, "top_k": rag.TOP_K, "dim": int(vecs.shape[1]),
            "system": rag.SYSTEM, "rewrite": rag.REWRITE, "stop": sorted(rag.STOP),
            "chunks": [{"id": c["id"], "title": c["title"], "text": c["text"]} for c in chunks],
            "vectors": base64.b64encode(vecs.tobytes()).decode()}
    (ROOT / "site" / "api").mkdir(exist_ok=True)
    (ROOT / "site" / "api" / "_index.json").write_text(json.dumps(live, ensure_ascii=False), encoding="utf-8")
    print(f"site/data.json: {len(chunks)} úseků, {len(data['edges'])} hran, {len(questions)} otázek")
    print("v1", strip(s1)); print("v2", strip(s2)); print("holdout", data["holdout"])

if __name__ == "__main__":
    main()
