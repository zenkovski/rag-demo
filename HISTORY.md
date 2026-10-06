# Vývoj verzí

Co se v každé verzi změnilo, proč a jestli to pomohlo. Čísla otázku po otázce: [RESULTS.md](RESULTS.md).

| Verze | Hlavní změna | Správně (66 otázek) | Správný § mezi 5 úseky (56) |
|---|---|---|---|
| v1 | e5-base lokálně, free model `nemotron-3-super` | 54 | 47 |
| v2 | přepis otázky, BM25 + RRF, e5-large přes API, `deepseek-v4.1-flash` | 60 | 53 |
| v3 | LLM vybere 5 z 20 kandidátů, poznámka mzda × plat, doptání | 65 | 56 |
| v3.1 | odpověď píše `deepseek-v4-pro`, užitečné „nevím“ | 66 | 56 |

## v1 → v2: hledání

| Problém ve v1 | Úprava ve v2 |
|---|---|
| Lidé píšou „výplata“ a „odejít“, zákon „mzda“ a „okamžitě zrušit“. | **Přepis otázky** do jazyka zákona (LLM). |
| Hledání podle významu občas mine přesné slovo. | **BM25** (hledání podle slov) nad přepsanou otázkou, spojené metodou **RRF**. |
| Model si u DPČ přidal „300 hodin ročně“ (platí jen pro DPP). | **Přísnější pravidla** v promptu. |
| e5-base běží jen lokálně (1 GB), na webu ne. | **e5-large přes API**, stejný model při měření i na webu. |

Hledání po krocích (správný § mezi 5 úseky, 56 otázek):

| Krok | hit@5 |
|---|---|
| e5-base | 47 |
| e5-large | 50 |
| + BM25 nad laickou otázkou | **44** (zhoršení: slovo „výplata“ v zákoně není) |
| + přepis otázky, BM25 nad přepisem | 53 |
| + výběr přes LLM, odstavec 1 a odkazy | 56 |

## v2 → v3: chyby podle kroku

Každá chyba vznikne buď v **hledání** (model nedostal správný odstavec), nebo ve **čtení** (dostal ho, ale špatně použil).

| Chyba ve v2 | Krok | Oprava |
|---|---|---|
| Nemocenská: kolik peněz | hledání (§ 29 ZNP až 11.) | LLM vybere 5 z 20 + dohledání „podle odstavce 2“ |
| Otcovská: délka i výše | hledání (§ 38c až 10.) | LLM vybere 5 z 20 |
| Noční práce 20 % místo 10 % | čtení (mzda × plat) | úsek nese poznámku „platí pro mzdu / plat“ |
| Posudek „nesmí“ místo „nemusí“ | čtení | pravidlo „není povinen“ = nemusí; stabilně až s modelem Pro (v3.1) |

Dvě pevná pravidla bez AI:
- K vybranému odstavci 2, 3… se přidá odstavec 1 téhož §. Opravilo regresi u odpočinku mezi směnami.
- Dohledají se odstavce, na které úsek odkazuje („ve výši podle odstavce 2“).

## v3 → v3.1: nestabilní čtení a zbytečné „nevím“

- Levný model četl stejný odstavec jednou správně, jindy špatně. Stačila změna pátého úseku v podkladech.
- Často říkal „nevím“, i když odpověď měl před sebou („Mám nárok na lékaře?“).
- Pokus na 5 problémových otázkách: nové zadání samo spravilo 3, silnější model sám 3, oba dohromady 5.
- Proto odpověď píše `deepseek-v4-pro`. Přepis a výběr dál dělá levný Flash.
- Nevýhoda: Pro cituje méně často, ne za každou větu.

## Skryté přemýšlení modelu

DeepSeek Flash před odpovědí tiše „přemýšlel“, u výběru úseků až 4 800 tokenů. Krok trval 30 s a stál 10× víc. Od v3 je vypnuté (`reasoning: {enabled: false}`): krok trvá 1,5 s a kvalita se nezhoršila. Většina z celkových 0,66 $ padla na tohle, než jsem to našel.

## Větší zdroj

První verze měla 5 témat zákoníku práce (260 odstavců). Teď 4 předpisy (2 475 odstavců). Na stejných 24 otázkách hledání nezhoršilo (24 z 24). Měření první verze: `data/archive_5temat/`.
