# -*- coding: utf-8 -*-
"""Jednorázový běh ZMRAZENÉ verze (v3.1) na nové sadě data/testset_heldout_v4.json (24 otázek).

Sada se smí pustit JEDNOU. Proto:
  1. před prvním voláním se zapíše zámek results/heldout_v4.lock (čas, commit, otisk sady, otisky promptů),
  2. druhé spuštění se odmítne (i po přerušeném běhu), jen --force to obejde a poznamená se do výsledku,
  3. kód a prompty se mezi napsáním sady a během nesmějí měnit: zámek uloží otisky, ať je to ověřitelné.

  python tools/run_heldout.py                    # jen plán a odhad ceny, nic se nevolá
  python tools/run_heldout.py --live             # spustí (OPENROUTER_API_KEY v .env, rozpočet ~0,05 $)
  python tools/run_heldout.py --live --max-usd 0.08

Po běhu: odpovědi se ručně zkontrolují proti textu zákona (data/manual_review_v4.json) a čísla se doplní do docs/benchmark-results.md.
POZOR: klíč živého webu má jen pár centů. Použij samostatný klíč.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import answer_checks as ac  # noqa: E402
import datasets  # noqa: E402
import experiments  # noqa: E402
import metrics as M  # noqa: E402
import rag  # noqa: E402
import security_checks as sc  # noqa: E402

ROOT = datasets.ROOT
LOCK = ROOT / "results" / "heldout_v4.lock"
OUT = ROOT / "results" / "heldout_v4.json"
COST_PER_Q = 0.0012          # horní odhad z měření (bez soudce je to méně)


def load() -> list[dict]:
    return json.loads((datasets.DATA / "testset_heldout_v4.json").read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    qs = load()
    max_usd = float(argv[argv.index("--max-usd") + 1]) if "--max-usd" in argv else 0.10
    print(f"{len(qs)} otázek, odhad ceny {len(qs) * COST_PER_Q:.3f} $, strop {max_usd:.2f} $")
    if "--live" not in argv:
        print("Nic se nevolalo. Pro spuštění přidej --live (jednou).")
        return 0
    if LOCK.exists() and "--force" not in argv:
        print(f"ODMÍTNUTO: sada v4 už byla spuštěna ({LOCK.read_text(encoding='utf-8').splitlines()[0]}). Druhý běh by z ní udělal ladicí sadu.")
        return 2
    LOCK.parent.mkdir(exist_ok=True)
    lock = {"started": datetime.now().isoformat(timespec="seconds"), "git": experiments.git_info(), "testset_sha256": datasets.sha256(datasets.DATA / "testset_heldout_v4.json"),
            "prompt_hashes": experiments.prompt_hashes(), "forced": "--force" in argv}
    LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=1), encoding="utf-8")

    chunks = rag.load_chunks()
    rows, cost = [], 0.0
    for q in qs:
        if cost > max_usd:
            print(f"STOP: překročen strop {max_usd} $ (zbylé otázky nespuštěny)")
            break
        t0 = time.time()
        hits, rewritten, steps = rag.search(q["q"], mode="hybrid_rerank", trace=True)
        text, usage = rag.answer(q["q"], hits, chunks)
        cost += usage.get("cost") or 0
        top = [chunks[i]["id"] for i, _ in hits]
        cand = [chunks[i]["id"] for i, _ in steps.get("fused", [])]
        supplied = [chunks[i]["text"] for i, _ in hits]
        row = {"id": q["id"], "type": q["type"], "q": q["q"], "gold": q["gold"], "gold_chunks": q["chunks"], "rewritten": rewritten, "top5": top, "candidates20": cand,
               "answer": text, "checks": ac.check(text, supplied, q["q"]), "seconds": round(time.time() - t0, 1), "cost_usd": usage.get("cost")}
        if q["chunks"]:
            row["first_gold_rank_top5"] = M.first_gold_rank(top, q["chunks"])
            row["recall@5"] = M.recall_at_k(top, q["chunks"], 5)
            row["gold_in_candidates"] = all(g in cand for g in q["chunks"])
        row["abstained"] = ac.is_abstention(text)
        row["canary_ok"] = sc.no_canary(text, q.get("canary"))
        row["prompt_leak_ok"] = sc.no_prompt_leak(text, rag.SYSTEM_V3)
        rows.append(row)
        print(f"{q['id']} {q['type']:<12} abstained={row['abstained']!s:<5} recall@5={row.get('recall@5', '-')}  {row['seconds']} s")
    OUT.write_text(json.dumps({"lock": lock, "cost_usd": round(cost, 5), "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    ans = [r for r in rows if "recall@5" in r]
    if ans:
        m, lo, hi = M.bootstrap_ci([r["recall@5"] for r in ans])
        print(f"\nRecall@5 na {len(ans)} otázkách s odpovědí: {m:.2f} (95 %: {lo:.2f}–{hi:.2f}). Cena {cost:.4f} $.")
    print(f"Uloženo {OUT}. Teď: ruční kontrola odpovědí do data/manual_review_v4.json, pak python tools/make_docs.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
