# -*- coding: utf-8 -*-
"""Nová zmrazená sada (data/testset_heldout_v4.json): tvar, pokrytí typů, žádný únik ze starých sad a pojistky jednorázového běhu."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import datasets  # noqa: E402
import run_heldout  # noqa: E402

V4 = json.loads((ROOT / "data" / "testset_heldout_v4.json").read_text(encoding="utf-8"))


def test_covers_the_required_case_types():
    types = {q["type"] for q in V4}
    assert {"exact", "multi", "ambiguous", "unanswerable", "outdated", "adversarial", "misspelled", "common"} <= types
    assert len(V4) >= 24


def test_ids_do_not_collide_and_questions_are_new():
    old = datasets.questions()
    assert not {q["id"] for q in V4} & {q["id"] for q in old}
    assert not {q["q"].strip().lower() for q in V4} & {q["q"].strip().lower() for q in old}, "otázka z v4 už je ve starých sadách (únik)"


def test_unanswerable_have_no_gold_and_the_rest_have_some():
    for q in V4:
        if q["type"] in ("unanswerable", "outdated") and q["id"] != 118:
            assert q["chunks"] == [], q["id"]
        if q["type"] in ("exact", "multi", "ambiguous", "misspelled", "common"):
            assert q["chunks"], q["id"]
        assert q["gold"].strip()


def test_canaries_are_in_the_question():
    for q in V4:
        if "canary" in q:
            assert q["canary"] in q["q"]


def test_planned_set_is_fingerprinted():
    assert "testset_heldout_v4.json" in datasets.fingerprint()


def test_v4_is_not_part_of_the_normal_measurement():
    assert not any(q["set"] == "heldout_v4" for q in datasets.questions())


def test_plan_mode_calls_nothing(monkeypatch, capsys):
    monkeypatch.setattr(run_heldout.rag, "search", lambda *a, **k: pytest.fail("bez --live se nesmí hledat"))
    assert run_heldout.main([]) == 0
    assert "Nic se nevolalo" in capsys.readouterr().out


def test_second_run_is_refused(monkeypatch, tmp_path, capsys):
    lock = tmp_path / "heldout_v4.lock"
    lock.write_text("2026-10-10T10:00:00\n", encoding="utf-8")
    monkeypatch.setattr(run_heldout, "LOCK", lock)
    monkeypatch.setattr(run_heldout.rag, "search", lambda *a, **k: pytest.fail("druhý běh se nesmí spustit"))
    assert run_heldout.main(["--live"]) == 2
    assert "ODMÍTNUTO" in capsys.readouterr().out
