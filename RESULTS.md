# Výsledky měření

Zdroj: 4 předpisy, 2 475 úseků (celý zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění,
nařízení vlády o překážkách v práci). 66 testovacích otázek v 5 sadách, 56 má odpověď v předpisech, 10 záměrně ne.
Verdikt „správně“ je po druhé kontrole všech odpovědí proti textu zákona (Claude Opus 5.5).

## v1 → v2 → v3

| Měřítko | v1 | v2 | v3 |
|---|---|---|---|
| Model | `nvidia/nemotron-3-super-120b-a12b:free` | `deepseek/deepseek-v4.1-flash` | `deepseek/deepseek-v4-pro` |
| Vyhledávání | e5-base | e5-large + BM25 + přepis (RRF) | v2 + LLM vybere 5 z 20 kandidátů |
| Pravidla odpovědi | základní | přísnější | + varianty (mzda × plat), doptání, musí/nemusí/nesmí |
| **Odpověď správně (celkem)** | 54 z 66 | 60 z 66 | 66 z 66 |
| z toho otázky s odpovědí | 44 z 56 | 50 z 56 | 56 z 56 |
| z toho správně „nevím“, když zdroj mlčí | 10 z 10 | 10 z 10 | 10 z 10 |
| Správný paragraf mezi 5 úseky pro model (hit@5) | 47 z 56 | 53 z 56 | 56 z 56 |
| Správný paragraf v top 3 (hit@3) | 42 z 56 | 50 z 56 | 56 z 56 |
| „Nevím“, i když odpověď ve zdroji byla | 5 z 56 | 3 z 56 | 0 z 56 |
| Opírá se o zdroj (podle AI soudce) | 60 z 66 | 64 z 66 | 65 z 66 |
| AI soudce se shodl s druhou kontrolou | 65 z 66 | 64 z 66 | 65 z 66 |

## Podle sad

| Sada | otázek | v1 | v2 | v3 | v3 hit@5 |
|---|---|---|---|---|---|
| testovací | 20 | 16 | 19 | 20 | 19 z 19 |
| kontrolní | 10 | 7 | 10 | 10 | 9 z 9 |
| nové předpisy | 16 | 13 | 13 | 16 | 12 z 12 |
| po opravě | 10 | 8 | 8 | 10 | 8 z 8 |
| po v3.1 | 10 | 10 | 10 | 10 | 8 z 8 |

- **testovací (1–20):** podle chyb na nich jsem navrhl v2, výsledek je tu nadsazený.
- **kontrolní (21–30):** napsané až po návrhu v2.
- **nové předpisy (31–46):** napsané po přidání předpisů. Podle 4 chyb v2 na sadách 1–46 jsem navrhl v3, takže i tady je v3 zvýhodněná.
- **po opravě (47–56):** napsané po návrhu v3, ještě před jejím spuštěním. Nejpoctivější srovnání v2 a v3.

## Co udělal větší zdroj s vyhledáváním

Stejných 24 otázek, které měly odpověď už v první verzi (5 témat zákoníku práce, 260 úseků).
Teď se hledá v 2 475 úsecích, tedy v 10× větší kupce.

| Zdroj | správný § mezi 5 nalezenými |
|---|---|
| 5 témat, 260 úseků (v2) | 24 z 24 |
| 4 předpisy, 2 475 úseků (v2) | 24 z 24 |

## Co pomohlo ve vyhledávání

Všech 56 otázek s odpovědí, mění se jen způsob hledání.

| Režim | hit@3 | hit@5 |
|---|---|---|
| embeddingy e5-base (v1) | 42 z 56 | 47 z 56 |
| embeddingy e5-large | 48 z 56 | 50 z 56 |
| e5-large + BM25 nad laickou otázkou | 39 z 56 | 44 z 56 |
| e5-large + přepis otázky + BM25 nad přepisem (v2) | 50 z 56 | 53 z 56 |
| v2 + LLM vybere 5 z 20 kandidátů (v3) | 56 z 56 | 56 z 56 |

## Otázka po otázce

