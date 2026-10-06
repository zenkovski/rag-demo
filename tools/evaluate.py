# -*- coding: utf-8 -*-
"""Měření kvality na 20 testovacích otázkách.
  .venv/Scripts/python tools/evaluate.py --retrieval   # jen vyhledávání, všechny 3 režimy (dense / hybrid / hybrid+přepis)
  .venv/Scripts/python tools/evaluate.py               # v2: vyhledávání + odpovědi + LLM soudce -> data/eval.json
  .venv/Scripts/python tools/evaluate.py --holdout     # 10 nových otázek, v1 i v2 (kontrola přeučení)
  .venv/Scripts/python tools/evaluate.py --report      # jen přepíše RESULTS.md (z uložených výsledků + ruční kontroly)
Ruční kontrola: data/manual_review.json (v2) a data/manual_review_v1.json (v1)."""
import json, sys
import rag

ROOT = rag.ROOT
NEVIM = "Nevím"
JUDGE_MODEL = rag.LLM_MODEL

JUDGE = """Jsi přísný hodnotitel odpovědí právního asistenta. Dostaneš otázku, správnou (zlatou) odpověď,
úseky zákona, které asistent dostal, a odpověď asistenta.
Posuď:
- correct: odpovídá odpověď asistenta věcně zlaté odpovědi? Pokud zlatá odpověď je NEVÍM, je správně jen odmítnutí.
  Drobné vynechání vedlejší výjimky nevadí, chybné číslo nebo opačný závěr vadí.
- grounded: opírá se každé tvrzení asistenta o dodané úseky (nic si nevymyslel)?
- reason: jedna krátká věta česky, proč."""

def load(name):
    p = ROOT / "data" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def judge(item, hits, chunks, text):
    ctx = "\n".join(f"[{n}] {chunks[i]['id']}: {chunks[i]['text']}" for n, (i, _) in enumerate(hits, 1))
    raw, usage = rag.llm(JUDGE + "\nVrať jen JSON s klíči correct (true/false), grounded (true/false), reason (text).",
                         f"Otázka: {item['q']}\n\nZlatá odpověď: {item['gold']}\n\nÚseky:\n{ctx}\n\nOdpověď asistenta: {text}",
                         JUDGE_MODEL)
    raw = raw[raw.index("{"):raw.rindex("}") + 1]   # pro jistotu vyřízni jen JSON
    return json.loads(raw), usage

def tests():
    return json.loads((ROOT / "data" / "testset.json").read_text(encoding="utf-8"))

