"""Tests for the exercise tooling: verdict assertions, blind spots, saved runs."""

import json
from types import SimpleNamespace as NS

from evals import check_evaluators as ce
from evals.run_evals import diff_runs, save_report


def test_evaluators_give_the_expected_verdicts():
    assert ce.mismatches() == []


def test_mismatch_is_reported_when_an_evaluator_changes():
    wrong = {**ce.EXPECTED, "silent fallback": {**ce.EXPECTED["silent fallback"], "NotFallback": True}}
    assert any("silent fallback" in m and "NotFallback" in m for m in ce.mismatches(wrong))


def test_known_blind_spots_still_pass_specific_focus():
    # These two outputs are bad; SpecificFocus cannot tell. If this test fails, the evaluator got smarter.
    assert ce.blind_spots() == {"empty focus areas": True, "unrelated advice": True}


def _report(risk: str, specific: bool) -> NS:
    case = NS(
        name="c1",
        output={"risk": risk, "focus_areas": ["x"], "fallback_used": False},
        assertions={"SpecificFocus": NS(value=specific)},
    )
    return NS(cases=[case])


def test_save_then_diff_shows_what_changed(tmp_path):
    path = tmp_path / "before.json"
    save_report(_report("high", True), path, model="m", prompt="p1")
    data = json.loads(path.read_text())
    assert data["model"] == "m" and data["prompt_sha"] and data["saved_at"] and data["cases"]["c1"]["risk"] == "high"
    lines = diff_runs(_report("low", False), path)
    assert any("c1" in l and "high" in l and "low" in l for l in lines)
    assert any("SpecificFocus" in l for l in lines)
    assert diff_runs(_report("high", True), path) == []


def test_judge_calibration_cases_are_labelled_both_ways():
    from evals import check_judge

    verdicts = [v for _, v in check_judge.HUMAN.values()]
    assert any(verdicts) and not all(verdicts)
    assert len(check_judge.HUMAN) == 4
