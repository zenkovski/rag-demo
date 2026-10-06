# Výsledky měření

20 testovacích otázek: 16 má odpověď v zákoně, 4 záměrně ne (tam je správně „nevím“).
Verdikt „správně“ je po ruční kontrole všech 20 odpovědí proti textu zákona.

## v1 → v2

| Měřítko | v1 | v2 |
|---|---|---|
| Model | `nvidia/nemotron-3-super-120b-a12b:free` | `deepseek/deepseek-v4.1-flash` |
| Vyhledávání | embeddingy | embeddingy + BM25 + přepis otázky (RRF) |
| **Odpověď správně (celkem)** | **18 z 20** | **20 z 20** |
| z toho otázky s odpovědí | 14 z 16 | 16 z 16 |
| z toho „nevím“, když zdroj mlčí | 4 z 4 | 4 z 4 |
| Správný paragraf v top 3 (hit@3) | 13 z 16 | 13 z 16 |
| „Nevím“, i když odpověď ve zdroji byla | 0 z 16 | 0 z 16 |
| Opírá se o zdroj (podle AI soudce) | 20 z 20 | 20 z 20 |
| AI soudce se shodl s ruční kontrolou | 19 z 20 | 20 z 20 |

## Co pomohlo ve vyhledávání

Stejných 16 otázek, mění se jen způsob hledání. hit@5 = správný paragraf je mezi 5 úseky, které dostane model.

| Režim | hit@3 | hit@5 |
|---|---|---|
| jen embeddingy (v1) | 13 z 16 | 15 z 16 |
| + BM25 (hledání podle slov) | 13 z 16 | 14 z 16 |
| + přepis otázky do jazyka zákona (v2) | 13 z 16 | 16 z 16 |

## Kontrola přeučení: 10 nových otázek

Úpravy v2 jsem navrhl podle chyb na 20 testovacích otázkách, takže tam může být výsledek přikrášlený.
Proto jsem až potom napsal 10 nových otázek (`data/testset_holdout.json`) a změřil na nich v1 i v2 beze změn.

| Měřítko | v1 | v2 |
|---|---|---|
| Odpověď správně (ruční kontrola) | 8 z 10 | 9 z 10 |
| Správný paragraf mezi 5 nalezenými | 6 z 8 | 7 z 8 |

- **v1 #24:** Vyhledávání nenašlo § 223 odst. 1 (krácení dovolené), model proto řekl „nevím“.
- **v1 #28:** § 218 odst. 1 se nenašel. Model napsal „do 31. 12. následujícího roku“, to ve zdroji není.
- **v2 #28:** § 218 odst. 1 se nenašel ani po přepisu otázky. Odpověď cituje jen pravidlo o 30. červnu a hlavní zásadu (vyčerpat v daném roce) vynechává.

Cena nových volání API při měření v2: 0.01528 $.

## v2 otázka po otázce

