# -*- coding: utf-8 -*-
"""Krok 6: předpočítá vše pro web -> site/data.json (úseky, hrany grafu, odpovědi, výsledky měření).
Spuštění (až po tools/evaluate.py):  .venv/Scripts/python tools/build_data.py"""
import json
import numpy as np
import rag

ROOT = rag.ROOT

# 10 ukázkových otázek navíc (mimo testovací sadu)
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

# ruční kontrola ukázkových odpovědí (nejsou v testovací sadě, ale na webu je vidět i tohle)
DEMO_REVIEW = {
    "Může mi zaměstnavatel dát výpověď, když jsem nemocný?":
        (False, "Zavádějící. Vyhledávání nenašlo § 53 odst. 1, který výpověď během pracovní neschopnosti zakazuje (ochranná doba). Model pak odpověděl na jinou otázku: výpověď kvůli dlouhodobé ztrátě zdravotní způsobilosti."),
}

def edges(vecs, chunks, k=2, min_sim=0.84):
    """Hrany grafu: sousední odstavce téhož § + k nejpodobnějších úseků (podle embeddingů)."""
    out = set()
    for a in range(len(chunks) - 1):
        if chunks[a]["para"] == chunks[a + 1]["para"]:
            out.add((a, a + 1))
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, -1)
    for a in range(len(chunks)):
        for b in np.argsort(-sims[a])[:k]:
            if sims[a, b] >= min_sim:
                out.add((min(a, int(b)), max(a, int(b))))
    return sorted(out)

def main():
    meta = json.loads((ROOT / "data" / "chunks.json").read_text(encoding="utf-8"))
    chunks = meta["chunks"]
    vecs = rag.index()
    ev = json.loads((ROOT / "data" / "eval.json").read_text(encoding="utf-8"))
    mp = ROOT / "data" / "manual_review.json"
    manual = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    ids = {c["id"]: n for n, c in enumerate(chunks)}

    questions = []
    for r in ev["rows"]:                                   # testovací otázky (s hodnocením)
        m = manual.get(str(r["id"]), {})
        questions.append({"q": r["q"], "answer": r["answer"], "hits": [[ids[t["id"]], t["score"]] for t in r["top"]],
                          "test": {"id": r["id"], "level": r["level"], "gold": r["gold"], "gold_chunks": r["chunks"],
                                   "hit3": r["hit3"], "correct": m.get("correct", r["judge"]["correct"]),
                                   "judge": r["judge"]["correct"], "note": m.get("note") or r["judge"]["reason"]}})
    for q in DEMO:                                         # ukázkové otázky
        hits = rag.search(q)
        text, _ = rag.answer(q, hits, chunks)
        ok, note = DEMO_REVIEW.get(q, (True, "Ručně ověřeno proti textu zákona."))
        questions.append({"q": q, "answer": text, "hits": [[i, round(s, 3)] for i, s in hits], "test": None,
                          "review": {"ok": ok, "note": note}})
        print("ok", q, flush=True)

    rows = ev["rows"]
    ans = [r for r in rows if r["chunks"]]
    final = [q["test"]["correct"] for q in questions if q["test"]]
    summary = {"n": len(rows), "correct": sum(final), "hit3": sum(r["hit3"] for r in ans), "n_answerable": len(ans),
               "nevim_ok": sum(r["said_nevim"] for r in rows if not r["chunks"]), "n_unanswerable": len(rows) - len(ans),
               "judge_agree": sum(q["test"]["correct"] == q["test"]["judge"] for q in questions if q["test"])}
    data = {"source": meta["source"], "version": meta["version"], "downloaded": meta["downloaded"],
            "llm": rag.LLM_MODEL, "embeddings": rag.EMB_MODEL, "top_k": rag.TOP_K, "summary": summary,
            "chunks": [{k: c[k] for k in ("id", "title", "topic", "text")} for c in chunks],
            "edges": edges(vecs, chunks), "questions": questions}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"site/data.json: {len(chunks)} úseků, {len(data['edges'])} hran, {len(questions)} otázek, {summary}")

if __name__ == "__main__":
    main()
