# -*- coding: utf-8 -*-
"""Generuje docs/benchmark-results.md a docs/failure-gallery.md ze záznamu běhu (results/runs/*.json) a uložených dat.
Čísla se do textu dostávají z dat, ne z hlavy: po novém měření se dokumenty přepíšou samy.
  python tools/make_docs.py            # z posledního běhu v results/runs/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import datasets  # noqa: E402
import diagnose  # noqa: E402
import evaluate  # noqa: E402

ROOT = datasets.ROOT
DOCS = ROOT / "docs"
SYS_LABEL = {
    "dense_base": "e5-base, význam otázky (lokálně)", "dense_large": "e5-large, význam otázky", "bm25_raw": "BM25, laická otázka",
    "bm25_rewrite": "BM25, přepsaná otázka", "rrf_dense_bm25": "RRF: e5-large + BM25 (bez přepisu)",
    "rrf_dense_rewrite": "RRF: e5-large (otázka + přepis), bez BM25", "rrf_v2": "RRF: e5-large (otázka + přepis) + BM25 nad přepisem (v2)",
    "weighted_v2": "vážený součet místo RRF", "v3_llm_rerank": "v3: v2 + LLM vybere 5 z 20 + pravidla odstavců (finální)",
}


def latest_run() -> dict:
    files = sorted((ROOT / "results" / "runs").glob("*.json"))
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _ci(m: dict) -> str:
    return f"{m['mean']:.2f} ({m['ci95'][0]:.2f}–{m['ci95'][1]:.2f})"


def write_benchmark(rec: dict) -> Path:
    r, cfg, n = rec["run"], rec["config"], rec["n"]
    ret, ans = rec["retrieval"], rec["answers"]
    L = ["# Výsledky měření", "",
         f"Generuje `tools/experiments.py` + `tools/make_docs.py`. Běh z commitu `{r['git']['commit']}`{' (necommitované změny)' if r['git']['dirty'] else ''}, "
         f"{r['started']}, {r['mode']}, trval {r['runtime_s']} s, cena {r['cost_usd']:.2f} $. Python {r['python']}, numpy {r['numpy']}, {r['platform']}.", "",
         "**Co je změřené a co ne.** Hledání se tu přehrává z uložených embeddingů a uložených odpovědí LLM (přepis, výběr). Kód hledání je tedy ověřený a běh je opakovatelný, "
         "ale **žádné nové volání modelu se neprovedlo**. Odpovědi (sekce 4) jsou z dřívějších měření s ruční kontrolou. Co to neříká, je u každé sekce.", "",
         "## 0. Data", "",
         f"{n['questions']} otázek, z toho {n['answerable']} s odpovědí v zákonech a {n['questions'] - n['answerable']} záměrně bez ní (správně je „nevím“). "
         f"Role sad (dev / validation / test) a důkaz, kdy vznikly: [`data/splits.json`](../data/splits.json), pravidla v [evaluation-methodology.md](evaluation-methodology.md).", "",
         "| Role | Otázek s odpovědí | Sady |", "|---|---|---|",
         f"| dev | {n['answerable_dev']} | 1–46 (podle nich se ladilo) |",
         f"| validation | {n['answerable_validation']} | 47–56 |",
         f"| test | {n['answerable_test']} | 57–66 |", "",
         "Otisky dat: " + ", ".join(f"`{k}` {v}" for k, v in rec["datasets"].items()), "",
         f"Konfigurace: embedding `{cfg['embedding']}` (v1 `{cfg['embedding_v1']}`), přepis a výběr `{cfg['llm_rewrite_rerank']}`, odpověď `{cfg['llm_answer']}`, "
         f"{cfg['n_candidates']} kandidátů, {cfg['top_k']} úseků pro model, RRF k = {cfg['rrf_k']}. Otisky promptů: " + ", ".join(f"{k} `{v}`" for k, v in cfg["prompt_hashes"].items()) + ".", ""]

    # 1) hledání
    L += ["## 1. Hledání", "",
          f"Správný úsek mezi prvními k, na všech {n['answerable']} otázkách s odpovědí. V závorce 95% interval spolehlivosti (bootstrap přes otázky, 10 000 losování). "
          "U otázek se dvěma správnými úseky Recall počítá podíl nalezených.", "",
          "| Systém | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Recall@20 | MRR | nDCG@5 |", "|---|---|---|---|---|---|---|---|"]
    for s, lab in SYS_LABEL.items():
        v = ret["all"].get(s)
        if not v:
            continue
        m = v["metrics"]
        mean = {k: (f"{x['mean']:.2f}" if x else "–") for k, x in ((k, m.get(k)) for k in ("recall@1", "recall@3", "recall@10", "recall@20", "ndcg@5"))}
        L.append(f"| {lab} | {mean['recall@1']} | {mean['recall@3']} | {_ci(m['recall@5'])} | {mean['recall@10']} | {mean['recall@20']} | {_ci(m['mrr'])} | {mean['ndcg@5']} |")
    L += ["", "Finální systém vrací jen 5 úseků (tolik dostane model), proto u něj chybí Recall@10 a @20.", "",
          "### Po rolích sad (Recall@5 a MRR)", "",
          "| Systém | dev (n=%d) R@5 | MRR | validation (n=%d) R@5 | MRR | test (n=%d) R@5 | MRR |" % (n["answerable_dev"], n["answerable_validation"], n["answerable_test"]),
          "|---|---|---|---|---|---|---|"]
    for s, lab in SYS_LABEL.items():
        if s not in ret["all"]:
            continue
        cells = []
        for sp in ("dev", "validation", "test"):
            m = ret[sp][s]["metrics"]
            cells += [f"{m['recall@5']['mean']:.2f}", f"{m['mrr']['mean']:.2f}"]
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    L += ["", f"**Pozor na velikost.** Test má {n['answerable_test']} a validation {n['answerable_validation']} otázek. Rozdíl o jednu otázku je 12 procentních bodů, intervaly spolehlivosti jsou široké "
          "a u 8 z 8 je dolní mez ~0,68 (Wilson). Dev číslo je nadsazené: podle něj se ladilo. Role „test“ tu slouží jako kontrola, ne jako důkaz.", ""]

    # 2) ablace
    a = ret["all"]
    gm = lambda s, k: a[s]["metrics"][k]["mean"]
    L += ["## 2. Co která část přináší (ablace)", "",
          "Párové porovnání na stejných otázkách. „A lepší / B lepší“ = u kolika otázek měl A, resp. B vyšší Recall@5. "
          "p je přesný oboustranný znaménkový test: p pod 0,05 říká, že rozdíl pravděpodobně není náhoda. Nad tím je to jen pozorování.", "",
          "| Porovnání | A lepší | B lepší | shoda | p |", "|---|---|---|---|---|"]
    names = {"rrf_v2": "RRF v2", "dense_large": "jen e5-large", "rrf_dense_bm25": "RRF bez přepisu", "rrf_dense_rewrite": "RRF bez BM25",
             "weighted_v2": "vážený součet", "v3_llm_rerank": "v3 (výběr LLM)", "dense_base": "e5-base"}
    for k, v in rec["paired_tests_recall5_all"].items():
        x, y = k.split(" vs ")
        L.append(f"| {names.get(x, x)} × {names.get(y, y)} | {v['a_better']} | {v['b_better']} | {v['ties']} | {v['p']:.3f} |")
    L += ["", "Co z toho plyne (čísla jsou z tabulek výše):", ""]
    L.append(f"- **Výběr přes LLM je jediná komponenta s jasným přínosem.** Recall@1 {gm('rrf_v2', 'recall@1'):.2f} → {gm('v3_llm_rerank', 'recall@1'):.2f}, MRR {gm('rrf_v2', 'mrr'):.2f} → {gm('v3_llm_rerank', 'mrr'):.2f}, "
             f"lepší u {rec['paired_tests_recall5_all']['v3_llm_rerank vs rrf_v2']['a_better']} otázek, horší u {rec['paired_tests_recall5_all']['v3_llm_rerank vs rrf_v2']['b_better']}.")
    L.append(f"- **BM25 se v těchto otázkách nevyplatilo.** RRF bez BM25 má Recall@5 {gm('rrf_dense_rewrite', 'recall@5'):.2f} a Recall@20 {gm('rrf_dense_rewrite', 'recall@20'):.2f}, "
             f"RRF s BM25 {gm('rrf_v2', 'recall@5'):.2f} a {gm('rrf_v2', 'recall@20'):.2f}. Rozdíl není statisticky průkazný, ale směr je opačný, než jsem čekal. "
             "Sada neobsahuje otázky na přesná čísla paragrafů a identifikátory, tedy přesně to, v čem má být BM25 silné. Rozhodnutí proto odkládám na novou sadu (viz [limitations.md](limitations.md)).")
    L.append(f"- **Přepis otázky bez BM25 nevadí.** Samotný e5-large: Recall@5 {gm('dense_large', 'recall@5'):.2f}; s přepisem: {gm('rrf_dense_rewrite', 'recall@5'):.2f}. Rozdíl zhruba o dvě otázky, nepůjde rozlišit od náhody.")
    L.append(f"- **e5-large proti e5-base:** Recall@5 {gm('dense_large', 'recall@5'):.2f} proti {gm('dense_base', 'recall@5'):.2f}." if "dense_base" in a else "- e5-base: přeskočeno (chybí torch nebo model).")
    L.append(f"- **Laická otázka do BM25 škodí:** {gm('bm25_raw', 'recall@5'):.2f} proti {gm('bm25_rewrite', 'recall@5'):.2f} po přepisu. Tady přepis zjevně pomáhá (zákon říká „mzda“, ne „výplata“).")
    L += ["", "### RRF: parametr k", "", "| k | Recall@5 | MRR |", "|---|---|---|"]
    for k, v in rec["rrf_k_sweep"].items():
        L.append(f"| {k}{' (použito)' if k == '60' else ''} | {_ci(v['recall@5'])} | {_ci(v['mrr'])} |")
    L += ["", "Hodnota k se na výsledku skoro nepozná: intervaly se překrývají. Proto zůstává výchozí 60.", "",
          "### RRF proti váženému součtu skóre", "",
          f"Váhu BM25 jsem vybíral jen na dev otázkách (podle MRR): **{cfg['weighted_bm25_weight_from_dev']}**. "
          f"Na všech otázkách má vážený součet Recall@5 {gm('weighted_v2', 'recall@5'):.2f} a MRR {gm('weighted_v2', 'mrr'):.2f}, RRF {gm('rrf_v2', 'recall@5'):.2f} a {gm('rrf_v2', 'mrr'):.2f}. "
          f"Rozdíl je neprůkazný (p = {rec['paired_tests_recall5_all']['rrf_v2 vs weighted_v2']['p']:.2f}). RRF zůstává, protože nepotřebuje ladit váhu a normalizaci skóre. "
          "Optimální váha BM25 vyšla velmi nízká, což je stejný signál jako výše: slova hledání moc nepomáhají.", ""]

    # 3) rerank
    rr = rec["rerank"]
    L += ["## 3. Výběr 5 z 20: žádný, cross-encoder, LLM", "",
          f"Stejných {rr['llm']['n']} otázek, stejných 20 kandidátů z RRF. Uložené výsledky z `tools/rerank_compare.py` (cross-encoder běžel lokálně na CPU, {rr['cross_encoder_s_na_otazku_cpu']} s na otázku). "
          "Hit@5 = je mezi pěti vybranými aspoň jeden správný úsek.", "",
          "| Způsob | Hit@5 | MRR@5 |", "|---|---|---|"]
    for k in ("rrf5", "ce", "llm"):
        L.append(f"| {rr[k]['label']} | {_ci(rr[k]['hit@5'])} | {_ci(rr[k]['mrr@5'])} |")
    p = rr["paired_llm_vs_ce"]
    L += ["", f"LLM proti cross-encoderu: lepší u {p['a_better']} otázek, horší u {p['b_better']}, p = {p['p']:.3f}. "
          "Číslo 56 proti 52 z README tedy ukazuje směr, ale na 56 otázkách ho nejde považovat za prokázané. "
          "LLM navíc vidí všech 20 kandidátů najednou a platí se za každý dotaz. Cross-encoder je zdarma, deterministický, ale na CPU pomalý.", ""]

    # 4) odpovědi
    L += ["## 4. Odpovědi", "",
          "Zdroj: uložené běhy v1, v2, v3 (v3 = finální) a moje ruční kontrola proti textu zákona (druhý verdikt Claude Opus 5.5, který jsem prošel). "
          "Správnost je úsudek, nelze ji spočítat pravidlem. Proto je vedle AI soudce a mojí kontroly přidaná deterministická kontrola (sloupce vpravo), která soudce nepotřebuje.", "",
          "| Verze | Sada | Správně (95% interval) | Zbytečné „nevím“ | Správné „nevím“ | Odpověděl bez zdroje | Čísla mimo citované úseky |", "|---|---|---|---|---|---|---|"]
    for v in ("v1", "v2", "v3"):
        for sp in ("all", "dev", "validation", "test"):
            x = ans[v]["per_split"][sp]
            lab = {"all": "všechny", "dev": "dev", "validation": "validation", "test": "test"}[sp]
            L.append(f"| {v} | {lab} | {x['correct']} z {x['n']} ({x['correct_ci95'][0]:.2f}–{x['correct_ci95'][1]:.2f}) | {x['false_refusals']} z {x['answerable']} | "
                     f"{x['correct_refusals']} z {x['unanswerable']} | {x['answered_without_source']} z {x['unanswerable']} | {x['det_unsupported_number']} |")
    t = rec["transitions"]
    L += ["", f"**Změny po otázkách.** v1 → v2: opraveno {len(t['v1->v2']['fixed'])}, zhoršeno {len(t['v1->v2']['regressed'])} (otázky {', '.join(map(str, t['v1->v2']['regressed']))}). "
          f"v2 → v3: opraveno {len(t['v2->v3']['fixed'])}, zhoršeno {len(t['v2->v3']['regressed'])}.", "",
          "**Co z toho nevyplývá.** 66 z 66 u v3 je nadsazené: ladilo se podle 56 z těchto otázek. Poctivá kontrola je řádek „test“ (10 otázek, dolní mez intervalu ~0,72) a ten sám o sobě "
          "nedokazuje, že systém na nových otázkách dopadne stejně. Proto je připravená nová sada, která se pustí jednou (viz [evaluation-methodology.md](evaluation-methodology.md)).", "",
          "**Kontrola čísel.** Sloupec „čísla mimo citované úseky“ je podezření, ne chyba: číslo v odpovědi, které není v textu žádného citovaného úseku. "
          "Kontrola rozlišuje dva případy: číslo, které je v jiném dodaném úseku než citovaném (špatná citace), a číslo, které není v žádném (odvozená hodnota, např. součet nebo polovina, nebo vymyšlené). "
          "Čísla zapsaná v zákoně slovy („patnáctidenní“) se převádějí na číslice.", ""]
    fl = ans["v3"]["per_split"]["all"].get("flagged", [])
    qtext = {q["id"]: q["q"] for q in datasets.questions()}
    L += [f"Podezření u v3 ({len(fl)} odpovědí):", "", "| Otázka | Číslo v jiném dodaném úseku (špatná citace) | Číslo v žádném úseku (odvozené?) | Citované úseky |", "|---|---|---|---|"]
    L += [f"| {x['id']}: {qtext[x['id']]} | {', '.join(x['misattributed']) or '–'} | {', '.join(x['in_no_chunk']) or '–'} | {x['cited']} |" for x in fl]
    L += ["", "Ruční projití těchto odpovědí: součet (24 + 11 = 35 hodin), polovina (20 hodin z 40) a „od 15. dne“ po 14 dnech jsou správné odvozené hodnoty, které odpověď sama vysvětluje, "
          "ale nejdou doložit citací. **Jedna skutečná chyba v citaci:** u otázky 21 je „11 hodin“ v úseku [4], odpověď ho cituje jako [1]. Odpověď je věcně správně, jen odkaz míří jinam. "
          "Tohle by AI soudce, který porovnává smysl, snadno přehlédl.", ""]

    # 5) provoz
    ops = rec["ops"]
    lat = ops["retrieval_compute_latency"]
    L += ["## 5. Provoz", "",
          "| Verze | Cena na otázku při měření |", "|---|---|"]
    for v, c in ops["cost_per_question_usd"].items():
        L.append(f"| {v} | {c:.5f} $ |")
    L += ["", f"{ops['cost_note'][0].upper() + ops['cost_note'][1:]}. Celý projekt vyšel asi na 0,66 $ včetně chyb (viz [incident skrytého přemýšlení](incidents/2026-10-06-skryte-premysleni.md)).", "",
          f"Čas samotného výpočtu hledání (matice × vektor, BM25, RRF) z cache: **p50 {lat['p50_ms']} ms, p95 {lat['p95_ms']} ms**, max {lat['max_ms']} ms ({lat['calls']} volání, tento počítač). "
          f"{ops['latency_note'][0].upper() + ops['latency_note'][1:]}", "",
          "p50/p95/p99 celé služby, propustnost a chybovost pod zátěží **nejsou změřené**. Zátěžový test by běžel proti placenému API a proti limitu 0,75 $ na klíči, takže se nedělal (viz [limitations.md](limitations.md)).", ""]

    # 6) regrese
    L += ["## 6. Regrese proti referenčnímu stavu", ""]
    L += ([f"- {x}" for x in rec["regressions"]] if rec.get("regressions") else ["Žádné. Pořadí správných úseků u finálního systému je stejné nebo lepší než v `results/baseline.json`."])
    out = DOCS / "benchmark-results.md"
    DOCS.mkdir(exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


# ---------- galerie chyb ----------
FIXES = {
    20: ("Hledání: zákon o nemocenském pojištění má stovky podobných odstavců, správné dva (§ 192 ZP, § 29 ZNP) se nedostaly mezi 5.",
         "v3: LLM vybere 5 z 20 kandidátů a pevné pravidlo dohledá odstavec, na který úsek odkazuje („ve výši podle odstavce 2“)."),
    36: ("Hledání: § 38c ZNP (výše otcovské) nebyl mezi 5 úseky, model napsal půl odpovědi.", "v3: LLM vybere 5 z 20 a přidá § 38c."),
    38: ("Čtení: model smíchal mzdu (soukromý zaměstnavatel, § 116: nejméně 10 %) a plat (stát, § 125: 20 %).",
         "v3: každý úsek v podkladech nese poznámku „platí pro mzdu / plat“ a prompt říká, aby uvedl obě varianty, když to otázka nerozlišuje."),
    40: ("Čtení: zákon říká, že zaměstnavatel nemusí vydat posudek dřív než 2 měsíce před koncem. Levný model napsal „nesmí“ a výsledek se mezi běhy měnil.",
         "v3: pravidlo „není povinen = nemusí“ v promptu, od v3.1 odpověď píše silnější model."),
    49: ("Hledání: § 41 ZNP (60 %) se nenašel, model správně řekl „nevím“. AI soudce to bez přemýšlení označil za správně.",
         "v3: výběr přes LLM. Soudce se opravuje ruční kontrolou, proto je v měření druhý verdikt."),
    51: ("Hledání: § 141 odst. 1 se nenašel, model řekl „nevím“. AI soudce to přehlédl.", "v3: výběr přes LLM, ruční kontrola."),
}


WEB_EXPECTED = {
    "Může mi zaměstnavatel dát výpověď, když jsem nemocný?":
        "Ne, v době dočasné pracovní neschopnosti (ochranná doba) se výpověď zakazuje (§ 53 odst. 1 písm. a) ZP); zákaz se nevztahuje na výjimky v § 54 (např. výpověď pro organizační změny).",
    "Kolik hodin týdně je normální pracovní doba?":
        "40 hodin týdně; u mladistvého mladšího 15 let nebo toho, kdo NEukončil povinnou školní docházku, nejvýše 35 hodin (§ 79a odst. 1 ZP).",
}


def _case(title: str, row: dict, gold: str, cat: list[str], cause: str, fix: str, proof: str) -> list[str]:
    ans = (row.get("answer") or "").strip().replace("\n", " ")
    return [f"### {title}", "",
            f"- **Vstup:** {row['q']}",
            f"- **Očekávané chování:** {gold}",
            f"- **Skutečné chování:** {ans[:420]}{'…' if len(ans) > 420 else ''}",
            f"- **Kategorie:** {', '.join(f'{c} ({diagnose.CATEGORIES[c]})' for c in cat) or '–'}",
            f"- **Příčina:** {cause}", f"- **Oprava:** {fix}", f"- **Důkaz:** {proof}", ""]


def write_gallery(rec: dict) -> Path:
    ev, man = evaluate.load("eval.json"), evaluate.load("manual_review.json")
    qs = {q["id"]: q for q in datasets.questions()}
    fin = {v: evaluate.final(ev[v]["rows"], man.get(v, {})) for v in evaluate.VERSIONS}
    rows = {v: {r["id"]: r for r in ev[v]["rows"]} for v in evaluate.VERSIONS}
    sysmap = {"v1": "dense_base", "v2": "rrf_v2", "v3": "rrf_v2"}

    cand = rec.get("candidates_top20", {})

    def cats(v: str, i: int) -> list[str]:
        """Kategorie selhání. „Nalezeno“ znamená VŠECHNY správné úseky (u otázky se dvěma správnými stačí jeden chybějící)."""
        r, q = rows[v][i], qs[i]
        gold = set(q["chunks"])
        final_ids = {t["id"] if isinstance(t, dict) else t for t in r["top"]}
        c_ids = set(cand.get(sysmap[v], {}).get(str(i), []))
        return diagnose.classify(answerable=bool(gold), correct=bool(fin[v][i]), said_nevim=bool(r["said_nevim"]), gold_in_final=gold <= final_ids,
                                 gold_in_candidates=gold <= (c_ids | final_ids), grounded=bool(r["judge"]["grounded"]))

    L = ["# Galerie chyb", "",
         "Skutečná selhání z měření: vstup, očekávané a skutečné chování, kde v řetězci vznikla, příčina, oprava a důkaz, že oprava pomohla. "
         "Kategorie říkají, KDE se řetěz přerušil, ať je jasné, co opravovat:", ""]
    L += [f"- **{k}** – {v}" for k, v in diagnose.CATEGORIES.items()]
    L += ["", "## Kolik selhání v které kategorii", "",
          "| Verze | Odpovědí špatně | A nenalezeno | B vyřazeno | C špatně přečteno | E měl odmítnout | F zbytečné „nevím“ |", "|---|---|---|---|---|---|---|"]
    for v in evaluate.VERSIONS:
        bad = [i for i in fin[v] if not fin[v][i]]
        cnt = {c: sum(diagnose.primary(cats(v, i)) == c for i in bad) for c in "ABCEF"}
        L.append(f"| {v} | {len(bad)} z {len(fin[v])} | {cnt['A']} | {cnt['B']} | {cnt['C']} | {cnt['E']} | {cnt['F']} |")
    L += ["", "Kategorie D (tvrzení bez opory) se počítá zvlášť, protože se může přidat i ke správné odpovědi: viz sekci o kontrole čísel v [benchmark-results.md](benchmark-results.md). "
          "Hlavní příčina je tu jedna na odpověď (A před B před C před E a F). „Nalezeno“ znamená všechny správné úseky. Pro v1 a v2 (nemají výběr z 20) znamená B „byl mezi 20 nejlepšími, ale ořez na 5 ho vyřadil“. "
          "Kandidáti v1 a v2 jsou z přehrání (v2 původně používalo přepis se skrytým přemýšlením, proto se mohou o kousek lišit od dobového měření).", "",
          "## Opravené chyby (v2 → v3)", ""]
    for i in rec["transitions"]["v2->v3"]["fixed"]:
        cause, fix = FIXES.get(i, ("viz poznámka v `data/manual_review.json`", "v3"))
        note = man.get("v2", {}).get(str(i), {}).get("note", "")
        c = cats("v2", i)
        L += _case(f"Otázka {i}: {qs[i]['q']}", rows["v2"][i], qs[i]["gold"], c, cause + (f" Ruční poznámka: {note}" if note else ""), fix,
                   f"ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z {rec['n']['questions']}.")
    L += ["## Zhoršení: v1 → v2", "",
          "Oprava jedné věci rozbila jinou. Dvě otázky, které v1 měla správně, ve v2 selhaly. Proto se po každé změně měří znovu všechno, ne jen opravená otázka.", ""]
    for i in rec["transitions"]["v1->v2"]["regressed"]:
        note = man.get("v2", {}).get(str(i), {}).get("note", "")
        L += _case(f"Otázka {i}: {qs[i]['q']}", rows["v2"][i], qs[i]["gold"], cats("v2", i), note or "viz `data/manual_review.json`",
                   "opraveno ve v3 (stejná otázka je ve v3 správně)", f"v3: {'správně' if fin['v3'][i] else 'chyba'}.")
    L += ["## Regrese uvnitř vývoje v3 (v3.0 → oprava)", "",
          "Detailní rozbor je jako incident: [2026-10-06 regrese u odpočinku mezi směnami](incidents/2026-10-06-regrese-odpocinek.md).", ""]

    # otevřené chyby: ukázkové otázky na webu
    site = json.loads((ROOT / "site" / "data.json").read_text(encoding="utf-8"))
    L += ["## Otevřené chyby (zatím neopravené)", "",
          "Z 16 ukázkových otázek na webu jsou dvě špatně. Nechávám je vidět i na webu. Žádná z nich není v testovacích sadách, takže je nikdo neladil.", ""]
    for q in site["questions"]:
        rv = q.get("review")
        if rv and not rv.get("ok"):
            kind = "hledání" if "hledání" in rv["note"] else "čtení"
            cat = ["A"] if kind == "hledání" else ["C"]
            fix = ("Příčina je změřená, oprava zatím není nasazená: viz [ADR-004](decisions/ADR-004-rewrite-a-bm25.md). Přepis otázky odvedl hledání jinam "
                   "(správný odstavec je podle významu původní otázky na 12. místě, podle přepsané na 219., v BM25 přepisu na 106.). Návrh opravy se musí vyzkoušet na nové sadě, ne na této otázce."
                   if kind == "hledání" else
                   "Zatím bez opravy. Návrh: pravidlo v promptu pro podmínky „před / po ukončení“ a test na víc otázek s převrácenou podmínkou; ověřit na nové sadě.")
            L += _case(f"Web: {q['q']}", {"q": q["q"], "answer": q["answer"]}, WEB_EXPECTED.get(q["q"], "viz poznámka k příčině"), cat, rv["note"], fix,
                       "není (oprava se zatím neprovedla; nepíšu, že je opraveno).")
    out = DOCS / "failure-gallery.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    rec = latest_run()
    print(write_benchmark(rec))
    print(write_gallery(rec))