def run_retrieval():
    """hit@3 a hit@5 pro každý režim vyhledávání."""
    chunks = rag.load_chunks()
    out = {}
    for mode in rag.MODES:
        rows = []
        for t in tests():
            hits, rw = rag.search(t["q"], mode=mode)
            ids = [chunks[i]["id"] for i, _ in hits]
            rows.append({"id": t["id"], "top": ids, "rewritten": rw,
                         "hit3": any(g in ids[:3] for g in t["chunks"]) if t["chunks"] else None,
                         "hit5": any(g in ids[:5] for g in t["chunks"]) if t["chunks"] else None})
        ans = [r for r in rows if r["hit3"] is not None]
        out[mode] = {"hit3": sum(r["hit3"] for r in ans), "hit5": sum(r["hit5"] for r in ans), "n": len(ans), "rows": rows}
        print(f"{mode:<15} hit@3 {out[mode]['hit3']}/{len(ans)}  hit@5 {out[mode]['hit5']}/{len(ans)}  "
              f"miss@5: {[r['id'] for r in ans if not r['hit5']]}", flush=True)
    (ROOT / "data" / "retrieval_compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

def run():
    chunks = rag.load_chunks()
    rows, cost = [], 0.0
    for t in tests():
        hits, rw = rag.search(t["q"])
        top_ids = [chunks[i]["id"] for i, _ in hits]
        text, u1 = rag.answer(t["q"], hits, chunks)
        verdict, u2 = judge(t, hits, chunks, text)
        cost += (u1.get("cost") or 0) + (u2.get("cost") or 0)
        rows.append({**t, "rewritten": rw, "top": [{"id": chunks[i]["id"], "score": round(s, 3)} for i, s in hits],
                     "hit3": (any(g in top_ids[:3] for g in t["chunks"]) if t["chunks"] else None),
                     "answer": text, "cited": [top_ids[n - 1] for n in rag.cited(text) if n <= len(top_ids)],
                     "said_nevim": text.startswith(NEVIM), "judge": verdict})
        print(f"{t['id']:>2} hit@3={rows[-1]['hit3']}  judge={verdict['correct']}  {t['q'][:55]}", flush=True)
    (ROOT / "data" / "eval.json").write_text(json.dumps({"model": rag.LLM_MODEL, "mode": rag.MODE, "rows": rows,
                                                         "cost_usd_new_calls": round(cost, 5)},
                                                        ensure_ascii=False, indent=1), encoding="utf-8")

V1 = {"mode": "dense", "model": "nvidia/nemotron-3-super-120b-a12b:free", "system": rag.SYSTEM_V1}
V2 = {"mode": rag.MODE, "model": rag.LLM_MODEL, "system": rag.SYSTEM}

def run_holdout():
    """10 nových otázek, napsaných až po návrhu v2: v1 i v2 stejně (kontrola přeučení na testovací sadu)."""
    chunks = rag.load_chunks()
    items = json.loads((ROOT / "data" / "testset_holdout.json").read_text(encoding="utf-8"))
    out = {}
    for name, cfg in (("v1", V1), ("v2", V2)):
        rows = []
        for t in items:
            hits, rw = rag.search(t["q"], mode=cfg["mode"])
            top_ids = [chunks[i]["id"] for i, _ in hits]
            text, _ = rag.answer(t["q"], hits, chunks, system=cfg["system"], model=cfg["model"])
            verdict, _ = judge(t, hits, chunks, text)
            rows.append({**t, "rewritten": rw, "top": top_ids, "answer": text, "said_nevim": text.startswith(NEVIM),
                         "hit3": any(g in top_ids[:3] for g in t["chunks"]) if t["chunks"] else None,
                         "hit5": any(g in top_ids for g in t["chunks"]) if t["chunks"] else None, "judge": verdict})
            print(f"{name} {t['id']} hit@5={rows[-1]['hit5']} judge={verdict['correct']}", flush=True)
        out[name] = rows
    (ROOT / "data" / "eval_holdout.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

def summarize(ev, manual):
    rows = ev["rows"]
    ans = [r for r in rows if r["chunks"]]
    nev = [r for r in rows if not r["chunks"]]
    final = {r["id"]: manual.get(str(r["id"]), {}).get("correct", r["judge"]["correct"]) for r in rows}
    return {"n": len(rows), "correct": sum(final.values()),
            "correct_answerable": sum(final[r["id"]] for r in ans), "n_answerable": len(ans),
            "nevim_ok": sum(r["said_nevim"] for r in nev), "n_unanswerable": len(nev),
            "nevim_wrong": sum(r["said_nevim"] for r in ans),
            "hit3": sum(r["hit3"] for r in ans),
            "judge_correct": sum(r["judge"]["correct"] for r in rows),
            "grounded": sum(r["judge"]["grounded"] for r in rows),
            "judge_agree": sum(final[r["id"]] == r["judge"]["correct"] for r in rows), "final": final}

def report():
    v2, v1 = load("eval.json"), load("eval_v1.json")
    s2, s1 = summarize(v2, load("manual_review.json")), summarize(v1, load("manual_review_v1.json"))
    rc = load("retrieval_compare.json")
    m2, m1 = load("manual_review.json"), load("manual_review_v1.json")
    L = ["# Výsledky měření", "",
         "20 testovacích otázek: 16 má odpověď v zákoně, 4 záměrně ne (tam je správně „nevím“).",
         "Verdikt „správně“ je po ruční kontrole všech 20 odpovědí proti textu zákona.", "",
         "## v1 → v2", "",
         "| Měřítko | v1 | v2 |", "|---|---|---|",
         f"| Model | `{v1.get('model', 'nvidia/nemotron-3-super-120b-a12b:free')}` | `{v2['model']}` |",
         "| Vyhledávání | embeddingy e5-base | e5-large + BM25 + přepis otázky (RRF) |",
         f"| **Odpověď správně (celkem)** | **{s1['correct']} z 20** | **{s2['correct']} z 20** |",
         f"| z toho otázky s odpovědí | {s1['correct_answerable']} z 16 | {s2['correct_answerable']} z 16 |",
         f"| z toho „nevím“, když zdroj mlčí | {s1['nevim_ok']} z 4 | {s2['nevim_ok']} z 4 |",
         f"| Správný paragraf v top 3 (hit@3) | {s1['hit3']} z 16 | {s2['hit3']} z 16 |",
         f"| „Nevím“, i když odpověď ve zdroji byla | {s1['nevim_wrong']} z 16 | {s2['nevim_wrong']} z 16 |",
         f"| Opírá se o zdroj (podle AI soudce) | {s1['grounded']} z 20 | {s2['grounded']} z 20 |",
         f"| AI soudce se shodl s ruční kontrolou | {s1['judge_agree']} z 20 | {s2['judge_agree']} z 20 |", ""]
    if rc:
        L += ["## Co pomohlo ve vyhledávání", "",
              "Stejných 16 otázek, mění se jen způsob hledání. hit@5 = správný paragraf je mezi 5 úseky, které dostane model.", "",
              "| Režim | hit@3 | hit@5 |", "|---|---|---|"]
        names = {"dense": "embeddingy e5-base (v1)", "dense_large": "embeddingy e5-large", "hybrid": "e5-large + BM25 nad laickou otázkou",
                 "hybrid_rewrite": "e5-large + přepis otázky + BM25 nad přepisem (v2)"}
        L += [f"| {names[m]} | {rc[m]['hit3']} z {rc[m]['n']} | {rc[m]['hit5']} z {rc[m]['n']} |" for m in rag.MODES] + [""]
    ho, mh = load("eval_holdout.json"), load("manual_review_holdout.json")
    if ho:
        def hs(name):
            rows, man = ho[name], mh.get(name, {})
            ok = [man.get(str(r["id"]), {}).get("correct", r["judge"]["correct"]) for r in rows]
            ans = [r for r in rows if r["chunks"]]
            return sum(ok), sum(r["hit5"] for r in ans), len(ans)
        (c1, h1, n), (c2, h2, _) = hs("v1"), hs("v2")
        L += ["## Kontrola přeučení: 10 nových otázek", "",
              "Úpravy v2 jsem navrhl podle chyb na 20 testovacích otázkách, takže tam může být výsledek přikrášlený.",
              "Proto jsem až potom napsal 10 nových otázek (`data/testset_holdout.json`) a změřil na nich v1 i v2 beze změn.",
              "První verze v2 (embeddingy e5-base) na nich měla 9 z 10 (chyba u #28). Pak jsem kvůli webu přešel na e5-large přes API",
              "a #28 se tím spravila. Změna nebyla kvůli téhle otázce, ale nové otázky už tím nejsou úplně čisté: další krok je nová sada.", "",
              "| Měřítko | v1 | v2 |", "|---|---|---|",
              f"| Odpověď správně (ruční kontrola) | {c1} z {len(ho['v1'])} | {c2} z {len(ho['v2'])} |",
              f"| Správný paragraf mezi 5 nalezenými | {h1} z {n} | {h2} z {n} |", ""]
        L += [f"- **v{v[1]} #{k}:** {x['note']}" for v in ("v1", "v2") for k, x in mh.get(v, {}).items() if not x["correct"]] + [""]
    L += [f"Cena nových volání API při měření v2: {v2.get('cost_usd_new_calls', 0)} $.", "",
          "## v2 otázka po otázce", "",
          "| # | Typ | Otázka | hit@3 | v1 | v2 | Poznámka k v2 |", "|---|---|---|---|---|---|---|"]
    for r in v2["rows"]:
        note = m2.get(str(r["id"]), {}).get("note") or r["judge"]["reason"]
        h = "–" if r["hit3"] is None else ("ano" if r["hit3"] else "**ne**")
        f = lambda ok: "správně" if ok else "**chyba**"
        L.append(f"| {r['id']} | {r['level']} | {r['q']} | {h} | {f(s1['final'][r['id']])} | {f(s2['final'][r['id']])} | {note} |")
    L += ["", "## Poznámky k v1 (chyby)", ""]
    L += [f"- **{k}:** {v['note']}" for k, v in m1.items() if not v["correct"]]
    (ROOT / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))

if __name__ == "__main__":
    if "--retrieval" in sys.argv:
        run_retrieval()
    elif "--holdout" in sys.argv:
        run_holdout()
    elif "--report" in sys.argv:
        report()
    else:
        run()
        report()
