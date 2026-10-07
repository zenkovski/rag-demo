# -*- coding: utf-8 -*-
"""Co lidi na webu hledali: vlastní otázky a kliky na připravené otázky (anonymně, z Upstash Redis).
  .venv/Scripts/python tools/stats.py          # posledních 50 vlastních otázek + nejklikanější připravené
Přístup k Redis: KV_REST_API_URL / KV_REST_API_TOKEN v .env, jinak se načtou z proměnných projektu na Vercelu
(potřebuje VERCEL_TOKEN v .env nebo v ../SecondBrain-OS/.env). Nic nestojí."""
import json, os, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
PROJECT = "lukas-rag"
KEYS = ("KV_REST_API_URL", "KV_REST_API_TOKEN", "UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN")


def dotenv(path):
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def redis_access():
    env = {**dotenv(ROOT.parent / "SecondBrain-OS" / ".env"), **dotenv(ROOT / ".env"), **os.environ}
    url = env.get("KV_REST_API_URL") or env.get("UPSTASH_REDIS_REST_URL")
    tok = env.get("KV_REST_API_TOKEN") or env.get("UPSTASH_REDIS_REST_TOKEN")
    if url and tok:
        return url, tok
    vt = env.get("VERCEL_TOKEN")
    if not vt:
        sys.exit("Chybí přístup k Redis i VERCEL_TOKEN.")
    h = {"Authorization": f"Bearer {vt}"}
    proj = requests.get(f"https://api.vercel.com/v9/projects/{PROJECT}", headers=h, timeout=30).json()
    team = proj.get("accountId")
    envs = requests.get(f"https://api.vercel.com/v9/projects/{proj['id']}/env", headers=h, params={"teamId": team}, timeout=30).json().get("envs", [])
    vals = {}
    for e in envs:
        if e["key"] in KEYS:
            r = requests.get(f"https://api.vercel.com/v1/projects/{proj['id']}/env/{e['id']}", headers=h, params={"teamId": team}, timeout=30).json()
            vals[e["key"]] = r.get("value")
    url = vals.get("KV_REST_API_URL") or vals.get("UPSTASH_REDIS_REST_URL")
    tok = vals.get("KV_REST_API_TOKEN") or vals.get("UPSTASH_REDIS_REST_TOKEN")
    if not (url and tok):
        sys.exit("Projekt na Vercelu zatím nemá připojenou databázi Upstash Redis.")
    return url, tok


def main():
    url, tok = redis_access()
    cmds = [["LRANGE", "rag:live", "0", "49"], ["LLEN", "rag:live"], ["HGETALL", "rag:preset"], ["HGETALL", "rag:src"]]
    res = requests.post(url + "/pipeline", headers={"Authorization": f"Bearer {tok}"}, json=cmds, timeout=30).json()
    live, n_live, preset, src = (r.get("result") for r in res)
    pairs = lambda flat: sorted(((flat[i], int(flat[i + 1])) for i in range(0, len(flat or []), 2)), key=lambda x: -x[1])
    print(f"\nVlastní otázky celkem: {n_live} (posledních {len(live)}, nejnovější nahoře)")
    for raw in live:
        d = json.loads(raw)
        print(f"  {d['t'][:16].replace('T', ' ')}  {'[nevím] ' if d.get('nevim') else ''}{d['q']}")
    print("\nZdroj kliků: " + ", ".join(f"{k} {v}" for k, v in pairs(src)) if src else "\nZdroj kliků: zatím nic")
    print("\nNejklikanější připravené otázky:")
    for q, n in pairs(preset)[:25]:
        print(f"  {n:>4}×  {q}")


if __name__ == "__main__":
    main()
