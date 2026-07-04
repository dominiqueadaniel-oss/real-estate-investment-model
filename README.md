# Real Estate Investment Model

A standardized underwriting workbook, in code, that scores rental property
deals against a defined investment playbook: the same Financial Model, Tax
Model, LTR/STR/Appreciation purchase-criteria scorecards, and Market
Evaluation Framework for every property, so decisions aren't driven by
anecdote.

Not tax or investment advice. Every tax figure is an estimate meant to be
reviewed with a CPA.

## Setup

```
pip install -r requirements.txt
```

## Evaluate a property

```
python -m investment_model.cli evaluate examples/str_sevier_county.json
python -m investment_model.cli evaluate examples/ltr_murfreesboro.json --format json
```

Write your own property file by copying one of `examples/*.json` and
filling in acquisition, income, expenses, growth assumptions, market
framework scores, and the category-specific factors (`ltr_factors`,
`str_factors`, or `appreciation_factors`).

Output is a markdown (or JSON) report containing:
- **Financial Model**: loan amount, cash invested, NOI, cap rate, DSCR,
  cash-on-cash return, 5/10-year equity and IRR.
- **Tax Model**: depreciation (straight-line or cost-segregation-accelerated),
  estimated first-year tax savings, and the playbook's explicit caveats on
  STR material participation, cost segregation variability, and REPS.
- **Purchase criteria scorecard** (LTR or STR) with pass/fail against every
  target, and the reject rule (2+ failures = reject).
- **Appreciation scorecard** (qualitative 1-10 average) for Appreciation-
  category properties.
- **Market Evaluation Framework**: 1-10 x 9 or 10 categories, total /100.
- **Investment philosophy check**: appreciates / cash flow / tax benefit,
  needs 2 of 3.
- An overall **PURSUE / CONSIDER / REJECT** decision with reasons.

## Check portfolio allocation

```
python -m investment_model.cli portfolio examples/portfolio.json
```

Compares a list of properties (by category and dollar value) against the
40% STR / 40% LTR / 20% Appreciation target allocation.

## Adjust the playbook

All thresholds (cash-on-cash minimum, DSCR minimum, reject-at-failure
counts, market-score pursue threshold, cost segregation defaults, etc.)
live in `playbook.yaml`, not in the code. Edit it as the strategy evolves;
`--playbook path/to/other.yaml` points the CLI at an alternate config.

See `docs/playbook_reference.md` for the condensed source criteria.

## Tests

```
python -m pytest
```
