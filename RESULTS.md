# Výsledky měření

Zdroj: 4 předpisy, 2 475 úseků (celý zákoník práce, zákon o zaměstnanosti, zákon o nemocenském pojištění,
nařízení vlády o překážkách v práci). 56 testovacích otázek ve 4 sadách, 48 má odpověď v předpisech, 8 záměrně ne.
Verdikt „správně“ je po ruční kontrole všech odpovědí proti textu zákona.

## v1 → v2 → v3

| Měřítko | v1 | v2 | v3 |
|---|---|---|---|
| Model | `nvidia/nemotron-3-super-120b-a12b:free` | `deepseek/deepseek-v4.1-flash` | `deepseek/deepseek-v4.1-flash` |
| Vyhledávání | e5-base | e5-large + BM25 + přepis (RRF) | v2 + LLM vybere 5 z 20 kandidátů |
| Pravidla odpovědi | základní | přísnější | + varianty (mzda × plat), doptání, musí/nemusí/nesmí |
| **Odpověď správně (celkem)** | 44 z 56 | 50 z 56 | 55 z 56 |
| z toho otázky s odpovědí | 36 z 48 | 42 z 48 | 47 z 48 |
| z toho správně „nevím“, když zdroj mlčí | 8 z 8 | 8 z 8 | 8 z 8 |
| Správný paragraf mezi 5 úseky pro model (hit@5) | 39 z 48 | 45 z 48 | 48 z 48 |
| Správný paragraf v top 3 (hit@3) | 34 z 48 | 43 z 48 | 48 z 48 |
| „Nevím“, i když odpověď ve zdroji byla | 5 z 48 | 3 z 48 | 0 z 48 |
| Opírá se o zdroj (podle AI soudce) | 50 z 56 | 54 z 56 | 55 z 56 |
| AI soudce se shodl s ruční kontrolou | 55 z 56 | 54 z 56 | 54 z 56 |

## Podle sad

| Sada | otázek | v1 | v2 | v3 | v3 hit@5 |
|---|---|---|---|---|---|
| testovací | 20 | 16 | 19 | 20 | 19 z 19 |
| kontrolní | 10 | 7 | 10 | 10 | 9 z 9 |
| nové předpisy | 16 | 13 | 13 | 15 | 12 z 12 |
| po opravě | 10 | 8 | 8 | 10 | 8 z 8 |

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

Všech 48 otázek s odpovědí, mění se jen způsob hledání.

| Režim | hit@3 | hit@5 |
|---|---|---|
| embeddingy e5-base (v1) | 34 z 48 | 39 z 48 |
| embeddingy e5-large | 40 z 48 | 42 z 48 |
| e5-large + BM25 nad laickou otázkou | 33 z 48 | 37 z 48 |
| e5-large + přepis otázky + BM25 nad přepisem (v2) | 43 z 48 | 45 z 48 |
| v2 + LLM vybere 5 z 20 kandidátů (v3) | 48 z 48 | 48 z 48 |

## Otázka po otázce

