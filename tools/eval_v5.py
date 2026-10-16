# -*- coding: utf-8 -*-
"""Měření na velké sadě (data/testset_v5.json + zmrazená v4) BEZ placeného API.

Co se mění proti produkci a proč (kvůli ceně, ne kvůli kvalitě):
  - vektor otázky: lokální intfloat/multilingual-e5-large (stejný model jako přes OpenRouter; shodu ověřuje `parity`),
    vektory odstavců zůstávají ty z API (data/emb_cache.npz),
  - kroky s jazykovým modelem (přepis, výběr 5 z 20, odpověď): Claude Sonnet jako podagent Claude Code se STEJNÝMI prompty
    (rag.REWRITE, rag.RERANK, rag.SYSTEM_V3). Výsledek je tedy „řetězec v3 s Claudem“, ne produkční řetězec s DeepSeekem.
Kód hledání (BM25, RRF, pravidla odstavce 1 a odkazů) je beze změny: volá se rag.search.

Postup (každé kolo = soubor úkolů pro podagenta a načtení jeho odpovědí):
  python tools/eval_v5.py export            # najde kroky, které ještě nemají odpověď -> .tmp/v5/tasks.json
  (podagent zapíše .tmp/v5/answers.json: {"<key>": "<text>", ...})
  python tools/eval_v5.py import .tmp/v5/answers.json
  ... opakovat, dokud export nehlásí 0 úkolů (3 kola: přepis, výběr, odpověď)
  python tools/eval_v5.py judge-export      # úkoly pro Claude soudce -> .tmp/v5/judge_tasks.json
  python tools/eval_v5.py judge-import <soubor>
  python tools/eval_v5.py report            # results/eval_v5.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import answer_checks as ac  # noqa: E402
import metrics as M  # noqa: E402
import rag  # noqa: E402

ROOT = rag.ROOT
TMP = ROOT / ".tmp" / "v5"
LLM_CACHE = ROOT / "data" / "llm_cache_claude.json"        # odpovědi Clauda (podagent), odděleně od DeepSeeku
EMB_CACHE = ROOT / "data" / "emb_cache_local.npz"          # lokální vektory otázek
JUDGE_FILE = ROOT / "data" / "judge_v5_claude.json"
OUT = ROOT / "results" / "eval_v5.json"
SETS = {"v5": "testset_v5.json", "v4": "testset_heldout_v4.json"}
LLM_NAME = "claude-sonnet (Claude Code subagent, same prompts)"


class Missing(Exception):
    """Krok potřebuje odpověď modelu, která zatím není v cache."""


def questions() -> list[dict]:
    out = []
    for name, f in SETS.items():
        out += [{**q, "set": name} for q in json.loads((ROOT / "data" / f).read_text(encoding="utf-8"))]
    return out


def key(system: str, user: str) -> str:
    return hashlib.sha256(f"claude|{system}|{user}".encode()).hexdigest()


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------- náhrady za placená volání ----------
_model = None
_emb: dict | None = None


def local_embed(texts: list[str]) -> np.ndarray:
    """Vektory otázek lokálně; texty odstavců („passage: …“) z API cache, ať index zůstane stejný jako v produkci."""
    global _model, _emb
    if _emb is None:
        _emb = dict(np.load(EMB_CACHE)) if EMB_CACHE.exists() else {}
    api = rag._emb_cache if rag._emb_cache is not None else dict(np.load(ROOT / "data" / "emb_cache.npz"))
    rag._emb_cache = api
    todo = [t for t in dict.fromkeys(texts) if not t.startswith("passage: ") and t not in _emb]
    if todo:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("intfloat/multilingual-e5-large")
        for t, v in zip(todo, _model.encode(todo, normalize_embeddings=True)):
            _emb[t] = v.astype(np.float32)
        np.savez(EMB_CACHE, **_emb)
    return np.stack([api[t] if t.startswith("passage: ") else _emb[t] for t in texts])


def install(record: list | None = None) -> None:
    """Přesměruje rag.llm na cache Clauda a rag.embed_api na lokální model. Chybějící odpověď = úkol pro podagenta."""
    cache = load_json(LLM_CACHE)

    def llm(system, user, model=None, reasoning=True):
        k = key(system, user)
        if k in cache:
            return cache[k], {}
        if record is not None:
            record.append({"key": k, "system": system, "user": user})
        raise Missing(k)

    rag.llm = llm
    rag.embed_api = local_embed


def run_one(q: dict) -> dict:
    chunks = rag.load_chunks()
    hits, rewritten, steps = rag.search(q["q"], mode="hybrid_rerank", trace=True)
    text, _ = rag.answer(q["q"], hits, chunks)
    return {"hits": [i for i, _ in hits], "rewritten": rewritten, "fused": [i for i, _ in steps["fused"]], "answer": text}


# ---------- příkazy ----------
def export() -> int:
    tasks: list = []
    install(tasks)
    done = 0
    for q in questions():
        try:
            run_one(q)
            done += 1
        except Missing:
            pass
    uniq = list({t["key"]: t for t in tasks}.values())
    TMP.mkdir(parents=True, exist_ok=True)
    (TMP / "tasks.json").write_text(json.dumps(uniq, ensure_ascii=False, indent=1), encoding="utf-8")
    kinds = {"rewrite": rag.REWRITE, "rerank": rag.RERANK}
    by = {n: sum(t["system"] == s for t in uniq) for n, s in kinds.items()}
    by["answer"] = len(uniq) - sum(by.values())
    print(f"hotovo {done}/{len(questions())} otázek, úkolů pro model: {len(uniq)} {by} -> {TMP / 'tasks.json'}")
    return len(uniq)


def import_answers(path: str) -> None:
    new = load_json(Path(path))
    cache = load_json(LLM_CACHE)
    cache.update({k: str(v).strip() for k, v in new.items()})
    LLM_CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"načteno {len(new)}, v cache Clauda celkem {len(cache)}")


def results() -> list[dict]:
    install()
    chunks = rag.load_chunks()
    rows = []
    for q in questions():
        r = run_one(q)
        fast = [i for i, _ in rag.search(q["q"], k=10, mode="dense_large")[0]]
        hybrid = [i for i, _ in rag.search(q["q"], k=10, mode="hybrid")[0]]
        ids = lambda xs: [chunks[i]["id"] for i in xs]
        supplied = [chunks[i]["text"] for i in r["hits"]]
        rows.append({"id": q["id"], "set": q["set"], "type": q.get("type", ""), "q": q["q"], "gold": q["gold"], "gold_chunks": q["chunks"],
                     "fast_top10": ids(fast), "hybrid_top10": ids(hybrid), "candidates20": ids(r["fused"]), "top5": ids(r["hits"]),
                     "rewritten": r["rewritten"], "answer": r["answer"], "checks": ac.check(r["answer"], supplied, q["q"]),
                     "supplied": [{"n": n, "id": chunks[i]["id"], "text": chunks[i]["text"]} for n, i in enumerate(r["hits"], 1)]})
    return rows


def judge_export() -> None:
    tasks = [{"id": r["id"], "q": r["q"], "gold": r["gold"], "answerable": bool(r["gold_chunks"]), "answer": r["answer"], "passages": r["supplied"]}
             for r in results()]
    (TMP / "judge_tasks.json").write_text(json.dumps(tasks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(tasks)} úkolů pro soudce -> {TMP / 'judge_tasks.json'}")


def judge_import(path: str) -> None:
    j = load_json(JUDGE_FILE)
    j.update({str(k): v for k, v in load_json(Path(path)).items()})
    JUDGE_FILE.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"verdiktů celkem {len(j)}")


def report() -> None:
    rows = results()
    judge = load_json(JUDGE_FILE)
    ans = [r for r in rows if r["gold_chunks"]]
    una = [r for r in rows if not r["gold_chunks"]]

    def retr(field: str, k: int) -> dict:
        rec = [M.recall_at_k(r[field], r["gold_chunks"], k) for r in ans]
        mrr = [1 / rk if (rk := M.first_gold_rank(r[field][:k], r["gold_chunks"])) else 0.0 for r in ans]
        m, lo, hi = M.bootstrap_ci(rec)
        return {"recall@%d" % k: round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "mrr@%d" % k: round(float(np.mean(mrr)), 4)}

    verdicts = {r["id"]: judge.get(str(r["id"]), {}) for r in rows}
    correct = [r for r in ans if verdicts[r["id"]].get("verdict") == "correct"]
    refused_ok = [r for r in una if ac.is_abstention(r["answer"])]
    false_refusals = [r for r in ans if ac.is_abstention(r["answer"])]
    judged = sum(1 for v in verdicts.values() if v)
    summary = {
        "llm": LLM_NAME, "query_embedding": "local intfloat/multilingual-e5-large", "n": len(rows), "answerable": len(ans), "unanswerable": len(una),
        "per_set": {s: sum(r["set"] == s for r in rows) for s in SETS},
        "retrieval": {"fast (e5-large, no LLM)": retr("fast_top10", 5), "hybrid (e5 + BM25, no LLM)": retr("hybrid_top10", 5),
                      "candidates20 (after rewrite, before pick)": retr("candidates20", 20), "v3 top5 (Claude pick)": retr("top5", 5)},
        "answers": {"judged": judged, "correct": len(correct), "correct_wilson95": [round(x, 4) for x in M.wilson_interval(len(correct), len(ans))[1:]],
                    "partial": sum(verdicts[r["id"]].get("verdict") == "partial" for r in ans),
                    "wrong": sum(verdicts[r["id"]].get("verdict") == "wrong" for r in ans),
                    "false_refusals": len(false_refusals),
                    "correct_refusals": len(refused_ok), "refusal_wilson95": [round(x, 4) for x in M.wilson_interval(len(refused_ok), len(una))[1:]],
                    "det_bad_citation": sum(bool(r["checks"]["bad_citations"]) for r in rows),
                    "det_no_citation": sum(r["checks"]["no_citation"] for r in rows),
                    "det_unsupported_number": sum(bool(r["checks"]["unsupported_numbers"]) for r in rows)},
    }
    for r in rows:
        r.pop("supplied")
        r["judge"] = verdicts[r["id"]]
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        export()
    elif cmd == "import":
        import_answers(sys.argv[2])
    elif cmd == "judge-export":
        judge_export()
    elif cmd == "judge-import":
        judge_import(sys.argv[2])
    elif cmd == "report":
        report()
    else:
        print(__doc__)
