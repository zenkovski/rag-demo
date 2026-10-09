# -*- coding: utf-8 -*-
"""Seznam připravených otázek pro site/api/hit.js. Počítadlo kliků přijme jen otázku z tohoto seznamu,
takže si do Redisu nikdo nemůže nasypat vlastní řetězce (jinak by šlo databázi zaplnit unikátními klíči).
  python tools/make_presets.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))
presets = sorted({q["q"][:200].strip() for q in data["questions"]})
(ROOT / "site" / "api" / "_presets.json").write_text(json.dumps(presets, ensure_ascii=False, indent=0), encoding="utf-8")
print(len(presets), "připravených otázek -> site/api/_presets.json")
