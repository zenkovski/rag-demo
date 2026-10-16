[Česky](cs/ai-assisted-development.md)

# Development with AI: who did what and where the AI went wrong

The project was built with the Claude Code assistant. The project does not pretend that a human wrote the code. More important is **what was verified, by whom, and where an error was found in the process**.

## Who did what

| Part | Who | How verified |
|---|---|---|
| Chain code (`tools/rag.py` etc.), website, initial question sets and measurements (6–7 Oct 2026) | Claude Code (Opus 5.5), directed by Lukáš Procházka | a second check of all answers against the text of the law by a different model, **results reviewed by the project owner** |
| Measurement layer, security tests, CI, documents, frozen set v4 (9 Oct 2026) | Claude Code (Sonnet 5.5) | tests, mutation checks of the defences and CI on GitHub (see below) |
| Decisions about what will be done and what will not | Lukáš Procházka | – |

**What was not done:** the work from 9 Oct 2026 (metrics, ablations, security tests, documents, the new set) **was not checked line by line by the project owner before publication**. The claim "verified" in the documents means "verified by running a test or script", not "read and approved by a human". The new set v4 and its correct answers were created the same way and **have no independent legal review**.

## Where the AI proposed something wrong and what it revealed

| When | What happened | What revealed it | What changed |
|---|---|---|---|
| 6 Oct | Hidden model "reasoning" burned most of the budget; nobody expected it, the output was short | cost and time in `usage` | [incident](incidents/2026-10-06-skryte-premysleni.md), one call is measured before a batch |
| 6 Oct | LLM selection dropped the base rule (v3.0) | comparison **per question**, not the average | [incident](incidents/2026-10-06-regrese-odpocinek.md), fixed rule + test |
| 6 Oct | The AI judge overlooked wrong "I don't know" answers and marked one correct answer as an error | manual check against the law | second verdict, deterministic checks ([ADR-006](decisions/ADR-006-deterministicke-kontroly.md)) |
| 7 Oct | The README claimed "20 of 20 on questions written in advance" | audit of set roles from git (9 Oct) | [corrected](evaluation-methodology.md#2-dev-validation-test-and-leakage-prevention): truly untouched are 10 |
| 9 Oct | The first version of the number check marked "15 days" as unsupported; the law writes "patnáctidenní" ("fifteen-day") | a test on real answers | conversion of numerals written as words, a test |
| 9 Oct | The first version of the error classification counted "at least one correct chunk" as found; for a question with two correct paragraphs (paternity) this hid the missing paragraph | reading the generated gallery, not the metrics | "found" = all correct chunks, a test |
| 9 Oct | A text in a document claimed "all derived values" before it was recomputed what remained after the check fix; in reality a **wrong citation** remained too | recomputation after the fix | the table of suspicions is generated from data, the manual comment is accurate |
| 9 Oct | The first version of the quality gate, when candidates changed, crashed on a missing key instead of a clear message; there was a risk it would call the paid API locally | thinking through failure, a test | offline mode `RAG_OFFLINE`, a missing cache = error, `tests/conftest.py` forbids network |
| 9 Oct | A test script created a directory `%SystemDrive%` in the repo (a subprocess without environment variables) | `git status` | directory deleted, script fixed |
| 9 Oct | When another browser was added, an error showed up in the **test**, not in the product (QA project: a test in WebKit read the list before it was rendered) | repeating 10× | [QA repo](https://github.com/zenkovski/qa-portfolio#reliability) |

## What follows for further work

1. A document with numbers is **generated from data** (`tools/make_docs.py`), not written from memory. Hand-written sentences must be re-checked after the data changes.
2. A defence counts as tested only when it was **broken** and the test failed (mutation check).
3. Whoever presents the project must be able to explain: why RRF and not a weighted sum, why results on dev do not count as proof, what Recall@k × MRR is, what the offline gate proves and does not prove, why permission is in the search and not in the prompt. If the author cannot explain it, the corresponding claim should be removed from the presentation.
