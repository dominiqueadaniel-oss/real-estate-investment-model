import pytest

from investment_model.config import load_playbook
from investment_model.inputs import Acquisition, Expenses, TaxAssumptions
from investment_model.tax import (
    building_value,
    cost_seg_first_year_depreciation,
    evaluate_tax,
    straight_line_annual_depreciation,
)


@pytest.fixture
def playbook():
    return load_playbook()


@pytest.fixture
def acq():
    return Acquisition(
        purchase_price=500000,
        down_payment_pct=0.20,
        interest_rate=0.075,
        loan_term_years=30,
    )


@pytest.fixture
def expenses():
    return Expenses(property_taxes=2000, insurance=4500, maintenance_repairs=4000, supplies=1500)


def test_building_value_excludes_land():
    assert building_value(500000, 0.20) == 400000


def test_straight_line_depreciation():
    assert straight_line_annual_depreciation(400000, 27.5) == pytest.approx(14545.45, abs=0.5)


def test_cost_seg_first_year_exceeds_straight_line():
    sl = straight_line_annual_depreciation(400000, 27.5)
    accelerated = cost_seg_first_year_depreciation(400000, 27.5, reclass_pct=0.28, bonus_depreciation_pct=0.60)
    assert accelerated > sl


def test_evaluate_tax_without_cost_segregation(acq, expenses, playbook):
    tax = TaxAssumptions(land_value_pct=0.20, marginal_tax_rate=0.32, use_cost_segregation=False)
    result = evaluate_tax(acq, expenses, tax, playbook)
    assert result.used_cost_segregation is False
    assert result.first_year_depreciation == pytest.approx(result.annual_straight_line_depreciation)
    assert result.losses_offset_active_income is False
    assert len(result.caveats) >= 3


def test_evaluate_tax_with_cost_segregation_increases_first_year_savings(acq, expenses, playbook):
    base_tax = TaxAssumptions(land_value_pct=0.20, marginal_tax_rate=0.32, use_cost_segregation=False)
    seg_tax = TaxAssumptions(
        land_value_pct=0.20,
        marginal_tax_rate=0.32,
        use_cost_segregation=True,
        cost_seg_reclass_pct_of_building=0.28,
        bonus_depreciation_pct=0.60,
        reps_or_material_participation=True,
    )
    base_result = evaluate_tax(acq, expenses, base_tax, playbook)
    seg_result = evaluate_tax(acq, expenses, seg_tax, playbook)
    assert seg_result.estimated_first_year_tax_savings > base_result.estimated_first_year_tax_savings
    assert seg_result.losses_offset_active_income is True
