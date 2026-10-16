# Incident: výběr přes LLM zahodil základní pravidlo (odpočinek mezi směnami)

**Stav:** opraveno, hlídáno testem a quality gate. **Zjištěno:** 6. 10. 2026, měřením po zavedení v3. **Kde se pokazilo:** výběr úseků (krok mezi hledáním a odpovědí).

## Symptom

Po zavedení výběru „LLM vybere 5 z 20 kandidátů“ (commit `458bb46`, v3.0) se celkový výsledek zlepšil (v2 50 → v3 54 z 56), ale jedna otázka, kterou v2 měla správně, přestala fungovat:

> **Kolik hodin odpočinku musím mít mezi dvěma směnami?** Správně: nepřetržitý denní odpočinek alespoň 11 hodin (§ 90 odst. 1 ZP).

Odpověď ve v3.0 základní číslo vůbec nenapsala:

> „Základní pravidlo je v úsecích jen naznačeno (odstavec 1 se cituje, ale není uveden), takže přesnou základní délku odpočinku z dodaných úseků nezjistíme. Jisté je, že za uvedených podmínek může být zkrácen…“

Odpověď byla bezpečná („nevím“), ale k ničemu. Žádná chyba v logu, žádná výjimka. Jen horší odpověď.

## Jak se to našlo

Ne čtením odpovědí, ale **porovnáním po otázkách** (v2 → v3) po každé změně: hit@5 klesl na jediné otázce z „ano“ na „ne“, přestože celek rostl. Kdyby se sledoval jen průměr (54 z 56 je lepší než 50), regrese by zmizela v součtu.

## Příčina (měřitelná)

Správný odstavec **je** mezi 20 kandidáty. Rozhodl krok výběru:

| Krok | § 90 odst. 1 (pravidlo) | § 90 odst. 2, 3 (výjimky) |
|---|---|---|
| Kandidáti z RRF (20) | ano | ano |
| **Výběr LLM (v3.0)** | **vyřazeno** | vybráno |
| Pět úseků pro model | chybí | `ZP § 90 odst. 3`, `odst. 2`, `§ 90a`, … |

LLM vybíral úseky, které „odpovídají na otázku o zkrácení odpočinku“, a výjimky vypadají relevantněji než základní pravidlo. Chyba není v modelu ani v promptu jako takovém, je v tom, že **výjimka se bez svého pravidla nedá správně přečíst**. Kategorie podle [galerie chyb](../failure-gallery.md): **B – nalezeno, ale vyřazeno**. Lepší prompt ani lepší hledání by to nespravily jistě; spolehlivě to spraví jen pevné pravidlo.

Důkaz z dat (`data/eval.json`, commit `458bb46`, otázka 10): pět úseků pro model bylo `ZP § 90 odst. 3`, `odst. 2`, `§ 90a`, `§ 85 odst. 3`, `§ 100 odst. 2`. Odstavec 1 chyběl.

## Oprava

Pevné pravidlo **bez AI** (`rag.with_odst1`, commit `1e76718`): k vybranému odstavci 2, 3… se vždy přidá odstavec 1 téhož paragrafu, i když nebyl mezi kandidáty.

Proč pravidlo a ne „zakázat LLM vynechat odstavec 1“: LLM je nestabilní a nová formulace promptu by chybu jen přesunula. Pravidlo je deterministické a jde otestovat.

## Důkaz, že oprava pomohla a nic nerozbila

- Otázka 10 po opravě: pět úseků `ZP § 90 odst. 3`, **`odst. 1`**, `odst. 2`, … Odpověď: „…nepřetržitý denní odpočinek alespoň 11 hodin… Mladistvému alespoň 12 hodin, případně 14 hodin“ (správně).
- Celkem hit@5 na prvních 48 otázkách s odpovědí: **47 → 48**. Po opravě se změřily **všechny** otázky znovu, ne jen ta jedna: žádná další nezhoršila.

## Co se z toho stalo trvalé

1. **Unit test** `tests/test_rag.py::test_with_odst1_adds_base_rule`: výjimka (§ 90 odst. 2) dostane za sebe odstavec 1.
2. **Quality gate** (`python tools/experiments.py --check`): pořadí správného úseku u každé otázky je v `results/baseline.json`; kdyby někdo pravidlo odstranil, selže u této otázky, ne až v průměru.
3. **Postup:** po každé změně se porovnává po otázkách (`transitions` v [benchmark-results.md](../benchmark-results.md)), ne jen součet.

## Co by tomu zabránilo dřív

Měření po otázkách hned u první verze výběru. Průměr (54 z 56) vypadal jako úspěch a oprava přišla až po prohlédnutí jednotlivých otázek.
