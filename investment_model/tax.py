"""Tax Model estimates (playbook: Tax Model + "Key Caveats on the STR Tax
Strategy" sections).

This produces an estimate, not tax advice -- every output should be reviewed
with a CPA, which is exactly what the source document itself says. The
caveats below are carried into the report verbatim so the numbers are never
shown without their conditions attached:

  1. STR "material participation" (average stay <=7 days, or <=30 days with
     substantial services) must be established and documented; buying an STR
     does not by itself create a W-2 income offset.
  2. A cost-segregation first-year deduction is plausible but depends on
     construction type, land/improvement allocation, the depreciation rules
     in effect when placed in service, and the engineering study's findings.
  3. Real Estate Professional Status (REPS) must be satisfied every tax year
     individually -- it is not a one-time threshold.
"""
from __future__ import annotations

from dataclasses import dataclass

from investment_model.financial import first_year_interest_paid
from investment_model.inputs import Acquisition, Expenses, TaxAssumptions

CAVEATS = [
    "STR material participation (avg stay <=7 days, or <=30 days with substantial "
    "services) must be established and documented under an IRS test each year -- "
    "purchasing an STR does not by itself create a W-2 income offset.",
    "The cost segregation first-year deduction is an estimate; the actual figure "
    "depends on construction type, land-to-improvement allocation, the depreciation "
    "rules in effect when the property is placed in service, and the engineering "
    "study's findings.",
    "Real Estate Professional Status (REPS), if relied upon, must be satisfied each "
    "tax year individually (>50% of personal service hours in real property trades "
    "or businesses, plus material participation per activity or a grouping election) "
    "-- it does not permanently unlock unlimited deductions once met.",
    "All figures here are estimates for underwriting purposes only. Review with a CPA "
    "before relying on them.",
]


@dataclass
class TaxResults:
    building_value: float
    annual_straight_line_depreciation: float
    first_year_depreciation: float  # straight-line, or accelerated if cost seg used
    used_cost_segregation: bool
    first_year_interest_paid: float
    estimated_deductible_expenses: float
    estimated_first_year_tax_savings: float
    losses_offset_active_income: bool  # per reps_or_material_participation flag
    caveats: list[str]


def building_value(purchase_price: float, land_value_pct: float) -> float:
    return purchase_price * (1 - land_value_pct)


def straight_line_annual_depreciation(building_val: float, depreciation_years: float) -> float:
    return building_val / depreciation_years


def cost_seg_first_year_depreciation(
    building_val: float,
    depreciation_years: float,
    reclass_pct: float,
    bonus_depreciation_pct: float,
) -> float:
    """Portion of building basis reclassified to 5/7/15-yr property is
    depreciated in year one via bonus depreciation; the remaining basis
    continues on the standard 27.5-yr straight-line schedule."""
    reclassified = building_val * reclass_pct
    remaining_basis = building_val - reclassified
    accelerated = reclassified * bonus_depreciation_pct
    remaining_straight_line_year1 = remaining_basis / depreciation_years
    return accelerated + remaining_straight_line_year1


def evaluate_tax(
    acq: Acquisition,
    expenses: Expenses,
    tax: TaxAssumptions,
    playbook: dict,
) -> TaxResults:
    tax_cfg = playbook["tax_model"]
    depreciation_years = tax_cfg["residential_depreciation_years"]
    land_pct = tax.land_value_pct if tax.land_value_pct is not None else tax_cfg["default_land_value_pct"]

    bval = building_value(acq.purchase_price, land_pct)
    sl_annual = straight_line_annual_depreciation(bval, depreciation_years)

    if tax.use_cost_segregation:
        reclass_pct = tax.cost_seg_reclass_pct_of_building or tax_cfg["cost_segregation"]["default_reclass_pct_of_building"]
        bonus_pct = tax.bonus_depreciation_pct or tax_cfg["cost_segregation"]["default_bonus_depreciation_pct"]
        first_year_dep = cost_seg_first_year_depreciation(bval, depreciation_years, reclass_pct, bonus_pct)
    else:
        first_year_dep = sl_annual

    interest_y1 = first_year_interest_paid(acq)
    deductible_expenses = (
        interest_y1
        + expenses.property_taxes
        + expenses.insurance
        + expenses.maintenance_repairs
        + expenses.supplies
        + first_year_dep
    )
    tax_savings = deductible_expenses * tax.marginal_tax_rate

    return TaxResults(
        building_value=bval,
        annual_straight_line_depreciation=sl_annual,
        first_year_depreciation=first_year_dep,
        used_cost_segregation=tax.use_cost_segregation,
        first_year_interest_paid=interest_y1,
        estimated_deductible_expenses=deductible_expenses,
        estimated_first_year_tax_savings=tax_savings,
        losses_offset_active_income=tax.reps_or_material_participation,
        caveats=CAVEATS,
    )
