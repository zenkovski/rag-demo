# -*- coding: utf-8 -*-
"""Jádro RAG: vyhledání úseků a odpověď s citacemi (LLM přes OpenRouter).

Vyhledávání (v2) = hybrid:
  1. LLM přepíše laickou otázku do jazyka zákona ("výplata" -> "mzda"),
  2. pro původní i přepsanou otázku hledám dvakrát: podle významu (embeddingy) a podle slov (BM25),
  3. čtyři pořadí spojím metodou RRF (reciprocal rank fusion) a vezmu top 5.
Vyzkoušení:  .venv/Scripts/python tools/rag.py "Nezaplatili mi výplatu, můžu odejít?" """
import json, math, os, re, sys, unicodedata
from collections import Counter
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EMB_MODEL = "intfloat/multilingual-e5-base"     # vícejazyčný model z Hugging Face, umí češtinu
LLM_MODEL = "deepseek/deepseek-v4.1-flash"      # přes OpenRouter, ~0,05 $ / 1M vstupních tokenů
TOP_K = 5                                       # kolik úseků dostane model jako podklad
MODES = ("dense", "hybrid", "hybrid_rewrite")   # v1 = dense, v2 = hybrid_rewrite
MODE = "hybrid_rewrite"

# ---------- data a embeddingy ----------
_model = None
def embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMB_MODEL)
    return _model

def load_chunks():
    return json.loads((ROOT / "data" / "chunks.json").read_text(encoding="utf-8"))["chunks"]

def passage(c):
    # E5 modely chtějí předponu "passage: " u dokumentů a "query: " u otázek
    return f"passage: {c['id']} {c['title']}. {c['text']}"

def build_index():
    """Spočítá vektor pro každý úsek a uloží je (normalizované -> cosine = skalární součin)."""
    vecs = embedder().encode([passage(c) for c in load_chunks()], normalize_embeddings=True,
                             batch_size=16, show_progress_bar=True)
    np.save(ROOT / "data" / "embeddings.npy", vecs.astype(np.float32))
    return vecs

_index = None
def index():
    global _index
    if _index is None:
        p = ROOT / "data" / "embeddings.npy"
        _index = np.load(p) if p.exists() else build_index()
    return _index

def dense_scores(text):
    q = embedder().encode([f"query: {text}"], normalize_embeddings=True)[0]
    return index() @ q                                 # cosine podobnost se všemi úseky

# ---------- BM25 (hledání podle slov) ----------
STOP = set("a i k o s u v z ve se na do za po od je jsou byl být by aby ale ani nebo když pokud jak kdy kolik "
           "co to ten ta tím tak také jen již už mi mě mne mu jsem jsi jste můžu může mohu musí podle při pro "
           "než jeho jejich který která které této tohoto".split())

