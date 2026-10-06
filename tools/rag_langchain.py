# -*- coding: utf-8 -*-
"""Stejný RAG postup jako tools/rag.py, ale postavený v LangChainu (langchain-core 1.x, LCEL).

Proč dvě verze: rag.py je napsaný ručně, aby bylo vidět každý krok. Tahle verze ukazuje totéž
idiomaticky v LangChainu: dokumenty, retrievery, Runnable řetězy a model přes OpenRouter.
langchain-community (kde býval BM25Retriever) se ukončuje, proto jsou retrievery vlastní třídy nad langchain-core.

  .venv/Scripts/python tools/rag_langchain.py "Nezaplatili mi výplatu, můžu odejít?"
  .venv/Scripts/python tools/rag_langchain.py --compare     # stejné výsledky jako rag.py? (56 otázek; --rw i nový přepis)
"""
import json, os, sys
from typing import List
import numpy as np
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
import rag

load_dotenv(rag.ROOT / ".env")
K_EACH = 50                                         # kolik kandidátů vrátí každý retriever (jako v rag.py)

# ---------- dokumenty ----------
CHUNKS = rag.load_chunks()
DOCS = [Document(page_content=c["text"], metadata={"i": i, "id": c["id"], "title": c["title"]}) for i, c in enumerate(CHUNKS)]

