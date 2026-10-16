[Česky](../docs/cs/security/threat-model.md)

# Threat model

What I protect, from whom, with what, and what remains open. It applies to **this demo** (public data, no users, no document uploads),
not to a general "AI platform". Where a security property is **not** in the project, it says so. Nothing here claims "it is secure":
the tests prove only what they try (the "Verified" column).

Related: [tests](../tests/test_security.py) · [live injection set](injection_cases.json) · [ADR-003](../docs/decisions/ADR-003-opravneni-v-hledani.md) · [limitations](../docs/limitations.md)

## 1. What I protect (assets)

| # | Asset | Why it matters |
|---|---|---|
| A1 | OpenRouter API key and its budget (limit $0.75, as of 9 Oct 2026 ~$0.09 remains) | leak = someone else's spending; exhaustion = the demo stops answering |
| A2 | Correctness of answers | people may trust incorrect legal information |
| A3 | Availability of the live demo | it is a showcase for employers |
| A4 | Visitors' questions (stored in Upstash Redis) | free text may contain personal data |
| A5 | Access to Upstash and Vercel (tokens) | writing to the database, deployment |
| A6 | Source texts of the laws | public, confidentiality plays no role; what matters is **integrity** (whoever changes them changes the answers) |

## 2. Trust boundaries

```
browser (untrusted) ──► Vercel function ask.js / hit.js ──► OpenRouter (third-party service, receives the question text)
                                    │                      └► Upstash Redis (counters, custom questions)
                                    └► _index.json (frozen law data, part of the deployment)
model output = UNTRUSTED (may contain anything, even HTML)
```

Trusted: the function code, the frozen data, the system prompt. Untrusted: everything from the browser (including the `Origin` and `x-rag-client` headers, which can be forged) and everything the model returns.

## 3. Threats, defences and residual risks

