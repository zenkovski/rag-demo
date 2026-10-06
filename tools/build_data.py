# -*- coding: utf-8 -*-
"""Předpočítá vše pro web -> site/data.json (úseky, rozložení mapy, odpovědi v2, výsledky měření v1 i v2)
a site/api/_index.json (data pro živou funkci).
Spuštění (až po tools/evaluate.py a --retrieval):  .venv/Scripts/python tools/build_data.py"""
import base64, json
import numpy as np
import rag
import evaluate as E

ROOT = rag.ROOT

# ukázkové otázky navíc (mimo testovací sady)
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
    "Kolik dostanu za práci o víkendu?",
    "Může mi zaměstnavatel nařídit práci z domova?",
    "Jak dlouho můžu být maximálně na nemocenské?",
    "Kolik peněz dostanu na mateřské?",
    "Dostanu podporu v nezaměstnanosti, když jsem dal výpověď sám?",
    "Kolik dní volna dostanu na stěhování?",
]

# ruční kontrola ukázkových odpovědí (nejsou v testovacích sadách, ale na webu je vidět i tohle)
DEMO_REVIEW = json.loads((ROOT / "data" / "demo_review.json").read_text(encoding="utf-8")) \
    if (ROOT / "data" / "demo_review.json").exists() else {}

def edges(vecs, chunks, k=2):
    """Hrany mapy: sousední odstavce téhož § + k nejpodobnějších úseků (podle embeddingů)."""
    out = set()
    for a in range(len(chunks) - 1):
        if chunks[a]["law"] == chunks[a + 1]["law"] and chunks[a]["para"] == chunks[a + 1]["para"]:
            out.add((a, a + 1))
    sims = vecs @ vecs.T
    np.fill_diagonal(sims, -1)
    for a in range(len(chunks)):
        for b in np.argsort(-sims[a])[:k]:
            out.add((min(a, int(b)), max(a, int(b))))
    return sorted(out)

def layout(vecs, links, ticks=300, seed=1):
    """Silové rozložení mapy (jako d3-force), spočítané předem: v prohlížeči by 2 500 teček trvalo dlouho.
    Start = 2D projekce embeddingů (PCA), pak pružiny po hranách + odpuzování + slabá gravitace do středu."""
    n = len(vecs)
    x = vecs - vecs.mean(0)
    _, _, vt = np.linalg.svd(x, full_matrices=False)
    p = (x @ vt[:2].T).astype(np.float32)
    p = p / np.abs(p).max() * 400 + np.random.default_rng(seed).normal(0, 1, p.shape).astype(np.float32)
    v = np.zeros_like(p)
    src, dst = np.array([a for a, _ in links]), np.array([b for _, b in links])
    deg = np.bincount(np.concatenate([src, dst]), minlength=n).astype(np.float32)
    bias = deg[src] / (deg[src] + deg[dst])
    alpha, decay = 1.0, 1 - 0.001 ** (1 / ticks)
    for _ in range(ticks):
        d = p[None, :, :] - p[:, None, :]                       # d[i, j] = p[j] - p[i]
        l2 = np.maximum((d ** 2).sum(-1), 1.0)
        np.fill_diagonal(l2, np.inf)
        v += (d * (-18 * alpha / l2)[..., None]).sum(1)          # odpuzování všech teček
        dl = p[dst] + v[dst] - p[src] - v[src]                   # pružiny po hranách, délka 18
        ln = np.maximum(np.sqrt((dl ** 2).sum(-1)), 1e-6)
        f = (dl * ((ln - 18) / ln * alpha * 0.6)[:, None])
        np.add.at(v, dst, -f * bias[:, None])
        np.add.at(v, src, f * (1 - bias)[:, None])
        v += -p * 0.05 * alpha                                   # gravitace do středu
        close = l2 < 64                                          # tečky se nepřekrývají (poloměr 4)
        if close.any():
            ln2 = np.sqrt(np.where(close, l2, 64))
            v -= (d * np.where(close, (8 - ln2) / ln2 * 0.35, 0)[..., None]).sum(1)
        v *= 0.6
        p += v
        alpha += (0.001 - alpha) * decay
    p -= p.mean(0)
    return [[round(float(a), 1), round(float(b), 1)] for a, b in p]