| # | Typ | Otázka | hit@3 | v1 | v2 | Poznámka k v2 |
|---|---|---|---|---|---|---|
| 1 | snadná | Kolik týdnů dovolené mám minimálně za rok? | ano | správně | správně | Asistent správně uvádí obecné minimum 4 týdny a doplňující zákonné výjimky, které jsou podloženy citovanými úseky. |
| 2 | snadná | Jak dlouhá může být zkušební doba u běžného zaměstnance? | ano | správně | správně | Asistent správně uvádí maximální délku 4 měsíce pro běžného zaměstnance a jeho doplňující tvrzení jsou podložena dodanými úseky zákona. |
| 3 | střední | Může mě šéf vyhodit ve zkušební době bez udání důvodu? | ano | správně | správně | Odpověď správně uvádí, že zaměstnavatel může ve zkušební době zrušit pracovní poměr bez důvodu, s výjimkou prvních 14 dnů pracovní neschopnosti, a opírá se o dodaný § 66. |
| 4 | snadná | Jak dlouhá je výpovědní doba? | **ne** | správně | správně | Správně (nejméně 2 měsíce, výjimka 1 měsíc). Správný § 51 odst. 2 byl až 4. nalezený, model ho přesto použil. |
| 5 | střední | Od kdy začíná běžet výpovědní doba? | ano | správně | správně | Odpověď přesně vystihuje začátek i konec výpovědní doby podle § 51 odst. 1 a opírá se o dodaný úsek. |
| 6 | snadná | Kolik hodin ročně můžu odpracovat na dohodu o provedení práce (DPP)? | ano | správně | správně | Asistent správně uvádí limit 300 hodin ročně na DPP a doplňuje započítání dalších DPP u téhož zaměstnavatele podle dodaných úseků. |
| 7 | střední | Kolik hodin týdně můžu pracovat na dohodu o pracovní činnosti? | ano | **chyba** | správně | Správně: v průměru nejvýše polovina stanovené týdenní pracovní doby. Chyba z v1 (300 hodin) zmizela; konkrétní číslo 20 hodin ale nenapsal. |
| 8 | snadná | Po kolika hodinách práce mám nárok na pauzu na jídlo? | ano | správně | správně | Odpověď přesně vystihuje pravidlo ze zákona včetně výjimky pro mladistvé a opírá se o dodaný úsek [1]. |
| 9 | střední | Kolik přesčasů mi může zaměstnavatel nařídit? | ano | správně | správně | Asistent správně uvádí limit nařízené přesčasové práce i možnost dalšího přesčasu jen po dohodě a doplňující údaj o průměrném rozsahu je podložený dodanými úseky. |
| 10 | střední | Kolik hodin odpočinku musím mít mezi dvěma směnami? | **ne** | správně | správně | Správně (11 hodin, mladiství 12). Správný § 90 odst. 1 byl až 4. nalezený. |
| 11 | těžká | Ve firmě jsem rok a půl a propouštějí mě, protože jsem nadbytečný. Kolik dostanu odstupné? | ano | správně | správně | Asistent správně určil dvojnásobek průměrného výdělku pro pracovní poměr 1 až 2 roky při výpovědi podle § 52 písm. a) až c), což odpovídá zlaté odpovědi i dodanému § 67 odst. 1. |
| 12 | těžká | Může mi zaměstnavatel dát výpověď z jakéhokoli důvodu, třeba že se mu nelíbím? | ano | správně | správně | Asistent správně uvádí, že zaměstnavatel může dát výpověď jen z důvodů výslovně stanovených v § 52, a jeho tvrzení jsou podložena dodanými úseky. |
| 13 | střední | Jak dlouho mám čas napadnout neplatnou výpověď u soudu? | ano | správně | správně | Asistent správně uvádí dvouměsíční lhůtu od dne, kdy měl pracovní poměr výpovědí skončit, což odpovídá zlaté odpovědi i citovanému § 72. |
| 14 | střední | Proplatí mi zaměstnavatel nevyčerpanou dovolenou? | ano | správně | správně | Odpověď správně uvádí, že náhrada za nevyčerpanou dovolenou přísluší pouze při skončení pracovního poměru, a její doplňující tvrzení odpovídají dodaným úsekům. |
| 15 | těžká | Firma mi už měsíc nezaplatila výplatu. Můžu hned odejít? | **ne** | **chyba** | správně | V1 chyba, teď správně: přepis otázky do jazyka zákona („okamžitě zrušit“, „nevyplatil mzdu“) dostal § 56 odst. 1 mezi nalezené úseky (5. místo). |
| 16 | těžká | Kolikrát mi můžou prodloužit smlouvu na dobu určitou? | ano | správně | správně | Správně (nejvýše dvakrát, prodloužení se počítá). Vynechal, že jeden poměr smí trvat nejdéle 3 roky. |
| 17 | bez odpovědi | Jaká je minimální mzda v roce 2026? | – | správně | správně | Asistent správně odmítl odpovědět, protože minimální mzda není v dodaných úsecích zákona upravena. |
| 18 | bez odpovědi | Jak dlouho trvá mateřská dovolená? | – | správně | správně | Asistent správně odmítl odpovědět, protože délka mateřské dovolené není v dodaných úsecích zákona. |
| 19 | bez odpovědi | Za jakých podmínek můžu pracovat z domova na home office? | – | správně | správně | Asistent správně odmítl odpovědět, protože home office ani § 317 není v dodaných úsecích zákona. |
| 20 | bez odpovědi | Kolik peněz dostanu, když budu na nemocenské? | – | správně | správně | Asistent správně odmítl odpovědět, protože v dodaných úsecích zákona není úprava nemocenské ani náhrady mzdy při nemoci. |

## Poznámky k v1 (chyby)

- **7:** Hlavní číslo (20 hodin týdně) správně, ale přidal nepravdu: „za rok nesmíte překročit 300 hodin“. Limit 300 h platí pro DPP; § 76 odst. 1 říká opak. AI soudce chybu nepoznal.
- **15:** Chyba vyhledávání: správný § 56 odst. 1 nebyl mezi nalezenými úseky (otázka mluví o „výplatě“ a „odejít“, zákon o „mzdě“ a „okamžitém zrušení“). Model pak odpověděl jen lhůtami z § 59 a podmínku 15 dnů po splatnosti vynechal.
