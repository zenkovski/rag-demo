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
EMB_MODEL_V1 = "intfloat/multilingual-e5-base"   # v1: lokálně přes sentence-transformers (Hugging Face)
EMB_MODEL = "intfloat/multilingual-e5-large"     # v2: přes OpenRouter API, aby stejný model běžel i na webu
LLM_MODEL = "deepseek/deepseek-v4.1-flash"       # přes OpenRouter, ~0,05 $ / 1M vstupních tokenů
TOP_K = 5                                        # kolik úseků dostane model jako podklad
MODES = ("dense", "dense_large", "hybrid", "hybrid_rewrite", "hybrid_rerank")   # v1 = dense, v2 = hybrid_rewrite, v3 = hybrid_rerank
MODE = "hybrid_rerank"
N_CAND = 20                                      # v3: kolik kandidátů z RRF dostane LLM k výběru

# ---------- data a embeddingy ----------
def load_chunks():
    return json.loads((ROOT / "data" / "chunks.json").read_text(encoding="utf-8"))["chunks"]

def passage(c):
    # E5 modely chtějí předponu "passage: " u dokumentů a "query: " u otázek
    return f"passage: {c['id']} {c['title']}. {c['text']}"

_model = None
def embedder():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMB_MODEL_V1)
    return _model

def embed_api(texts):
    """Embeddingy přes OpenRouter (e5-large). Výsledky se ukládají, opakovaný běh nic nestojí."""
    import requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    cache_file = ROOT / "data" / "emb_cache.npz"
    cache = dict(np.load(cache_file)) if cache_file.exists() else {}
    todo = [t for t in dict.fromkeys(texts) if t not in cache]
    for i in range(0, len(todo), 64):
        batch = todo[i:i + 64]
        r = requests.post("https://openrouter.ai/api/v1/embeddings", timeout=120,
                          headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                          json={"model": EMB_MODEL, "input": batch})
        r.raise_for_status()
        for t, d in zip(batch, r.json()["data"]):
            v = np.array(d["embedding"], dtype=np.float32)
            cache[t] = v / np.linalg.norm(v)
    if todo:
        np.savez(cache_file, **cache)
    return np.stack([cache[t] for t in texts])

def quantize(vecs):
    """Vektory na int8 + 1 měřítko na vektor (4× menší soubor pro webovou funkci).
    Python i web počítají se stejnými zaokrouhlenými čísly, takže najdou stejné úseky."""
    scale = (np.abs(vecs).max(axis=1) / 127).astype(np.float32)
    q = np.round(vecs / scale[:, None]).astype(np.int8)
    return q, scale

def dequantize(q, scale):
    """Zpět na float32 a znovu na délku 1 (kosinová podobnost = skalární součin, stejně jako v LangChainu)."""
    v = q.astype(np.float32) * scale[:, None]
    return (v / np.linalg.norm(v.astype(np.float64), axis=1)[:, None]).astype(np.float32)

_index = {}
def index(model="large"):
    """Matice vektorů všech úseků (normalizované -> cosine = skalární součin)."""
    if model not in _index:
        if model == "large":
            _index[model] = dequantize(*quantize(embed_api([passage(c) for c in load_chunks()])))
        else:
            p = ROOT / "data" / "embeddings.npy"
            if not p.exists():
                vecs = embedder().encode([passage(c) for c in load_chunks()], normalize_embeddings=True, batch_size=16)
                np.save(p, vecs.astype(np.float32))
            _index[model] = np.load(p)
    return _index[model]

def dense_scores(text, model="large"):
    if model == "large":
        q = embed_api([f"query: {text}"])[0]
    else:
        q = embedder().encode([f"query: {text}"], normalize_embeddings=True)[0].astype(np.float32)
    return index(model) @ q                            # cosine podobnost se všemi úseky

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
REWRITE = """Přepiš otázku laika do formulace, jakou by použil český právní předpis (zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění).
Použij odborné právní pojmy místo hovorových slov. Nic nepřidávej a na otázku neodpovídej.
Vrať jen jednu přepsanou větu."""

def rewrite(question, reasoning=True):
    text, _ = llm(REWRITE, question, reasoning=reasoning)
    return text.strip().strip('"').splitlines()[0] if text.strip() else question