def main():
    meta = json.loads((ROOT / "data" / "chunks.json").read_text(encoding="utf-8"))
    chunks = meta["chunks"]
    ev, man = E.load("eval.json"), E.load("manual_review.json")
    S, rc = E.summaries(), E.load("retrieval_compare.json")
    fin = {v: E.final(ev[v]["rows"], man.get(v, {})) for v in E.VERSIONS}
    old = {v: {r["id"]: r for r in ev[v]["rows"]} for v in ("v1", "v2")}

    questions = []
    for r in ev["v3"]["rows"]:
        m = man.get("v3", {}).get(str(r["id"]), {})
        ok = fin["v3"][r["id"]]
        # kde se chyba stala: správný odstavec nebyl mezi 5 úseky -> hledání, jinak čtení (model text špatně použil)
        fail = None if ok else (m.get("fail") or ("hledání" if r["chunks"] and not r["hit5"] else "čtení"))
        top = [t["id"] for t in r["top"]]
        hits, _, trace = rag.search(r["q"], trace=True)   # stejné pořadí jako při měření (přepis je v cache)
        assert [chunks[i]["id"] for i, _ in hits] == top, r["id"]
        questions.append({"q": r["q"], "answer": r["answer"], "rewritten": r.get("rewritten"),
                          "hits": [[i, round(s, 3)] for i, s in hits], "trace": trace,
                          "test": {"set": r["set"], "id": r["id"], "level": r["level"], "gold": r["gold"],
                                   "gold_chunks": r["chunks"], "hit5": r["hit5"], "correct": ok, "fail": fail,
                                   "judge": r["judge"]["correct"], "note": m.get("note") or r["judge"]["reason"],
                                   "v2_correct": fin["v2"][r["id"]], "v2_answer": old["v2"][r["id"]]["answer"],
                                   "v2_note": man.get("v2", {}).get(str(r["id"]), {}).get("note"),
                                   "v1_correct": fin["v1"][r["id"]], "v1_answer": old["v1"][r["id"]]["answer"]}})
    for q in DEMO:
        hits, rw, trace = rag.search(q, trace=True)
        text, _ = rag.answer(q, hits, chunks)
        ok, note = DEMO_REVIEW.get(q, [None, "Zatím ručně nezkontrolováno."])
        questions.append({"q": q, "answer": text, "rewritten": rw, "hits": [[i, round(s, 3)] for i, s in hits],
                          "trace": trace, "test": None, "review": {"ok": ok, "note": note}})
        print("demo", q, "|", text[:80].replace("\n", " "), flush=True)

    vecs = rag.index()
    ed = edges(vecs, chunks)
    pos = layout(vecs, ed)
    data = {"sources": meta["sources"], "downloaded": meta["downloaded"],
            "llm": rag.LLM_MODEL, "llm_v1": E.V1["model"], "embeddings": rag.EMB_MODEL, "top_k": rag.TOP_K,
            "eval": S, "scale": E.scale(),
            "retrieval": {m: {"hit3": rc[m]["hit3"], "hit5": rc[m]["hit5"], "n": rc[m]["n"]} for m in rag.MODES},
            "cost_usd": ev["v3"].get("cost_usd_full"),
            "chunks": [{**{k: c[k] for k in ("id", "law", "title", "topic", "text")}, "p": pos[n]} for n, c in enumerate(chunks)],
            "edges": ed, "questions": questions}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # data pro živou funkci (site/api/ask.js): texty úseků, jejich vektory (int8) a prompty; žádná tajemství
    q8, scale = rag.quantize(rag.embed_api([rag.passage(c) for c in chunks]))
    live = {"emb_model": rag.EMB_MODEL, "llm": rag.LLM_MODEL, "top_k": rag.TOP_K, "dim": int(q8.shape[1]),
            "system": rag.SYSTEM_V3, "rewrite": rag.REWRITE, "rerank": rag.RERANK, "n_cand": rag.N_CAND, "stop": sorted(rag.STOP),
            "chunks": [{"id": c["id"], "title": c["title"], "text": c["text"], **({"note": rag.note(c)} if rag.note(c) else {}),
                        **({"o1": rag.odst1(n)} if rag.odst1(n) is not None else {})} for n, c in enumerate(chunks)],
            "vectors": base64.b64encode(q8.tobytes()).decode(),
            "scales": base64.b64encode(scale.astype("<f4").tobytes()).decode()}
    (ROOT / "site" / "api").mkdir(exist_ok=True)
    (ROOT / "site" / "api" / "_index.json").write_text(json.dumps(live, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"site/data.json: {len(chunks)} úseků, {len(ed)} hran, {len(questions)} otázek")
    for v in E.VERSIONS:
        print(v, S[v]["all"])
    print("scale", data["scale"])

if __name__ == "__main__":
    main()
