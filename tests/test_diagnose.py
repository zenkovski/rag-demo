# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import diagnose as d  # noqa: E402

base = dict(answerable=True, correct=False, said_nevim=False, gold_in_final=True, gold_in_candidates=True)


def test_not_retrieved_vs_dropped():
    assert d.classify(**{**base, "gold_in_final": False, "gold_in_candidates": False}) == ["A"]
    assert d.classify(**{**base, "gold_in_final": False}) == ["B"]


def test_misread_means_context_was_right():
    assert d.classify(**base) == ["C"]


def test_correct_answer_has_no_finding():
    assert d.classify(**{**base, "correct": True}) == []


def test_false_refusal_keeps_the_retrieval_cause():
    # odmítl a správný úsek mu nedali: dvě věci najednou, F a A
    r = d.classify(**{**base, "said_nevim": True, "gold_in_final": False, "gold_in_candidates": False})
    assert r == ["F", "A"] and d.primary(r) == "A"


def test_should_have_abstained():
    assert d.classify(answerable=False, correct=False, said_nevim=False, gold_in_final=False, gold_in_candidates=False) == ["E"]
    assert d.classify(answerable=False, correct=True, said_nevim=True, gold_in_final=False, gold_in_candidates=False) == []


def test_unsupported_claim_only_counts_on_wrong_answers():
    assert "D" in d.classify(**{**base, "grounded": False})
    assert d.classify(**{**base, "correct": True, "unsupported_numbers": True}) == []


def test_primary_prefers_chain_break_over_abstention():
    assert d.primary(["F", "B"]) == "B" and d.primary(["D"]) == "D" and d.primary([]) == "-"
