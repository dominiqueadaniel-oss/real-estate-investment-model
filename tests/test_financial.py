import pytest

from investment_model import financial
from investment_model.inputs import Acquisition, Expenses, GrowthAssumptions, Income


@pytest.fixture
def acq():
    return Acquisition(
        purchase_price=300000,
        down_payment_pct=0.20,
        interest_rate=0.06,
        loan_term_years=30,
        closing_costs=5000,
        renovation_budget=0,
        furniture_budget=0,
    )


@pytest.fixture
def income():
    return Income(annual_rent_or_str_revenue=24000, other_income=0, vacancy_rate=0.05)


@pytest.fixture
def expenses():
    return Expenses(property_taxes=3000, insurance=1200, maintenance_repairs=1200, capex_reserve=1200, management=1920)


@pytest.fixture
def growth():
    return GrowthAssumptions(rent_growth_rate=0.03, expense_growth_rate=0.03, appreciation_rate=0.03, selling_cost_pct=0.07)


def test_loan_amount_and_down_payment(acq):
    assert financial.loan_amount(acq) == 240000
    assert financial.down_payment(acq) == 60000


def test_total_cash_invested(acq):
    assert financial.total_cash_invested(acq) == 65000


def test_monthly_mortgage_payment_known_value():
    # $240,000 loan, 6% annual, 30yr -> ~$1,439/mo (standard amortization formula)
    payment = financial.monthly_mortgage_payment(240000, 0.06, 30)
    assert payment == pytest.approx(1439.09, abs=0.5)


def test_zero_interest_mortgage():
    payment = financial.monthly_mortgage_payment(120000, 0.0, 10)
    assert payment == pytest.approx(1000.0)


def test_remaining_balance_decreases_over_time():
    principal = 240000
    bal_0 = financial.remaining_balance(principal, 0.06, 30, 0)
    bal_60 = financial.remaining_balance(principal, 0.06, 30, 60)
    bal_360 = financial.remaining_balance(principal, 0.06, 30, 360)
    assert bal_0 == pytest.approx(principal)
    assert bal_60 < bal_0
    assert bal_360 == pytest.approx(0, abs=1.0)


def test_effective_gross_income(income):
    assert financial.effective_gross_income(income) == pytest.approx(24000 * 0.95)


def test_noi_and_cap_rate(income, expenses, acq):
    n = financial.noi(income, expenses)
    assert n == pytest.approx(financial.effective_gross_income(income) - expenses.total())
    cr = financial.cap_rate(income, expenses, acq)
    assert cr == pytest.approx(n / acq.purchase_price)


def test_dscr(income, expenses, acq):
    result = financial.dscr(income, expenses, acq)
    ads = financial.annual_debt_service(acq)
    assert result == pytest.approx(financial.noi(income, expenses) / ads)


def test_cash_on_cash_return(income, expenses, acq):
    coc = financial.cash_on_cash_return(income, expenses, acq)
    expected = financial.annual_cash_flow(income, expenses, acq) / financial.total_cash_invested(acq)
    assert coc == pytest.approx(expected)


def test_equity_grows_with_appreciation_and_paydown(acq, growth):
    e5 = financial.equity_at_year(acq, growth, 5)
    e10 = financial.equity_at_year(acq, growth, 10)
    assert e10 > e5 > financial.down_payment(acq)


def test_irr_over_holding_period_returns_reasonable_value(income, expenses, acq, growth):
    result = financial.irr_over_holding_period(income, expenses, acq, growth, 5)
    assert result is not None
    assert -0.5 < result < 1.0


def test_irr_returns_none_without_sign_change():
    # all-negative cash flows -> no solvable IRR
    assert financial.irr([-100, -50, -20]) is None
