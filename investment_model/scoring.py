"""Purchase Criteria scorecards, Market Evaluation Framework, and the
Investment Philosophy ("at least 2 of 3") check -- all driven by
playbook.yaml so thresholds stay in one editable place.
"""
from __future__ import annotations

from dataclasses import dataclass

from investment_model.financial import FinancialResults
from investment_model.inputs import (
    AppreciationFactors,
    GrowthAssumptions,
    LTRMarketFactors,
    MarketFrameworkScores,
    STRMarketFactors,
)
from investment_model.tax import TaxResults


@dataclass
class Criterion:
    name: str
    target: str
    actual: str
    passed: bool


@dataclass
class ScorecardResult:
    category: str
    criteria: list[Criterion]
    failures: int
    reject: bool


def ltr_scorecard(
    financials: FinancialResults, factors: LTRMarketFactors, playbook: dict
) -> ScorecardResult:
    t = playbook["long_term_rental_scorecard"]["targets"]
    criteria = [
        Criterion(
            "Cash-on-cash return",
            f"> {t['cash_on_cash_return_min']:.0%}",
            f"{financials.cash_on_cash_return:.1%}",
            financials.cash_on_cash_return > t["cash_on_cash_return_min"],
        ),
        Criterion(
            "Cap rate",
            f"> {t['cap_rate_min']:.0%}",
            f"{financials.cap_rate:.1%}",
            financials.cap_rate > t["cap_rate_min"],
        ),
        Criterion(
            "DSCR",
            f"> {t['dscr_min']}",
            f"{financials.dscr:.2f}",
            financials.dscr > t["dscr_min"],
        ),
        Criterion(
            "Population growth",
            "positive",
            f"{factors.population_growth_pct:.1%}",
            factors.population_growth_pct > 0,
        ),
        Criterion(
            "Job growth",
            "above national average",
            f"{factors.job_growth_pct:.1%} vs {factors.national_job_growth_benchmark_pct:.1%}",
            factors.job_growth_pct > factors.national_job_growth_benchmark_pct,
        ),
        Criterion(
            "School ratings",
            f">= {t['school_rating_min']}/10 (good)",
            f"{factors.school_rating}/10",
            factors.school_rating >= t["school_rating_min"],
        ),
        Criterion(
            "Crime",
            f"<= {t['crime_score_max']}/10 (low)",
            f"{factors.crime_score}/10",
            factors.crime_score <= t["crime_score_max"],
        ),
        Criterion(
            "Property age",
            f"< {t['property_age_years_max']} years preferred",
            f"{factors.property_age_years} years",
            factors.property_age_years < t["property_age_years_max"],
        ),
    ]
    failures = sum(1 for c in criteria if not c.passed)
    reject = failures >= playbook["long_term_rental_scorecard"]["reject_at_failures"]
    return ScorecardResult("LTR", criteria, failures, reject)


