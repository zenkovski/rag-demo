# -*- coding: utf-8 -*-
"""Krok 2: stáhne 4 pracovněprávní předpisy a rozdělí je na úseky (1 úsek = 1 odstavec paragrafu).
Spuštění:  .venv/Scripts/python tools/chunk.py   ->  data/chunks.json"""
import json, re, datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent

# zkratka (začátek ID úseku), číslo ve Sbírce, adresa, název
LAWS = [
    ("ZP", "262/2006 Sb.", "https://www.zakonyprolidi.cz/cs/2006-262", "Zákoník práce"),
    ("ZZ", "435/2004 Sb.", "https://www.zakonyprolidi.cz/cs/2004-435", "Zákon o zaměstnanosti"),
    ("ZNP", "187/2006 Sb.", "https://www.zakonyprolidi.cz/cs/2006-187", "Zákon o nemocenském pojištění"),
    ("NV 590", "590/2006 Sb.", "https://www.zakonyprolidi.cz/cs/2006-590", "Nařízení vlády o překážkách v práci"),
]

# Oblasti = kategorie na webu (barva v mapě i filtr otázek). Zákoník práce podle rozsahů paragrafů.
ZP_AREAS = [
    ("Smlouva a zkušební doba", 33, 47),
    ("Výpověď a odstupné", 48, 73),
    ("DPP a DPČ", 74, 77),
    ("Pracovní doba a přesčasy", 78, 100),
    ("Mzda, náhrady a překážky", 109, 190),
    ("Nemoc a rodičovství", 191, 198),
    ("Mzda, náhrady a překážky", 199, 210),
    ("Dovolená", 211, 223),
]
LAW_AREA = {"ZZ": "Nezaměstnanost a úřad práce", "ZNP": "Nemoc a rodičovství", "NV 590": "Mzda, náhrady a překážky"}
OTHER = "Další části zákoníku práce"

def area_of(law, num):
    if law != "ZP":
        return LAW_AREA[law]
    return next((name for name, a, b in ZP_AREAS if a <= num <= b), OTHER)

def clean(el):
    for n in el.select(".linknote, sup"):   # odkazy na poznámky pod čarou pryč
        n.decompose()
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()

def fetch(url):
    raw = ROOT / "data" / "raw" / (url.rsplit("/", 1)[1] + ".html")
    if not raw.exists():
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text, encoding="utf-8")
    return BeautifulSoup(raw.read_text(encoding="utf-8"), "html.parser")

def chunk_law(law, url, law_name):
    soup = fetch(url)
    version = next(t.strip() for t in soup.find_all(string=re.compile(r"Aktuální znění")))
    chunks, seen = [], set()
    para = None          # aktuální § (číslo + písmeno, např. "52" nebo "39a")
    title = ""           # nadpis nad paragrafem
    current = None       # rozpracovaný úsek
    annex = False        # příloha nařízení: úsek = 1 číslovaný bod
    new = lambda cid, odst, text, num: {"id": cid, "law": law, "para": para, "odst": odst, "title": title,
                                        "topic": area_of(law, num), "text": text}
    for el in soup.select("div.Frags > *"):
        cls = el.get("class") or []
        text = clean(el)
        if "AT" in cls:                                    # začátek přílohy
            annex, para, current = True, None, None
            if law != "NV 590":                            # jen příloha nařízení má obsah k otázkám (ZP: katalog platových tříd)
                break
            continue
        if annex:
            m = re.match(r"(\d+)\.\s+(\S.*)", text)
            if m and "L3" in cls:                          # „5. Uzavření manželství“ = nový bod
                title, para = m.group(2), "příloha"
                current = new(f"{law} příloha bod {m.group(1)}", m.group(1), "", 0)
                chunks.append(current)
            elif current is not None and text and "NADPIS" not in cls:
                current["text"] = (current["text"] + " " + text).strip()
            continue
        if "PARA" in cls:                                  # nový paragraf
            m = re.match(r"§\s*(\d+)([a-z]?)$", text)
            current = None
            if not m:
                para = None
                continue
            para = m.group(1) + m.group(2)
            if para in seen:                               # bereme jen 1. výskyt (pozdější jsou z novel)
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
            cid = f"{law} § {para}" + (f" odst. {odst}" if odst else "")
            current = new(cid, odst, text, int(re.match(r"\d+", para).group()))
            chunks.append(current)
        else:                                              # písmena a), b)… patří k odstavci
            current["text"] += " " + text
    # pryč se zrušenými odstavci a se závěrečnými ustanoveními (účinnost, seznamy zrušených předpisů, směrnice EU)
    junk = re.compile(r"^(Účinnost|Zrušovací ustanovení|ZÁVĚREČNÁ USTANOVENÍ|USTANOVENÍ, KTERÝMI SE ZAPRACOVÁVAJÍ)", re.I)
    chunks = [c for c in chunks if c["text"] and "zrušen" not in c["text"][:20].lower() and not junk.match(c["title"])
              and not c["text"].startswith(("Toto nařízení nabývá", "Tento zákon nabývá", "Zrušuje se"))]
    for c in chunks:                                       # pár obřích výčtů zkrátím, ať se vejdou do podkladů pro model
        if len(c["text"]) > 6000:
            c["text"] = c["text"][:6000].rsplit(" ", 1)[0] + " …"
    src = {"law": law, "name": law_name, "url": url, "version": version, "chunks": len(chunks), "paragraphs": len(seen)}
    return chunks, src

def main():
    chunks, sources = [], []
    for law, num, url, name in LAWS:
        c, src = chunk_law(law, url, name)
        src["number"] = num
        chunks += c
        sources.append(src)
        print(f"{law:<7} {num:<13} {src['version']} | úseků: {len(c)} | paragrafů: {src['paragraphs']}")
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "duplicitní ID"
    out = {"sources": sources, "downloaded": datetime.date.today().isoformat(), "chunks": chunks}
    (ROOT / "data" / "chunks.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"celkem úseků: {len(chunks)}")

if __name__ == "__main__":
    main()
