# -*- coding: utf-8 -*-
"""Krok 5: měření kvality na 20 testovacích otázkách.
  .venv/Scripts/python tools/evaluate.py --retrieval   # jen vyhledávání (zdarma, bez API)
  .venv/Scripts/python tools/evaluate.py               # vyhledávání + odpovědi + LLM soudce (20 + 20 volání LLM přes OpenRouter)
  .venv/Scripts/python tools/evaluate.py --report      # jen přepíše RESULTS.md z uložených výsledků + ruční kontroly
Výstup: data/eval.json a RESULTS.md. Ruční kontrola se zapisuje do data/manual_review.json."""
import json, sys
from pathlib import Path
import rag

ROOT = rag.ROOT
NEVIM = "Nevím"

JUDGE = """Jsi přísný hodnotitel odpovědí právního asistenta. Dostaneš otázku, správnou (zlatou) odpověď,
úseky zákona, které asistent dostal, a odpověď asistenta.
Posuď:
- correct: odpovídá odpověď asistenta věcně zlaté odpovědi? Pokud zlatá odpověď je NEVÍM, je správně jen odmítnutí.
  Drobné vynechání vedlejší výjimky nevadí, chybné číslo nebo opačný závěr vadí.
- grounded: opírá se každé tvrzení asistenta o dodané úseky (nic si nevymyslel)?
- reason: jedna krátká věta česky, proč."""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["correct", "grounded", "reason"],
          "properties": {"correct": {"type": "boolean"}, "grounded": {"type": "boolean"},
                         "reason": {"type": "string"}}}

def judge(item, hits, chunks, text):
    ctx = "\n".join(f"[{n}] {chunks[i]['id']}: {chunks[i]['text']}" for n, (i, _) in enumerate(hits, 1))
    raw, usage = rag.llm(JUDGE + "\nVrať jen JSON s klíči correct (true/false), grounded (true/false), reason (text).",
                         f"Otázka: {item['q']}\n\nZlatá odpověď: {item['gold']}\n\nÚseky:\n{ctx}\n\nOdpověď asistenta: {text}",
                         json_mode=False)
    raw = raw[raw.index("{"):raw.rindex("}") + 1]   # pro jistotu vyřízni jen JSON
    return json.loads(raw), usage

def run(retrieval_only):
    chunks = rag.load_chunks()
    tests = json.loads((ROOT / "data" / "testset.json").read_text(encoding="utf-8"))
    rows, tok_in, tok_out = [], 0, 0
    for t in tests:
        hits = rag.search(t["q"])
        top_ids = [chunks[i]["id"] for i, _ in hits]
        row = {**t, "top": [{"id": chunks[i]["id"], "score": round(s, 3)} for i, s in hits],
               "hit3": (any(g in top_ids[:3] for g in t["chunks"]) if t["chunks"] else None)}
        if not retrieval_only:
            text, u1 = rag.answer(t["q"], hits, chunks)
            verdict, u2 = judge(t, hits, chunks, text)
            row.update(answer=text, cited=[top_ids[n - 1] for n in rag.cited(text) if n <= len(top_ids)],
                       said_nevim=text.startswith(NEVIM), judge=verdict)
            tok_in += u1.get("prompt_tokens", 0) + u2.get("prompt_tokens", 0)
            tok_out += u1.get("completion_tokens", 0) + u2.get("completion_tokens", 0)
        rows.append(row)
        print(f"{t['id']:>2} hit@3={row['hit3']}  {t['q'][:60]}", flush=True)
    path = ROOT / "data" / ("eval_retrieval.json" if retrieval_only else "eval.json")
    path.write_text(json.dumps({"rows": rows, "tokens_in": tok_in, "tokens_out": tok_out},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    if not retrieval_only:
        print(f"tokeny: vstup {tok_in}, výstup {tok_out}")

def report():
    ev = json.loads((ROOT / "data" / "eval.json").read_text(encoding="utf-8"))
    rows = ev["rows"]
    mp = ROOT / "data" / "manual_review.json"
    manual = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    ans = [r for r in rows if r["chunks"]]
    hit = sum(r["hit3"] for r in ans)
    judge_ok = sum(r["judge"]["correct"] for r in rows)
    grounded = sum(r["judge"]["grounded"] for r in rows)
    final = [manual.get(str(r["id"]), {}).get("correct", r["judge"]["correct"]) for r in rows]
    agree = sum(f == r["judge"]["correct"] for f, r in zip(final, rows))
    nev = [r for r in rows if not r["chunks"]]
    L = ["# Výsledky měření", "",
         f"Model odpovědí i soudce: `{rag.LLM_MODEL}`. Embeddingy: `{rag.EMB_MODEL}`. Do odpovědi jde top {rag.TOP_K} úseků.", "",
         "| Měřítko | Výsledek |", "|---|---|",
         f"| Vyhledávání: správný úsek mezi top 3 (hit@3) | **{hit} z {len(ans)}** (jen otázky, které odpověď mají) |",
         f"| Odpověď správně – po ruční kontrole | **{sum(final)} z {len(rows)}** |",
         f"| Odpověď správně – podle LLM soudce | {judge_ok} z {len(rows)} |",
         f"| Odpověď se opírá o zdroj (soudce) | {grounded} z {len(rows)} |",
         f"| Řekl „nevím“, když zdroj odpověď nemá | {sum(r['said_nevim'] for r in nev)} z {len(nev)} |",
         f"| Řekl „nevím“, i když odpověď ve zdroji byla | {sum(r['said_nevim'] for r in ans)} z {len(ans)} |",
         f"| Shoda LLM soudce s ruční kontrolou | {agree} z {len(rows)} |", "",
         f"Spotřeba API při měření: {ev['tokens_in']} vstupních a {ev['tokens_out']} výstupních tokenů.", "",
         "## Otázka po otázce", "",
         "| # | Typ | Otázka | hit@3 | Výsledek | Poznámka |", "|---|---|---|---|---|---|"]
    for f, r in zip(final, rows):
        note = manual.get(str(r["id"]), {}).get("note") or r["judge"]["reason"]
        h = "–" if r["hit3"] is None else ("ano" if r["hit3"] else "**ne**")
        L.append(f"| {r['id']} | {r['level']} | {r['q']} | {h} | {'správně' if f else '**chyba**'} | {note} |")
    (ROOT / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:14]))

if __name__ == "__main__":
    if "--report" in sys.argv:
        report()
    else:
        run("--retrieval" in sys.argv)
        if "--retrieval" not in sys.argv:
            report()
