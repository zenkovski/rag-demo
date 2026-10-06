# Výsledky měření

Model odpovědí i soudce: `nvidia/nemotron-3-super-120b-a12b:free`. Embeddingy: `intfloat/multilingual-e5-base`. Do odpovědi jde top 5 úseků.

| Měřítko | Výsledek |
|---|---|
| Vyhledávání: správný úsek mezi top 3 (hit@3) | **13 z 16** (jen otázky, které odpověď mají) |
| Odpověď správně – po ruční kontrole | **18 z 20** |
| Odpověď správně – podle LLM soudce | 19 z 20 |
| Odpověď se opírá o zdroj (soudce) | 20 z 20 |
| Řekl „nevím“, když zdroj odpověď nemá | 4 z 4 |
| Řekl „nevím“, i když odpověď ve zdroji byla | 0 z 16 |
| Shoda LLM soudce s ruční kontrolou | 19 z 20 |

Spotřeba API při měření: 41288 vstupních a 17870 výstupních tokenů.

## Otázka po otázce

| # | Typ | Otázka | hit@3 | Výsledek | Poznámka |
|---|---|---|---|---|---|
| 1 | snadná | Kolik týdnů dovolené mám minimálně za rok? | ano | správně | Odpověď asistenta přesně uvádí minimální výměru dovolené 4 týdny v kalendářním roce, což odpovídá zlaté odpovědi a je podloženo citovaným § 212 odst. 1. |
| 2 | snadná | Jak dlouhá může být zkušební doba u běžného zaměstnance? | ano | správně | Správně (4 měsíce). Drobnost: u věty o prodloužení cituje [4] (§ 35 odst. 3) místo [3] (§ 35 odst. 4). |
| 3 | střední | Může mě šéf vyhodit ve zkušební době bez udání důvodu? | ano | správně | Správně. Vynechal ale výjimku: zaměstnavatel nesmí zrušit poměr v prvních 14 dnech pracovní neschopnosti. |
| 4 | snadná | Jak dlouhá je výpovědní doba? | ano | správně | Odpověď přesně uvádí minimální výpovědní dobu a výjimku podle § 51 odst. 2 a doplňuje informaci o možnosti prodloužení podle § 51 odst. 3, což je v souladu s předloženými úseky. |
| 5 | střední | Od kdy začíná běžet výpovědní doba? | ano | správně | Asistent správně uvádí, že výpovědní doba začíná dnem doručení výpovědi druhé straně, což je v souladu s § 51 odst. 1 (úsek [2]). |
| 6 | snadná | Kolik hodin ročně můžu odpracovat na dohodu o provedení práce (DPP)? | ano | správně | Asistent správně uvádí limit 300 hodin ročně a opírá ho o § 75 odst. 1, který tuto hranici stanoví. |
| 7 | střední | Kolik hodin týdně můžu pracovat na dohodu o pracovní činnosti? | **ne** | **chyba** | Hlavní číslo (20 hodin týdně) správně, ale přidal nepravdu: „za rok nesmíte překročit 300 hodin“. Limit 300 h platí pro DPP; § 76 odst. 1 říká opak. AI soudce chybu nepoznal. |
| 8 | snadná | Po kolika hodinách práce mám nárok na pauzu na jídlo? | ano | správně | Odpověď asistenta přesně odpovídá citovanému ustanovení § 88 odst. 1 a obsahuje všechny podstatné informace ze zlaté odpovědi. |
| 9 | střední | Kolik přesčasů mi může zaměstnavatel nařídit? | ano | správně | Odpověď správně uvádí, že nařízený přesčas může činit nejvýše 8 hodin týdně a 150 hodin za rok (§93 odst. 2) a doplňuje informaci o průměrném týdenním limitu v období až 26 týdnů (§93 odst. 4), což odpovídá zlaté odpovědi a je podloženo uvedenými úseky. |
| 10 | střední | Kolik hodin odpočinku musím mít mezi dvěma směnami? | ano | správně | Správně (11 hodin, mladiství 12). Citaci napsal jako 【3】, web ji převádí na [3]. |
| 11 | těžká | Ve firmě jsem rok a půl a propouštějí mě, protože jsem nadbytečný. Kolik dostanu odstupné? | ano | správně | Správně (nejméně dvojnásobek průměrného výdělku). Drobnost: § 67 odst. 4 cituje jako [4] místo [5]. |
| 12 | těžká | Může mi zaměstnavatel dát výpověď z jakéhokoli důvodu, třeba že se mu nelíbím? | ano | správně | Odpověď správně uvádí, že výpověď zaměstnavatele je omezena na důvody § 52 a osobní nelibost mezi nimi není, což odpovídá zlaté odpovědi a je podloženo uvedenými paragrafy. |
| 13 | střední | Jak dlouho mám čas napadnout neplatnou výpověď u soudu? | ano | správně | Asistent správně uvádí lhůtu dvou měsíců ode dne, kdy měl pracovní poměr skončit, což přesně odpovídá zlaté odpovědi a je podloženo úsekem [1] (§ 72). |
| 14 | střední | Proplatí mi zaměstnavatel nevyčerpanou dovolenou? | **ne** | správně | Odpověď asistenta přesně odpovídá zlaté odpovědi a je podpořena citovaným úsekem [5], který uvádí, že náhrada za nevyčerpanou dovolenou přísluší pouze při skončení pracovního poměru. |
| 15 | těžká | Firma mi už měsíc nezaplatila výplatu. Můžu hned odejít? | **ne** | **chyba** | Chyba vyhledávání: správný § 56 odst. 1 nebyl mezi nalezenými úseky (otázka mluví o „výplatě“ a „odejít“, zákon o „mzdě“ a „okamžitém zrušení“). Model pak odpověděl jen lhůtami z § 59 a podmínku 15 dnů po splatnosti vynechal. |
| 16 | těžká | Kolikrát mi můžou prodloužit smlouvu na dobu určitou? | ano | správně | Asistent správně uvádí, že mezi týmiž stranami lze pracovní poměr na dobu určitou opakovat (tj. prodloužit) nejvýše dvakrát, což odpovídá zlaté odpovědi, a své tvrzení opírá o citaci § 39 odst. 2 z poskytnutých úseků. |
| 17 | bez odpovědi | Jaká je minimální mzda v roce 2026? | – | správně | Asistent správně uvádí, že výše minimální mzdy pro rok 2026 není obsažena v předložených úsecích zákona, což odpovídá zlaté odpovědi. |
| 18 | bez odpovědi | Jak dlouho trvá mateřská dovolená? | – | správně | Asistent správně uvedl, že v poskytnutých úsecích není informace o délce mateřské dovolené, což odpovídá zlaté odpovědi. |
| 19 | bez odpovědi | Za jakých podmínek můžu pracovat z domova na home office? | – | správně | Asistent správně uvádí, že v poskytnutých úsecích zákona není informace o home office, což odpovídá zlaté odpovědi 'NEVÍM'. |
| 20 | bez odpovědi | Kolik peněz dostanu, když budu na nemocenské? | – | správně | Asistent správně uvedl, že informace o výši nemocenské není v poskytnutých úsecích zákona, což odpovídá zlaté odpovědi 'NEVÍM'. |
