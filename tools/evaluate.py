# -*- coding: utf-8 -*-
"""Měření kvality na 46 testovacích otázkách (3 sady), v1 i v2 nad stejnými 4 předpisy.
  .venv/Scripts/python tools/evaluate.py --retrieval   # jen vyhledávání, všechny režimy -> data/retrieval_compare.json
  .venv/Scripts/python tools/evaluate.py               # v1 i v2: vyhledávání + odpovědi + LLM soudce -> data/eval.json
  .venv/Scripts/python tools/evaluate.py --report      # jen přepíše RESULTS.md (z uložených výsledků + ruční kontroly)
Ruční kontrola: data/manual_review.json  {"v2": {"id": {"correct": …, "note": …}}, "v1": {…}}
Archiv měření nad 5 tématy zákoníku práce (260 úseků): data/archive_5temat/."""
import json, sys
import rag

ROOT = rag.ROOT
NEVIM = "Nevím"
JUDGE_MODEL = rag.LLM_MODEL

# sady: testovací (podle ní jsem ladil v2), nové (napsané po návrhu v2), rozšíření (po přidání dalších předpisů)
SETS = [("test", "testset.json"), ("holdout", "testset_holdout.json"), ("new", "testset_new.json")]
SET_NAMES = {"test": "testovací", "holdout": "kontrolní", "new": "nové předpisy"}

JUDGE = """Jsi přísný hodnotitel odpovědí právního asistenta. Dostaneš otázku, správnou (zlatou) odpověď,
úseky zákona, které asistent dostal, a odpověď asistenta.
Posuď:
- correct: odpovídá odpověď asistenta věcně zlaté odpovědi? Pokud zlatá odpověď je NEVÍM, je správně jen odmítnutí.
  Drobné vynechání vedlejší výjimky nevadí, chybné číslo nebo opačný závěr vadí.
- grounded: opírá se každé tvrzení asistenta o dodané úseky (nic si nevymyslel)?
- reason: jedna krátká věta česky, proč."""

V1 = {"mode": "dense", "model": "nvidia/nemotron-3-super-120b-a12b:free", "system": rag.SYSTEM_V1}
V2 = {"mode": rag.MODE, "model": rag.LLM_MODEL, "system": rag.SYSTEM}

def load(name):
    p = ROOT / "data" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def tests():
    out = []
    for name, f in SETS:
        out += [{**t, "set": name} for t in json.loads((ROOT / "data" / f).read_text(encoding="utf-8"))]
    return out

def judge(item, hits, chunks, text):
    ctx = "\n".join(f"[{n}] {chunks[i]['id']}: {chunks[i]['text']}" for n, (i, _) in enumerate(hits, 1))
    raw, usage = rag.llm(JUDGE + "\nVrať jen JSON s klíči correct (true/false), grounded (true/false), reason (text).",
                         f"Otázka: {item['q']}\n\nZlatá odpověď: {item['gold']}\n\nÚseky:\n{ctx}\n\nOdpověď asistenta: {text}",
                         JUDGE_MODEL)
    raw = raw[raw.index("{"):raw.rindex("}") + 1]   # pro jistotu vyřízni jen JSON
    return json.loads(raw), usage

def hit(t, ids, n):
    return any(g in ids[:n] for g in t["chunks"]) if t["chunks"] else None

