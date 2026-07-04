import pytest

from investment_model.config import load_playbook
from investment_model.portfolio import PortfolioEntry, evaluate_allocation


@pytest.fixture
def playbook():
    return load_playbook()


def test_allocation_matches_target_when_balanced(playbook):
    entries = [
        PortfolioEntry("STR A", "STR", 400000),
        PortfolioEntry("LTR A", "LTR", 400000),
        PortfolioEntry("Appreciation A", "Appreciation", 200000),
    ]
    result = evaluate_allocation(entries, playbook)
    assert result.current_pct["STR"] == pytest.approx(0.40)
    assert result.current_pct["LTR"] == pytest.approx(0.40)
    assert result.current_pct["Appreciation"] == pytest.approx(0.20)
    assert result.drift_pct["STR"] == pytest.approx(0.0)


def test_allocation_flags_overweight_category(playbook):
    entries = [PortfolioEntry("STR A", "STR", 500000), PortfolioEntry("LTR A", "LTR", 350000)]
    result = evaluate_allocation(entries, playbook)
    assert result.drift_pct["STR"] > 0
    assert result.drift_pct["Appreciation"] < 0  # zero allocation vs 20% target


def test_empty_portfolio_does_not_divide_by_zero(playbook):
    result = evaluate_allocation([], playbook)
    assert result.total_value == 0
    assert all(v == 0.0 for v in result.current_pct.values())
