# Výsledky měření

Zdroj: 4 předpisy, 2 475 úseků (celý zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění,
nařízení vlády o překážkách v práci). 46 testovacích otázek ve 3 sadách, 40 má odpověď v předpisech, 6 záměrně ne.
Verdikt „správně“ je po ruční kontrole všech odpovědí proti textu zákona.

## v1 → v2

| Měřítko | v1 | v2 |
|---|---|---|
| Model | `nvidia/nemotron-3-super-120b-a12b:free` | `deepseek/deepseek-v4.1-flash` |
| Vyhledávání | embeddingy e5-base | e5-large + BM25 + přepis otázky (RRF) |
| **Odpověď správně (celkem)** | **36 z 46** | **42 z 46** |
| z toho otázky s odpovědí | 30 z 40 | 36 z 40 |
| z toho správně „nevím“, když zdroj mlčí | 6 z 6 | 6 z 6 |
| Správný paragraf mezi 5 nalezenými (hit@5) | 33 z 40 | 39 z 40 |
| Správný paragraf v top 3 (hit@3) | 29 z 40 | 37 z 40 |
| „Nevím“, i když odpověď ve zdroji byla | 4 z 40 | 1 z 40 |
| Opírá se o zdroj (podle AI soudce) | 41 z 46 | 44 z 46 |
| AI soudce se shodl s ruční kontrolou | 46 z 46 | 46 z 46 |

## Podle sad

| Sada | otázek | v1 správně | v2 správně | v2 hit@5 |
|---|---|---|---|---|
| testovací | 20 | 16 | 19 | 18 z 19 |
| kontrolní | 10 | 7 | 10 | 9 z 9 |
| nové předpisy | 16 | 13 | 13 | 12 z 12 |

- **testovací (1–20):** podle chyb na nich jsem navrhl v2, výsledek v2 je tu proto nadsazený.
- **kontrolní (21–30):** napsané až po návrhu v2.
- **nové předpisy (31–46):** napsané po přidání dalších předpisů, žádné ladění podle nich.

## Co udělal větší zdroj s vyhledáváním

Stejných 24 otázek, které měly odpověď už v první verzi (5 témat zákoníku práce, 260 úseků).
Teď se hledá v 2 475 úsecích, tedy v 10× větší kupce.

| Zdroj | správný § mezi 5 nalezenými |
|---|---|
| 5 témat, 260 úseků | 24 z 24 |
| 4 předpisy, 2 475 úseků | 24 z 24 |

## Co pomohlo ve vyhledávání

Všech 40 otázek s odpovědí, mění se jen způsob hledání.

| Režim | hit@3 | hit@5 |
|---|---|---|
| embeddingy e5-base (v1) | 29 z 40 | 33 z 40 |
| embeddingy e5-large | 35 z 40 | 37 z 40 |
| e5-large + BM25 nad laickou otázkou | 28 z 40 | 32 z 40 |
| e5-large + přepis otázky + BM25 nad přepisem (v2) | 37 z 40 | 39 z 40 |

Cena nových volání API při měření: v2 0.04283 $, v1 (model zdarma) jen AI soudce.

## Otázka po otázce