# ---------- vyhledávání ----------
def rrf(rankings, k=60):
    """Reciprocal rank fusion: úsek, který je vysoko ve více pořadích, vyhraje.
    Vrací [(index, skóre)] seřazené od nejlepšího (při shodě vyhrává dřív viděný úsek)."""
    score = {}
    for ranking in rankings:
        for rank, i in enumerate(ranking):
            score[i] = score.get(i, 0) + 1 / (k + rank + 1)
    return sorted(score.items(), key=lambda x: -x[1])

def top(scores, n=50):
    """Pořadí indexů od nejvyššího skóre; stabilní řazení, nulová skóre se nepočítají."""
    order = np.argsort(-scores, kind="stable")
    return [int(i) for i in order[:n] if scores[i] > 0]

RERANK = """Dostaneš otázku a očíslované úseky českých právních předpisů.
Vyber úseky, které jsou potřeba k odpovědi na otázku, nejvýše 5, nejdůležitější první.
Když odpověď potřebuje víc odstavců (třeba délku i výši dávky, nebo pravidlo i jeho výjimku), vyber všechny.
Vrať jen čísla úseků oddělená čárkou, např.: 3, 1, 7. Když žádný úsek k otázce nepatří, vrať 0."""

def rerank_prompt(question, rewritten, cands, chunks):
    return f"Otázka: {question}\nV jazyce zákona: {rewritten}\n\nÚseky:\n" + "\n".join(
        f"[{n}] {chunks[i]['id']} ({chunks[i]['title']}): {chunks[i]['text'][:400]}" for n, i in enumerate(cands, 1))

def parse_pick(text, n):
    """Čísla z odpovědi modelu -> pořadí kandidátů (bez opakování, jen platná, nejvýše 5)."""
    out = []
    for m in re.findall(r"\d+", text):
        x = int(m)
        if 1 <= x <= n and x - 1 not in out:
            out.append(x - 1)
    return out[:TOP_K]

def rerank(question, rewritten, cands):
    """v3: LLM přečte 20 kandidátů z RRF a vybere ty, které k odpovědi opravdu patří."""
    text, _ = llm(RERANK, rerank_prompt(question, rewritten, cands, load_chunks()), reasoning=False)
    return [cands[j] for j in parse_pick(text, len(cands))]

def search(question, k=TOP_K, mode=MODE, trace=False):
    """Vrátí (hits, přepsaná otázka[, stopa]). hits = [(index úseku, cosine podobnost s otázkou), ...]
    stopa = mezikroky pro vizualizaci "přemýšlení" na webu (co našel který způsob hledání)."""
    model = "base" if mode == "dense" else "large"
    d = dense_scores(question, model)
    rewritten, rankings, steps, fused = None, [], {}, []
    if mode in ("dense", "dense_large"):
        order = [(i, 0.0) for i in top(d, len(d))]
    else:
        rankings.append(top(d)); steps["dense_q"] = rankings[-1]           # význam: původní otázka
        if mode in ("hybrid_rewrite", "hybrid_rerank"):
            rewritten = rewrite(question, reasoning=mode != "hybrid_rerank")   # v3 bez skrytého přemýšlení
            rankings.append(top(dense_scores(rewritten))); steps["dense_rw"] = rankings[-1]   # význam: přepsaná
        # slova: jen z otázky v jazyce zákona; laická slova ("výplata") v zákoně nejsou a přidávají šum
        rankings.append(top(bm25_scores(rewritten or question))); steps["bm25"] = rankings[-1]
        order = fused = rrf(rankings)
    if mode == "hybrid_rerank":
        cands = [i for i, _ in fused[:N_CAND]]
        picked = rerank(question, rewritten, cands)
        steps["rerank"] = picked
        # vybrané první, zbytek do 5 doplní pořadí z RRF (model dostane vždy 5 úseků)
        order = [(i, 0.0) for i in picked] + [(i, s) for i, s in fused if i not in picked]
    hits = [(int(i), float(d[i])) for i, _ in order[:k]]
    if not trace:
        return hits, rewritten
    steps = {name: lst[:20] for name, lst in steps.items()}
    steps["fused"] = [[int(i), round(sc, 5)] for i, sc in fused[:N_CAND]]
    return hits, rewritten, steps

