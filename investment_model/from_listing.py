"""Builds a full PropertyInput dict from a partial, flat dict of fields
pulled off a real estate listing (see .claude/skills/evaluate-listing).

A listing page (Zillow, Redfin, Realtor.com, an MLS sheet, etc.) only ever
gives you: price, address/market, beds/baths/sqft, year built, HOA dues,
tax history, and sometimes a rent estimate. It never gives you the
playbook's subjective judgment fields -- school ratings, crime, population/
job growth, STR occupancy, market framework scores, financing terms, or
tax elections. Rather than silently inventing numbers for those and
presenting them as real, every field not supplied in `raw` is filled with
a documented placeholder and returned in `assumptions` so the report can
show, in one place, exactly what still needs to be verified before this is
relied on.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class Assumption:
    field: str
    value: Any
    reason: str


class MissingRequiredField(Exception):
    pass


REQUIRED_FIELDS = ["name", "market", "category", "purchase_price", "annual_rent_or_str_revenue"]


def _get_or_default(raw: dict, key: str, default: Any, reason: str, assumptions: list[Assumption]) -> Any:
    if key in raw and raw[key] is not None:
        return raw[key]
    assumptions.append(Assumption(key, default, reason))
    return default


def build_property_input(raw: dict, playbook: dict) -> tuple[dict, list[Assumption]]:
    """Returns (full nested property dict ready for PropertyInput.from_dict, assumptions)."""
    missing = [f for f in REQUIRED_FIELDS if not raw.get(f)]
    if missing:
        raise MissingRequiredField(
            f"Missing required field(s) that cannot be reasonably defaulted: {', '.join(missing)}"
        )

    category = raw["category"]
    if category not in ("LTR", "STR", "Appreciation"):
        raise MissingRequiredField(f"category must be LTR, STR, or Appreciation, got {category!r}")

    price = float(raw["purchase_price"])
    fin_defaults = playbook["financial_defaults"]
    a: list[Assumption] = []

    acquisition = {
        "purchase_price": price,
        "down_payment_pct": _get_or_default(raw, "down_payment_pct", 0.20, "typical investor down payment", a),
        "interest_rate": _get_or_default(raw, "interest_rate", 0.07, "placeholder current-market rate -- confirm with lender", a),
        "loan_term_years": _get_or_default(raw, "loan_term_years", 30, "standard term", a),
        "closing_costs": _get_or_default(raw, "closing_costs", round(price * 0.02, 2), "estimated at 2% of purchase price", a),
        "renovation_budget": _get_or_default(raw, "renovation_budget", 0, "none assumed", a),
        "furniture_budget": _get_or_default(
            raw, "furniture_budget", 15000 if category == "STR" else 0,
            "typical STR furnishing budget" if category == "STR" else "not applicable", a,
        ),
    }

    vacancy_default = 0.0 if category == "STR" else 0.06
    income = {
        "annual_rent_or_str_revenue": float(raw["annual_rent_or_str_revenue"]),
        "other_income": _get_or_default(raw, "other_income", 0, "none assumed", a),
        "vacancy_rate": _get_or_default(raw, "vacancy_rate", vacancy_default, "playbook scorecard target used as placeholder", a),
    }

    management_default = round(income["annual_rent_or_str_revenue"] * (0.20 if category == "STR" else 0.08), 2)
    expenses = {
        "property_taxes": _get_or_default(raw, "property_taxes", round(price * 0.011, 2), "estimated at 1.1% of purchase price/yr -- confirm from listing tax history", a),
        "insurance": _get_or_default(raw, "insurance", round(price * (0.009 if category == "STR" else 0.0035), 2), "estimated from purchase price -- get a real quote", a),
        "hoa": _get_or_default(raw, "hoa", 0, "not shown on listing", a),
        "maintenance_repairs": _get_or_default(raw, "maintenance_repairs", round(price * 0.01, 2), "estimated at 1% of purchase price/yr", a),
        "capex_reserve": _get_or_default(raw, "capex_reserve", round(price * 0.01, 2), "estimated at 1% of purchase price/yr", a),
        "utilities": _get_or_default(raw, "utilities", 3000 if category == "STR" else 0, "STR: owner-paid estimate; LTR: assumed tenant-paid", a),
        "cleaning": _get_or_default(raw, "cleaning", round(income["annual_rent_or_str_revenue"] * 0.10, 2) if category == "STR" else 0, "estimated at 10% of STR revenue", a),
        "management": _get_or_default(raw, "management", management_default, f"estimated at {'20%' if category == 'STR' else '8%'} of gross revenue", a),
        "supplies": _get_or_default(raw, "supplies", 200, "small flat estimate", a),
        "software": _get_or_default(raw, "software", 150, "small flat estimate", a),
        "marketing": _get_or_default(raw, "marketing", 0, "none assumed", a),
        "licenses": _get_or_default(raw, "licenses", 0, "none assumed", a),
    }

    growth = {
        "rent_growth_rate": _get_or_default(raw, "rent_growth_rate", fin_defaults["rent_growth_rate"], "playbook default", a),
        "expense_growth_rate": _get_or_default(raw, "expense_growth_rate", fin_defaults["expense_growth_rate"], "playbook default", a),
        "appreciation_rate": _get_or_default(raw, "appreciation_rate", fin_defaults["appreciation_rate"], "playbook default", a),
        "selling_cost_pct": _get_or_default(raw, "selling_cost_pct", fin_defaults["selling_cost_pct"], "playbook default", a),
    }

    market_framework = {
        "cash_flow_score": _get_or_default(raw, "cash_flow_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "appreciation_score": _get_or_default(raw, "appreciation_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "taxes_score": _get_or_default(raw, "taxes_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "landlord_laws_score": _get_or_default(raw, "landlord_laws_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "population_growth_score": _get_or_default(raw, "population_growth_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "job_growth_score": _get_or_default(raw, "job_growth_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "regulatory_stability_score": _get_or_default(raw, "regulatory_stability_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "natural_disaster_risk_score": _get_or_default(raw, "natural_disaster_risk_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        "competition_score": _get_or_default(raw, "competition_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
    }
    if category == "STR":
        market_framework["tourism_score"] = _get_or_default(raw, "tourism_score", 5, "NEEDS RESEARCH -- neutral placeholder", a)

    tax = {
        "land_value_pct": _get_or_default(raw, "land_value_pct", playbook["tax_model"]["default_land_value_pct"], "playbook default", a),
        "marginal_tax_rate": _get_or_default(raw, "marginal_tax_rate", 0.32, "placeholder combined marginal rate -- confirm with CPA", a),
        "use_cost_segregation": _get_or_default(raw, "use_cost_segregation", False, "not requested", a),
        "reps_or_material_participation": _get_or_default(raw, "reps_or_material_participation", False, "not established -- see tax model caveats", a),
    }

    prop: dict[str, Any] = {
        "name": raw["name"],
        "market": raw["market"],
        "category": category,
        "acquisition": acquisition,
        "income": income,
        "expenses": expenses,
        "growth": growth,
        "market_framework": market_framework,
        "tax": tax,
    }

    property_age_years = raw.get("property_age_years")
    if property_age_years is None and raw.get("year_built"):
        property_age_years = date.today().year - int(raw["year_built"])
        a.append(Assumption("property_age_years", property_age_years, f"derived from year_built {raw['year_built']}"))
    if category == "LTR":
        prop["ltr_factors"] = {
            "population_growth_pct": _get_or_default(raw, "population_growth_pct", 0.0, "NEEDS RESEARCH -- neutral placeholder", a),
            "job_growth_pct": _get_or_default(raw, "job_growth_pct", 0.0, "NEEDS RESEARCH -- neutral placeholder", a),
            "national_job_growth_benchmark_pct": _get_or_default(
                raw, "national_job_growth_benchmark_pct", playbook["tax_model"]["national_job_growth_benchmark_pct"], "playbook default", a
            ),
            "school_rating": _get_or_default(raw, "school_rating", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "crime_score": _get_or_default(raw, "crime_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "property_age_years": property_age_years if property_age_years is not None else _get_or_default(raw, "property_age_years", 20, "unknown -- neutral placeholder", a),
        }
    elif category == "STR":
        prop["str_factors"] = {
            "occupancy_pct": _get_or_default(raw, "occupancy_pct", 0.55, "NEEDS RESEARCH -- below playbook target, conservative placeholder", a),
            "adr_growth_pct": _get_or_default(raw, "adr_growth_pct", 0.0, "NEEDS RESEARCH -- neutral placeholder", a),
            "str_regulations_stable": _get_or_default(raw, "str_regulations_stable", False, "NOT VERIFIED -- confirm local STR ordinance status", a),
            "nearby_attractions_score": _get_or_default(raw, "nearby_attractions_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "seasonality_score": _get_or_default(raw, "seasonality_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "guest_rating_potential_score": _get_or_default(raw, "guest_rating_potential_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        }
    else:  # Appreciation
        prop["appreciation_factors"] = {
            "population_growth_score": _get_or_default(raw, "population_growth_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "employment_score": _get_or_default(raw, "employment_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "corporate_investment_score": _get_or_default(raw, "corporate_investment_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "infrastructure_score": _get_or_default(raw, "infrastructure_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "housing_supply_score": _get_or_default(raw, "housing_supply_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "median_income_growth_score": _get_or_default(raw, "median_income_growth_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "migration_trend_score": _get_or_default(raw, "migration_trend_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
            "historical_appreciation_score": _get_or_default(raw, "historical_appreciation_score", 5, "NEEDS RESEARCH -- neutral placeholder", a),
        }

    return prop, a
