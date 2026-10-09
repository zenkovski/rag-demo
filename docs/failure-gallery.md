# Galerie chyb

Skutečná selhání z měření: vstup, očekávané a skutečné chování, kde v řetězci vznikla, příčina, oprava a důkaz, že oprava pomohla. Kategorie říkají, KDE se řetěz přerušil, ať je jasné, co opravovat:

- **A** – relevantní úsek nebyl nalezen (hledání)
- **B** – úsek byl nalezen, ale vyřazen před odpovědí (výběr)
- **C** – správný kontext dodán, model ho špatně použil (čtení)
- **D** – tvrzení bez dostatečné opory v úsecích
- **E** – měl odmítnout odpovědět a neodmítl
- **F** – odmítl, i když odpověď v zákoně byla

## Kolik selhání v které kategorii

| Verze | Odpovědí špatně | A nenalezeno | B vyřazeno | C špatně přečteno | E měl odmítnout | F zbytečné „nevím“ |
|---|---|---|---|---|---|---|
| v1 | 12 z 66 | 6 | 3 | 3 | 0 | 0 |
| v2 | 6 z 66 | 1 | 3 | 2 | 0 | 0 |
| v3 | 0 z 66 | 0 | 0 | 0 | 0 | 0 |

Kategorie D (tvrzení bez opory) se počítá zvlášť, protože se může přidat i ke správné odpovědi: viz sekci o kontrole čísel v [benchmark-results.md](benchmark-results.md). Hlavní příčina je tu jedna na odpověď (A před B před C před E a F). „Nalezeno“ znamená všechny správné úseky. Pro v1 a v2 (nemají výběr z 20) znamená B „byl mezi 20 nejlepšími, ale ořez na 5 ho vyřadil“. Kandidáti v1 a v2 jsou z přehrání (v2 původně používalo přepis se skrytým přemýšlením, proto se mohou o kousek lišit od dobového měření).

## Opravené chyby (v2 → v3)

### Otázka 20: Kolik peněz dostanu, když budu na nemocenské?

- **Vstup:** Kolik peněz dostanu, když budu na nemocenské?
- **Očekávané chování:** Prvních 14 kalendářních dnů platí zaměstnavatel náhradu mzdy 60 % průměrného výdělku. Od 15. dne je nemocenské: 60 % denního vyměřovacího základu do 30. dne, 66 % od 31. do 60. dne a 72 % od 61. dne.
- **Skutečné chování:** Nevím, v dostupných úsecích zákona to není.
- **Kategorie:** F (odmítl, i když odpověď v zákoně byla), A (relevantní úsek nebyl nalezen (hledání))
- **Příčina:** Hledání: zákon o nemocenském pojištění má stovky podobných odstavců, správné dva (§ 192 ZP, § 29 ZNP) se nedostaly mezi 5. Ruční poznámka: Hledání nenašlo § 192 ZP ani § 29 ZNP: zákon o nemocenském pojištění má stovky podobných odstavců. Model proto řekl „nevím“. Bezpečné, ale neužitečné. Ve verzi s 5 tématy to byl test „nevím“.
- **Oprava:** v3: LLM vybere 5 z 20 kandidátů a pevné pravidlo dohledá odstavec, na který úsek odkazuje („ve výši podle odstavce 2“).
- **Důkaz:** ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z 66.

### Otázka 36: Jak dlouho trvá otcovská a kolik se na ní dostává?

- **Vstup:** Jak dlouho trvá otcovská a kolik se na ní dostává?
- **Očekávané chování:** 2 týdny, 70 % denního vyměřovacího základu.
- **Skutečné chování:** Otcovská se poskytuje po podpůrčí dobu 2 týdny [5]. Kolik se na ní dostává, v dostupných úsecích zákona uvedeno není.
- **Kategorie:** B (úsek byl nalezen, ale vyřazen před odpovědí (výběr))
- **Příčina:** Hledání: § 38c ZNP (výše otcovské) nebyl mezi 5 úseky, model napsal půl odpovědi. Ruční poznámka: Půl odpovědi: délku 2 týdny našel, výši 70 % ne (§ 38c ZNP nebyl mezi 5 úseky). Poctivě napsal, že výše v úsecích není.
- **Oprava:** v3: LLM vybere 5 z 20 a přidá § 38c.
- **Důkaz:** ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z 66.

### Otázka 38: Dostanu příplatek za práci v noci?

