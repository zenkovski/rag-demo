# -*- coding: utf-8 -*-
"""Měřicí laboratoř: ablační srovnání hledání, odpovědí a provozu, vše OFFLINE z uložených výsledků (0 $).

  python tools/experiments.py                # spustí, uloží results/runs/<čas>.json a přepíše docs/benchmark-results.md
  python tools/experiments.py --check        # porovná s results/baseline.json, při regresi skončí kódem 1 (pro CI)
  python tools/experiments.py --save-baseline  # nový referenční stav (jen úmyslně, po zkontrolování rozdílu)
  python tools/experiments.py --no-base      # přeskočí e5-base (potřebuje torch a stažený model)

Každý běh ukládá: konfiguraci, verze modelů a otisky dat, metriky s intervaly spolehlivosti, runtime, cenu a seznam regresí.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import answer_checks as ac  # noqa: E402
import datasets  # noqa: E402
import evaluate  # noqa: E402
import metrics as M  # noqa: E402
import rag  # noqa: E402
import replay  # noqa: E402

ROOT = datasets.ROOT
RESULTS = ROOT / "results"
SPLITS = ("all", "dev", "validation", "test")
W_GRID = [round(0.05 * i, 2) for i in range(0, 13)]       # váha BM25 0 … 0,6
RRF_KS = (10, 30, 60, 100)


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    return {"commit": run("rev-parse", "--short", "HEAD") or None, "dirty": bool(run("status", "--porcelain", "--", "tools", "data", "tests"))}


def prompt_hashes() -> dict:
    h = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]
    return {"rewrite": h(rag.REWRITE), "rerank": h(rag.RERANK), "answer_v3": h(rag.SYSTEM_V3)}


def _ids(chunks, idxs):
    return [chunks[i]["id"] for i in idxs]


def select_weight(comps, golds, dev_ids, chunks) -> tuple[float, list]:
    """Váhu BM25 pro vážený součet vybírám jen na dev otázkách (podle MRR), ať se na test nelaďí."""
    table = []
    for w in W_GRID:
        rk = {i: _ids(chunks, replay.weighted(comps[i], w)) for i in dev_ids}
        table.append((w, M.summarize(rk, {i: golds[i] for i in dev_ids}, ks=(5,))["metrics"]["mrr"]["mean"]))
    best = max(table, key=lambda x: (x[1], -x[0]))[0]
    return best, table


def run(with_base: bool = True) -> dict:
    t_start = time.time()
    qs = datasets.questions()
    chunks = rag.load_chunks()
    answerable = [q for q in qs if q["chunks"]]
    golds = {q["id"]: q["chunks"] for q in answerable}
    split_of = {q["id"]: q["split"] for q in qs}
    ids_in = {"all": [q["id"] for q in answerable]}
    for s in ("dev", "validation", "test"):
        ids_in[s] = [q["id"] for q in answerable if q["split"] == s]

    comps = {q["id"]: replay.components(q["q"]) for q in answerable}
    w_best, w_table = select_weight(comps, golds, ids_in["dev"], chunks)

    # --- pořadí pro všechny systémy ---
    ranks: dict[str, dict[int, list[str]]] = {}
    misses: dict[int, str] = {}
    for q in answerable:
        r = replay.rankings_for(q["q"], w_best, with_base=with_base)
        if "_cache_miss" in r:
            misses[q["id"]] = r.pop("_cache_miss")
        for name, order in r.items():
            ranks.setdefault(name, {})[q["id"]] = _ids(chunks, order)
    if misses:                                                         # nelze přehrát: nejde měřit, jen hlásit
        return {"run": {"started": datetime.now().isoformat(timespec="seconds"), "git": git_info(), "runtime_s": round(time.time() - t_start, 1)},
                "cache_miss": {str(i): m for i, m in misses.items()}}
    systems = [s for s in replay.SYSTEMS if s in ranks]

    # --- metriky po splitech ---
    retrieval = {}
    for sp in SPLITS:
        retrieval[sp] = {}
        for s in systems:
            ks = (1, 3, 5) if s == "v3_llm_rerank" else (1, 3, 5, 10, 20)     # v3 vrací jen 5 úseků
            sub = {i: ranks[s][i] for i in ids_in[sp]}
            r = M.summarize(sub, {i: golds[i] for i in ids_in[sp]}, ks=ks)
            r.pop("per_question")
            retrieval[sp][s] = r
    per_q = {s: {i: M.first_gold_rank(ranks[s][i], golds[i]) for i in ids_in["all"]} for s in systems}

    # --- párové testy (na všech 56 otázkách, shoda = Recall@5 po otázce) ---
    def r5(s):
        return [M.recall_at_k(ranks[s][i], golds[i], 5) for i in ids_in["all"]]
    paired = {}
    for a, b in [("rrf_v2", "dense_large"), ("rrf_v2", "rrf_dense_bm25"), ("rrf_v2", "rrf_dense_rewrite"),
                 ("rrf_v2", "weighted_v2"), ("v3_llm_rerank", "rrf_v2")]:
        if a in ranks and b in ranks:
            paired[f"{a} vs {b}"] = M.sign_test(r5(a), r5(b))
    if "dense_base" in ranks:
        paired["dense_large vs dense_base"] = M.sign_test(r5("dense_large"), r5("dense_base"))

    # --- RRF: parametr k ---
    rrf_k = {}
    for k in RRF_KS:
        rk = {}
        for i in ids_in["all"]:
            c = comps[i]
            t = lambda s: rag.top(s, replay.DEPTH)
            rk[i] = _ids(chunks, [x for x, _ in rag.rrf([t(c["d_q"]), t(c["d_rw"]), t(c["b_rw"])], k)][:replay.DEPTH])
        s = M.summarize(rk, golds, ks=(5,))
        rrf_k[str(k)] = {m: s["metrics"][m] for m in ("recall@5", "mrr")}

    # --- reranking: žádný / cross-encoder / LLM (uložené výsledky, 20 kandidátů z RRF) ---
    rc = json.loads((datasets.DATA / "rerank_compare.json").read_text(encoding="utf-8"))
    rerank = {}
    for key, label in (("rrf5", "bez výběru (prvních 5 z RRF)"), ("ce", "cross-encoder bge-reranker-v2-m3"), ("llm", "LLM výběr (deepseek-v4.1-flash)")):
        hit = [float(r[key] is not None) for r in rc["rows"]]
        mrr = [(1.0 / r[key]) if r[key] else 0.0 for r in rc["rows"]]
        rerank[key] = {"label": label, "n": len(hit), "hit@5": dict(zip(("mean", "ci95"), (lambda m, lo, hi: (round(m, 4), [round(lo, 4), round(hi, 4)]))(*M.bootstrap_ci(hit)))),
                       "mrr@5": dict(zip(("mean", "ci95"), (lambda m, lo, hi: (round(m, 4), [round(lo, 4), round(hi, 4)]))(*M.bootstrap_ci(mrr))))}
    rerank["paired_llm_vs_ce"] = M.sign_test([float(r["llm"] is not None) for r in rc["rows"]], [float(r["ce"] is not None) for r in rc["rows"]])
    rerank["cross_encoder_s_na_otazku_cpu"] = rc["cross_encoder_s_na_otazku_cpu"]

    # --- odpovědi (uložené běhy v1/v2/v3 + ruční kontrola) ---
    ev, man = evaluate.load("eval.json"), evaluate.load("manual_review.json")
    cid_text = {c["id"]: c["text"] for c in chunks}
    answers = {}
    for v in evaluate.VERSIONS:
        rows = ev[v]["rows"]
        fin = evaluate.final(rows, man.get(v, {}))
        per = {}
        for sp in SPLITS:
            sel = [r for r in rows if sp == "all" or split_of[r["id"]] == sp]
            ans_r = [r for r in sel if r["chunks"]]
            una_r = [r for r in sel if not r["chunks"]]
            det = []
            for r in sel:
                supplied = [cid_text[t["id"]] if isinstance(t, dict) else cid_text[t] for t in r["top"]]
                det.append(ac.check(r["answer"], supplied, r["q"]))
            p, lo, hi = M.wilson_interval(sum(fin[r["id"]] for r in sel), len(sel))
            per[sp] = {
                "n": len(sel), "correct": sum(fin[r["id"]] for r in sel), "correct_ci95": [round(lo, 3), round(hi, 3)],
                "answerable": len(ans_r), "answerable_correct": sum(fin[r["id"]] for r in ans_r),
                "false_refusals": sum(r["said_nevim"] for r in ans_r),                          # odmítl, i když odpověď v zákoně byla
                "unanswerable": len(una_r), "correct_refusals": sum(r["said_nevim"] for r in una_r),
                "answered_without_source": sum(not r["said_nevim"] for r in una_r),            # měl odmítnout a neodmítl
                "judge_grounded": sum(bool(r["judge"]["grounded"]) for r in sel),
                "det_bad_citation": sum(bool(d["bad_citations"]) for d in det),
                "det_no_citation": sum(d["no_citation"] for d in det),
                "det_unsupported_number": sum(bool(d["unsupported_numbers"]) for d in det),
                "det_misattributed_number": sum(bool(d["misattributed_numbers"]) for d in det),
                "det_number_in_no_chunk": sum(bool(d["numbers_in_no_chunk"]) for d in det),
            }
            if sp == "all":
                per[sp]["flagged"] = [{"id": r["id"], "misattributed": d["misattributed_numbers"], "in_no_chunk": d["numbers_in_no_chunk"], "cited": d["cited"]}
                                  for r, d in zip(sel, det) if d["unsupported_numbers"]]
        answers[v] = {"model": ev[v]["model"], "cost_usd_full_run": ev[v]["cost_usd_full"], "per_split": per,
                      "final": {str(r["id"]): bool(fin[r["id"]]) for r in rows}}
    transitions = {}
    for a, b in (("v1", "v2"), ("v2", "v3")):
        fa, fb = answers[a]["final"], answers[b]["final"]
        transitions[f"{a}->{b}"] = {"fixed": sorted(int(i) for i in fa if not fa[i] and fb[i]), "regressed": sorted(int(i) for i in fa if fa[i] and not fb[i])}

    # --- provoz ---
    sample = [q["q"] for q in answerable if q["split"] == "dev"][:20]
    n_q = len(qs)
    ops = {
        "cost_per_question_usd": {v: round(answers[v]["cost_usd_full_run"] / n_q, 5) for v in evaluate.VERSIONS},
        "cost_note": "cena zahrnuje volání odpovědi i AI soudce při měření; ceny z odpovědí OpenRouteru uložených v cache",
        "retrieval_compute_latency": replay.retrieval_latency(sample),
        "latency_note": "jen výpočet hledání z cache (matice × vektor, BM25, RRF). Volání LLM a embedding API tu nejsou: p50/p95 celé služby se offline změřit nedá.",
    }

    # --- záznam o běhu ---
    record = {
        "run": {"started": datetime.now().isoformat(timespec="seconds"), "git": git_info(), "mode": "offline replay z cache (0 $)",
                "python": platform.python_version(), "numpy": np.__version__, "platform": f"{platform.system()} {platform.machine()}",
                "runtime_s": None, "cost_usd": 0.0},
        "config": {"embedding": rag.EMB_MODEL, "embedding_v1": rag.EMB_MODEL_V1, "llm_rewrite_rerank": rag.LLM_MODEL, "llm_answer": rag.ANSWER_MODEL,
                   "top_k": rag.TOP_K, "n_candidates": rag.N_CAND, "rrf_k": 60, "weighted_bm25_weight_from_dev": w_best,
                   "prompt_hashes": prompt_hashes(), "bootstrap": {"n": 10000, "alpha": 0.05, "seed": 0}},
        "datasets": datasets.fingerprint(),
        "n": {"questions": len(qs), "answerable": len(answerable), **{f"answerable_{s}": len(ids_in[s]) for s in ("dev", "validation", "test")}},
        "weighted_fusion_weight_search_on_dev": [{"w_bm25": w, "mrr": round(m, 4)} for w, m in w_table],
        "retrieval": retrieval, "paired_tests_recall5_all": paired, "rrf_k_sweep": rrf_k, "rerank": rerank,
        "answers": answers, "transitions": transitions, "ops": ops,
        "per_question_first_gold_rank": {s: {str(i): r for i, r in v.items()} for s, v in per_q.items()},
        "candidates_top20": {s: {str(i): ranks[s][i][:rag.N_CAND] for i in ids_in["all"]} for s in ("dense_base", "rrf_v2") if s in ranks},
    }
    record["run"]["runtime_s"] = round(time.time() - t_start, 1)
    return record


# ---------- porovnání s referenčním stavem ----------
def regressions(rec: dict, base: dict) -> list[str]:
    """Co je horší než v baseline. Hledání z cache je deterministické, takže tolerance je nulová:
    jakýkoli pokles pořadí správného úseku u finálního systému je změna kódu, ne náhoda."""
    out = []
    a, b = rec["per_question_first_gold_rank"].get("v3_llm_rerank", {}), base["per_question_first_gold_rank"].get("v3_llm_rerank", {})
    for i, rb in b.items():
        ra = a.get(i)
        found_b, found_a = rb is not None and rb <= rag.TOP_K, ra is not None and ra <= rag.TOP_K
        if found_b and not found_a:
            out.append(f"otázka {i}: správný úsek byl v 5 úsecích pro model a teď tam není (pořadí {rb} -> {ra})")
        elif found_b and found_a and ra > rb:
            out.append(f"otázka {i}: správný úsek klesl z pořadí {rb} na {ra}")
    for sp in SPLITS:
        for m in ("recall@5", "mrr"):
            x = rec["retrieval"][sp]["v3_llm_rerank"]["metrics"][m]["mean"]
            y = base["retrieval"][sp]["v3_llm_rerank"]["metrics"][m]["mean"]
            if x < y - 1e-9:
                out.append(f"{sp}: v3 {m} {y} -> {x}")
    for sys_ in ("rrf_v2", "dense_large", "bm25_rewrite"):
        x = rec["retrieval"]["all"][sys_]["metrics"]["recall@10"]["mean"]
        y = base["retrieval"]["all"][sys_]["metrics"]["recall@10"]["mean"]
        if x < y - 1e-9:
            out.append(f"all: {sys_} recall@10 {y} -> {x}")
    return out


def save(rec: dict) -> Path:
    d = RESULTS / "runs"
    d.mkdir(parents=True, exist_ok=True)
    p = d / (datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def main(argv: list[str]) -> int:
    os.environ["RAG_OFFLINE"] = "1"                                    # žádné volání API, nikdy
    rec = run(with_base="--no-base" not in argv)
    if "cache_miss" in rec:
        print(f"NELZE PŘEHRÁT: u {len(rec['cache_miss'])} otázek se změnil vstup modelu, uložená odpověď se nehodí.")
        print("Změna ovlivnila kandidáty (hledání před výběrem). Kvalitu takové změny jde ověřit jen živým měřením (tools/evaluate.py, stojí peníze).")
        for i, m in list(rec["cache_miss"].items())[:5]:
            print(f"  - otázka {i}: {m}")
        return 1
    base_file = RESULTS / "baseline.json"
    base = json.loads(base_file.read_text(encoding="utf-8")) if base_file.exists() else None
    rec["regressions"] = regressions(rec, base) if base else []
    if "--save-baseline" in argv:
        RESULTS.mkdir(exist_ok=True)
        base_file.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print("baseline uložena:", base_file)
    if "--check" not in argv:
        print("záznam:", save(rec))
        import make_docs
        make_docs.write_benchmark(rec)
        make_docs.write_gallery(rec)
    v3 = rec["retrieval"]["all"]["v3_llm_rerank"]["metrics"]
    print(f"v3 recall@5 {v3['recall@5']['mean']}  mrr {v3['mrr']['mean']}  (n={rec['n']['answerable']}, {rec['run']['runtime_s']} s)")
    if rec["regressions"]:
        print("REGRESE:")
        for r in rec["regressions"]:
            print("  -", r)
        return 1
    print("bez regresí" + ("" if base else " (baseline zatím není)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
