# Model hrozeb

Co chráním, před kým, čím a co zůstává otevřené. Platí pro **tohle demo** (veřejná data, žádní uživatelé, žádné nahrávání dokumentů),
ne pro obecnou „AI platformu“. Kde bezpečnostní vlastnost v projektu **není**, je to napsané. Nic tu netvrdí „je to bezpečné“:
testy dokazují jen to, co zkoušejí (sloupec „Ověřeno“).

Související: [testy](../tests/test_security.py) · [živá sada injekcí](injection_cases.json) · [ADR-003](../docs/decisions/ADR-003-opravneni-v-hledani.md) · [limity](../docs/limitations.md)

## 1. Co chráním (aktiva)

| # | Aktivum | Proč na něm záleží |
|---|---|---|
| A1 | OpenRouter API klíč a jeho rozpočet (limit 0,75 $, ke dni 9. 10. 2026 zbývá ~0,09 $) | únik = cizí útrata; vyčerpání = demo přestane odpovídat |
| A2 | Správnost odpovědí | lidé mohou věřit nesprávné právní informaci |
| A3 | Dostupnost živého dema | je to ukázka pro zaměstnavatele |
| A4 | Otázky návštěvníků (ukládají se do Upstash Redis) | volný text může obsahovat osobní údaje |
| A5 | Přístup do Upstash a Vercelu (tokeny) | zápis do databáze, nasazení |
| A6 | Zdrojové texty zákonů | veřejné, důvěrnost nehraje roli; záleží na **celistvosti** (kdo je změní, změní odpovědi) |

## 2. Hranice důvěry

```
prohlížeč (nedůvěryhodný) ──► Vercel funkce ask.js / hit.js ──► OpenRouter (cizí služba, dostane text otázky)
                                    │                         └► Upstash Redis (počítadla, vlastní otázky)
                                    └► _index.json (zmrazená data zákonů, součást nasazení)
výstup modelu = NEDŮVĚRYHODNÝ (může obsahovat cokoli, i HTML)
```

Důvěryhodné: kód funkce, zmrazená data, systémový prompt. Nedůvěryhodné: všechno z prohlížeče (včetně hlaviček `Origin` a `x-rag-client`, které jde padělat) a všechno, co vrátí model.

## 3. Hrozby, obrany a zbytková rizika

