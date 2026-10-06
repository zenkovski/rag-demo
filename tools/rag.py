# -*- coding: utf-8 -*-
"""Jádro RAG: vyhledání úseků (embeddingy + cosine) a odpověď s citacemi (LLM přes OpenRouter).
Vyzkoušení:  .venv/Scripts/python tools/rag.py "Kolik mám dovolené?" """
import json, os, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EMB_MODEL = "intfloat/multilingual-e5-base"   # vícejazyčný model z Hugging Face, umí češtinu
LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"   # zdarma přes OpenRouter (Ultra free byl přetížený)
TOP_K = 5                                       # kolik úseků dostane model jako podklad

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
    chunks = load_chunks()
    vecs = embedder().encode([passage(c) for c in chunks], normalize_embeddings=True,
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

def search(question, k=TOP_K):
    """Vrátí k nejpodobnějších úseků: [(index, skóre), ...]"""
    q = embedder().encode([f"query: {question}"], normalize_embeddings=True)[0]
    scores = index() @ q                              # cosine podobnost se všemi úseky
    top = np.argsort(-scores)[:k]
    return [(int(i), float(scores[i])) for i in top]

SYSTEM = """Jsi asistent, který odpovídá na otázky o českém zákoníku práce.
Odpovídej POUZE z dodaných úseků zákona. Nic si nedomýšlej z vlastní paměti.
Za každou větu, která vychází z úseku, dej citaci ve tvaru [1], [2] podle čísla úseku.
Pokud úseky na otázku neodpovídají, napiš přesně: "Nevím, v dostupných úsecích zákona to není." a nic dalšího.
Piš česky, stručně (2–5 vět), srozumitelně pro laika."""

def llm(system, user, json_mode=False):
    """Jedno volání jazykového modelu přes OpenRouter. Klíč se čte z .env (nikdy není v kódu)."""
    import time, hashlib, requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    # cache: stejná otázka + stejné úseky = uložená odpověď (opakovaný běh nic nevolá a čísla se nemění)
    cache_file = ROOT / "data" / "llm_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    key = hashlib.sha256(f"{LLM_MODEL}|{system}|{user}|{json_mode}".encode()).hexdigest()
    if key in cache:
        return cache[key]["text"], cache[key]["usage"]
    body = {"model": LLM_MODEL, "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    for attempt in range(8):                       # free modely bývají přetížené -> počkej a zkus znovu
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

def answer(question, hits, chunks):
    ctx = "\n\n".join(f"[{n}] {chunks[i]['id']} ({chunks[i]['title']}): {chunks[i]['text']}"
                      for n, (i, _) in enumerate(hits, 1))
    text, usage = llm(SYSTEM, f"Úseky zákona:\n\n{ctx}\n\nOtázka: {question}")
    # model občas píše citace jako 【3】 místo [3]; sjednotím formát (obsah se nemění)
    return re.sub(r"【(\d+)】", r"[\1]", text), usage

def cited(text):
    """Čísla citací, která model v odpovědi opravdu použil."""
    return sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})

if __name__ == "__main__":
    chunks = load_chunks()
    q = " ".join(sys.argv[1:]) or "Kolik týdnů dovolené mi náleží?"
    hits = search(q)
    for i, s in hits:
        print(f"{s:.3f}  {chunks[i]['id']:<16} {chunks[i]['text'][:90]}")
    if "--answer" in os.environ.get("RAG_FLAGS", ""):
        text, usage = answer(q, hits, chunks)
        print("\n" + text, "\n", usage)
