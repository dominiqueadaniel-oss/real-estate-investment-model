"""Assembles the Financial Model, Tax Model, scorecards, Market Evaluation
Framework, and Investment Philosophy check into one underwriting report,
and renders it as Markdown (the "standardized underwriting workbook" the
playbook's closing Observations section recommends).
"""
from __future__ import annotations

from dataclasses import dataclass

from investment_model.financial import FinancialResults, evaluate_financials
from investment_model.inputs import PropertyInput
from investment_model.scoring import (
    AppreciationScoreResult,
    MarketFrameworkResult,
    PhilosophyCheck,
    ScorecardResult,
    appreciation_scorecard,
    ltr_scorecard,
    market_framework_score,
    philosophy_check,
    str_scorecard,
)
from investment_model.tax import TaxResults, evaluate_tax


@dataclass
class EvaluationReport:
    property: PropertyInput
    financials: FinancialResults
    tax: TaxResults
    scorecard: ScorecardResult | None
    appreciation: AppreciationScoreResult | None
    market: MarketFrameworkResult
    philosophy: PhilosophyCheck
    decision: str
    reasons: list[str]


def evaluate_property(prop: PropertyInput, playbook: dict) -> EvaluationReport:
    financials = evaluate_financials(prop.income, prop.expenses, prop.acquisition, prop.growth)
    tax = evaluate_tax(prop.acquisition, prop.expenses, prop.tax, playbook)
    philosophy = philosophy_check(financials, tax, prop.growth, playbook)
    market = market_framework_score(prop.market_framework, prop.category, playbook)

    scorecard = None
    appreciation = None
    reasons: list[str] = []

    if prop.category == "LTR":
        if prop.ltr_factors is None:
            raise ValueError("LTR property requires ltr_factors")
        scorecard = ltr_scorecard(financials, prop.ltr_factors, playbook)
        if scorecard.reject:
            threshold = playbook["long_term_rental_scorecard"]["reject_at_failures"]
            reasons.append(f"LTR scorecard failed {scorecard.failures} criteria (reject at {threshold}+)")
    elif prop.category == "STR":
        if prop.str_factors is None:
            raise ValueError("STR property requires str_factors")
        scorecard = str_scorecard(financials, prop.str_factors, prop.acquisition.purchase_price, playbook)
        if scorecard.reject:
            threshold = playbook["short_term_rental_scorecard"]["reject_at_failures"]
            reasons.append(f"STR scorecard failed {scorecard.failures} criteria (reject at {threshold}+)")
    elif prop.category == "Appreciation":
        if prop.appreciation_factors is None:
            raise ValueError("Appreciation property requires appreciation_factors")
        appreciation = appreciation_scorecard(prop.appreciation_factors)
    else:
        raise ValueError(f"Unknown category: {prop.category}")

    if not philosophy.meets_minimum:
        p = playbook["philosophy"]
        reasons.append(
            f"Investment philosophy check failed: only {philosophy.criteria_met}/3 criteria met "
            f"(need >= {p['min_criteria_met']})"
        )
    if not market.pursue:
        reasons.append(
            f"Market score {market.normalized_out_of_100:.0f}/100 below pursue threshold "
            f"{playbook['market_framework']['pursue_threshold']}"
        )

    if reasons:
        decision = "REJECT"
    else:
        borderline = (
            (scorecard is not None and scorecard.failures > 0)
            or (market.normalized_out_of_100 - playbook["market_framework"]["pursue_threshold"] < 10)
            or (philosophy.criteria_met == playbook["philosophy"]["min_criteria_met"])
        )
        decision = "CONSIDER" if borderline else "PURSUE"

    return EvaluationReport(
        property=prop,
        financials=financials,
        tax=tax,
        scorecard=scorecard,
        appreciation=appreciation,
        market=market,
        philosophy=philosophy,
        decision=decision,
        reasons=reasons,
    )