| # | Sada | Otázka | hit@5 | v1 | v2 | v3 | Poznámka k v3 |
|---|---|---|---|---|---|---|---|
| 1 | testovací | Kolik týdnů dovolené mám minimálně za rok? | ano | správně | správně | správně | Asistent správně uvádí minimální výměru 4 týdny podle § 212 odst. 1 a jeho tvrzení jsou podložena dodanými úseky. |
| 2 | testovací | Jak dlouhá může být zkušební doba u běžného zaměstnance? | ano | správně | správně | správně | Asistent správně uvádí 4měsíční limit pro běžného zaměstnance a doplňuje relevantní omezení pro pracovní poměr na dobu určitou, obojí podložené dodanými úseky. |
| 3 | testovací | Může mě šéf vyhodit ve zkušební době bez udání důvodu? | ano | správně | správně | správně | Odpověď přesně vystihuje zlatou odpověď i citovaný § 66 odst. 1 a opírá se pouze o dodaný úsek. |
| 4 | testovací | Jak dlouhá je výpovědní doba? | ano | správně | správně | správně | Správně (2 měsíce, výjimky 1 měsíc), doptal se, jestli nejde o dohodu podle § 87a. |
| 5 | testovací | Od kdy začíná běžet výpovědní doba? | ano | správně | správně | správně | Správně. Nově se doptal, jestli jde o obecnou výpověď, nebo zvláštní případ (pravidlo 7 ve v3). |
| 6 | testovací | Kolik hodin ročně můžu odpracovat na dohodu o provedení práce (DPP)? | ano | správně | správně | správně | Asistent správně uvádí limit 300 hodin ročně a započítávání dalších DPP u téhož zaměstnavatele, což odpovídá zlaté odpovědi i citovaným úsekům. |
| 7 | testovací | Kolik hodin týdně můžu pracovat na dohodu o pracovní činnosti? | ano | **chyba** | správně | správně | Odpověď správně uvádí limit poloviny stanovené týdenní pracovní doby (20 h) a všechna tvrzení jsou podložena citovanými úseky. |
| 8 | testovací | Po kolika hodinách práce mám nárok na pauzu na jídlo? | ano | správně | správně | správně | Odpověď správně uvádí hranici 6 hodin pro dospělé i 4,5 hodiny pro mladistvé a obě tvrzení se opírají o dodaný § 88 odst. 1. |
| 9 | testovací | Kolik přesčasů mi může zaměstnavatel nařídit? | ano | správně | správně | správně | Odpověď správně uvádí limity 8 hodin týdně a 150 hodin ročně i možnost navýšení jen po dohodě, vše podloženo citovanými úseky. |
| 10 | testovací | Kolik hodin odpočinku musím mít mezi dvěma směnami? | ano | **chyba** | správně | správně | Opraveno pravidlem „odstavec 1“: výběr přes LLM vzal jen výjimky (§ 90 odst. 2 a 3), pravidlo k nim přidalo § 90 odst. 1 se základními 11 hodinami. Před tou opravou to byla jediná nová chyba v3. |
| 11 | testovací | Ve firmě jsem rok a půl a propouštějí mě, protože jsem nadbytečný. Kolik dostanu odstupné? | ano | správně | správně | správně | Asistent správně určil dvojnásobek průměrného výdělku pro dobu 1–2 roky při nadbytečnosti dle § 52 písm. c) a opřel se o dodaný § 67 odst. 1. |
| 12 | testovací | Může mi zaměstnavatel dát výpověď z jakéhokoli důvodu, třeba že se mu nelíbím? | ano | správně | správně | správně | Správně, s příklady důvodů z § 52. |
| 13 | testovací | Jak dlouho mám čas napadnout neplatnou výpověď u soudu? | ano | správně | správně | správně | Asistent správně uvádí dvouměsíční lhůtu od skončení pracovního poměru a opírá se o dodaný § 72. |
| 14 | testovací | Proplatí mi zaměstnavatel nevyčerpanou dovolenou? | ano | správně | správně | správně | Odpověď správně uvádí, že náhrada přísluší jen při skončení pracovního poměru, a doplňující tvrzení jsou podložena dodanými úseky. |
| 15 | testovací | Firma mi už měsíc nezaplatila výplatu. Můžu hned odejít? | ano | **chyba** | správně | správně | Asistent správně a s odkazy na úseky zákona uvádí, že při nevyplacení mzdy do 15 dnů po splatnosti lze okamžitě zrušit pracovní poměr, včetně lhůty podle § 59. |
| 16 | testovací | Kolikrát mi můžou prodloužit smlouvu na dobu určitou? | ano | správně | správně | správně | Odpověď správně uvádí limit dvou opakování (prodloužení se počítá jako opakování) a je plně podložena citovaným § 39 odst. 2. |
| 17 | testovací | Jaká je minimální mzda v roce 2026? | – | správně | správně | správně | Asistent správně odmítl uvést konkrétní částku, protože ta v dodaných úsecích ani v předpisech není a vyhlašuje se sdělením MPSV. |
| 18 | testovací | Jak dlouho trvá mateřská dovolená? | ano | správně | správně | správně | Odpověď správně uvádí 28/37 týdnů dle § 195 odst. 1 a doplňující podmínky jsou věcně správné i podložené dodanými úseky. |
| 19 | testovací | Za jakých podmínek můžu pracovat z domova na home office? | ano | správně | správně | správně | Odpověď vystihuje obě podmínky ze zlaté odpovědi a opírá se výhradně o úseky [1] a [2]. |
| 20 | testovací | Kolik peněz dostanu, když budu na nemocenské? | ano | **chyba** | **chyba** | správně | Opraveno pravidlem odkazů: § 192 odst. 1 říká jen „ve výši podle odstavce 2“, asistent si teď odstavec 2 dohledá. Odpověď má 60 % od zaměstnavatele za prvních 14 dní i nemocenské 60/66/72 %. |
| 21 | kontrolní | Kolik hodin volna v kuse musím mít aspoň jednou za týden? | ano | **chyba** | správně | správně | Odpověď správně uvádí 24 hodin pro dospělé s navazujícím denním odpočinkem a 48 hodin pro mladistvé, vše podloženo citovanými úseky. |
| 22 | kontrolní | Musí mi šéf dovolenou oznámit dopředu? | ano | správně | správně | správně | Odpověď správně uvádí povinnost písemného oznámení 14 dnů předem a je podložena citovanými úseky zákona. |
| 23 | kontrolní | Mám smlouvu jen na 4 měsíce. Jak dlouhou zkušební dobu mi můžou dát? | ano | správně | správně | správně | Asistent správně aplikoval § 35 odst. 3 a uvedl maximální zkušební dobu 2 měsíce, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 24 | kontrolní | Jeden den jsem nepřišel do práce a neomluvil se. Může mi šéf vzít dovolenou? | ano | **chyba** | správně | správně | Asistent správně a věcně shodně se zákonem i zlatou odpovědí uvedl, že zaměstnavatel může krátit dovolenou o neomluveně zameškané hodiny, a opřel se o citovaný § 223 odst. 1. |
| 25 | kontrolní | Kdy mi přijdou peníze za odstupné? | ano | správně | správně | správně | Odpověď věcně odpovídá zlaté odpovědi a opírá se výhradně o dodaný úsek zákona [1]. |
| 26 | kontrolní | Když se se šéfem domluvíme na konci práce, musí to být na papíře? | ano | správně | správně | správně | Odpověď správně uvádí, že dohoda o rozvázání pracovního poměru musí být písemná, a opírá se o citované úseky zákona. |
| 27 | kontrolní | Jsem těhotná. Může mě zaměstnavatel vyhodit ze dne na den? | ano | správně | správně | správně | Asistent správně uvádí, že zaměstnavatel nesmí okamžitě zrušit pracovní poměr s těhotnou zaměstnankyní, a jeho tvrzení jsou podložena dodanými úseky zákona. |
| 28 | kontrolní | Do kdy si musím vybrat letošní dovolenou? | ano | **chyba** | správně | správně | Odpověď vystihuje hlavní pravidlo ze zlaté odpovědi a je plně podložena dodanými úseky zákona. |
| 29 | kontrolní | Kolik je stravenkový paušál na jeden den? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky výši stravenkového paušálu neuvádějí. |
| 30 | kontrolní | Kolik dní placeného volna dostanu na vlastní svatbu? | ano | správně | správně | správně | Odpověď přesně vystihuje 2 dny volna s náhradou mzdy jen za 1 den a je plně podložena úsekem [1]. |
| 31 | nové předpisy | Jak dlouho dostanu podporu v nezaměstnanosti, když mi je 35 let? | ano | správně | správně | správně | Asistent správně uvádí 5 měsíců pro uchazeče do 52 let a odkazuje na příslušné úseky zákona. |
| 32 | nové předpisy | Kolik procent z výplaty dostanu jako podporu v nezaměstnanosti? | ano | správně | správně | správně | Odpověď přesně vystihuje procentní sazby podle věku i strop podpory a všechny údaje jsou podloženy citovanými úseky. |
| 33 | nové předpisy | Kolik si můžu přivydělat, když jsem v evidenci na úřadu práce? | ano | správně | správně | správně | Odpověď správně uvádí limit poloviny minimální mzdy pro pracovní poměr i DPČ a povinnost oznámení úřadu práce, vše podloženo citovaným § 25 odst. 3. |
| 34 | nové předpisy | Jak dlouho musím předtím pracovat, abych měl nárok na podporu v nezaměstnanosti? | ano | správně | správně | správně | Asistent správně uvádí základní podmínku 12 měsíců v posledních 2 letech i zvláštní případ 9 měsíců po vyčerpání podpůrčí doby, vše podloženo citovanými úseky. |
| 35 | nové předpisy | Od kolikátého dne nemoci se platí nemocenská? | ano | správně | správně | správně | Asistent správně uvádí, že nemocenské se platí od 15. kalendářního dne a prvních 14 dnů náleží náhrada mzdy, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 36 | nové předpisy | Jak dlouho trvá otcovská a kolik se na ní dostává? | ano | **chyba** | **chyba** | správně | Opraveno ve v3: výběr přes LLM přidal § 38c, takže odpověď má délku (2 týdny) i výši (70 %). |
| 37 | nové předpisy | Jak dlouho můžu být doma s nemocným dítětem na ošetřovném? | ano | správně | správně | správně | Odpověď správně uvádí 9 dnů, resp. 16 dnů pro osamělého rodiče, a obě tvrzení jsou podložena dodanými úseky. |
| 38 | nové předpisy | Dostanu příplatek za práci v noci? | ano | **chyba** | **chyba** | správně | Opraveno ve v3: rozliší mzdu (nejméně 10 %), plat (20 %) i dohody. AI soudce to označil za chybu, protože zlatá odpověď mluví jen o mzdě. Ruční kontrola: správně. |
| 39 | nové předpisy | Kolik příplatku dostanu za přesčas? | ano | **chyba** | správně | správně | Správně, rozlišil mzdu a plat a na konci se doptal, co uživatel myslel. |
| 40 | nové předpisy | Do kdy mi musí zaměstnavatel vydat pracovní posudek? | ano | správně | **chyba** | **chyba** | Znovu chyba: po přidání pravidla odkazů se podklady trochu změnily a model zase napsal „nesmí vydat dříve“ místo „není povinen vydat dříve“. Pravidlo 8 tedy nefunguje spolehlivě: stejný model na skoro stejném vstupu čte jednou správně, jindy ne. AI soudce chybu přehlédl. |
| 41 | nové předpisy | Jak dlouho dopředu musím požádat o rodičovskou dovolenou? | ano | správně | správně | správně | Asistent správně uvádí lhůtu 30 dnů i výjimku vážných důvodů podle § 196 odst. 2, byť opomíjí požadavek písemnosti. |
| 42 | nové předpisy | Kolik dní volna dostanu, když mi zemře máma? | ano | správně | správně | správně | Asistent správně uvádí 1 den s náhradou mzdy na pohřeb rodiče, další den při obstarávání pohřbu a až 5 dnů bez náhrady mzdy, vše podloženo úsekem [1]. |
| 43 | nové předpisy | Kolik peněz dostanu celkem na rodičovském příspěvku? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky rodičovský příspěvek neupravují, a nic si nevymyslel. |
| 44 | nové předpisy | Kolik zaplatím jako OSVČ měsíčně na sociálním pojištění? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neobsahují úpravu pojistného OSVČ. |
| 45 | nové předpisy | Jak dlouhá je výpovědní doba z nájmu bytu? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neobsahují úpravu nájmu bytu (pouze zákoník práce a služební zákon), a věcně tak odpovídá zlaté odpovědi. |
| 46 | nové předpisy | Kolik je sleva na dani na poplatníka? | – | správně | správně | správně | Asistent odpovídá, že informaci nemá, což odpovídá zlaté odpovědi a dodané úseky se slevou na dani na poplatníka skutečně nesouvisí. |
| 47 | po opravě | Co dostanu, když pracuji ve svátek? | ano | správně | správně | správně | Správně, varianty pro mzdu i plat. |
| 48 | po opravě | Do kdy po narození dítěte musím nastoupit na otcovskou? | ano | správně | správně | správně | Odpověď správně uvádí lhůtu 6 týdnů od narození včetně prodloužení o dny hospitalizace a všechny údaje vycházejí z dodaného § 38a. |
| 49 | po opravě | Kolik peněz dostanu na ošetřovném? | ano | správně | **chyba** | správně | Asistent správně uvádí 60 % denního vyměřovacího základu pro ošetřovné i dlouhodobé ošetřovné, což odpovídá zlaté odpovědi i dodaným úsekům. |
| 50 | po opravě | Dostanu něco navíc za pracovní pohotovost? | ano | správně | správně | správně | Odpověď správně uvádí odměnu nejméně 10 % průměrného výdělku a všechna tvrzení jsou podložena dodanými úseky zákona. |
| 51 | po opravě | Do kdy mi musí zaměstnavatel vyplatit výplatu? | ano | **chyba** | **chyba** | správně | Asistent správně uvádí lhůtu splatnosti mzdy podle § 141 odst. 1 a jeho tvrzení jsou podložena dodanými úseky. |
| 52 | po opravě | Musí mi zaměstnavatel při odchodu dát zápočťák? | ano | **chyba** | správně | správně | Odpověď správně uvádí povinnost vydat potvrzení o zaměstnání při skončení PP, DPČ i DPP za zákonných podmínek a všechny údaje jsou podloženy § 313. |
| 53 | po opravě | Můžu mít vedle práce ještě živnost ve stejném oboru jako můj zaměstnavatel? | ano | správně | správně | správně | Asistent správně uvádí, že je třeba předchozí písemný souhlas zaměstnavatele, což odpovídá § 304 odst. 1 ZP i zlaté odpovědi. |
| 54 | po opravě | Co musí obsahovat pracovní smlouva? | ano | správně | správně | správně | Asistent správně uvedl všechny tři povinné náležitosti dle § 34 odst. 1 ZP a dodatky o písemné formě a vyhotoveních jsou věcně správné a podložené dodanými úseky. |
| 55 | po opravě | Kolik je příspěvek na bydlení? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky příspěvek na bydlení podle zákona o státní sociální podpoře neobsahují. |
| 56 | po opravě | Kolik let musím odpracovat, abych dostal důchod? | – | správně | správně | správně | Asistent správně odmítl odpovědět, protože dodané úseky neupravují podmínky nároku na starobní důchod a zlatá odpověď je NEVÍM. |

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