| # | Sada | Otázka | hit@5 | v1 | v2 | v3 | Poznámka k v3 |
|---|---|---|---|---|---|---|---|
| 1 | testovací | Kolik týdnů dovolené mám minimálně za rok? | ano | správně | správně | správně | Asistent správně uvádí minimální výměru 4 týdny dle § 212 odst. 1 a opírá se pouze o dodaný úsek. |
| 2 | testovací | Jak dlouhá může být zkušební doba u běžného zaměstnance? | ano | správně | správně | správně | Asistent správně uvádí limit 4 měsíce pro běžného zaměstnance a doplňující podmínky jsou věcně správné i podložené citovanými úseky. |
| 3 | testovací | Může mě šéf vyhodit ve zkušební době bez udání důvodu? | ano | správně | správně | správně | Odpověď přesně vystihuje zlatou odpověď i § 66 odst. 1 a opírá se pouze o dodaný úsek. |
| 4 | testovací | Jak dlouhá je výpovědní doba? | ano | správně | správně | správně | Asistent správně uvádí obecnou dvouměsíční výpovědní dobu i výjimku jednoho měsíce podle § 52 písm. f) až h), což odpovídá zlaté odpovědi, a všechna tvrzení jsou podložena dodanými úseky. |
| 5 | testovací | Od kdy začíná běžet výpovědní doba? | ano | správně | správně | správně | Asistent správně uvádí obecné pravidlo podle § 51 odst. 1 ZP i výjimku podle § 78 odst. 7 ZZ, obojí je podloženo dodanými úseky. |
| 6 | testovací | Kolik hodin ročně můžu odpracovat na dohodu o provedení práce (DPP)? | ano | správně | správně | správně | Odpověď správně uvádí limit 300 hodin ročně u jednoho zaměstnavatele a sčítání více DPP, což odpovídá zlaté odpovědi i citovaným úsekům. |
| 7 | testovací | Kolik hodin týdně můžu pracovat na dohodu o pracovní činnosti? | ano | **chyba** | správně | správně | Asistent správně uvádí limit poloviny stanovené týdenní pracovní doby (20 h) a jeho posuzování za 52 týdnů, vše podloženo dodanými úseky. |
| 8 | testovací | Po kolika hodinách práce mám nárok na pauzu na jídlo? | ano | správně | správně | správně | Odpověď správně uvádí obě lhůty (6 hodin i 4,5 hodiny pro mladistvé) a opírá se výhradně o dodaný § 88 odst. 1. |
| 9 | testovací | Kolik přesčasů mi může zaměstnavatel nařídit? | ano | správně | správně | správně | Odpověď věcně odpovídá zlaté odpovědi (8 h/týden, 150 h/rok, nad rozsah jen po dohodě) a všechna tvrzení jsou podložena citovanými úseky zákona. |
| 10 | testovací | Kolik hodin odpočinku musím mít mezi dvěma směnami? | ano | **chyba** | správně | správně | Opraveno: ve v3.0 výběr přes LLM vyhodil základní § 90 odst. 1, pravidlo „odstavec 1“ ho vrátilo. Odpověď má 11 hodin i výjimky. |
| 11 | testovací | Ve firmě jsem rok a půl a propouštějí mě, protože jsem nadbytečný. Kolik dostanu odstupné? | ano | správně | správně | správně | Asistent správně určil dvojnásobek průměrného výdělku podle § 67 odst. 1 písm. b) a § 52 písm. c), což odpovídá zlaté odpovědi i dodaným úsekům. |
| 12 | testovací | Může mi zaměstnavatel dát výpověď z jakéhokoli důvodu, třeba že se mu nelíbím? | ano | správně | správně | správně | Odpověď správně uvádí taxativní výčet důvodů v § 52 a že osobní neoblíbenost mezi ně nepatří, vše podloženo dodanými úseky. |
| 13 | testovací | Jak dlouho mám čas napadnout neplatnou výpověď u soudu? | ano | správně | správně | správně | Asistent správně uvádí dvouměsíční lhůtu od zamýšleného skončení pracovního poměru a opírá se o § 72. |
| 14 | testovací | Proplatí mi zaměstnavatel nevyčerpanou dovolenou? | ano | správně | správně | správně | Odpověď správně uvádí, že náhrada přísluší jen při skončení pracovního poměru, a doplňuje přesnou výjimku pro dodatkovou dovolenou podle dodaných úseků. |
| 15 | testovací | Firma mi už měsíc nezaplatila výplatu. Můžu hned odejít? | ano | **chyba** | správně | správně | Odpověď správně a s oporou v dodaných úsecích potvrzuje možnost okamžitého zrušení při nevyplacení mzdy do 15 dnů po splatnosti a doplňuje relevantní lhůty a náhradu mzdy. |
| 16 | testovací | Kolikrát mi můžou prodloužit smlouvu na dobu určitou? | ano | správně | správně | správně | Odpověď správně uvádí limit dvou opakování včetně prodloužení a doplňující podmínky, vše podloženo citovaným § 39 odst. 2. |
| 17 | testovací | Jaká je minimální mzda v roce 2026? | – | správně | správně | správně | Asistent správně odmítl uvést konkrétní částku, protože ta v dodaných úsecích ani v předpisech není a vyhlašuje se sdělením MPSV. |
| 18 | testovací | Jak dlouho trvá mateřská dovolená? | ano | správně | správně | správně | Asistent správně uvádí 28/37 týdnů dle § 195 odst. 1 a doplňující údaje jsou věrně citovány z dodaných úseků. |
| 19 | testovací | Za jakých podmínek můžu pracovat z domova na home office? | ano | správně | správně | správně | Odpověď věcně odpovídá zlaté odpovědi a všechna tvrzení jsou podložena dodanými úseky zákona. |
| 20 | testovací | Kolik peněz dostanu, když budu na nemocenské? | ano | **chyba** | **chyba** | správně | Opraveno: § 192 odst. 1 říká jen „ve výši podle odstavce 2“, dohledání odkazu přidalo odstavec 2 (60 %). Odpověď má náhradu od zaměstnavatele i nemocenské 60/66/72 %. |
| 21 | kontrolní | Kolik hodin volna v kuse musím mít aspoň jednou za týden? | ano | **chyba** | správně | správně | Asistent správně uvádí 24 hodin týdenního odpočinku s navazujícím denním odpočinkem a doplňuje relevantní výjimky i mladistvé, vše podložené dodanými úseky. |
| 22 | kontrolní | Musí mi šéf dovolenou oznámit dopředu? | ano | správně | správně | správně | Odpověď přesně vystihuje § 217 odst. 1 ZP včetně možnosti kratší dohody a opírá se výhradně o dodaný úsek. |
| 23 | kontrolní | Mám smlouvu jen na 4 měsíce. Jak dlouhou zkušební dobu mi můžou dát? | ano | správně | správně | správně | Asistent správně uvádí maximálně 2 měsíce jako polovinu 4měsíční smlouvy a oba limity opírá o citované úseky. |
| 24 | kontrolní | Jeden den jsem nepřišel do práce a neomluvil se. Může mi šéf vzít dovolenou? | ano | **chyba** | správně | správně | Odpověď přesně odpovídá zlaté odpovědi i § 223 odst. 1 ZP, o který se opírá. |
| 25 | kontrolní | Kdy mi přijdou peníze za odstupné? | ano | správně | správně | správně | Odpověď věcně odpovídá zlaté odpovědi i § 67 odst. 5 ZP a všechna tvrzení jsou podložena dodaným úsekem. |
| 26 | kontrolní | Když se se šéfem domluvíme na konci práce, musí to být na papíře? | ano | správně | správně | správně | Asistent správně uvádí, že dohoda o rozvázání pracovního poměru musí být písemná, a jeho tvrzení jsou podložena citovanými úseky zákona. |
| 27 | kontrolní | Jsem těhotná. Může mě zaměstnavatel vyhodit ze dne na den? | ano | správně | správně | správně | Asistent správně uvádí, že zaměstnavatel nesmí okamžitě zrušit pracovní poměr s těhotnou zaměstnankyní, což odpovídá zlaté odpovědi i citovaným úsekům. |
| 28 | kontrolní | Do kdy si musím vybrat letošní dovolenou? | ano | **chyba** | správně | správně | Věcně správně a úplně. Formulace „musíte si vybrat“ je nepřesná: povinnost určit čerpání má zaměstnavatel. |
| 29 | kontrolní | Kolik je stravenkový paušál na jeden den? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky výši stravenkového paušálu neuvádějí. |
| 30 | kontrolní | Kolik dní placeného volna dostanu na vlastní svatbu? | ano | správně | správně | správně | Odpověď přesně odpovídá zlaté odpovědi i úseku [1] a neobsahuje žádné nepravdivé tvrzení. |
| 31 | nové předpisy | Jak dlouho dostanu podporu v nezaměstnanosti, když mi je 35 let? | ano | správně | správně | správně | Asistent správně uvádí 5 měsíců pro věk do 52 let a odkazuje na příslušné úseky zákona. |
| 32 | nové předpisy | Kolik procent z výplaty dostanu jako podporu v nezaměstnanosti? | ano | správně | správně | správně | Odpověď přesně vystihuje procentní sazby i věkové hranice podle § 50 odst. 3 a všechna tvrzení jsou podložena dodanými úseky. |
| 33 | nové předpisy | Kolik si můžu přivydělat, když jsem v evidenci na úřadu práce? | ano | správně | správně | správně | Odpověď správně uvádí limit poloviny minimální mzdy pro pracovní poměr i DPČ a oznamovací povinnost, vše podloženo dodanými úseky. |
| 34 | nové předpisy | Jak dlouho musím předtím pracovat, abych měl nárok na podporu v nezaměstnanosti? | ano | správně | správně | správně | Asistent správně uvádí základní podmínku 12 měsíců pojištění za poslední 2 roky a správně shrnuje i výjimky podle § 48 a § 49. |
| 35 | nové předpisy | Od kolikátého dne nemoci se platí nemocenská? | ano | správně | správně | správně | Odpověď správně uvádí 15. kalendářní den i náhradu mzdy za prvních 14 dnů a obě tvrzení jsou podložena citovanými úseky. |
| 36 | nové předpisy | Jak dlouho trvá otcovská a kolik se na ní dostává? | ano | **chyba** | **chyba** | správně | Opraveno ve v3: výběr přes LLM přidal § 38c, odpověď má délku (2 týdny) i výši (70 %). |
| 37 | nové předpisy | Jak dlouho můžu být doma s nemocným dítětem na ošetřovném? | ano | správně | správně | správně | Odpověď správně uvádí 9 dnů, výjimku 16 dnů pro osamělého rodiče i pravidlo o dovršení 10 let, vše podloženo dodanými úseky. |
| 38 | nové předpisy | Dostanu příplatek za práci v noci? | ano | **chyba** | **chyba** | správně | Opraveno ve v3: rozliší mzdu (nejméně 10 %), plat (20 %) i dohody. AI soudce to označil za chybu, protože zlatá odpověď mluví jen o mzdě. Ruční kontrola: správně. |
| 39 | nové předpisy | Kolik příplatku dostanu za přesčas? | ano | **chyba** | správně | správně | Odpověď správně vystihuje zákonnou úpravu příplatku za přesčas pro mzdu i plat a opírá se o citované úseky. |
| 40 | nové předpisy | Do kdy mi musí zaměstnavatel vydat pracovní posudek? | ano | správně | **chyba** | správně | Opraveno ve v3.1: silnější model píše správně „nemusí vydat dříve“. Levný model tu větu převracel na „nesmí“, a to nestabilně (jednou správně, jindy špatně). |
| 41 | nové předpisy | Jak dlouho dopředu musím požádat o rodičovskou dovolenou? | ano | správně | správně | správně | Odpověď správně uvádí lhůtu 30 dnů i výjimku vážných důvodů podle § 196 odst. 2, i když nezmiňuje písemnou formu. |
| 42 | nové předpisy | Kolik dní volna dostanu, když mi zemře máma? | ano | správně | správně | správně | Odpověď přesně odpovídá zlaté odpovědi i bodu 7 přílohy NV 590, ze kterého vychází. |
| 43 | nové předpisy | Kolik peněz dostanu celkem na rodičovském příspěvku? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky rodičovský příspěvek neupravují, a nic si nevymyslel. |
| 44 | nové předpisy | Kolik zaplatím jako OSVČ měsíčně na sociálním pojištění? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neobsahují úpravu pojistného OSVČ. |
| 45 | nové předpisy | Jak dlouhá je výpovědní doba z nájmu bytu? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neobsahují úpravu nájmu bytu (pouze zákoník práce a služební zákon), a věcně tak odpovídá zlaté odpovědi. |
| 46 | nové předpisy | Kolik je sleva na dani na poplatníka? | – | správně | správně | správně | Asistent odpovídá, že informaci nemá, což odpovídá zlaté odpovědi a dodané úseky se slevou na dani na poplatníka skutečně nesouvisí. |
| 47 | po opravě | Co dostanu, když pracuji ve svátek? | ano | správně | správně | správně | Správně, varianty pro mzdu i plat. |
| 48 | po opravě | Do kdy po narození dítěte musím nastoupit na otcovskou? | ano | správně | správně | správně | Odpověď správně uvádí lhůtu 6 týdnů, prodloužení o dny hospitalizace i limit jednoho roku, vše podloženo citovanými úseky. |
| 49 | po opravě | Kolik peněz dostanu na ošetřovném? | ano | správně | **chyba** | správně | Asistent správně uvádí 60 % denního vyměřovacího základu a jeho tvrzení jsou podložena dodanými úseky. |
| 50 | po opravě | Dostanu něco navíc za pracovní pohotovost? | ano | správně | správně | správně | Asistent správně uvádí odměnu nejméně 10 % průměrného výdělku a správně doplňuje, že za výkon práce v době pohotovosti náleží mzda/plat a odměna za pohotovost nepřísluší, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 51 | po opravě | Do kdy mi musí zaměstnavatel vyplatit výplatu? | ano | **chyba** | **chyba** | správně | Odpověď správně uvádí lhůtu splatnosti mzdy dle § 141 odst. 1 i související pravidla a všechny citace odpovídají dodaným úsekům. |
| 52 | po opravě | Musí mi zaměstnavatel při odchodu dát zápočťák? | ano | **chyba** | správně | správně | Odpověď vystihuje povinnost vydat potvrzení o zaměstnání při skončení pracovního poměru i dohod, včetně výjimek u DPP, a opírá se o citovaný § 313. |
| 53 | po opravě | Můžu mít vedle práce ještě živnost ve stejném oboru jako můj zaměstnavatel? | ano | správně | správně | správně | Asistent správně uvádí, že vedlejší výdělečná činnost shodná s předmětem činnosti zaměstnavatele vyžaduje předchozí písemný souhlas, což odpovídá § 304 odst. 1 zákoníku práce. |
| 54 | po opravě | Co musí obsahovat pracovní smlouva? | ano | správně | správně | správně | Odpověď správně uvádí všechny zákonné náležitosti podle § 34 odst. 1 a doplňuje i písemnou formu a další náležitosti pro cizince, vše se opírá o dodané úseky. |
| 55 | po opravě | Kolik je příspěvek na bydlení? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky příspěvek na bydlení podle zákona o státní sociální podpoře neobsahují. |
| 56 | po opravě | Kolik let musím odpracovat, abych dostal důchod? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neupravují podmínky nároku na starobní důchod a zlatá odpověď je NEVÍM. |
| 57 | po v3.1 | Může mě šéf poslat na služební cestu, i když nechci? | ano | správně | správně | správně | Asistent správně uvádí, že vyslání na pracovní cestu je možné jen na základě dohody, a doplňuje výjimku pro těhotné a pečující osoby podle § 240, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 58 | po v3.1 | Musí zaměstnavatel zapisovat, kolik hodin jsem odpracoval? | ano | správně | správně | správně | Asistent správně potvrzuje povinnost evidence odpracované směny a přesčasů dle § 96 odst. 1 a jeho tvrzení jsou podložena dodanými úseky. |
| 59 | po v3.1 | Dostanu volno, když mi manželka rodí? | ano | správně | správně | správně | Odpověď přesně vystihuje zlatou odpověď i příslušný úsek NV 590 bod 6. |
| 60 | po v3.1 | Jsem těhotná a pracuji v noci. Můžu chtít jen denní směny? | ano | správně | správně | správně | Odpověď přesně odpovídá zlaté odpovědi a opírá se o citovaný § 239 odst. 1. |
| 61 | po v3.1 | Kolik hodin denně může pracovat mladistvý, který ještě chodí na povinnou školní docházku? | ano | správně | správně | správně | Asistent správně uvádí limit 7 hodin denně pro mladistvého neukončivšího povinnou školní docházku podle § 79a ZP, což odpovídá zlaté odpovědi, a jeho tvrzení jsou podložena dodanými úseky. |
| 62 | po v3.1 | Kolik musím zaplatit, když v práci omylem něco rozbiju? | ano | správně | správně | správně | Odpověď správně uvádí limit čtyřapůlnásobku průměrného výdělku při nedbalosti a doplňuje relevantní související pravidla, vše podložené dodanými úseky. |
| 63 | po v3.1 | Jak dlouho musím být pojištěná, abych dostala peněžitou pomoc v mateřství? | ano | správně | správně | správně | Asistent správně uvádí základní podmínku 270 dní ve dvou letech i doplňkovou variantu 540 dní podle § 37a, obojí podložené dodanými úseky. |
| 64 | po v3.1 | Musí mi zaměstnavatel písemně říct, kolik mám dovolené a jak dlouhá je zkušební doba? | ano | správně | správně | správně | Odpověď správně uvádí povinnost písemně informovat o dovolené i zkušební době, pokud nejsou v pracovní smlouvě, a opírá se o § 37 a § 35. |
| 65 | po v3.1 | Kolik se platí výživné na dítě? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky výživné na dítě neupravují, což odpovídá zlaté odpovědi. |
| 66 | po v3.1 | Kdy můžu jít do předčasného důchodu? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neobsahují úpravu předčasného důchodu. |