# ---------- LLM ----------
COST = 0.0                                       # součet ceny volání (i z cache), pro výpočet ceny měření
def llm(system, user, model=None, reasoning=True):
    """Jedno volání jazykového modelu přes OpenRouter. Klíč se čte z .env (nikdy není v kódu).
    reasoning=False vypne skryté přemýšlení modelu (v3): stejná úloha za ~1/10 času i ceny."""
    import time, hashlib, requests
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    model = model or LLM_MODEL
    # cache: stejný model + stejný vstup = uložená odpověď (opakovaný běh nic nestojí a čísla se nemění)
    cache_file = ROOT / "data" / "llm_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    global COST
    key = hashlib.sha256((f"{model}|{system}|{user}|False" + ("" if reasoning else "|noreason")).encode()).hexdigest()
    if key in cache:
        COST += cache[key]["usage"].get("cost") or 0
        return cache[key]["text"], cache[key]["usage"]
    body = {"model": model, "temperature": 0,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if not reasoning:
        body["reasoning"] = {"enabled": False}
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
        COST += usage.get("cost") or 0
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        return text, usage
    raise RuntimeError(f"OpenRouter: {r.status_code} {r.text[:200]}")

SYSTEM = """Jsi asistent, který odpovídá na otázky o českém pracovním právu: zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění a nařízení vlády o překážkách v práci.
Pravidla:
1. Odpovídej POUZE z dodaných úseků zákona. Nic nedoplňuj z vlastní paměti.
2. Každé tvrzení musí přímo vyplývat z úseku, který za ním citujete. Citace piš ve tvaru [1], [2].
3. Úseky mohou mluvit o jiné situaci nebo jiném typu smlouvy, než na který se ptá otázka. Takové úseky nepoužívej.
4. Když si nejsi jistý, jestli úsek tvrzení podporuje, tvrzení vynech.
5. Pokud úseky na otázku neodpovídají, napiš přesně: "Nevím, v dostupných úsecích zákona to není." a nic dalšího.
Piš česky, stručně (2–4 věty), srozumitelně pro laika. Bez nadpisů a bez tučného písma."""

SYSTEM_V1 = """Jsi asistent, který odpovídá na otázky o českém pracovním právu: zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění a nařízení vlády o překážkách v práci.
Odpovídej POUZE z dodaných úseků zákona. Nic si nedomýšlej z vlastní paměti.
Za každou větu, která vychází z úseku, dej citaci ve tvaru [1], [2] podle čísla úseku.
Pokud úseky na otázku neodpovídají, napiš přesně: "Nevím, v dostupných úsecích zákona to není." a nic dalšího.
Piš česky, stručně (2–5 vět), srozumitelně pro laika."""

SYSTEM_V3 = SYSTEM.replace("Piš česky, stručně", """6. Když se pravidla v úsecích liší podle skupiny (mzda u soukromého zaměstnavatele × plat ve státní sféře, mladistvý × dospělý, DPP × DPČ) a otázka neříká, která skupina platí, uveď varianty zvlášť: „Pokud …, pak … [n]. Pokud …, pak … [m].“
7. Když jde otázku pochopit víc způsoby, odpověz krátce na každý význam zvlášť a na konci se jednou větou zeptej, který měl uživatel na mysli.
8. Zachovej přesný význam povinností: „je povinen“ = musí, „není povinen“ = nemusí (to neznamená „nesmí“), „nesmí“ = zákaz. Čísla, procenta a lhůty opiš přesně.
Piš česky, stručně""")

def note(c):
    """v3: komu úsek platí. Zákoník práce má zvlášť mzdu (firmy, § 113–121) a plat (stát, § 122–137)."""
    m = re.match(r"\d+", c.get("para") or "")
    if c.get("law") != "ZP" or not m:
        return ""
    n = int(m.group())
    if 113 <= n <= 121:
        return " · platí pro mzdu (soukromý zaměstnavatel)"
    if 122 <= n <= 137:
        return " · platí pro plat (stát, kraje, obce, státní organizace)"
    return ""

def context(hits, chunks, notes=False):
    return "\n\n".join(f"[{n}] {chunks[i]['id']} ({chunks[i]['title']}{note(chunks[i]) if notes else ''}): {chunks[i]['text']}"
                       for n, (i, _) in enumerate(hits, 1))

def answer(question, hits, chunks, system=None, model=None):
    system = system or SYSTEM_V3
    ctx = context(hits, chunks, notes=system == SYSTEM_V3)
    text, usage = llm(system, f"Úseky zákona:\n\n{ctx}\n\nOtázka: {question}", model, reasoning=system != SYSTEM_V3)
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
