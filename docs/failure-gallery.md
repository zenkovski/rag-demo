[Česky](cs/failure-gallery.md)

# Failure gallery

Abbreviations: ZP = Labour Code, ZZ = Employment Act, ZNP = Sickness Insurance Act, NV 590 = Government Decree 590/2006. Questions, answers and manual review notes quoted below are in Czech, as in the data files.

Real failures from the measurements: input, expected and actual behaviour, where in the chain it arose, the cause, the fix and proof that the fix helped. The categories say WHERE the chain broke, so it is clear what to fix:

- **A** – relevant chunk not found (retrieval)
- **B** – chunk found but dropped before answering (selection)
- **C** – correct context supplied, model used it wrongly (reading)
- **D** – claim without sufficient support in the chunks
- **E** – should have refused to answer and did not
- **F** – refused although the answer was in the law

## How many failures in which category

| Version | Wrong answers | A not found | B dropped | C misread | E should have refused | F needless "I don't know" |
|---|---|---|---|---|---|---|
| v1 | 12 of 66 | 6 | 3 | 3 | 0 | 0 |
| v2 | 6 of 66 | 1 | 3 | 2 | 0 | 0 |
| v3 | 0 of 66 | 0 | 0 | 0 | 0 | 0 |

Category D (claim without support) is counted separately, because it can be added even to a correct answer: see the number-check section in [benchmark-results.md](benchmark-results.md). There is one primary cause per answer here (A before B before C before E and F). "Found" means all correct chunks. For v1 and v2 (which have no selection from 20), B means "it was among the top 20, but the cut to 5 dropped it". The v1 and v2 candidates come from a replay (v2 originally used a rewrite with hidden reasoning, so they may differ slightly from the measurement at the time).

## Fixed failures (v2 → v3)

### Question 20: Kolik peněz dostanu, když budu na nemocenské?

- **Input:** Kolik peněz dostanu, když budu na nemocenské?
- **Expected behaviour:** Prvních 14 kalendářních dnů platí zaměstnavatel náhradu mzdy 60 % průměrného výdělku. Od 15. dne je nemocenské: 60 % denního vyměřovacího základu do 30. dne, 66 % od 31. do 60. dne a 72 % od 61. dne.
- **Actual behaviour:** Nevím, v dostupných úsecích zákona to není.
- **Category:** F (refused although the answer was in the law), A (relevant chunk not found (retrieval))
- **Cause:** Retrieval: the Sickness Insurance Act has hundreds of similar paragraphs; the two correct ones (§ 192 ZP, § 29 ZNP) did not make it into the 5. Manual note: Hledání nenašlo § 192 ZP ani § 29 ZNP: zákon o nemocenském pojištění má stovky podobných odstavců. Model proto řekl „nevím“. Bezpečné, ale neužitečné. Ve verzi s 5 tématy to byl test „nevím“.
- **Fix:** v3: the LLM picks 5 of 20 candidates and a fixed rule looks up the paragraph a chunk refers to ("in the amount according to paragraph 2").
- **Proof:** correct in v3 (manual review), v2 → v3 regressed 0 questions out of 66.

### Question 36: Jak dlouho trvá otcovská a kolik se na ní dostává?

- **Input:** Jak dlouho trvá otcovská a kolik se na ní dostává?
- **Expected behaviour:** 2 týdny, 70 % denního vyměřovacího základu.
- **Actual behaviour:** Otcovská se poskytuje po podpůrčí dobu 2 týdny [5]. Kolik se na ní dostává, v dostupných úsecích zákona uvedeno není.
- **Category:** B (chunk found but dropped before answering (selection))
- **Cause:** Retrieval: § 38c ZNP (amount of paternity benefit) was not among the 5 chunks, the model wrote half an answer. Manual note: Půl odpovědi: délku 2 týdny našel, výši 70 % ne (§ 38c ZNP nebyl mezi 5 úseky). Poctivě napsal, že výše v úsecích není.
- **Fix:** v3: the LLM picks 5 of 20 and adds § 38c.
- **Proof:** correct in v3 (manual review), v2 → v3 regressed 0 questions out of 66.

### Question 38: Dostanu příplatek za práci v noci?