def str_scorecard(
    financials: FinancialResults, factors: STRMarketFactors, purchase_price: float, playbook: dict
) -> ScorecardResult:
    t = playbook["short_term_rental_scorecard"]["targets"]
    revenue_multiple = (financials.effective_gross_income / purchase_price) if purchase_price else 0
    lo, hi = t["seasonality_score_range"]
    criteria = [
        Criterion(
            "Occupancy",
            f"> {t['occupancy_pct_min']:.0%} annually",
            f"{factors.occupancy_pct:.1%}",
            factors.occupancy_pct > t["occupancy_pct_min"],
        ),
        Criterion(
            "ADR growth",
            "increasing",
            f"{factors.adr_growth_pct:+.1%}",
            factors.adr_growth_pct > 0,
        ),
        Criterion(
            "Revenue multiple",
            f"> {t['revenue_multiple_min']:.0%} of acquisition cost",
            f"{revenue_multiple:.1%}",
            revenue_multiple > t["revenue_multiple_min"],
        ),
        Criterion(
            "Local STR regulations",
            "stable",
            "stable" if factors.str_regulations_stable else "unstable",
            factors.str_regulations_stable == t["str_regulations_stable"],
        ),
        Criterion(
            "Nearby attractions",
            f">= {t['nearby_attractions_score_min']}/10 (significant)",
            f"{factors.nearby_attractions_score}/10",
            factors.nearby_attractions_score >= t["nearby_attractions_score_min"],
        ),
        Criterion(
            "Seasonality",
            f"{lo}-{hi}/10 (moderate)",
            f"{factors.seasonality_score}/10",
            lo <= factors.seasonality_score <= hi,
        ),
        Criterion(
            "Guest rating potential",
            f">= {t['guest_rating_potential_score_min']}/10 (high)",
            f"{factors.guest_rating_potential_score}/10",
            factors.guest_rating_potential_score >= t["guest_rating_potential_score_min"],
        ),
    ]
    failures = sum(1 for c in criteria if not c.passed)
    reject = failures >= playbook["short_term_rental_scorecard"]["reject_at_failures"]
    return ScorecardResult("STR", criteria, failures, reject)


@dataclass
class AppreciationScoreResult:
    factor_scores: dict[str, float]
    average_score: float  # out of 10


def appreciation_scorecard(factors: AppreciationFactors) -> AppreciationScoreResult:
    scores = {
        "Population growth": factors.population_growth_score,
        "Employment": factors.employment_score,
        "Corporate investment": factors.corporate_investment_score,
        "Infrastructure": factors.infrastructure_score,
        "Housing supply": factors.housing_supply_score,
        "Median income growth": factors.median_income_growth_score,
        "Migration trends": factors.migration_trend_score,
        "Historical appreciation": factors.historical_appreciation_score,
    }
    return AppreciationScoreResult(scores, sum(scores.values()) / len(scores))


@dataclass
class MarketFrameworkResult:
    scores: dict[str, float]
    total: float
    out_of: float
    normalized_out_of_100: float
    pursue: bool


def market_framework_score(
    mf: MarketFrameworkScores, category: str, playbook: dict
) -> MarketFrameworkResult:
    fields = {
        "Cash flow": mf.cash_flow_score,
        "Appreciation": mf.appreciation_score,
        "Taxes": mf.taxes_score,
        "Landlord laws": mf.landlord_laws_score,
        "Population growth": mf.population_growth_score,
        "Job growth": mf.job_growth_score,
        "Regulatory stability": mf.regulatory_stability_score,
        "Natural disaster risk": mf.natural_disaster_risk_score,
        "Competition": mf.competition_score,
    }
    out_of = len(fields) * 10
    if category == "STR" and mf.tourism_score is not None:
        fields["Tourism"] = mf.tourism_score
        out_of += 10
    total = sum(fields.values())
    normalized = total / out_of * 100
    threshold = playbook["market_framework"]["pursue_threshold"]
    return MarketFrameworkResult(fields, total, out_of, normalized, normalized >= threshold)


@dataclass
class PhilosophyCheck:
    appreciates: bool
    produces_cash_flow: bool
    creates_tax_benefits: bool
    criteria_met: int
    meets_minimum: bool


def philosophy_check(
    financials: FinancialResults,
    tax_results: TaxResults,
    growth: GrowthAssumptions,
    playbook: dict,
) -> PhilosophyCheck:
    p = playbook["philosophy"]
    appreciates = growth.appreciation_rate > p["appreciation_min_annual_pct"]
    cash_flow = financials.annual_cash_flow > p["cash_flow_min_annual"]
    tax_benefit = tax_results.estimated_first_year_tax_savings > p["tax_benefit_min_annual_savings"]
    met = sum([appreciates, cash_flow, tax_benefit])
    return PhilosophyCheck(
        appreciates, cash_flow, tax_benefit, met, met >= p["min_criteria_met"]
    )
