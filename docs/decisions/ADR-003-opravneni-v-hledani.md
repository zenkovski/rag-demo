[Česky](../cs/decisions/ADR-003-opravneni-v-hledani.md)

# ADR-003: Permissions are enforced in the retrieval layer, not in the prompt

**Status:** accepted as a pattern, **not wired into the live website** · **Date:** 9 Oct 2026

## Context

If the system searched over documents with different access rights, there are two ways a leak can happen: the model receives text the user must not see and then repeats it (by mistake or on request); or the text appears in citations or intermediate results.

The defence "the prompt says you must not show this" is **unreliable**: a prompt can be bypassed (see prompt injection) and the model has already seen the text.

## Decision

Permissions are **enforced before the model**, in the retrieval: `rag.search(question, allow={"ZP"})` gives disallowed regulations a zero score in all three rankings, so they do not get among the candidates, into the selection, into the five chunks for the model, into the trace or into the citations. The prompt does not know about the disallowed documents at all.

## Verification

`tests/test_security.py` verifies on 20 questions that with `allow={"ZP"}` a disallowed regulation is **not** (a) in the result, (b) in any intermediate step of the trace, (c) in the prompt text the model would receive when selecting candidates. A fake model records what it would receive. A second test proves the filter does something (without the filter a chunk from the sickness insurance act appears). After switching off the mask the test fails (verified).

## Consequences and limits

- The filter is by **regulation** (`law`), not by user. A real system would need a list of allowed documents per user and its source of truth (IdP, permissions database). **Not implemented.**
- The web function does not use `allow`, because it has no users or non-public documents.
- **There is no answer cache.** If one were added, its key must contain the set of allowed documents, otherwise an answer for one user could be served to another.
- It does not address a leak through **vectors**: the embedding of a disallowed document is in the index. In a gross leak of the index, part of the text could be estimated from the vectors. For confidential data a separate index per tenant would be needed.