| ID | Threat | What prevents it | Verified (test) | Residual risk |
|---|---|---|---|---|
| T1 | **Direct prompt injection** in the question ("ignore the rules…", prompt leak, language switch) | The system prompt is a separate message; the question is only in the user message. Whitespace and line breaks are normalised, so the question cannot create a line that pretends to be the block "Úseky zákona:" (law chunks) or "Otázka:" (question). Limit of 300 characters. | `test_web_function`: the system prompt stays unchanged, the question does not insert its own block. **The model's behaviour against injection has not been measured**: a live set of 14 cases is prepared ([injection_cases.json](injection_cases.json)) but not run (it costs ~$0.02 and the website key has only a few cents of budget left). | **Medium and unknown.** Until the live set is run, I do not know how the model behaves. The detectors are tested only on made-up bad answers. |
| T2 | **Indirect injection** (instructions in a document) | The source is only the frozen text of the laws from zakonyprolidi.cz, no uploads. Rule 3 in the prompt ("do not use a chunk about a different situation"). Data fingerprints (`results/…json`) reveal a change of files. | A data fingerprint in every run record. Cases INJ-06 and INJ-07 imitate a chunk with an instruction inside the question (not verified live). | Low today, **high if user documents were added.** There the text would need to be sanitised and the trust source labelled. Not implemented. |
| T3 | **Unauthorised access to documents** | Pointless today: everything is public. As a pattern there is `rag.search(..., allow={"ZP"})` in the retrieval layer: a disallowed regulation gets no score, so it does not reach the model, candidates, trace or citations. The prompt does not know about it at all. | `test_disallowed_law_never_reaches_model_candidates_or_trace` (20 questions, including the content of the prompt for candidate selection), `test_filter_really_filters…`, `test_empty_allow_list…`. Mutation check: after switching off the mask the test fails. | The filter is only by **regulation**, not by user. The web function does not use `allow` (no one to use it for). There is no answer cache, so there is no leak path through a cache. **If a cache were added, its key would have to contain the set of allowed documents.** |
| T4 | **Tenant isolation** | There are no tenants or users. | – | Deliberately not addressed. I do not pretend to be a multi-tenant system that does not exist. |
| T5 | **Secret leakage** | The key only in an environment variable on Vercel and in the local `.env` (in `.gitignore`). Only the `site/` folder is deployed. The function's response never returns the key. | `test_no_secrets_in_tracked_files` (key patterns in all tracked files), `test_env_example_has_no_value`, harness: the key does not appear in the response or in anything that goes to the client; it goes only to `openrouter.ai` in a header. | The model never receives the key, so it cannot reveal it. Only the `site/` folder is deployed; the test guards that there is no secret in it or elsewhere in tracked files. It does not cover files outside git (the local `.env` and `.tmp/`). |
| T6 | **Misuse of agent tools** | There is no agent or tools. | – | N/A. |
| T7 | **Denial-of-wallet** (someone else's spending) | 10 questions per IP per day, a cap of 400 per function instance, proof of work (4 zeros of SHA-256, 1–3 s in the browser), 300 characters, hidden model reasoning turned off (cost), **a hard limit of $0.75 directly on the key at the provider** (the toughest safeguard). | Harness: the 11th question from one IP → 429 and **no model call**; the same proof of work a second time → 400; one question = exactly 4 model calls; a failed call is not counted towards the limit. `test_worst_case_daily_cost_fits_into_key_limit`: 400 × $0.00112 = $0.45. | The counters are **in the function's memory**, not in the database: more instances = more allowed questions. An attacker with many IPs and computing power can exhaust the remaining ~$0.09 in a day. The money is protected (the cap is hard), availability is not: the website then shows "The budget for live questions is exhausted" („Rozpočet na živé otázky je vyčerpaný“). |
| T8 | **Malicious input and output (XSS)** | The model's answer is escaped (`esc`) before rendering and only then are bold text, line breaks and citation buttons produced. | `test_rendered_answer_cannot_inject_html` runs the **real code** `esc()` and `fmt()` from `site/index.html` on 5 malicious strings. Mutation check: after breaking `esc` the test fails. | No Content-Security-Policy, so if someone broke `esc`, the browser would catch nothing. Not addressed. |
| T9 | **Misuse of analytics** (`hit.js`) | **Found during the audit:** `hit.js` wrote an arbitrary string from the request to Redis (a forged `Origin` header was enough), and it could be filled with unique keys. Fix: only questions from the list of prepared ones are counted (`site/api/_presets.json`, generated by `tools/make_presets.py`). | Harness: a foreign string is not written to the database, a prepared question is. | **The fix is in the repository but is not deployed.** Until deployed to Vercel, the old version behaves as before. |
| T10 | **Forged request origin** | The `Origin` and `x-rag-client` headers can be forged from any script. I do not treat them as protection, only as a filter against the simplest bots. The real protection is proof of work, limits and the budget. | Harness: a foreign origin → 403 (verifies that the filter does what it does, not that it is unbreakable). | See T7. |
| T11 | **Privacy of custom questions** | The question text, time and the "I don't know" flag are stored, without IP, the last 5 000 records (LTRIM). The page says so in the footer. | – | "Anonymous" is overstated: free text may contain names and other personal data that the visitor types in. A filter and a fixed retention period are missing. |
| T12 | **A forged script from a CDN** | D3 is loaded from cdnjs with a pinned version, icons from unpkg (version 2.1.1). | – | **No Subresource Integrity.** If the CDN served different content, it would run on the page. Fix: an SRI hash or your own copy of the file. Not done. |
| T13 | **Incorrect answer about the law** (integrity) | It answers only from the supplied chunks, every claim is cited, "this is not legal advice", errors are publicly visible. | Quality measurement ([benchmark-results.md](../docs/benchmark-results.md)). | **Real and measured:** for the question „Může mi zaměstnavatel dát výpověď, když jsem nemocný?“ ("Can my employer give me notice when I am ill?") the website answers in a misleading way ([failure gallery](../docs/failure-gallery.md#open-failures-not-fixed-yet)). |
| T14 | **An outdated or changed law** | The data are frozen as of 6 Oct 2026, file fingerprints in the run record. The website and README say so. | – | Laws change. There is no automatic update (described in [DESIGN.md](../DESIGN.md#11-what-would-be-missing-for-production)). |

## 4. What has NOT been verified

- **The model's behaviour under attack.** See T1. The set and the runner (`tools/security_eval.py --live`) are prepared, waiting for a separate key with a budget.
- No penetration test, no dependency scanning (vulnerabilities of libraries have not been checked).
- The rate limit was tested on one instance of the function. The behaviour of multiple instances on Vercel was not tried.
- Authorisation is verified only at the level of retrieval over frozen data, not on a real system with users.

## 5. How this is maintained

- `python -m pytest tests` (includes all the security tests, 9 s, no key) runs in CI on every push.
- A new website feature that calls the model or writes to the database must add a row to this file and a test to `tests/js_harness.cjs`.
- After changing a defence, always try to **break the defence** and verify the test fails. A test that never fails says nothing. (Done for the permission mask, `hit.js`, `esc` and the per-IP limit.)