def _fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def render_markdown(report: EvaluationReport) -> str:
    p = report.property
    f = report.financials
    t = report.tax
    lines = []
    lines.append(f"# Underwriting Report: {p.name}")
    lines.append(f"*{p.market} -- {p.category}*\n")
    lines.append(f"## Decision: **{report.decision}**")
    if report.reasons:
        lines.append("Reasons:")
        for r in report.reasons:
            lines.append(f"- {r}")
    lines.append("")

    lines.append("## Financial Model")
    lines.append(f"- Loan amount: {_fmt_money(f.loan_amount)}  |  Down payment: {_fmt_money(f.down_payment)}")
    lines.append(f"- Total cash invested: {_fmt_money(f.total_cash_invested)}")
    lines.append(f"- Monthly mortgage payment: {_fmt_money(f.monthly_mortgage_payment)}")
    lines.append(f"- Effective gross income: {_fmt_money(f.effective_gross_income)}/yr")
    lines.append(f"- NOI: {_fmt_money(f.noi)}/yr")
    lines.append(f"- Cap rate: {f.cap_rate:.2%}")
    lines.append(f"- DSCR: {f.dscr:.2f}")
    lines.append(f"- Annual cash flow: {_fmt_money(f.annual_cash_flow)}")
    lines.append(f"- Cash-on-cash return: {f.cash_on_cash_return:.2%}")
    lines.append(f"- Equity at year 5 / year 10: {_fmt_money(f.equity_5yr)} / {_fmt_money(f.equity_10yr)}")
    irr5 = f"{f.irr_5yr:.1%}" if f.irr_5yr is not None else "n/a"
    irr10 = f"{f.irr_10yr:.1%}" if f.irr_10yr is not None else "n/a"
    lines.append(f"- IRR (5yr / 10yr): {irr5} / {irr10}\n")

    lines.append("## Tax Model (estimate -- confirm with CPA)")
    lines.append(f"- Building value (post land allocation): {_fmt_money(t.building_value)}")
    lines.append(f"- Straight-line annual depreciation: {_fmt_money(t.annual_straight_line_depreciation)}")
    seg = "yes" if t.used_cost_segregation else "no"
    lines.append(f"- First-year depreciation (cost segregation applied: {seg}): {_fmt_money(t.first_year_depreciation)}")
    lines.append(f"- Estimated first-year tax savings: {_fmt_money(t.estimated_first_year_tax_savings)}")
    offset = "yes (REPS / material participation claimed)" if t.losses_offset_active_income else "no -- passive losses only unless REPS/material participation is documented"
    lines.append(f"- Can offset active/W-2 income: {offset}")
    lines.append("- Caveats:")
    for c in t.caveats:
        lines.append(f"  - {c}")
    lines.append("")

    if report.scorecard:
        sc = report.scorecard
        lines.append(f"## {sc.category} Purchase Criteria Scorecard ({sc.failures} failure(s))")
        for c in sc.criteria:
            mark = "PASS" if c.passed else "FAIL"
            lines.append(f"- [{mark}] {c.name}: target {c.target}, actual {c.actual}")
        lines.append("")

    if report.appreciation:
        a = report.appreciation
        lines.append(f"## Appreciation Scorecard (avg {a.average_score:.1f}/10)")
        for name, score in a.factor_scores.items():
            lines.append(f"- {name}: {score}/10")
        lines.append("")

    m = report.market
    lines.append(f"## Market Evaluation Framework: {m.total:.0f}/{m.out_of:.0f} ({m.normalized_out_of_100:.0f}/100)")
    for name, score in m.scores.items():
        lines.append(f"- {name}: {score}/10")
    lines.append("")

    ph = report.philosophy
    lines.append("## Investment Philosophy Check (need >=2 of 3)")
    lines.append(f"- Appreciates: {'yes' if ph.appreciates else 'no'}")
    lines.append(f"- Produces cash flow: {'yes' if ph.produces_cash_flow else 'no'}")
    lines.append(f"- Creates tax benefits: {'yes' if ph.creates_tax_benefits else 'no'}")
    lines.append(f"- Criteria met: {ph.criteria_met}/3")

    return "\n".join(lines)