| # | Sada | Otázka | hit@5 | v1 | v2 | Poznámka k v2 |
|---|---|---|---|---|---|---|
| 1 | testovací | Kolik týdnů dovolené mám minimálně za rok? | ano | správně | správně | Asistent správně uvádí minimální výměru 4 týdny a doplňující vyšší výměry jsou podloženy dodanými úseky. |
| 2 | testovací | Jak dlouhá může být zkušební doba u běžného zaměstnance? | ano | správně | správně | Odpověď správně uvádí maximální délku 4 měsíce pro běžného zaměstnance a doplňující tvrzení jsou podložena dodanými úseky zákona. |
| 3 | testovací | Může mě šéf vyhodit ve zkušební době bez udání důvodu? | ano | správně | správně | Odpověď věcně odpovídá zlaté odpovědi a opírá se výhradně o dodaný úsek [1]. |
| 4 | testovací | Jak dlouhá je výpovědní doba? | ano | správně | správně | Asistent správně uvádí obecnou dvouměsíční výpovědní dobu i výjimku podle § 52 písm. f) až h); doplňující tvrzení jsou podložena dodanými úseky. |
| 5 | testovací | Od kdy začíná běžet výpovědní doba? | ano | správně | správně | Asistent správně uvádí, že výpovědní doba začíná dnem doručení výpovědi druhé smluvní straně, což odpovídá zlaté odpovědi i citovanému § 51 odst. 1. |
| 6 | testovací | Kolik hodin ročně můžu odpracovat na dohodu o provedení práce (DPP)? | ano | správně | správně | Odpověď správně uvádí limit 300 hodin ročně a započítání dalších DPP u téhož zaměstnavatele, což odpovídá zlaté odpovědi i citovaným úsekům. |
| 7 | testovací | Kolik hodin týdně můžu pracovat na dohodu o pracovní činnosti? | ano | **chyba** | správně | Asistent správně uvádí průměrný limit poloviny stanovené týdenní pracovní doby a opírá se o dodané úseky zákona. |
| 8 | testovací | Po kolika hodinách práce mám nárok na pauzu na jídlo? | ano | správně | správně | Odpověď správně uvádí pauzu nejdéle po 6 hodinách v trvání alespoň 30 minut i zvláštní pravidlo pro mladistvé po 4,5 hodinách a opírá se o dodaný § 88 odst. 1. |
| 9 | testovací | Kolik přesčasů mi může zaměstnavatel nařídit? | ano | správně | správně | Odpověď správně uvádí limit 8 hodin týdně a 150 hodin ročně, nadlimit jen po dohodě, a všechny doplňující údaje jsou podloženy dodanými úseky. |
| 10 | testovací | Kolik hodin odpočinku musím mít mezi dvěma směnami? | ano | **chyba** | správně | Asistent správně uvádí 11 hodin denního odpočinku a doplňuje zákonné výjimky pro mladistvé podle dodaného § 90 odst. 1. |
| 11 | testovací | Ve firmě jsem rok a půl a propouštějí mě, protože jsem nadbytečný. Kolik dostanu odstupné? | ano | správně | správně | Asistent správně uvádí, že při pracovním poměru 1 až 2 roky a výpovědi z důvodů podle § 52 písm. a) až c) náleží odstupné nejméně ve dvojnásobku průměrného výdělku, což odpovídá § 67 odst. 1 písm. b). |
| 12 | testovací | Může mi zaměstnavatel dát výpověď z jakéhokoli důvodu, třeba že se mu nelíbím? | ano | správně | správně | Asistent správně uvádí, že zaměstnavatel může dát výpověď jen z důvodů v § 52, a jeho tvrzení jsou podložena dodanými úseky. |
| 13 | testovací | Jak dlouho mám čas napadnout neplatnou výpověď u soudu? | ano | správně | správně | Asistent správně uvádí dvouměsíční lhůtu od dne, kdy měl pracovní poměr skončit, a jeho tvrzení jsou podložena dodaným úsekem [1]. |
| 14 | testovací | Proplatí mi zaměstnavatel nevyčerpanou dovolenou? | ano | správně | správně | Odpověď správně uvádí, že náhrada za nevyčerpanou dovolenou náleží jen při skončení pracovního poměru, a doplňující tvrzení jsou podložena dodanými úseky. |
| 15 | testovací | Firma mi už měsíc nezaplatila výplatu. Můžu hned odejít? | ano | **chyba** | správně | Asistent správně uvádí podmínku nevyplacení mzdy do 15 dnů po splatnosti i lhůtu pro okamžité zrušení podle § 56 a § 59, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 16 | testovací | Kolikrát mi můžou prodloužit smlouvu na dobu určitou? | ano | správně | správně | Správně (nejvýše dvakrát, prodloužení se počítá). Navíc uvedl strop 9 let, ten v textu opravdu je. Vynechal, že jedna smlouva smí být nejdéle na 3 roky. |
| 17 | testovací | Jaká je minimální mzda v roce 2026? | – | správně | správně | Správně „nevím“: konkrétní částka v předpisech není, § 111 odst. 7 jen říká, že ji vyhlašuje MPSV sdělením. Lepší odpověď by tohle vysvětlila. |
| 18 | testovací | Jak dlouho trvá mateřská dovolená? | ano | správně | správně | Odpověď správně uvádí základní délku mateřské dovolené 28/37 týdnů a doplňující případy jsou v souladu s dodanými úseky zákona. |
| 19 | testovací | Za jakých podmínek můžu pracovat z domova na home office? | ano | správně | správně | Odpověď správně uvádí písemnou dohodu i možnost nařízení při opatření orgánu veřejné moci a všechny doplňující údaje vycházejí z dodaných úseků. |
| 20 | testovací | Kolik peněz dostanu, když budu na nemocenské? | **ne** | **chyba** | **chyba** | Hledání nenašlo § 192 ZP ani § 29 ZNP: zákon o nemocenském pojištění má stovky podobných odstavců. Model proto řekl „nevím“. Bezpečné, ale neužitečné. Ve verzi s 5 tématy to byl test „nevím“. |
| 21 | kontrolní | Kolik hodin volna v kuse musím mít aspoň jednou za týden? | ano | **chyba** | správně | Odpověď správně uvádí 24 h týdenního odpočinku s navazujícím 11 h denním odpočinkem (celkem 35 h) i 48 h pro mladistvé a všechny údaje vycházejí z dodaných úseků. |
| 22 | kontrolní | Musí mi šéf dovolenou oznámit dopředu? | ano | správně | správně | Odpověď správně uvádí povinnost zaměstnavatele oznámit čerpání dovolené 14 dnů předem a doplňuje i zákonný případ oznámení ze strany zaměstnance, obojí je podloženo dodanými úseky. |
| 23 | kontrolní | Mám smlouvu jen na 4 měsíce. Jak dlouhou zkušební dobu mi můžou dát? | ano | správně | správně | Asistent správně uvádí maximálně polovinu sjednané doby, tedy 2 měsíce, a jeho tvrzení se opírají o dodané úseky zákona. |
| 24 | kontrolní | Jeden den jsem nepřišel do práce a neomluvil se. Může mi šéf vzít dovolenou? | ano | **chyba** | správně | Odpověď správně uvádí, že za neomluveně zameškanou směnu lze krátit dovolenou o zameškané hodiny, a opírá se o dodaný § 223 odst. 1. |
| 25 | kontrolní | Kdy mi přijdou peníze za odstupné? | ano | správně | správně | Odpověď věcně odpovídá § 67 odst. 5 a opírá se pouze o dodaný úsek [1]. |
| 26 | kontrolní | Když se se šéfem domluvíme na konci práce, musí to být na papíře? | ano | správně | správně | Asistent správně uvádí, že dohoda o rozvázání pracovního poměru musí být písemná, a jeho tvrzení jsou podložena příslušnými úseky zákona. |
| 27 | kontrolní | Jsem těhotná. Může mě zaměstnavatel vyhodit ze dne na den? | ano | správně | správně | Správně. Poslední věta („výpověď tyto úseky neupravují“) je zbytečná, AI soudce ji označil jako nepodloženou. |
| 28 | kontrolní | Do kdy si musím vybrat letošní dovolenou? | ano | **chyba** | správně | Odpověď správně uvádí obecné pravidlo o čerpání dovolené v kalendářním roce vzniku práva a všechny doplňující informace jsou podloženy dodanými úseky zákona. |
| 29 | kontrolní | Kolik je stravenkový paušál na jeden den? | – | správně | správně | Asistent správně odmítá odpověď, protože v dodaných úsecích není uvedena výše stravenkového paušálu. |
| 30 | kontrolní | Kolik dní placeného volna dostanu na vlastní svatbu? | ano | správně | správně | Odpověď přesně vystihuje 2 dny volna na vlastní svatbu a náhradu mzdy pouze za 1 den obřadu podle úseku [1]. |
| 31 | nové předpisy | Jak dlouho dostanu podporu v nezaměstnanosti, když mi je 35 let? | ano | správně | správně | Asistent správně uvádí, že ve 35 letech spadá do kategorie do 52 let věku, a proto má podpůrčí dobu 5 měsíců podle § 43 odst. 1. |
| 32 | nové předpisy | Kolik procent z výplaty dostanu jako podporu v nezaměstnanosti? | ano | správně | správně | Asistent správně uvádí procentní sazby pro obě věkové skupiny i základ podle § 50, všechny výroky jsou podloženy dodanými úseky. |
| 33 | nové předpisy | Kolik si můžu přivydělat, když jsem v evidenci na úřadu práce? | ano | správně | správně | Odpověď správně uvádí limit poloviny minimální mzdy pro pracovní poměr i DPČ a povinnost oznámení úřadu práce, vše podložené citovaným ustanovením. |
| 34 | nové předpisy | Jak dlouho musím předtím pracovat, abych měl nárok na podporu v nezaměstnanosti? | ano | správně | správně | Asistent správně uvádí 12 měsíců důchodového pojištění v posledních 2 letech před evidencí a opírá se o dodané úseky. |
| 35 | nové předpisy | Od kolikátého dne nemoci se platí nemocenská? | ano | správně | správně | Asistent správně uvádí, že nemocenské se standardně vyplácí od 15. kalendářního dne dočasné pracovní neschopnosti, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 36 | nové předpisy | Jak dlouho trvá otcovská a kolik se na ní dostává? | ano | **chyba** | **chyba** | Půl odpovědi: délku 2 týdny našel, výši 70 % ne (§ 38c ZNP nebyl mezi 5 úseky). Poctivě napsal, že výše v úsecích není. |
| 37 | nové předpisy | Jak dlouho můžu být doma s nemocným dítětem na ošetřovném? | ano | správně | správně | Asistent správně uvádí podpůrčí dobu 9, resp. 16 kalendářních dnů pro osamělého pojištěnce a jeho tvrzení jsou podložena citovanými úseky. |
| 38 | nové předpisy | Dostanu příplatek za práci v noci? | ano | **chyba** | **chyba** | Smíchal mzdu a plat: 20 % podle § 125 platí jen pro plat ve veřejné sféře. Pro běžnou mzdu je to nejméně 10 % (§ 116), to uvedl až jako druhé. |
| 39 | nové předpisy | Kolik příplatku dostanu za přesčas? | ano | **chyba** | správně | Asistent správně uvádí alespoň 25 % u mzdy i sazbu 25 %, resp. 50 % u platu podle dodaných ustanovení. |
| 40 | nové předpisy | Do kdy mi musí zaměstnavatel vydat pracovní posudek? | ano | správně | **chyba** | Obrátil význam: zákon říká, že zaměstnavatel posudek nemusí vydat dřív než 2 měsíce před koncem zaměstnání. Model napsal, že nesmí. |
| 41 | nové předpisy | Jak dlouho dopředu musím požádat o rodičovskou dovolenou? | ano | správně | správně | Odpověď správně uvádí lhůtu 30 dnů, výjimku vážných důvodů i písemnou formu žádosti a opírá se o dodané úseky. |
| 42 | nové předpisy | Kolik dní volna dostanu, když mi zemře máma? | ano | správně | správně | Odpověď správně uvádí 1 placený den na pohřeb, další placený den při obstarání pohřbu a až 5 neplacených dnů, vše opřené o dodaný úsek [1]. |
| 43 | nové předpisy | Kolik peněz dostanu celkem na rodičovském příspěvku? | – | správně | správně | Asistent správně odmítl odpovědět, protože rodičovský příspěvek není v dodaných úsecích zákona upraven. |
| 44 | nové předpisy | Kolik zaplatím jako OSVČ měsíčně na sociálním pojištění? | – | správně | správně | Asistent správně odmítl odpovědět, protože v dodaných úsecích není úprava pojistného OSVČ. |
| 45 | nové předpisy | Jak dlouhá je výpovědní doba z nájmu bytu? | – | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky se týkají pracovněprávních vztahů, nikoli nájmu bytu. |
| 46 | nové předpisy | Kolik je sleva na dani na poplatníka? | – | správně | správně | Asistent správně odmítl odpovědět, protože sleva na dani na poplatníka není v dodaných úsecích zákona. |

