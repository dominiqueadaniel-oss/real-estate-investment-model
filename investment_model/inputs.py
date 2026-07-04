"""Input data structures for a single property evaluation.

Every field maps to a line item named in the playbook's Financial Model,
Tax Model, and Purchase Criteria scorecards. A property is loaded from a
JSON file (see examples/) into a PropertyInput via `from_dict`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Category = Literal["LTR", "STR", "Appreciation"]


@dataclass
class Acquisition:
    purchase_price: float
    down_payment_pct: float
    interest_rate: float          # annual, decimal (e.g. 0.07)
    loan_term_years: int
    closing_costs: float = 0.0
    renovation_budget: float = 0.0
    furniture_budget: float = 0.0  # STR only


@dataclass
class Income:
    annual_rent_or_str_revenue: float
    other_income: float = 0.0     # laundry, parking, pet fees, etc.
    vacancy_rate: float = 0.0     # LTR: % of gross rent lost to vacancy


@dataclass
class Expenses:
    property_taxes: float = 0.0
    insurance: float = 0.0
    hoa: float = 0.0
    maintenance_repairs: float = 0.0
    capex_reserve: float = 0.0
    utilities: float = 0.0
    cleaning: float = 0.0          # STR
    management: float = 0.0
    supplies: float = 0.0
    software: float = 0.0
    marketing: float = 0.0
    licenses: float = 0.0

    def total(self) -> float:
        return sum(
            [
                self.property_taxes,
                self.insurance,
                self.hoa,
                self.maintenance_repairs,
                self.capex_reserve,
                self.utilities,
                self.cleaning,
                self.management,
                self.supplies,
                self.software,
                self.marketing,
                self.licenses,
            ]
        )


@dataclass
class GrowthAssumptions:
    rent_growth_rate: float
    expense_growth_rate: float
    appreciation_rate: float
    selling_cost_pct: float


@dataclass
class LTRMarketFactors:
    population_growth_pct: float
    job_growth_pct: float
    national_job_growth_benchmark_pct: float
    school_rating: float          # 1-10
    crime_score: float            # 1-10, lower = safer
    property_age_years: float


@dataclass
class STRMarketFactors:
    occupancy_pct: float
    adr_growth_pct: float
    str_regulations_stable: bool
    nearby_attractions_score: float   # 1-10
    seasonality_score: float          # 1-10, mid-range = moderate
    guest_rating_potential_score: float  # 1-10


@dataclass
class AppreciationFactors:
    population_growth_score: float
    employment_score: float
    corporate_investment_score: float
    infrastructure_score: float
    housing_supply_score: float
    median_income_growth_score: float
    migration_trend_score: float
    historical_appreciation_score: float


@dataclass
class MarketFrameworkScores:
    """1-10 scores for the Market Evaluation Framework (total /100)."""

    cash_flow_score: float
    appreciation_score: float
    taxes_score: float
    landlord_laws_score: float
    population_growth_score: float
    job_growth_score: float
    regulatory_stability_score: float
    natural_disaster_risk_score: float
    competition_score: float
    tourism_score: float | None = None  # only applicable to STR


@dataclass
class TaxAssumptions:
    land_value_pct: float = 0.20
    marginal_tax_rate: float = 0.32
    use_cost_segregation: bool = False
    cost_seg_reclass_pct_of_building: float | None = None  # falls back to playbook default
    bonus_depreciation_pct: float | None = None            # falls back to playbook default
    reps_or_material_participation: bool = False


@dataclass
class PropertyInput:
    name: str
    market: str
    category: Category
    acquisition: Acquisition
    income: Income
    expenses: Expenses
    growth: GrowthAssumptions
    market_framework: MarketFrameworkScores
    tax: TaxAssumptions = field(default_factory=TaxAssumptions)
    ltr_factors: LTRMarketFactors | None = None
    str_factors: STRMarketFactors | None = None
    appreciation_factors: AppreciationFactors | None = None

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "PropertyInput":
        return PropertyInput(
            name=d["name"],
            market=d["market"],
            category=d["category"],
            acquisition=Acquisition(**d["acquisition"]),
            income=Income(**d["income"]),
            expenses=Expenses(**d.get("expenses", {})),
            growth=GrowthAssumptions(**d["growth"]),
            market_framework=MarketFrameworkScores(**d["market_framework"]),
            tax=TaxAssumptions(**d.get("tax", {})),
            ltr_factors=LTRMarketFactors(**d["ltr_factors"]) if d.get("ltr_factors") else None,
            str_factors=STRMarketFactors(**d["str_factors"]) if d.get("str_factors") else None,
            appreciation_factors=(
                AppreciationFactors(**d["appreciation_factors"])
                if d.get("appreciation_factors")
                else None
            ),
        )
