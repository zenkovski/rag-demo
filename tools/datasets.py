# -*- coding: utf-8 -*-
"""Načtení testovacích otázek s rolí (dev / validation / test) a otisk dat pro záznam o běhu."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def splits() -> dict:
    return json.loads((DATA / "splits.json").read_text(encoding="utf-8"))


def questions(include_planned: bool = False) -> list[dict]:
    """Všechny otázky (id, q, gold, chunks, set, split). chunks = [] znamená, že správná odpověď je „nevím“."""
    sp = splits()
    out = []
    for name, meta in sp["sets"].items():
        for t in json.loads((DATA / meta["file"]).read_text(encoding="utf-8")):
            out.append({**t, "set": name, "split": meta["role"]})
    if include_planned:
        for name, meta in sp.get("planned", {}).items():
            f = DATA / meta["file"]
            if f.exists():
                out += [{**t, "set": name, "split": meta["role"]} for t in json.loads(f.read_text(encoding="utf-8"))]
    return out


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def fingerprint() -> dict:
    """Otisky souborů, na kterých běh proběhl (když se data změní, změní se i otisk)."""
    sp = splits()
    files = ["chunks.json", "splits.json"] + [m["file"] for m in sp["sets"].values()] + [m["file"] for m in sp.get("planned", {}).values() if (DATA / m["file"]).exists()]
    return {f: sha256(DATA / f) for f in files}