## Chyby v1

- **7:** Stejná chyba jako ve verzi s 5 tématy: k DPČ přidal „300 hodin ročně“, to platí jen pro DPP.
- **10:** § 90 odst. 1 se nenašel, model řekl „nevím“.
- **15:** Laická slova „výplata“ a „odejít“: hledání podle významu nenašlo § 56, model řekl „nevím“.
- **20:** § 192 ZP ani § 29 ZNP se nenašly, model řekl „nevím“.
- **21:** Našel jen odstavec o mladistvých (48 hodin), pravidlo pro dospělé (24 hodin) mu chybělo.
- **24:** § 223 odst. 1 (krácení dovolené) se nenašel, model řekl „nevím“.
- **28:** § 218 odst. 1 se nenašel. Napsal „musíte vyčerpat do konce roku“, zákon ale ukládá povinnost zaměstnavateli určit čerpání.
- **36:** Délka 2 týdny správně, výše 70 % chybí (§ 38c nebyl mezi úseky).
- **38:** Jako první uvedl 20 % podle § 125, to platí jen pro plat ve veřejné sféře. Pro mzdu je to nejméně 10 %.
- **39:** Smíchal mzdu a plat: 50 % za přesčas v den odpočinku platí jen u platu. Poslední věta o náhradním volnu je nepodložená.

## Historie

První verze hledala jen v 5 tématech zákoníku práce (260 úseků). Tam měla v2 na 30 otázkách 30 správně a v1 26.
Data té verze jsou v `data/archive_5temat/`. Šest otázek, které tehdy měly správnou odpověď „nevím“, má teď odpověď
v nových předpisech (třeba mateřská nebo svatba), takže dostaly novou zlatou odpověď (původní je v poli `gold_5temat`).
