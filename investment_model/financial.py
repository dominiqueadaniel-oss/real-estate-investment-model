"""Financial Model calculations (playbook: Acquisition / Income / Expenses /
Financing / Returns).

Assumptions, stated once here rather than scattered through the code:
  - NOI follows the playbook's own expense list, which includes capital
    expenditures as a line item under "Expenses" -- so unlike a strict
    appraisal-style NOI, the capex reserve IS subtracted before NOI here.
  - Cap rate and cash-on-cash both use total price / total cash invested,
    not appraised value, since underwriting happens pre-purchase.
  - IRR cash flows are: -total cash invested at year 0, annual pre-tax cash
    flow each year, plus net sale proceeds added to the final year.
"""
from __future__ import annotations

from dataclasses import dataclass

from investment_model.inputs import Acquisition, Expenses, GrowthAssumptions, Income


def loan_amount(acq: Acquisition) -> float:
    return acq.purchase_price * (1 - acq.down_payment_pct)


def down_payment(acq: Acquisition) -> float:
    return acq.purchase_price * acq.down_payment_pct


def total_cash_invested(acq: Acquisition) -> float:
    return down_payment(acq) + acq.closing_costs + acq.renovation_budget + acq.furniture_budget


def monthly_mortgage_payment(principal: float, annual_rate: float, term_years: int) -> float:
    n = term_years * 12
    if annual_rate == 0:
        return principal / n
    r = annual_rate / 12
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def annual_debt_service(acq: Acquisition) -> float:
    return monthly_mortgage_payment(loan_amount(acq), acq.interest_rate, acq.loan_term_years) * 12


def remaining_balance(principal: float, annual_rate: float, term_years: int, months_elapsed: int) -> float:
    n = term_years * 12
    if annual_rate == 0:
        return max(principal - principal / n * months_elapsed, 0.0)
    r = annual_rate / 12
    return principal * ((1 + r) ** n - (1 + r) ** months_elapsed) / ((1 + r) ** n - 1)


def first_year_interest_paid(acq: Acquisition) -> float:
    principal = loan_amount(acq)
    payment = monthly_mortgage_payment(principal, acq.interest_rate, acq.loan_term_years) * 12
    principal_paid = principal - remaining_balance(principal, acq.interest_rate, acq.loan_term_years, 12)
    return payment - principal_paid


def effective_gross_income(income: Income) -> float:
    """Annual rent/STR revenue net of vacancy, plus other income."""
    return income.annual_rent_or_str_revenue * (1 - income.vacancy_rate) + income.other_income


def noi(income: Income, expenses: Expenses) -> float:
    return effective_gross_income(income) - expenses.total()


def cap_rate(income: Income, expenses: Expenses, acq: Acquisition) -> float:
    return noi(income, expenses) / acq.purchase_price


def dscr(income: Income, expenses: Expenses, acq: Acquisition) -> float:
    ads = annual_debt_service(acq)
    if ads == 0:
        return float("inf")
    return noi(income, expenses) / ads


def annual_cash_flow(income: Income, expenses: Expenses, acq: Acquisition) -> float:
    return noi(income, expenses) - annual_debt_service(acq)


def cash_on_cash_return(income: Income, expenses: Expenses, acq: Acquisition) -> float:
    invested = total_cash_invested(acq)
    if invested == 0:
        return float("inf")
    return annual_cash_flow(income, expenses, acq) / invested


def property_value_at_year(acq: Acquisition, growth: GrowthAssumptions, year: int) -> float:
    return acq.purchase_price * (1 + growth.appreciation_rate) ** year


def equity_at_year(acq: Acquisition, growth: GrowthAssumptions, year: int) -> float:
    balance = remaining_balance(loan_amount(acq), acq.interest_rate, acq.loan_term_years, year * 12)
    return property_value_at_year(acq, growth, year) - balance


def net_sale_proceeds_at_year(acq: Acquisition, growth: GrowthAssumptions, year: int) -> float:
    value = property_value_at_year(acq, growth, year)
    balance = remaining_balance(loan_amount(acq), acq.interest_rate, acq.loan_term_years, year * 12)
    return value * (1 - growth.selling_cost_pct) - balance


def project_cash_flows(
    income: Income, expenses: Expenses, acq: Acquisition, growth: GrowthAssumptions, years: int
) -> list[float]:
    """Annual pre-tax cash flow for each of `years`, growing income/expenses
    at their respective assumed rates. Debt service is fixed (fixed-rate loan)."""
    ads = annual_debt_service(acq)
    flows = []
    for y in range(1, years + 1):
        egi = effective_gross_income(income) * (1 + growth.rent_growth_rate) ** (y - 1)
        exp = expenses.total() * (1 + growth.expense_growth_rate) ** (y - 1)
        flows.append(egi - exp - ads)
    return flows


def irr(cash_flows: list[float]) -> float | None:
    """cash_flows[0] is the initial outlay (negative); returns the periodic
    IRR via bisection. Returns None if no sign change / cannot solve."""
    if not any(cf > 0 for cf in cash_flows) or not any(cf < 0 for cf in cash_flows):
        return None

    def npv(rate: float) -> float:
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))

    low, high = -0.99, 10.0
    npv_low, npv_high = npv(low), npv(high)
    if npv_low * npv_high > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        npv_mid = npv(mid)
        if abs(npv_mid) < 1e-6:
            return mid
        if npv_low * npv_mid < 0:
            high, npv_high = mid, npv_mid
        else:
            low, npv_low = mid, npv_mid
    return (low + high) / 2


def irr_over_holding_period(
    income: Income, expenses: Expenses, acq: Acquisition, growth: GrowthAssumptions, years: int
) -> float | None:
    flows = project_cash_flows(income, expenses, acq, growth, years)
    flows[-1] += net_sale_proceeds_at_year(acq, growth, years)
    cash_flows = [-total_cash_invested(acq)] + flows
    return irr(cash_flows)


@dataclass
class FinancialResults:
    loan_amount: float
    down_payment: float
    total_cash_invested: float
    monthly_mortgage_payment: float
    annual_debt_service: float
    effective_gross_income: float
    noi: float
    cap_rate: float
    dscr: float
    annual_cash_flow: float
    cash_on_cash_return: float
    equity_5yr: float
    equity_10yr: float
    irr_5yr: float | None
    irr_10yr: float | None


def evaluate_financials(income: Income, expenses: Expenses, acq: Acquisition, growth: GrowthAssumptions) -> FinancialResults:
    return FinancialResults(
        loan_amount=loan_amount(acq),
        down_payment=down_payment(acq),
        total_cash_invested=total_cash_invested(acq),
        monthly_mortgage_payment=monthly_mortgage_payment(loan_amount(acq), acq.interest_rate, acq.loan_term_years),
        annual_debt_service=annual_debt_service(acq),
        effective_gross_income=effective_gross_income(income),
        noi=noi(income, expenses),
        cap_rate=cap_rate(income, expenses, acq),
        dscr=dscr(income, expenses, acq),
        annual_cash_flow=annual_cash_flow(income, expenses, acq),
        cash_on_cash_return=cash_on_cash_return(income, expenses, acq),
        equity_5yr=equity_at_year(acq, growth, 5),
        equity_10yr=equity_at_year(acq, growth, 10),
        irr_5yr=irr_over_holding_period(income, expenses, acq, growth, 5),
        irr_10yr=irr_over_holding_period(income, expenses, acq, growth, 10),
    )