| ID | Hrozba | Co brání | Ověřeno (test) | Zbytkové riziko |
|---|---|---|---|---|
| T1 | **Přímá prompt injekce** v otázce („ignoruj pravidla…“, únik promptu, změna jazyka) | Systémový prompt je oddělená zpráva; otázka je jen ve zprávě uživatele. Mezery a zalomení se sjednotí, takže v otázce nejde vytvořit řádek, který by se tvářil jako blok „Úseky zákona:“ nebo „Otázka:“. Strop 300 znaků. | `test_web_function`: systémový prompt zůstane beze změny, otázka nevloží vlastní blok. **Chování modelu proti injekci jsem nezměřil**: živá sada 14 případů je připravená ([injection_cases.json](injection_cases.json)), ale nespuštěná (stojí ~0,02 $ a klíč webu má zbývající rozpočet jen pár centů). | **Střední a neznámé.** Dokud se živá sada nespustí, nevím, jak se model zachová. Detektory jsou otestované jen na vymyšlených špatných odpovědích. |
| T2 | **Nepřímá injekce** (instrukce v dokumentu) | Zdrojem je jen zmrazený text zákonů ze zakonyprolidi.cz, žádné nahrávání. Pravidlo 3 v promptu („úsek o jiné situaci nepoužívej“). Otisky dat (`results/…json`) odhalí změnu souborů. | Otisk dat v každém záznamu o běhu. Případ INJ-06 a INJ-07 napodobují úsek s instrukcí v otázce (živě neověřeno). | Nízké dnes, **vysoké, kdyby přibyly uživatelské dokumenty.** Tam by bylo potřeba čistit text a označovat zdroj důvěry. Neimplementováno. |
| T3 | **Neoprávněný přístup k dokumentům** | Dnes nemá smysl: všechno je veřejné. Jako vzor je v hledací vrstvě `rag.search(..., allow={"ZP"})`: nepovolený předpis nedostane skóre, takže se nedostane k modelu, do kandidátů, stopy ani citací. Prompt o něm vůbec neví. | `test_disallowed_law_never_reaches_model_candidates_or_trace` (20 otázek, i obsah promptu pro výběr kandidátů), `test_filter_really_filters…`, `test_empty_allow_list…`. Mutační kontrola: po vypnutí masky test selže. | Filtr je jen podle **předpisu**, ne podle uživatele. Webová funkce `allow` nepoužívá (nemá komu). Cache odpovědí neexistuje, takže tu není cesta úniku přes cache. **Kdyby se cache přidala, klíč by musel obsahovat množinu povolených dokumentů.** |
| T4 | **Izolace tenantů** | Neexistují tenanti ani uživatelé. | – | Neřešeno záměrně. Nepředstírám multi-tenant systém, který neexistuje. |
| T5 | **Únik tajemství** | Klíč jen v proměnné prostředí na Vercelu a v lokálním `.env` (v `.gitignore`). Nasazuje se jen složka `site/`. Odpověď funkce klíč nikdy nevrací. | `test_no_secrets_in_tracked_files` (vzory klíčů ve všech sledovaných souborech), `test_env_example_has_no_value`, harness: klíč se neobjeví v odpovědi ani v ničem, co jde klientovi; jde jen na `openrouter.ai` v hlavičce. | Model klíč nikdy nedostane, takže ho nemůže vyzradit. Nasazuje se jen složka `site/`; že v ní ani jinde ve sledovaných souborech žádné tajemství není, hlídá test. Nepokrývá soubory mimo git (lokální `.env` a `.tmp/`). |
| T6 | **Zneužití nástrojů agenta** | Žádný agent ani nástroje neexistují. | – | N/A. |
| T7 | **Denial-of-wallet** (cizí útrata) | 10 otázek na IP a den, strop 400 na instanci funkce, proof of work (4 nuly SHA-256, 1–3 s v prohlížeči), 300 znaků, vypnuté skryté přemýšlení modelu (cena), **pevný limit 0,75 $ přímo na klíči u poskytovatele** (nejtvrdší pojistka). | Harness: 11. otázka z jedné IP → 429 a **žádné volání modelu**; stejný proof of work podruhé → 400; jedna otázka = právě 4 volání modelu; neúspěšné volání se do limitu nepočítá. `test_worst_case_daily_cost_fits_into_key_limit`: 400 × 0,00112 $ = 0,45 $. | Počítadla jsou **v paměti funkce**, ne v databázi: víc instancí = víc povolených otázek. Útočník s mnoha IP a výpočtem může vyčerpat zbývajících ~0,09 $ za den. Peníze jsou chráněné (strop je tvrdý), dostupnost ne: web pak ukáže „Rozpočet na živé otázky je vyčerpaný“. |
| T8 | **Škodlivý vstup a výstup (XSS)** | Odpověď modelu se před vykreslením escapuje (`esc`) a až potom se dělá tučné písmo, zalomení a tlačítka citací. | `test_rendered_answer_cannot_inject_html` spouští **skutečný kód** `esc()` a `fmt()` z `site/index.html` na 5 škodlivých řetězcích. Mutační kontrola: po rozbití `esc` test selže. | Žádný Content-Security-Policy, takže kdyby `esc` někdo rozbil, prohlížeč nic nezachytí. Neřešeno. |
| T9 | **Zneužití analytiky** (`hit.js`) | **Nalezeno při auditu:** `hit.js` zapisoval do Redisu libovolný řetězec z požadavku (stačí padělaná hlavička `Origin`), šlo ho zaplnit unikátními klíči. Oprava: počítají se jen otázky ze seznamu připravených (`site/api/_presets.json`, generuje `tools/make_presets.py`). | Harness: cizí řetězec se do databáze nezapíše, připravená otázka ano. | **Oprava je v repozitáři, ale není nasazená.** Do nasazení na Vercel se stará verze chová jako dřív. |
| T10 | **Padělání původu požadavku** | Hlavičky `Origin` a `x-rag-client` jdou padělat z jakéhokoli skriptu. Neberu je jako ochranu, jen jako filtr nejjednodušších robotů. Skutečnou ochranou jsou proof of work, limity a rozpočet. | Harness: cizí původ → 403 (ověřuje, že filtr dělá, co dělá, ne že je neprolomitelný). | Viz T7. |
| T11 | **Soukromí vlastních otázek** | Ukládá se text otázky, čas a příznak „nevím“, bez IP, posledních 5 000 záznamů (LTRIM). Stránka to říká v patičce. | – | „Anonymně“ je nadsazené: volný text může obsahovat jména a jiné osobní údaje, které tam návštěvník napíše. Chybí filtr a pevná doba uchování. |
| T12 | **Podvržený skript z CDN** | D3 se načítá z cdnjs s pevnou verzí, ikony z unpkg (verze 2.1.1). | – | **Bez Subresource Integrity.** Kdyby CDN vydala jiný obsah, běžel by na stránce. Oprava: SRI hash nebo vlastní kopie souboru. Neprovedeno. |
| T13 | **Nesprávná odpověď o právu** (integrita) | Odpovídá jen z dodaných úseků, každé tvrzení se cituje, „není to právní porada“, chyby jsou veřejně vidět. | Měření kvality ([benchmark-results.md](../docs/benchmark-results.md)). | **Reálné a změřené:** u otázky „Může mi zaměstnavatel dát výpověď, když jsem nemocný?“ web odpovídá zavádějícím způsobem ([galerie chyb](../docs/failure-gallery.md#otevřené-chyby-zatím-neopravené)). |
| T14 | **Zastaralý nebo změněný zákon** | Data jsou zmrazená k 6. 10. 2026, otisky souborů v záznamu o běhu. Web i README to říkají. | – | Zákony se mění. Automatická aktualizace neexistuje (popsaná v [DESIGN.md](../DESIGN.md#11-co-by-chybělo-do-provozu)). |

## 4. Co jsem NEověřil

- **Chování modelu pod útokem.** Viz T1. Připravená je sada a spouštěč (`tools/security_eval.py --live`), čeká na samostatný klíč s rozpočtem.
- Žádný penetrační test, žádné skenování závislostí (zranitelnosti knihoven nejsou zkontrolované).
- Rate limit jsem testoval na jedné instanci funkce. Chování víc instancí na Vercelu jsem nezkoušel.
- Autorizaci jsem ověřil jen na úrovni hledání nad zmrazenými daty, ne na reálném systému s uživateli.

## 5. Jak se to udržuje

- `python -m pytest tests` (zahrnuje všechny bezpečnostní testy, 9 s, bez klíče) běží v CI při každém pushi.
- Nová funkce webu, která volá model nebo píše do databáze, musí přidat řádek do tohoto souboru a test do `tests/js_harness.cjs`.
- Po změně obrany se vždy zkusí **obranu rozbít** a ověřit, že test selže. Test, který nikdy neselže, nic neříká. (Provedeno pro masku oprávnění, `hit.js`, `esc` a limit na IP.)
