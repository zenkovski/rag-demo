# -*- coding: utf-8 -*-
"""ŽIVÝ bezpečnostní test: pustí security/injection_cases.json proti skutečnému řetězci (hledání + odpověď přes OpenRouter).
Stojí peníze (asi 0,001 $ za případ, tj. ~0,02 $ za celou sadu), proto se bez --live jen vypíše plán a odhad.
  python tools/security_eval.py                # plán a odhad ceny, nic se nevolá
  python tools/security_eval.py --live         # spustí (potřebuje OPENROUTER_API_KEY v .env a rozpočet)
POZOR: na klíči webu zbývá jen pár centů. Pro tenhle test použij samostatný klíč, ať se nevyčerpá živé demo.
Výsledek se ukládá do results/security-<čas>.json. Deterministické detektory: tools/security_checks.py."""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rag  # noqa: E402
import security_checks as sc  # noqa: E402

ROOT = rag.ROOT
COST_PER_CASE = 0.0012          # z měření: ~0,0011 $ za otázku včetně soudce (soudce tu není, takže je to horní odhad)


def main(argv):
    cases = json.loads((ROOT / "security" / "injection_cases.json").read_text(encoding="utf-8"))
    print(f"{len(cases)} případů, odhad ceny {len(cases) * COST_PER_CASE:.3f} $")
    if "--live" not in argv:
        for c in cases:
            print(f"  {c['id']} [{c['type']}] {c['question'][:80]}")
        print("Nic se nevolalo. Pro spuštění přidej --live.")
        return 0
    chunks = rag.load_chunks()
    rows = []
    for c in cases:
        q = " ".join(c["question"].split())[:300]               # stejná úprava a limit jako na webu
        t0 = time.time()
        hits, _ = rag.search(q)
        text, usage = rag.answer(q, hits, chunks)
        res = sc.evaluate(text, system_prompt=rag.SYSTEM_V3, n_supplied=len(hits), canary=c.get("canary"), expect=c["expect"])
        rows.append({"id": c["id"], "type": c["type"], "ok": all(res.values()), "detectors": res, "answer": text, "cost": usage.get("cost"), "s": round(time.time() - t0, 1)})
        print(f"{c['id']} {'OK  ' if rows[-1]['ok'] else 'ÚNIK'} {res}")
    out = ROOT / "results" / f"security-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps({"model": rag.ANSWER_MODEL, "cases": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sum(r['ok'] for r in rows)} z {len(rows)} v pořádku, uloženo {out}")
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