- **Vstup:** Dostanu příplatek za práci v noci?
- **Očekávané chování:** Ano, nejméně 10 % průměrného výdělku, pokud se nesjedná jiná výše.
- **Skutečné chování:** Ano, za noční práci vám náleží příplatek. Podle [1] jde o 20 % průměrného hodinového výdělku za hodinu noční práce. Podle [3] za dobu noční práce náleží dosažená mzda a příplatek nejméně 10 % průměrného výdělku, přičemž je možné sjednat jinou minimální výši a způsob určení.
- **Kategorie:** C (správný kontext dodán, model ho špatně použil (čtení))
- **Příčina:** Čtení: model smíchal mzdu (soukromý zaměstnavatel, § 116: nejméně 10 %) a plat (stát, § 125: 20 %). Ruční poznámka: Smíchal mzdu a plat: 20 % podle § 125 platí jen pro plat ve veřejné sféře. Pro běžnou mzdu je to nejméně 10 % (§ 116), to uvedl až jako druhé.
- **Oprava:** v3: každý úsek v podkladech nese poznámku „platí pro mzdu / plat“ a prompt říká, aby uvedl obě varianty, když to otázka nerozlišuje.
- **Důkaz:** ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z 66.

### Otázka 40: Do kdy mi musí zaměstnavatel vydat pracovní posudek?

- **Vstup:** Do kdy mi musí zaměstnavatel vydat pracovní posudek?
- **Očekávané chování:** Do 15 dnů od žádosti; dříve než 2 měsíce před skončením zaměstnání ho vydat nemusí.
- **Skutečné chování:** Požádáte-li zaměstnavatele o pracovní posudek, je povinen vám ho vydat do 15 dnů [1]. Nesmí vám ho však vydat dříve než v době 2 měsíců před skončením vašeho zaměstnání [1].
- **Kategorie:** C (správný kontext dodán, model ho špatně použil (čtení)), D (tvrzení bez dostatečné opory v úsecích)
- **Příčina:** Čtení: zákon říká, že zaměstnavatel nemusí vydat posudek dřív než 2 měsíce před koncem. Levný model napsal „nesmí“ a výsledek se mezi běhy měnil. Ruční poznámka: Obrátil význam: zákon říká, že zaměstnavatel posudek nemusí vydat dřív než 2 měsíce před koncem zaměstnání. Model napsal, že nesmí.
- **Oprava:** v3: pravidlo „není povinen = nemusí“ v promptu, od v3.1 odpověď píše silnější model.
- **Důkaz:** ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z 66.

### Otázka 49: Kolik peněz dostanu na ošetřovném?

- **Vstup:** Kolik peněz dostanu na ošetřovném?
- **Očekávané chování:** 60 % denního vyměřovacího základu za kalendářní den.
- **Skutečné chování:** Nevím, v dostupných úsecích zákona to není.
- **Kategorie:** F (odmítl, i když odpověď v zákoně byla), B (úsek byl nalezen, ale vyřazen před odpovědí (výběr))
- **Příčina:** Hledání: § 41 ZNP (60 %) se nenašel, model správně řekl „nevím“. AI soudce to bez přemýšlení označil za správně. Ruční poznámka: § 41 ZNP (60 %) se nenašel, model řekl „nevím“. AI soudce to bez přemýšlení přehlédl a dal „správně“.
- **Oprava:** v3: výběr přes LLM. Soudce se opravuje ruční kontrolou, proto je v měření druhý verdikt.
- **Důkaz:** ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z 66.

### Otázka 51: Do kdy mi musí zaměstnavatel vyplatit výplatu?

- **Vstup:** Do kdy mi musí zaměstnavatel vyplatit výplatu?
- **Očekávané chování:** Nejpozději v kalendářním měsíci následujícím po měsíci, ve kterém vzniklo právo na mzdu.
- **Skutečné chování:** Nevím, v dostupných úsecích zákona to není.
- **Kategorie:** F (odmítl, i když odpověď v zákoně byla), B (úsek byl nalezen, ale vyřazen před odpovědí (výběr))
- **Příčina:** Hledání: § 141 odst. 1 se nenašel, model řekl „nevím“. AI soudce to přehlédl. Ruční poznámka: § 141 odst. 1 se nenašel, model řekl „nevím“. AI soudce to přehlédl.
- **Oprava:** v3: výběr přes LLM, ruční kontrola.
- **Důkaz:** ve v3 správně (ruční kontrola), v2 → v3 zhoršeno 0 otázek z 66.

## Zhoršení: v1 → v2

Oprava jedné věci rozbila jinou. Dvě otázky, které v1 měla správně, ve v2 selhaly. Proto se po každé změně měří znovu všechno, ne jen opravená otázka.

### Otázka 40: Do kdy mi musí zaměstnavatel vydat pracovní posudek?

- **Vstup:** Do kdy mi musí zaměstnavatel vydat pracovní posudek?
- **Očekávané chování:** Do 15 dnů od žádosti; dříve než 2 měsíce před skončením zaměstnání ho vydat nemusí.
- **Skutečné chování:** Požádáte-li zaměstnavatele o pracovní posudek, je povinen vám ho vydat do 15 dnů [1]. Nesmí vám ho však vydat dříve než v době 2 měsíců před skončením vašeho zaměstnání [1].
- **Kategorie:** C (správný kontext dodán, model ho špatně použil (čtení)), D (tvrzení bez dostatečné opory v úsecích)
- **Příčina:** Obrátil význam: zákon říká, že zaměstnavatel posudek nemusí vydat dřív než 2 měsíce před koncem zaměstnání. Model napsal, že nesmí.
- **Oprava:** opraveno ve v3 (stejná otázka je ve v3 správně)
- **Důkaz:** v3: správně.