## Chyby v2

- **20:** Hledání nenašlo § 192 ZP ani § 29 ZNP: zákon o nemocenském pojištění má stovky podobných odstavců. Model proto řekl „nevím“. Bezpečné, ale neužitečné. Ve verzi s 5 tématy to byl test „nevím“.
- **36:** Půl odpovědi: délku 2 týdny našel, výši 70 % ne (§ 38c ZNP nebyl mezi 5 úseky). Poctivě napsal, že výše v úsecích není.
- **38:** Smíchal mzdu a plat: 20 % podle § 125 platí jen pro plat ve veřejné sféře. Pro běžnou mzdu je to nejméně 10 % (§ 116), to uvedl až jako druhé.
- **40:** Obrátil význam: zákon říká, že zaměstnavatel posudek nemusí vydat dřív než 2 měsíce před koncem zaměstnání. Model napsal, že nesmí.
- **49:** § 41 ZNP (60 %) se nenašel, model řekl „nevím“. AI soudce to bez přemýšlení přehlédl a dal „správně“.
- **51:** § 141 odst. 1 se nenašel, model řekl „nevím“. AI soudce to přehlédl.

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
- **51:** § 141 odst. 1 se nenašel, odpověděl z jiného odstavce o výplatním termínu.
- **52:** § 313 se nenašel, model řekl „nevím“. AI soudce to přehlédl.

## Historie

První verze hledala jen v 5 tématech zákoníku práce (260 úseků). Tam měla v2 na 30 otázkách 30 správně a v1 26.
Data té verze jsou v `data/archive_5temat/`. Šest otázek, které tehdy měly správnou odpověď „nevím“, má teď odpověď
v nových předpisech (třeba mateřská nebo svatba), takže dostaly novou zlatou odpověď (původní je v poli `gold_5temat`).
