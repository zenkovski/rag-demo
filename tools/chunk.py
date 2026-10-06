# -*- coding: utf-8 -*-
"""Krok 2: stáhne zákoník práce a rozdělí ho na úseky (1 úsek = 1 odstavec paragrafu).
Spuštění:  .venv/Scripts/python tools/chunk.py   ->  data/chunks.json"""
import json, re, datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
URL = "https://www.zakonyprolidi.cz/cs/2006-262"
RAW = ROOT / "data" / "raw" / "zp.html"

# Vybraná témata = rozsahy paragrafů (podmnožina, ať je demo zvládnutelné)
TOPICS = [
    ("Vznik a zkušební doba", 33, 39),
    ("Skončení pracovního poměru, výpověď, odstupné", 48, 73),
    ("Dohody o pracích mimo pracovní poměr", 74, 77),
    ("Pracovní doba, přestávky, odpočinek, přesčas", 78, 100),
    ("Dovolená", 211, 223),
]

def topic_of(num):
    for name, a, b in TOPICS:
        if a <= num <= b:
            return name
    return None

def clean(el):
    for n in el.select(".linknote, sup"):   # odkazy na poznámky pod čarou pryč
        n.decompose()
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()

def main():
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text, encoding="utf-8")
    soup = BeautifulSoup(RAW.read_text(encoding="utf-8"), "html.parser")
    version = next(t.strip() for t in soup.find_all(string=re.compile(r"Aktuální znění")))

    chunks, seen = [], set()
    para = None          # aktuální § (číslo + písmeno, např. "52" nebo "39a")
    title = ""           # nadpis nad paragrafem
    current = None       # rozpracovaný úsek
    for el in soup.select("div.Frags > *"):
        cls = el.get("class") or []
        text = clean(el)
        if "PARA" in cls:                                  # nový paragraf
            m = re.match(r"§\s*(\d+)([a-z]?)$", text)
            current = None
            if not m:
                para = None
                continue
            para = m.group(1) + m.group(2)
            num = int(m.group(1))
            if para in seen or topic_of(num) is None:      # bereme jen 1. výskyt a jen vybraná témata
                para = None
                continue
            seen.add(para)
            # nadpis: hledej nejbližší NADPIS hned před nebo hned za §
            prev, nxt = el.find_previous_sibling(), el.find_next_sibling()
            if nxt is not None and "NADPIS" in (nxt.get("class") or []):
                title = clean(nxt)
            elif prev is not None and "NADPIS" in (prev.get("class") or []):
                title = clean(prev)
            # jinak platí nadpis z předchozího paragrafu (nadpis nad více §)
            continue
        if para is None or "NADPIS" in cls or not text:
            continue
        if any(c in cls for c in ("HLAVA", "DIL", "CAST", "ODDIL")):
            para = None                                    # konec paragrafu
            continue
        m = re.match(r"\((\d+)\)\s*", text)
        if m or current is None:                           # nový odstavec (nebo § bez odstavců)
            odst = m.group(1) if m else None
            cid = f"§ {para}" + (f" odst. {odst}" if odst else "")
            current = {"id": cid, "para": para, "odst": odst, "title": title,
                       "topic": topic_of(int(re.match(r"\d+", para).group())), "text": text}
            chunks.append(current)
        else:                                              # písmena a), b)… patří k odstavci
            current["text"] += " " + text

    chunks = [c for c in chunks if "zrušen" not in c["text"][:20].lower()]
    out = {"source": URL, "version": version, "downloaded": datetime.date.today().isoformat(),
           "chunks": chunks}
    (ROOT / "data" / "chunks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{version} | úseků: {len(chunks)} | paragrafů: {len(seen)}")

if __name__ == "__main__":
    main()