- **Input:** Dostanu příplatek za práci v noci?
- **Expected behaviour:** Ano, nejméně 10 % průměrného výdělku, pokud se nesjedná jiná výše.
- **Actual behaviour:** Ano, za noční práci vám náleží příplatek. Podle [1] jde o 20 % průměrného hodinového výdělku za hodinu noční práce. Podle [3] za dobu noční práce náleží dosažená mzda a příplatek nejméně 10 % průměrného výdělku, přičemž je možné sjednat jinou minimální výši a způsob určení.
- **Category:** C (correct context supplied, model used it wrongly (reading))
- **Cause:** Reading: the model mixed wage (private employer, § 116: at least 10%) and salary (state, § 125: 20%). Manual note: Smíchal mzdu a plat: 20 % podle § 125 platí jen pro plat ve veřejné sféře. Pro běžnou mzdu je to nejméně 10 % (§ 116), to uvedl až jako druhé.
- **Fix:** v3: every chunk in the context carries a note "applies to wage / salary" and the prompt tells the model to give both variants when the question does not distinguish them.
- **Proof:** correct in v3 (manual review), v2 → v3 regressed 0 questions out of 66.

### Question 40: Do kdy mi musí zaměstnavatel vydat pracovní posudek?

- **Input:** Do kdy mi musí zaměstnavatel vydat pracovní posudek?
- **Expected behaviour:** Do 15 dnů od žádosti; dříve než 2 měsíce před skončením zaměstnání ho vydat nemusí.
- **Actual behaviour:** Požádáte-li zaměstnavatele o pracovní posudek, je povinen vám ho vydat do 15 dnů [1]. Nesmí vám ho však vydat dříve než v době 2 měsíců před skončením vašeho zaměstnání [1].
- **Category:** C (correct context supplied, model used it wrongly (reading)), D (claim without sufficient support in the chunks)
- **Cause:** Reading: the law says the employer does not have to issue the reference earlier than 2 months before the end. The cheap model wrote "must not" and the result varied between runs. Manual note: Obrátil význam: zákon říká, že zaměstnavatel posudek nemusí vydat dřív než 2 měsíce před koncem zaměstnání. Model napsal, že nesmí.
- **Fix:** v3: the rule "is not obliged = does not have to" in the prompt; from v3.1 a stronger model writes the answer.
- **Proof:** correct in v3 (manual review), v2 → v3 regressed 0 questions out of 66.

### Question 49: Kolik peněz dostanu na ošetřovném?

- **Input:** Kolik peněz dostanu na ošetřovném?
- **Expected behaviour:** 60 % denního vyměřovacího základu za kalendářní den.
- **Actual behaviour:** Nevím, v dostupných úsecích zákona to není.
- **Category:** F (refused although the answer was in the law), B (chunk found but dropped before answering (selection))
- **Cause:** Retrieval: § 41 ZNP (60%) was not found, the model correctly said "I don't know". The AI judge marked this as correct without reasoning. Manual note: § 41 ZNP (60 %) se nenašel, model řekl „nevím“. AI soudce to bez přemýšlení přehlédl a dal „správně“.
- **Fix:** v3: LLM selection. The judge is corrected by manual review, which is why the measurement has a second verdict.
- **Proof:** correct in v3 (manual review), v2 → v3 regressed 0 questions out of 66.

### Question 51: Do kdy mi musí zaměstnavatel vyplatit výplatu?

- **Input:** Do kdy mi musí zaměstnavatel vyplatit výplatu?
- **Expected behaviour:** Nejpozději v kalendářním měsíci následujícím po měsíci, ve kterém vzniklo právo na mzdu.
- **Actual behaviour:** Nevím, v dostupných úsecích zákona to není.
- **Category:** F (refused although the answer was in the law), B (chunk found but dropped before answering (selection))
- **Cause:** Retrieval: § 141 para. 1 was not found, the model said "I don't know". The AI judge missed it. Manual note: § 141 odst. 1 se nenašel, model řekl „nevím“. AI soudce to přehlédl.
- **Fix:** v3: LLM selection, manual review.
- **Proof:** correct in v3 (manual review), v2 → v3 regressed 0 questions out of 66.

## Regressions: v1 → v2

Fixing one thing broke another. Two questions that v1 got right failed in v2. That is why everything is measured again after every change, not only the fixed question.

### Question 40: Do kdy mi musí zaměstnavatel vydat pracovní posudek?

- **Input:** Do kdy mi musí zaměstnavatel vydat pracovní posudek?
- **Expected behaviour:** Do 15 dnů od žádosti; dříve než 2 měsíce před skončením zaměstnání ho vydat nemusí.
- **Actual behaviour:** Požádáte-li zaměstnavatele o pracovní posudek, je povinen vám ho vydat do 15 dnů [1]. Nesmí vám ho však vydat dříve než v době 2 měsíců před skončením vašeho zaměstnání [1].
- **Category:** C (correct context supplied, model used it wrongly (reading)), D (claim without sufficient support in the chunks)
- **Cause:** Obrátil význam: zákon říká, že zaměstnavatel posudek nemusí vydat dřív než 2 měsíce před koncem zaměstnání. Model napsal, že nesmí.
- **Fix:** fixed in v3 (the same question is correct in v3)
- **Proof:** v3: correct.

