[Česky](../cs/decisions/ADR-004-prepis-a-bm25-otevrena-otazka.md)

# ADR-004: Question rewrite and BM25: benefit not proven

**Status:** **open** · **Date:** 9 Oct 2026

## Context

v2 added (a) a rewrite of the layperson's question into the language of the law and (b) BM25 over the rewritten question, combined with RRF. Original justification: BM25 wins on exact terms and numbers, the rewrite translates „výplata“ ("pay") into „mzda“ ("wage").

## What the data show

Offline ablation on 56 questions with an answer ([benchmark-results.md](../benchmark-results.md)):

| System | Recall@5 | Recall@20 |
|---|---|---|
| e5-large only (meaning) | 0.86 | 0.97 |
| RRF: e5-large over the question and the rewrite, **without BM25** | **0.88** | **0.99** |
| RRF + BM25 over the rewrite (v2, current state) | 0.86 | 0.96 |

- **BM25 did not improve retrieval**, it made it marginally worse. The paired test is inconclusive (3 : 5, p = 0.73), but **the direction is the opposite of what was expected**. The optimal BM25 weight in the weighted sum came out at 0.05.
- **The rewrite helps BM25** (lay question 0.58 → rewritten 0.76), but **embeddings do not need the rewrite** (e5-large only 0.86, with the rewrite 0.88; inconclusive).

## A real error connected to this

For the question „Může mi zaměstnavatel dát výpověď, když jsem nemocný?“ ("Can my employer give me notice when I am ill?") the website answers in a misleading way ([failure gallery](../failure-gallery.md#open-failures-not-fixed-yet)). The correct paragraph (ZP § 53 odst. 1, the ban on notice during the protection period; ZP = Labour Code) ranks as follows:

| Ranking | Place of the correct paragraph |
|---|---|
| meaning, **original** question | **12th** |
| meaning, **rewritten** question | 219th |
| BM25, rewritten question | 106th |
| BM25, lay question | 10th |

The rewrite („…rozvázat pracovní poměr výpovědí, nachází-li se zaměstnanec v dočasné pracovní neschopnosti?“ / "…terminate the employment relationship by notice if the employee is on temporary incapacity for work?") led the search to general paragraphs about termination of the relationship. After the RRF fusion the correct paragraph ended up in 45th place, i.e. outside the 20 candidates.

## Variants examined (offline, candidates only: Recall@20)

| Fusion | Recall@20 (56 questions) | rank of § 53 in the demo |
|---|---|---|
| current (question, rewrite, BM25 of the rewrite) | 0.964 | 45 |
| + BM25 of the lay question | 0.973 | 23 |
| question + rewrite, without BM25 | 0.991 | 31 |
| question + BM25 of the lay question + rewrite | 0.987 | **14** (within 20) |

## Decision

**Do not change for now.** The variants above **cannot be judged honestly on this data**: they arose from an error I already know and are judged on the same questions that were already used for tuning. On the dev, validation and test sets the differences are 1–2 questions.

## What will decide

The frozen set v4 ([testset_heldout_v4.json](../../data/testset_heldout_v4.json)) contains **exact references to sections and numbers**, exactly the case where BM25 should win, and **ambiguous and wrongly written questions**, where the rewrite should help. Procedure:

1. Before running, the list of variants above is fixed (nothing else is added).
2. The variants are run **live once** on v4 (requires ~$0.03 per variant, a new key).
3. A change is accepted only if it improves Recall@20 **without worsening** Recall@5 and MRR and the difference is conclusive, or if it is at least not worse and is simpler.

Until then the open error "notice of termination during illness" stays recorded as known.

## Consequences

- It is admitted that part of the architecture (BM25) is not backed by measurement. The reason it is here: the original assumption and success on exact terms, which this set has no way to show.
