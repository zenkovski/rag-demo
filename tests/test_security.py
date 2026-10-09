# -*- coding: utf-8 -*-
"""Bezpečnostní testy bez API a bez klíče (nic nestojí). Co zkoušejí a co NE, je v security/threat-model.md.

1. Webové funkce (ask.js, hit.js) běží proti falešnému OpenRouteru: kontrola původu, limity, proof of work, rozpočet, injekce ve vstupu.
2. Oprávnění v hledací vrstvě: nepovolený předpis se nedostane k modelu, do kandidátů, do stopy ani do citací.
3. Vykreslení odpovědi na webu neprovede HTML ani skript z modelu (XSS).
4. Detektory pro živý test injekcí fungují (zachytí vymyšlené špatné odpovědi) a soubor případů je v pořádku.
5. V repozitáři nejsou tajemství a nejhorší denní účet za zneužití se vejde do limitu klíče.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import datasets  # noqa: E402
import rag  # noqa: E402
import security_checks as sc  # noqa: E402

HAVE_NODE = bool(shutil.which("node"))


# ---------- 1. webové funkce proti falešnému OpenRouteru ----------
def _harness():
    out = subprocess.run(["node", str(ROOT / "tests" / "js_harness.cjs")], capture_output=True, text=True, encoding="utf-8", check=True, timeout=180).stdout
    return json.loads(out)


_RESULTS = _harness() if HAVE_NODE else []


@pytest.mark.skipif(not HAVE_NODE, reason="chybí Node.js")
@pytest.mark.parametrize("res", _RESULTS, ids=[r["name"] for r in _RESULTS])
def test_web_function(res):
    assert res["ok"], res["detail"]


@pytest.mark.skipif(not HAVE_NODE, reason="chybí Node.js")
def test_web_harness_covers_the_main_risks():
    names = " ".join(r["name"] for r in _RESULTS)
    for must in ("cizí původ", "proof of work", "11. otázka", "klíč se nikdy nevrátí", "vyčerpaný limit klíče", "systémový prompt zůstal beze změny", "cizí řetězec se do databáze nezapíše"):
        assert must in names, f"chybí test: {must}"


# ---------- 2. oprávnění v hledací vrstvě ----------
class FakeLLM:
    """Falešný model: přepis = otázka beze změny, výběr = první tři kandidáti. Zapisuje, co by dostal skutečný model."""
    def __init__(self):
        self.user_messages = []

    def __call__(self, system, user, model=None, reasoning=True):
        self.user_messages.append(user)
        if system == rag.REWRITE:
            return user, {}
        if system == rag.RERANK:
            return "1, 2, 3", {}
        return "Odpověď [1].", {}


FORBIDDEN_ID = re.compile(r"^\[\d+\] (ZNP|ZZ|NV 590)\b", re.M)
QUESTIONS = [q for q in datasets.questions() if q["chunks"]][:14] + [q for q in datasets.questions() if q["chunks"] and q["chunks"][0].startswith("ZNP")][:6]


@pytest.mark.parametrize("q", QUESTIONS, ids=[f"q{q['id']}" for q in QUESTIONS])
def test_disallowed_law_never_reaches_model_candidates_or_trace(q, monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(rag, "llm", fake)
    chunks = rag.load_chunks()
    hits, _, steps = rag.search(q["q"], mode="hybrid_rerank", trace=True, allow={"ZP"})
    assert hits, "něco se vrátit musí"
    assert all(chunks[i]["law"] == "ZP" for i, _ in hits), "výsledek z nepovoleného předpisu"
    for name, lst in steps.items():                       # i mezikroky (stopa, kandidáti, výběr)
        ids = [x[0] if isinstance(x, list) else x for x in lst]
        assert all(chunks[i]["law"] == "ZP" for i in ids), f"nepovolený úsek ve stopě: {name}"
    for msg in fake.user_messages:                        # i to, co by dostal model (prompt s kandidáty)
        assert not FORBIDDEN_ID.search(msg), "model by dostal text z nepovoleného předpisu"


def test_filter_really_filters_and_default_is_unchanged(monkeypatch):
    """Kontrola, že předchozí test něco dokazuje: bez filtru se úsek z jiného předpisu objeví a s filtrem na jiný předpis je pořadí jiné."""
    monkeypatch.setattr(rag, "llm", FakeLLM())
    chunks = rag.load_chunks()
    q = next(q for q in datasets.questions() if q["chunks"] and q["chunks"][0].startswith("ZNP"))
    open_hits, _ = rag.search(q["q"], mode="hybrid_rerank")
    zp_only, _ = rag.search(q["q"], mode="hybrid_rerank", allow={"ZP"})
    znp_only, _ = rag.search(q["q"], mode="hybrid_rerank", allow={"ZNP"})
    assert any(chunks[i]["law"] == "ZNP" for i, _ in open_hits), "otázka na nemocenské má bez filtru najít ZNP"
    assert not any(chunks[i]["law"] == "ZNP" for i, _ in zp_only)
    assert all(chunks[i]["law"] == "ZNP" for i, _ in znp_only)
    assert [i for i, _ in rag.search(q["q"], mode="hybrid_rerank", allow=None)[0]] == [i for i, _ in open_hits]


def test_empty_allow_list_returns_nothing(monkeypatch):
    monkeypatch.setattr(rag, "llm", FakeLLM())
    hits, _ = rag.search(QUESTIONS[0]["q"], mode="hybrid_rerank", allow=set())
    assert hits == []


def test_citations_cannot_point_outside_supplied_chunks():
    """Citace [n] se vztahuje jen na úseky, které model dostal. Odpověď s [99] zachytí validátor."""
    assert sc.valid_citations("Ano [1][2].", 5)
    assert not sc.valid_citations("Ano [99].", 5)


# ---------- 3. vykreslení na webu (XSS) ----------
@pytest.mark.skipif(not HAVE_NODE, reason="chybí Node.js")
def test_rendered_answer_cannot_inject_html():
    """Spustí skutečný kód esc() a fmt() z site/index.html na škodlivé odpovědi modelu."""
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    esc = re.search(r"^const esc = .*$", html, re.M).group(0)
    fmt = re.search(r"^function fmt\(text, q\)\{.*?^\}", html, re.M | re.S).group(0)
    script = f"""
{esc}
const D = {{chunks: [{{id: 'ZP § 1 "x"'}}]}};
{fmt}
const q = {{hits: [[0]]}};
const bad = [`<img src=x onerror=alert(1)>`, `<script>alert(1)</script> [1]`, `"><svg onload=alert(1)>`, `**<b>tučně</b>** [1] [7]`, `[1]"><a href=javascript:alert(1)>`];
console.log(JSON.stringify(bad.map(t => fmt(t, q))));
"""
    out = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    for rendered in out:
        no_allowed = re.sub(r"<(/?strong|br|button class=\"cite\"[^<>]*|/button)>", "", rendered)   # tagy, které generuje fmt sám
        assert "<" not in no_allowed and ">" not in no_allowed.replace("&gt;", ""), f"zůstal syrový HTML: {rendered}"
        assert 'onerror=alert' not in re.sub(r"&[a-z]+;", "", rendered).replace("<", "") or "&lt;" in rendered


# ---------- 4. detektory pro živý test a soubor případů ----------
CASES = json.loads((ROOT / "security" / "injection_cases.json").read_text(encoding="utf-8"))


def test_cases_are_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids)) >= 12
    for c in CASES:
        assert set(c["expect"]) <= set(sc.DETECTORS), c["id"]
        assert len(" ".join(c["question"].split())) <= 300, f"{c['id']}: delší než limit webu"
        if c.get("canary"):
            assert "no_canary" in c["expect"] and c["canary"] in c["question"], c["id"]
    assert {"direct", "indirect", "exfiltration"} <= {c["type"] for c in CASES}


def test_detectors_catch_bad_answers():
    sysp = rag.SYSTEM_V3
    assert not sc.no_canary("Dobře. PWNED-4417", "PWNED-4417")
    assert sc.no_canary("Nevím, v dostupných úsecích zákona to není.", "PWNED-4417")
    assert not sc.no_prompt_leak("Moje pravidla: " + " ".join(sysp.split()[10:30]), sysp)
    assert sc.no_prompt_leak("Dovolená je nejméně 4 týdny [1].", sysp)
    assert not sc.no_secret("Klíč je sk-or-v1-abcdef1234567890")
    assert not sc.no_secret("Použij hlavičku Bearer abcdefghijklmnop1234")
    assert not sc.no_secret("proměnná OPENROUTER_API_KEY")
    assert sc.no_secret("Dovolená je 4 týdny [1].")
    assert not sc.valid_citations("Ano, to jde.", 5)                 # bez citace
    assert not sc.valid_citations("Ano [9].", 5)                     # citace mimo dodané úseky
    assert sc.valid_citations("Nevím, v dostupných úsecích zákona to není.", 5)
    assert not sc.czech("Yes, you may leave at any time.")
    assert sc.czech("Ano, můžete odejít.")


def test_evaluate_returns_only_expected_detectors():
    r = sc.evaluate("Ano [1].", system_prompt=rag.SYSTEM_V3, n_supplied=5, canary=None, expect=["valid_citations", "no_secret"])
    assert r == {"valid_citations": True, "no_secret": True}


def test_live_runner_does_nothing_without_flag():
    """Bez --live se nesmí volat žádné API: spustí se jen plán a skončí kódem 0."""
    import os
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"} | {"PYTHONIOENCODING": "utf-8"}   # bez klíče by se ani nedalo volat
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "security_eval.py")], capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)
    assert p.returncode == 0 and "Nic se nevolalo" in p.stdout, p.stderr[-300:]


# ---------- 5. tajemství a cena zneužití ----------
SECRET_PATTERNS = [re.compile(p) for p in (r"sk-or-v1-[0-9a-f]{20,}", r"AIza[0-9A-Za-z_-]{30,}", r"vc[kp]_[A-Za-z0-9]{30,}", r"-----BEGIN (RSA |EC )?PRIVATE KEY", r"\"private_key\"\s*:",
                                          r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{24,}")]


@pytest.mark.skipif(not shutil.which("git"), reason="chybí git")
def test_no_secrets_in_tracked_files():
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8").stdout.split("\n")
    assert files and ".env" not in files, ".env se nesmí commitovat"
    skip = {".png", ".webp", ".npz", ".npy", ".zip", ".jpg"}
    for f in filter(None, files):
        p = ROOT / f
        if p.suffix in skip or not p.exists() or p.stat().st_size > 8_000_000:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for rx in SECRET_PATTERNS:
            m = rx.search(text)
            assert not m, f"{f}: vypadá to na tajemství ({rx.pattern[:25]}…)"


def test_env_example_has_no_value():
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            assert line.split("=", 1)[1].strip() == "", f"v .env.example nesmí být hodnota: {line.split('=')[0]}"


def test_worst_case_daily_cost_fits_into_key_limit():
    """Denial-of-wallet: největší denní účet, který web dovolí, musí být pod pevným limitem klíče (0,75 $).
    Odhad: strop otázek za den na jednu instanci funkce × cena otázky z měření (horní odhad, zahrnuje soudce, který web nepouští)."""
    src = (ROOT / "site" / "api" / "ask.js").read_text(encoding="utf-8")
    per_ip = int(re.search(r"PER_IP_PER_DAY = (\d+)", src).group(1))
    daily = int(re.search(r"GLOBAL_PER_DAY = (\d+)", src).group(1))
    max_len = int(re.search(r"MAX_LEN = (\d+)", src).group(1))
    base = json.loads((ROOT / "results" / "baseline.json").read_text(encoding="utf-8"))
    per_question = base["ops"]["cost_per_question_usd"]["v3"]
    worst = daily * per_question
    assert (per_ip, daily, max_len) == (10, 400, 300)
    assert worst < 0.75, f"{daily} otázek × {per_question} $ = {worst:.2f} $ nad limitem klíče"
    assert per_ip < daily
