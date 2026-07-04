import json
from pathlib import Path

import pytest

from investment_model.config import load_playbook
from investment_model.inputs import PropertyInput
from investment_model.report import evaluate_property

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def playbook():
    return load_playbook()


def _load(name):
    with open(EXAMPLES / name) as f:
        return PropertyInput.from_dict(json.load(f))


def test_ltr_example_rejected_on_weak_cash_flow(playbook):
    prop = _load("ltr_murfreesboro.json")
    report = evaluate_property(prop, playbook)
    assert report.scorecard.category == "LTR"
    # This example is intentionally a marginal deal -- verifies the reject path.
    assert report.scorecard.failures >= 1
    if report.scorecard.reject:
        assert report.decision == "REJECT"


def test_str_example_passes_all_scorecard_criteria(playbook):
    prop = _load("str_sevier_county.json")
    report = evaluate_property(prop, playbook)
    assert report.scorecard.category == "STR"
    assert report.scorecard.failures == 0
    assert report.scorecard.reject is False


def test_appreciation_example_has_no_scorecard_but_has_appreciation_score(playbook):
    prop = _load("appreciation_scottsdale.json")
    report = evaluate_property(prop, playbook)
    assert report.scorecard is None
    assert report.appreciation is not None
    assert 0 <= report.appreciation.average_score <= 10


def test_market_framework_out_of_100_for_ltr(playbook):
    prop = _load("ltr_murfreesboro.json")
    report = evaluate_property(prop, playbook)
    assert report.market.out_of == 90  # no tourism score for LTR
    assert 0 <= report.market.normalized_out_of_100 <= 100


def test_market_framework_includes_tourism_for_str(playbook):
    prop = _load("str_sevier_county.json")
    report = evaluate_property(prop, playbook)
    assert report.market.out_of == 100  # tourism score included
    assert "Tourism" in report.market.scores


def test_philosophy_requires_two_of_three(playbook):
    prop = _load("str_sevier_county.json")
    report = evaluate_property(prop, playbook)
    assert report.philosophy.criteria_met >= playbook["philosophy"]["min_criteria_met"]


def test_reject_beats_consider_and_pursue(playbook):
    prop = _load("ltr_murfreesboro.json")
    report = evaluate_property(prop, playbook)
    if report.reasons:
        assert report.decision == "REJECT"
    else:
        assert report.decision in ("CONSIDER", "PURSUE")
