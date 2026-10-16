[Česky](../cs/decisions/README.md)

# Decisions (ADR)

Every significant decision: context, decision, consequences, and what the alternatives were. The status "open" means the data are not sufficient and the decision is postponed until a specific measurement.

| ADR | Decision | Status |
|---|---|---|
| [001](ADR-001-offline-quality-gate.md) | The quality gate replays stored results, it does not call the model | accepted |
| [002](ADR-002-rrf-misto-vazeni.md) | RRF instead of a weighted sum of scores | accepted |
| [003](ADR-003-opravneni-v-hledani.md) | Permissions are enforced in the retrieval layer, not in the prompt | accepted (a pattern, not wired in) |
| [004](ADR-004-prepis-a-bm25-otevrena-otazka.md) | Question rewrite and BM25: benefit not proven | **open** |
| [005](ADR-005-llm-vyber-misto-cross-encoderu.md) | LLM selection instead of a cross-encoder | accepted, to be reconsidered |
| [006](ADR-006-deterministicke-kontroly.md) | Deterministic checks alongside the LLM judge | accepted |