### Question 49: Kolik peněz dostanu na ošetřovném?

- **Input:** Kolik peněz dostanu na ošetřovném?
- **Expected behaviour:** 60 % denního vyměřovacího základu za kalendářní den.
- **Actual behaviour:** Nevím, v dostupných úsecích zákona to není.
- **Category:** F (refused although the answer was in the law), B (chunk found but dropped before answering (selection))
- **Cause:** § 41 ZNP (60 %) se nenašel, model řekl „nevím“. AI soudce to bez přemýšlení přehlédl a dal „správně“.
- **Fix:** fixed in v3 (the same question is correct in v3)
- **Proof:** v3: correct.

## Regression during v3 development (v3.0 → fix)

A detailed analysis is in the incident: [2026-10-06 regression in rest between shifts](incidents/2026-10-06-regrese-odpocinek.md).

## Open failures (not fixed yet)

Of the 16 sample questions on the website, two are wrong. I leave them visible on the website too. Neither is in the test sets, so nobody tuned for them.

### Web: Kolik hodin týdně je normální pracovní doba?

- **Input:** Kolik hodin týdně je normální pracovní doba?
- **Expected behaviour:** 40 hours per week; for a juvenile under 15 or someone who has NOT completed compulsory schooling, at most 35 hours (§ 79a para. 1 ZP).
- **Actual behaviour:** Normální (stanovená) týdenní pracovní doba činí 40 hodin týdně [1]. Pro některé skupiny zaměstnanců je kratší: u mladistvých do 15 let nebo po ukončení povinné školní docházky nesmí překročit 35 hodin týdně [3], u ostatních mladistvých 40 hodin týdně [2]. Dále činí 37,5 hodiny týdně pro zaměstnance v podzemí při těžbě nebo ve vícesměnném či nepřetržitém režimu a 38,75 hodiny týdně pro dvousměnný režim [4].
- **Category:** C (correct context supplied, model used it wrongly (reading))
- **Cause:** Hlavní číslo správně (40 hodin), ale u mladistvých převrátil podmínku: § 79a odst. 1 platí pro ty, kdo povinnou školní docházku NEukončili, model napsal „po ukončení“. Kde se to pokazilo: čtení.
- **Fix:** No fix yet. Proposal: a prompt rule for "before / after termination" conditions and a test on more questions with an inverted condition; verify on a new set.
- **Proof:** none (the fix has not been made yet; I am not claiming it is fixed).

### Web: Může mi zaměstnavatel dát výpověď, když jsem nemocný?

- **Input:** Může mi zaměstnavatel dát výpověď, když jsem nemocný?
- **Expected behaviour:** No. During temporary incapacity for work (protection period) notice is prohibited (§ 53 para. 1 let. a) ZP); the prohibition does not apply to the exceptions in § 54 (e.g. notice for organisational changes).
- **Actual behaviour:** Pokud jste nemocný, zaměstnavatel vám může dát výpověď, ale jen z některých důvodů. Výpověď z důvodu porušení povinností (např. neuspokojivé pracovní výsledky) je možná pouze do 3 měsíců ode dne, kdy se o důvodu dověděl [4]. Výpověď musí předem projednat s odborovou organizací, pokud u něj působí [3]. Samotná nemoc jako důvod výpovědi v dostupných úsecích uvedena není.
- **Category:** A (relevant chunk not found (retrieval))
- **Cause:** Pořád chyba: § 53 odst. 1 (zákaz výpovědi v době pracovní neschopnosti) se nedostal ani mezi 20 kandidátů. Odpověď proto zavádějícím způsobem tvrdí, že výpověď v nemoci dát lze. Kde se to pokazilo: hledání.
- **Fix:** The cause is measured, the fix is not deployed yet: see [ADR-004](decisions/ADR-004-prepis-a-bm25-otevrena-otazka.md). The question rewrite sent retrieval elsewhere (the correct paragraph ranks 12th by the meaning of the original question, 219th by the rewritten one, and 106th in BM25 over the rewrite). A proposed fix must be tried on a new set, not on this question.
- **Proof:** none (the fix has not been made yet; I am not claiming it is fixed).

