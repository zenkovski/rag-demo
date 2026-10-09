# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import answer_checks as ac  # noqa: E402

CHUNKS = ["Dovolená činí nejméně 4 týdny v kalendářním roce.", "Náhrada mzdy činí 60 % průměrného výdělku."]


def test_numbers_skip_citations_and_paragraphs():
    assert ac.numbers("Podle § 212 odst. 1 je to 4 týdny [1].") == ["4"]
    assert ac.numbers("Je to 1 500 Kč a 2,5 %.") == ["1500", "2.5"]


def test_good_answer_has_no_findings():
    r = ac.check("Dovolená je nejméně 4 týdny [1].", CHUNKS)
    assert r == {"abstained": False, "cited": [1], "bad_citations": [], "no_citation": False, "unsupported_numbers": [],
                 "misattributed_numbers": [], "numbers_in_no_chunk": []}


def test_number_not_in_cited_chunk_is_flagged():
    r = ac.check("Náhrada činí 70 % [2].", CHUNKS)
    assert r["unsupported_numbers"] == ["70"]


def test_number_must_come_from_the_CITED_chunk():
    r = ac.check("Dovolená je 60 % [1].", CHUNKS)             # 60 % je v úseku 2, citován je 1
    assert r["unsupported_numbers"] == ["60"]


def test_citation_out_of_range():
    assert ac.check("Ano [3].", CHUNKS)["bad_citations"] == [3]


def test_missing_citation():
    assert ac.check("Dovolená je 4 týdny.", CHUNKS)["no_citation"] is True


def test_abstention_is_not_flagged():
    r = ac.check("Nevím, v dostupných úsecích zákona to není.", CHUNKS)
    assert r["abstained"] and not r["no_citation"] and r["unsupported_numbers"] == []


def test_number_from_question_is_allowed():
    assert ac.check("Ve 35 letech je to 4 týdny [1].", CHUNKS, question="Je mi 35 let, kolik mám dovolené?")["unsupported_numbers"] == []


def test_number_words_in_law_match_digits_in_answer():
    chunk = ["Výpovědní doba činí patnáct dnů ode dne doručení."]
    assert ac.check("Výpovědní doba je 15 dnů [1].", chunk)["unsupported_numbers"] == []
    assert ac.check("Výpovědní doba je 30 dnů [1].", chunk)["unsupported_numbers"] == ["30"]


def test_word_numbers_are_inflected_forms_too():
    assert ac.word_numbers("do patnácti dnů, po třech měsících, dvě hodiny") == ["15", "3", "2"]


def test_misattributed_number_vs_number_in_no_chunk():
    r = ac.check("Dovolená je 4 týdny [2] a celkem 80 dní [2].", CHUNKS)
    assert r["misattributed_numbers"] == ["4"]               # 4 týdny je v úseku 1, citován je 2
    assert r["numbers_in_no_chunk"] == ["80"]                # 80 není nikde: odvozené nebo vymyšlené


def test_compound_number_words():
    assert ac.word_numbers("s patnáctidenní výpovědní dobou") == ["15"]