def run_retrieval():
    """hit@3 a hit@5 pro každý režim vyhledávání (jen otázky, které mají odpověď v předpisech)."""
    chunks = rag.load_chunks()
    out = {}
    for mode in rag.MODES:
        rows = []
        for t in tests():
            hits, rw = rag.search(t["q"], mode=mode)
            ids = [chunks[i]["id"] for i, _ in hits]
            rows.append({"id": t["id"], "set": t["set"], "top": ids, "rewritten": rw, "hit3": hit(t, ids, 3), "hit5": hit(t, ids, 5)})
        ans = [r for r in rows if r["hit3"] is not None]
        out[mode] = {"hit3": sum(r["hit3"] for r in ans), "hit5": sum(r["hit5"] for r in ans), "n": len(ans), "rows": rows}
        print(f"{mode:<15} hit@3 {out[mode]['hit3']}/{len(ans)}  hit@5 {out[mode]['hit5']}/{len(ans)}  "
              f"miss@5: {[r['id'] for r in ans if not r['hit5']]}", flush=True)
    (ROOT / "data" / "retrieval_compare.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

def run(versions=("v2", "v1")):
    chunks = rag.load_chunks()
    out = load("eval.json")
    for name in versions:
        cfg = {"v1": V1, "v2": V2}[name]
        rows, cost = [], 0.0
        for t in tests():
            hits, rw = rag.search(t["q"], mode=cfg["mode"])
            ids = [chunks[i]["id"] for i, _ in hits]
            text, u1 = rag.answer(t["q"], hits, chunks, system=cfg["system"], model=cfg["model"])
            verdict, u2 = judge(t, hits, chunks, text)
            cost += (u1.get("cost") or 0) + (u2.get("cost") or 0)
            rows.append({**t, "rewritten": rw, "top": [{"id": chunks[i]["id"], "score": round(s, 3)} for i, s in hits],
                         "hit3": hit(t, ids, 3), "hit5": hit(t, ids, 5), "answer": text,
                         "cited": [ids[n - 1] for n in rag.cited(text) if n <= len(ids)],
                         "said_nevim": text.startswith(NEVIM), "judge": verdict})
            print(f"{name} {t['id']:>2} hit@5={rows[-1]['hit5']}  judge={verdict['correct']}  {t['q'][:55]}", flush=True)
        out[name] = {"model": cfg["model"], "mode": cfg["mode"], "rows": rows, "cost_usd_new_calls": round(cost, 5)}
        (ROOT / "data" / "eval.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

def final(rows, manual):
    return {r["id"]: manual.get(str(r["id"]), {}).get("correct", r["judge"]["correct"]) for r in rows}

def summarize(rows, manual):
    ans = [r for r in rows if r["chunks"]]
    nev = [r for r in rows if not r["chunks"]]
    fin = final(rows, manual)
    return {"n": len(rows), "correct": sum(fin[r["id"]] for r in rows),
            "correct_answerable": sum(fin[r["id"]] for r in ans), "n_answerable": len(ans),
            "nevim_ok": sum(fin[r["id"]] for r in nev), "n_unanswerable": len(nev),
            "nevim_wrong": sum(r["said_nevim"] for r in ans),
            "hit3": sum(r["hit3"] for r in ans), "hit5": sum(r["hit5"] for r in ans),
            "judge_correct": sum(r["judge"]["correct"] for r in rows),
            "grounded": sum(r["judge"]["grounded"] for r in rows),
            "judge_agree": sum(fin[r["id"]] == r["judge"]["correct"] for r in rows)}

def summaries():
    """{v1|v2: {all|test|holdout|new: souhrn}} po ruční kontrole."""
    ev, man = load("eval.json"), load("manual_review.json")
    out = {}
    for v in ("v1", "v2"):
        rows = ev[v]["rows"]
        out[v] = {"all": summarize(rows, man.get(v, {}))}
        for s, _ in SETS:
            out[v][s] = summarize([r for r in rows if r["set"] == s], man.get(v, {}))
    return out

def scale():
    """Stejné otázky, malý korpus (5 témat, 260 úseků) vs. velký (4 předpisy): našel se správný § mezi 5?"""
    ev = load("eval.json")["v2"]["rows"]
    old = {r["id"]: [t["id"] if isinstance(t, dict) else t for t in r["top"]] for r in load("archive_5temat/eval.json")["rows"]}
    old.update({r["id"]: r["top"] for r in load("archive_5temat/eval_holdout.json")["v2"]})
    olds = {r["id"]: r for r in load("archive_5temat/testset.json") + load("archive_5temat/testset_holdout.json")}
    rows = []
    for r in ev:
        o = olds.get(r["id"])
        if not o or not o["chunks"]:
            continue                                   # jen otázky, které měly odpověď už v malém korpusu
        rows.append({"id": r["id"], "small": any(g in old[r["id"]] for g in o["chunks"]), "big": r["hit5"]})
    return {"n": len(rows), "small": sum(x["small"] for x in rows), "big": sum(x["big"] for x in rows),
            "lost": [x["id"] for x in rows if x["small"] and not x["big"]], "gained": [x["id"] for x in rows if x["big"] and not x["small"]]}

def report():
    ev, man, rc = load("eval.json"), load("manual_review.json"), load("retrieval_compare.json")
    S, sc = summaries(), scale()
    fin = {v: final(ev[v]["rows"], man.get(v, {})) for v in ("v1", "v2")}
    a1, a2 = S["v1"]["all"], S["v2"]["all"]
    L = ["# Výsledky měření", "",
         "Zdroj: 4 předpisy, 2 475 úseků (celý zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění,",
         "nařízení vlády o překážkách v práci). 46 testovacích otázek ve 3 sadách, 40 má odpověď v předpisech, 6 záměrně ne.",
         "Verdikt „správně“ je po ruční kontrole všech odpovědí proti textu zákona.", "",
         "## v1 → v2", "",
         "| Měřítko | v1 | v2 |", "|---|---|---|",
         f"| Model | `{ev['v1']['model']}` | `{ev['v2']['model']}` |",
         "| Vyhledávání | embeddingy e5-base | e5-large + BM25 + přepis otázky (RRF) |",
         f"| **Odpověď správně (celkem)** | **{a1['correct']} z {a1['n']}** | **{a2['correct']} z {a2['n']}** |",
         f"| z toho otázky s odpovědí | {a1['correct_answerable']} z {a1['n_answerable']} | {a2['correct_answerable']} z {a2['n_answerable']} |",
         f"| z toho správně „nevím“, když zdroj mlčí | {a1['nevim_ok']} z {a1['n_unanswerable']} | {a2['nevim_ok']} z {a2['n_unanswerable']} |",
         f"| Správný paragraf mezi 5 nalezenými (hit@5) | {a1['hit5']} z {a1['n_answerable']} | {a2['hit5']} z {a2['n_answerable']} |",
         f"| Správný paragraf v top 3 (hit@3) | {a1['hit3']} z {a1['n_answerable']} | {a2['hit3']} z {a2['n_answerable']} |",
         f"| „Nevím“, i když odpověď ve zdroji byla | {a1['nevim_wrong']} z {a1['n_answerable']} | {a2['nevim_wrong']} z {a2['n_answerable']} |",
         f"| Opírá se o zdroj (podle AI soudce) | {a1['grounded']} z {a1['n']} | {a2['grounded']} z {a2['n']} |",
         f"| AI soudce se shodl s ruční kontrolou | {a1['judge_agree']} z {a1['n']} | {a2['judge_agree']} z {a2['n']} |", "",
         "## Podle sad", "",
         "| Sada | otázek | v1 správně | v2 správně | v2 hit@5 |", "|---|---|---|---|---|"]
    for s, _ in SETS:
        x1, x2 = S["v1"][s], S["v2"][s]
        L.append(f"| {SET_NAMES[s]} | {x2['n']} | {x1['correct']} | {x2['correct']} | {x2['hit5']} z {x2['n_answerable']} |")
    L += ["", "- **testovací (1–20):** podle chyb na nich jsem navrhl v2, výsledek v2 je tu proto nadsazený.",
          "- **kontrolní (21–30):** napsané až po návrhu v2.",
          "- **nové předpisy (31–46):** napsané po přidání dalších předpisů, žádné ladění podle nich.", ""]
    L += ["## Co udělal větší zdroj s vyhledáváním", "",
          f"Stejných {sc['n']} otázek, které měly odpověď už v první verzi (5 témat zákoníku práce, 260 úseků).",
          "Teď se hledá v 2 475 úsecích, tedy v 10× větší kupce.", "",
          "| Zdroj | správný § mezi 5 nalezenými |", "|---|---|",
          f"| 5 témat, 260 úseků | {sc['small']} z {sc['n']} |", f"| 4 předpisy, 2 475 úseků | {sc['big']} z {sc['n']} |", ""]
    if sc["lost"]:
        L += [f"Ztratily se otázky: {', '.join(map(str, sc['lost']))}." + (f" Nově se našly: {', '.join(map(str, sc['gained']))}." if sc["gained"] else ""), ""]
    if rc:
        names = {"dense": "embeddingy e5-base (v1)", "dense_large": "embeddingy e5-large", "hybrid": "e5-large + BM25 nad laickou otázkou",
                 "hybrid_rewrite": "e5-large + přepis otázky + BM25 nad přepisem (v2)"}
        L += ["## Co pomohlo ve vyhledávání", "",
              f"Všech {rc['dense']['n']} otázek s odpovědí, mění se jen způsob hledání.", "",
              "| Režim | hit@3 | hit@5 |", "|---|---|---|"]
        L += [f"| {names[m]} | {rc[m]['hit3']} z {rc[m]['n']} | {rc[m]['hit5']} z {rc[m]['n']} |" for m in rag.MODES] + [""]
    L += [f"Cena nových volání API při měření: v2 {ev['v2'].get('cost_usd_new_calls', 0)} $, v1 (model zdarma) jen AI soudce.", "",
          "## Otázka po otázce", "",
          "| # | Sada | Otázka | hit@5 | v1 | v2 | Poznámka k v2 |", "|---|---|---|---|---|---|---|"]
    f = lambda ok: "správně" if ok else "**chyba**"
    for r in ev["v2"]["rows"]:
        note = man.get("v2", {}).get(str(r["id"]), {}).get("note") or r["judge"]["reason"]
        h = "–" if r["hit5"] is None else ("ano" if r["hit5"] else "**ne**")
        L.append(f"| {r['id']} | {SET_NAMES[r['set']]} | {r['q']} | {h} | {f(fin['v1'][r['id']])} | {f(fin['v2'][r['id']])} | {note} |")
    L += ["", "## Chyby v1", ""]
    L += [f"- **{k}:** {v['note']}" for k, v in man.get("v1", {}).items() if not v["correct"]]
    L += ["", "## Historie", "",
          "První verze hledala jen v 5 tématech zákoníku práce (260 úseků). Tam měla v2 na 30 otázkách 30 správně a v1 26.",
          "Data té verze jsou v `data/archive_5temat/`. Šest otázek, které tehdy měly správnou odpověď „nevím“, má teď odpověď",
          "v nových předpisech (třeba mateřská nebo svatba), takže dostaly novou zlatou odpověď (původní je v poli `gold_5temat`)."]
    (ROOT / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:40]))

if __name__ == "__main__":
    if "--retrieval" in sys.argv:
        run_retrieval()
    elif "--report" in sys.argv:
        report()
    else:
        run(tuple(a for a in sys.argv[1:] if a in ("v1", "v2")) or ("v2", "v1"))
        report()