### Otázka 49: Kolik peněz dostanu na ošetřovném?

- **Vstup:** Kolik peněz dostanu na ošetřovném?
- **Očekávané chování:** 60 % denního vyměřovacího základu za kalendářní den.
- **Skutečné chování:** Nevím, v dostupných úsecích zákona to není.
- **Kategorie:** F (odmítl, i když odpověď v zákoně byla), B (úsek byl nalezen, ale vyřazen před odpovědí (výběr))
- **Příčina:** § 41 ZNP (60 %) se nenašel, model řekl „nevím“. AI soudce to bez přemýšlení přehlédl a dal „správně“.
- **Oprava:** opraveno ve v3 (stejná otázka je ve v3 správně)
- **Důkaz:** v3: správně.

## Regrese uvnitř vývoje v3 (v3.0 → oprava)

Detailní rozbor je jako incident: [2026-10-06 regrese u odpočinku mezi směnami](incidents/2026-10-06-regrese-odpocinek.md).

## Otevřené chyby (zatím neopravené)

Z 16 ukázkových otázek na webu jsou dvě špatně. Nechávám je vidět i na webu. Žádná z nich není v testovacích sadách, takže je nikdo neladil.

### Web: Kolik hodin týdně je normální pracovní doba?

- **Vstup:** Kolik hodin týdně je normální pracovní doba?
- **Očekávané chování:** 40 hodin týdně; u mladistvého mladšího 15 let nebo toho, kdo NEukončil povinnou školní docházku, nejvýše 35 hodin (§ 79a odst. 1 ZP).
- **Skutečné chování:** Normální (stanovená) týdenní pracovní doba činí 40 hodin týdně [1]. Pro některé skupiny zaměstnanců je kratší: u mladistvých do 15 let nebo po ukončení povinné školní docházky nesmí překročit 35 hodin týdně [3], u ostatních mladistvých 40 hodin týdně [2]. Dále činí 37,5 hodiny týdně pro zaměstnance v podzemí při těžbě nebo ve vícesměnném či nepřetržitém režimu a 38,75 hodiny týdně pro dvousměnný režim [4].
- **Kategorie:** C (správný kontext dodán, model ho špatně použil (čtení))
- **Příčina:** Hlavní číslo správně (40 hodin), ale u mladistvých převrátil podmínku: § 79a odst. 1 platí pro ty, kdo povinnou školní docházku NEukončili, model napsal „po ukončení“. Kde se to pokazilo: čtení.
- **Oprava:** Zatím bez opravy. Návrh: pravidlo v promptu pro podmínky „před / po ukončení“ a test na víc otázek s převrácenou podmínkou; ověřit na nové sadě.
- **Důkaz:** není (oprava se zatím neprovedla; nepíšu, že je opraveno).

### Web: Může mi zaměstnavatel dát výpověď, když jsem nemocný?

- **Vstup:** Může mi zaměstnavatel dát výpověď, když jsem nemocný?
- **Očekávané chování:** Ne, v době dočasné pracovní neschopnosti (ochranná doba) se výpověď zakazuje (§ 53 odst. 1 písm. a) ZP); zákaz se nevztahuje na výjimky v § 54 (např. výpověď pro organizační změny).
- **Skutečné chování:** Pokud jste nemocný, zaměstnavatel vám může dát výpověď, ale jen z některých důvodů. Výpověď z důvodu porušení povinností (např. neuspokojivé pracovní výsledky) je možná pouze do 3 měsíců ode dne, kdy se o důvodu dověděl [4]. Výpověď musí předem projednat s odborovou organizací, pokud u něj působí [3]. Samotná nemoc jako důvod výpovědi v dostupných úsecích uvedena není.
- **Kategorie:** A (relevantní úsek nebyl nalezen (hledání))
- **Příčina:** Pořád chyba: § 53 odst. 1 (zákaz výpovědi v době pracovní neschopnosti) se nedostal ani mezi 20 kandidátů. Odpověď proto zavádějícím způsobem tvrdí, že výpověď v nemoci dát lze. Kde se to pokazilo: hledání.
- **Oprava:** Příčina je změřená, oprava zatím není nasazená: viz [ADR-004](decisions/ADR-004-rewrite-a-bm25.md). Přepis otázky odvedl hledání jinam (správný odstavec je podle významu původní otázky na 12. místě, podle přepsané na 219., v BM25 přepisu na 106.). Návrh opravy se musí vyzkoušet na nové sadě, ne na této otázce.
- **Důkaz:** není (oprava se zatím neprovedla; nepíšu, že je opraveno).

