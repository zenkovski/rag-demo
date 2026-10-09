# Incident: skryté „přemýšlení“ modelu spálilo většinu rozpočtu

**Stav:** opraveno (vypnuté), poučení zapsané. **Zjištěno:** 6. 10. 2026 při zavádění v3, po utracení většiny z celkových ~0,66 $.

## Symptom

Krok „LLM vybere 5 z 20 kandidátů“ trval **kolem 30 s** na otázku a celé měření stálo násobně víc, než odpovídal odhad. Odpovědi vypadaly normálně, žádná chyba, žádný timeout.

## Příčina

Model `deepseek-v4.1-flash` přes OpenRouter před odpovědí tiše generuje „reasoning“ tokeny, které se neukazují v odpovědi, ale **platí se a trvají**. U výběru úseků to bylo až **4 800 tokenů** na jedno volání, přitom odpověď měla pár znaků („3, 1, 7“).

Nikdo to nečekal, protože výstup byl krátký. Cena a čas se skrývaly v poli `usage`, které se nekontrolovalo.

## Oprava

`reasoning: {"enabled": false}` u kroků, které to nepotřebují (přepis, výběr; v kódu parametr `reasoning=False`, v klíči cache je odlišen příponou `|noreason`, aby se staré uložené odpovědi nepletly s novými).

| | S přemýšlením | Bez |
|---|---|---|
| Čas kroku výběru | ~30 s | ~1,5 s |
| Cena kroku | ~10× víc | základ |
| Kvalita výběru | – | **nezhoršila se** (podle zápisu v [HISTORY.md](../../HISTORY.md); samostatné srovnání před/po neuchovávám) |

(Zdroj čísel: [HISTORY.md](../../HISTORY.md#skryté-přemýšlení-modelu). Čas a cena jsou odhady z doby incidentu; změřený rozdíl před/po jsem do dat neuložil, to je slabina.)

## Poučení (a co se změnilo)

1. **Před hromadným během změřit jedno volání** včetně času a počtu tokenů z `usage`, ne jen délky výstupu.
2. Každý běh ukládá cenu (`cost_usd` v `data/eval.json`) a od teď i do záznamu o běhu (`results/…json`, pole `ops.cost_per_question_usd`).
3. Odpovědi modelů se **ukládají do cache podle vstupu**, takže opakované měření nestojí nic. Kvůli tomu je teď možné pouštět měření a quality gate zdarma (viz [ADR-001](../decisions/ADR-001-offline-quality-gate.md)).
4. **Pevný limit na klíči** u poskytovatele (0,75 $) je nejtvrdší pojistka. Tento incident ji nespustil, ale ukázal, proč tam musí být.

## Co to NEdokazuje

Že reasoning je vždy zbytečný. U odpovědi na těžké otázky může pomoci; tady se to nezkoušelo (odpověď píše silnější model bez reasoningu a kvalita se měří). Rozhodlo se podle změřeného času, ceny a kvality na těchto 56 otázkách.