def tokens(text):
    """Malá písmena, bez diakritiky, kořen = prvních 5 znaků (hrubý stemmer pro češtinu: mzda/mzdu/mzdy -> mzda/mzdu…)."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    words = re.findall(r"[a-z0-9]+", t)
    raw_stop = {unicodedata.normalize("NFD", s) for s in STOP}
    raw_stop = {"".join(ch for ch in s if unicodedata.category(ch) != "Mn") for s in raw_stop}
    return [w[:5] for w in words if len(w) > 2 and w not in raw_stop]

_bm25 = None
def bm25_scores(text, k1=1.5, b=0.75):
    global _bm25
    if _bm25 is None:
        docs = [Counter(tokens(f"{c['title']} {c['text']}")) for c in load_chunks()]
        lens = np.array([sum(d.values()) for d in docs], dtype=float)
        df = Counter(w for d in docs for w in d)
        _bm25 = (docs, lens, df)
    docs, lens, df = _bm25
    N, avg = len(docs), lens.mean()
    s = np.zeros(N)
    for w in set(tokens(text)):
        if w not in df:
            continue
        idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
        tf = np.array([d.get(w, 0) for d in docs], dtype=float)
        s += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * lens / avg))
    return s

# ---------- přepis otázky ----------
REWRITE = """Přepiš otázku laika do formulace, jakou by použil český zákoník práce.
Použij odborné právní pojmy místo hovorových slov. Nic nepřidávej a na otázku neodpovídej.
Vrať jen jednu přepsanou větu."""

def rewrite(question):
    text, _ = llm(REWRITE, question)
    return text.strip().strip('"').splitlines()[0] if text.strip() else question

# ---------- vyhledávání ----------
def rrf(rankings, k=60):
    """Reciprocal rank fusion: úsek, který je vysoko ve více pořadích, vyhraje."""
    score = Counter()
    for ranking in rankings:
        for rank, i in enumerate(ranking):
            score[i] += 1 / (k + rank + 1)
    return [i for i, _ in score.most_common()]

def search(question, k=TOP_K, mode=MODE):
    """Vrátí (hits, přepsaná otázka). hits = [(index úseku, cosine podobnost s otázkou), ...]"""
    d = dense_scores(question)
    queries, rewritten = [question], None
    if mode == "dense":
        order = list(np.argsort(-d))
    else:
        if mode == "hybrid_rewrite":
            rewritten = rewrite(question)
            queries.append(rewritten)
        rankings = [list(np.argsort(-d)[:50])]                       # význam: původní otázka
        if rewritten:
            rankings.append(list(np.argsort(-dense_scores(rewritten))[:50]))   # význam: přepsaná otázka
        # slova: jen z otázky v jazyce zákona; laická slova ("výplata") v zákoně nejsou a přidávají šum
        rankings.append(list(np.argsort(-bm25_scores(rewritten or question))[:50]))
        order = rrf(rankings)
    return [(int(i), float(d[i])) for i in order[:k]], rewritten

# ---------- LLM ----------
def llm(system, user, model=None):
    """Jedno volání jazykového modelu přes OpenRouter. Klíč se čte z .env (nikdy není v kódu)."""
    import time, hashlib, requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    model = model or LLM_MODEL
    # cache: stejný model + stejný vstup = uložená odpověď (opakovaný běh nic nestojí a čísla se nemění)
    cache_file = ROOT / "data" / "llm_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    key = hashlib.sha256(f"{model}|{system}|{user}|False".encode()).hexdigest()
    if key in cache:
        return cache[key]["text"], cache[key]["usage"]
    body = {"model": model, "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    for attempt in range(8):                       # přetížení / limit -> počkej a zkus znovu
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", timeout=300, json=body,
                          headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"})
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code == 429 or r.status_code >= 500 or "error" in data:   # chyba může přijít i s kódem 200
            time.sleep(min(15 * (attempt + 1), 60))
            continue
        r.raise_for_status()
        text, usage = (data["choices"][0]["message"]["content"] or "").strip(), data.get("usage", {})
        cache[key] = {"text": text, "usage": usage}
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        return text, usage
    raise RuntimeError(f"OpenRouter: {r.status_code} {r.text[:200]}")

SYSTEM = """Jsi asistent, který odpovídá na otázky o českém zákoníku práce.
Pravidla:
1. Odpovídej POUZE z dodaných úseků zákona. Nic nedoplňuj z vlastní paměti.
2. Každé tvrzení musí přímo vyplývat z úseku, který za ním citujete. Citace piš ve tvaru [1], [2].
3. Úseky mohou mluvit o jiné situaci nebo jiném typu smlouvy, než na který se ptá otázka. Takové úseky nepoužívej.
4. Když si nejsi jistý, jestli úsek tvrzení podporuje, tvrzení vynech.
5. Pokud úseky na otázku neodpovídají, napiš přesně: "Nevím, v dostupných úsecích zákona to není." a nic dalšího.
Piš česky, stručně (2–4 věty), srozumitelně pro laika. Bez nadpisů a bez tučného písma."""

SYSTEM_V1 = """Jsi asistent, který odpovídá na otázky o českém zákoníku práce.
Odpovídej POUZE z dodaných úseků zákona. Nic si nedomýšlej z vlastní paměti.
Za každou větu, která vychází z úseku, dej citaci ve tvaru [1], [2] podle čísla úseku.
Pokud úseky na otázku neodpovídají, napiš přesně: "Nevím, v dostupných úsecích zákona to není." a nic dalšího.
Piš česky, stručně (2–5 vět), srozumitelně pro laika."""

def answer(question, hits, chunks, system=SYSTEM, model=None):
    ctx = "\n\n".join(f"[{n}] {chunks[i]['id']} ({chunks[i]['title']}): {chunks[i]['text']}"
                      for n, (i, _) in enumerate(hits, 1))
    text, usage = llm(system, f"Úseky zákona:\n\n{ctx}\n\nOtázka: {question}", model)
    # model občas píše citace jako 【3】 nebo [1][2] slepené; sjednotím formát (obsah se nemění)
    return re.sub(r"【(\d+)】", r"[\1]", text), usage

def cited(text):
    """Čísla citací, která model v odpovědi opravdu použil."""
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})

if __name__ == "__main__":
    chunks = load_chunks()
    q = " ".join(sys.argv[1:]) or "Kolik týdnů dovolené mi náleží?"
    for mode in MODES:
        hits, rw = search(q, mode=mode)
        print(f"\n[{mode}]" + (f"  přepis: {rw}" if rw else ""))
        for i, s in hits:
            print(f"  {s:.3f}  {chunks[i]['id']:<16} {chunks[i]['text'][:80]}")
