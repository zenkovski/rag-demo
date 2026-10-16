# ADR-006: Deterministické kontroly odpovědí vedle LLM soudce

**Stav:** přijato · **Datum:** 9. 10. 2026

## Kontext

Správnost odpovědi posuzuje AI soudce (DeepSeek), poté druhý model proti textu zákona a majitel projektu. Soudce se mýlil: přehlédl chybné „nevím“ (otázky 49, 51), označil správnou odpověď o mzdě a platu za chybu (38). Měřit kvalitu pouze dalším modelem je kruhové.

## Rozhodnutí

Vedle soudce běží **deterministické kontroly** (`tools/answer_checks.py`), které žádný model nepotřebují:

1. citace `[n]` míří na úsek, který model dostal,
2. odpověď, která není „nevím“, má aspoň jednu citaci,
3. každé číslo v odpovědi je v textu **citovaného** úseku (čísla slovy v zákoně se převádějí; odvozené hodnoty a špatně přiřazené citace se rozlišují).

## Výsledek

Na 66 odpovědích v3: žádná citace mimo rozsah, žádná odpověď bez citace, **3 podezření** na čísla. Ruční projití: 2 odvozené součty a 1 **skutečná špatná citace** („11 hodin“ je v úseku [4], odpověď cituje [1]; věcně správně). Tohle by soudce, který porovnává smysl, snadno přehlédl.

## Co kontrola NEdělá (a proč se hlásí jako „podezření“)

- Nezjistí, jestli věta z úseku **vyplývá** (to je úsudek, patří člověku nebo soudci).
- Neověří čísla zapsaná jako složeniny a slovní tvary mimo základní tvary (do devadesáti).
- **Není v živém řetězci**, jen v měření. Zapojit ji před zobrazením odpovědi je rozhodnutí o chování produktu (zahodit odpověď? zobrazit varování?), které se zatím neudělalo.

## Důsledky

Měřitelný signál bez ceny a bez důvěry v další model. Je to **doplněk**, ne náhrada úsudku.