class E5Embeddings(Embeddings):
    """e5-large přes OpenRouter. E5 chce předponu "query: " u otázky; dokumenty už předponu "passage: " mají.
    Vektory dokumentů jsou zaokrouhlené na int8 stejně jako v rag.py a na webu, ať všechny tři verze hledají stejně."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return rag.dequantize(*rag.quantize(rag.embed_api(texts))).tolist()
    def embed_query(self, text: str) -> List[float]:
        return rag.embed_api([f"query: {text}"])[0].tolist()

# vektorové úložiště: vektor se počítá z "passage: § … název. text" (stejně jako v rag.py)
STORE = InMemoryVectorStore(E5Embeddings())
STORE.add_texts([rag.passage(c) for c in CHUNKS], metadatas=[{"i": i} for i in range(len(CHUNKS))],
                ids=[str(i) for i in range(len(CHUNKS))])

class VectorRetriever(BaseRetriever):
    """Podle významu: kosinová podobnost v InMemoryVectorStore."""
    k: int = K_EACH
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        return [DOCS[d.metadata["i"]] for d, s in STORE.similarity_search_with_score(query, k=self.k) if s > 0]

class BM25Retriever(BaseRetriever):
    """Podle slov: BM25 se stejnou tokenizací jako rag.py (bez diakritiky, kořen 5 písmen)."""
    k: int = K_EACH
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        s = rag.bm25_scores(query)
        return [DOCS[i] for i in rag.top(s, self.k)]

def rrf(lists: dict) -> List[Document]:
    """Reciprocal rank fusion přes výsledky všech retrieverů (pořadí dokumentů, 1/(60 + pořadí)). Vrací 20 kandidátů."""
    order = rag.rrf([[d.metadata["i"] for d in docs] for docs in lists.values()])
    return [DOCS[i] for i, _ in order[:rag.N_CAND]]

# ---------- modely a prompty ----------
LLM = ChatOpenAI(model=rag.LLM_MODEL, temperature=0, base_url="https://openrouter.ai/api/v1", extra_body={"reasoning": {"enabled": False}},
                 api_key=os.environ["OPENROUTER_API_KEY"])
REWRITE = ChatPromptTemplate.from_messages([("system", rag.REWRITE), ("human", "{q}")])
RERANK = ChatPromptTemplate.from_messages([("system", rag.RERANK), ("human", "{prompt}")])
ANSWER = ChatPromptTemplate.from_messages([("system", rag.SYSTEM_V3), ("human", "Úseky zákona:\n\n{context}\n\nOtázka: {q}")])

def first_line(text: str) -> str:
    return text.strip().strip('"').splitlines()[0] if text.strip() else ""

def context(docs: List[Document]) -> str:
    return rag.context([(d.metadata["i"], 0) for d in docs], CHUNKS, notes=True)

def pick(x: dict) -> List[Document]:
    """Vybrané úseky první, zbytek do 5 doplní pořadí z RRF (jako rag.search)."""
    cands = [d.metadata["i"] for d in x["cands"]]
    chosen = [cands[j] for j in rag.parse_pick(x["pick"], len(cands))]
    return [DOCS[i] for i in (chosen + [i for i in cands if i not in chosen])[:rag.TOP_K]]

vector, bm25 = VectorRetriever(), BM25Retriever()

# ---------- LCEL řetěz: otázka -> přepis -> 3 hledání paralelně -> RRF (20) -> LLM vybere -> odpověď ----------
rewrite_chain = REWRITE | LLM | StrOutputParser() | RunnableLambda(first_line)
search_chain = RunnablePassthrough.assign(cands=RunnableParallel(
    dense_q=RunnableLambda(lambda x: x["q"]) | vector,     # význam: původní otázka
    dense_rw=RunnableLambda(lambda x: x["rw"]) | vector,   # význam: přepsaná otázka
    bm25=RunnableLambda(lambda x: x["rw"]) | bm25,         # slova: přepsaná otázka
) | RunnableLambda(rrf))
rerank_chain = RunnablePassthrough.assign(pick=RunnableLambda(
    lambda x: {"prompt": rag.rerank_prompt(x["q"], x["rw"], [d.metadata["i"] for d in x["cands"]], CHUNKS)})
    | RERANK | LLM | StrOutputParser()) | RunnablePassthrough.assign(docs=RunnableLambda(pick))
retrieve_chain = RunnablePassthrough.assign(rw=rewrite_chain) | search_chain | rerank_chain
answer_chain = retrieve_chain | RunnablePassthrough.assign(
    answer=RunnableLambda(lambda x: {"q": x["q"], "context": context(x["docs"])}) | ANSWER | LLM | StrOutputParser())

def compare(check_rewrite=False):
    """1) Hledání: dostane-li LangChain stejný přepis jako rag.py, najde stejných 20 kandidátů z RRF?
    2) Při stejné odpovědi výběrového modelu (uložená v cache rag.py) vyjde stejných 5 úseků?
    3) --rw: vyjde nové volání přepisu stejně jako uložené? (teplota 0 ≠ vždy stejný text, stojí pár haléřů)"""
    import evaluate
    tests = evaluate.tests()
    same_c = same_h = same_rw = 0
    for t in tests:
        hits, rw, st = rag.search(t["q"], trace=True)            # přepis i výběr z rag.py (uložené)
        out = search_chain.invoke({"q": t["q"], "rw": rw})
        a, b = [d.metadata["i"] for d in out["cands"]], [i for i, _ in st["fused"]]
        same_c += a == b
        pick_text, _ = rag.llm(rag.RERANK, rag.rerank_prompt(t["q"], rw, a, CHUNKS), reasoning=False)   # z cache, zdarma
        same_h += [d.metadata["i"] for d in pick({"cands": out["cands"], "pick": pick_text})] == [i for i, _ in hits]
        if check_rewrite:
            same_rw += rewrite_chain.invoke({"q": t["q"]}) == rw
        if a != b:
            print(f"#{t['id']} rozdíl v kandidátech")
    print(f"kandidáti z RRF (stejný přepis): stejných 20 ve stejném pořadí {same_c}/{len(tests)}")
    print(f"5 úseků pro model (stejný výběr): {same_h}/{len(tests)}")
    if check_rewrite:
        print(f"nový přepis přes LangChain shodný s uloženým: {same_rw}/{len(tests)}")

if __name__ == "__main__":
    if "--compare" in sys.argv:
        compare("--rw" in sys.argv)
    else:
        q = " ".join(sys.argv[1:]) or "Firma mi nezaplatila výplatu, můžu hned odejít?"
        out = answer_chain.invoke({"q": q})
        print("přepis:", out["rw"])
        print("úseky:", [d.metadata["id"] for d in out["docs"]])
        print(out["answer"])
