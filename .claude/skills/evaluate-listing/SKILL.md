---
name: evaluate-listing
description: Evaluate a real estate listing (a Zillow/Redfin/Realtor.com/MLS URL, or pasted listing text/details) against this repo's investment playbook, without the user hand-writing a property JSON file or running Python themselves. Use whenever the user pastes a listing link or listing details and asks to evaluate, underwrite, score, or check whether a property is a good deal.
---

# Evaluate a listing against the playbook

This repo's model (`investment_model/`) needs a fully-populated property JSON
to run — acquisition terms, income, expenses, growth assumptions, market
framework scores, and category-specific factors. A listing page never has
most of that: it has price, address, beds/baths/sqft, year built, HOA, and
sometimes a rent estimate. It never has school ratings, crime scores,
population/job growth, STR occupancy, or the financing terms the user
intends to use. This skill's job is to extract what's really on the
listing, get the handful of fields that are genuinely decision-critical,
and let the model's own default-filling (`investment_model/from_listing.py`)
handle everything else — while flagging every assumption it made so nothing
fabricated is presented as real.

## Steps

1. **Get the listing content.**
   - If given a URL, fetch it (WebFetch or an equivalent tool). Many listing
     sites (Zillow, Redfin) block automated fetches or return a stripped-down
     page. If the fetch fails, times out, or the content looks like a
     captcha/blocked page rather than a real listing, don't retry
     repeatedly — tell the user and ask them to paste the visible listing
     details instead (price, address, beds/baths/sqft, year built, HOA,
     property tax history, any rent estimate shown).
   - If given pasted text/details directly, use that.

2. **Determine the category.** Ask the user if it isn't already clear from
   context: `LTR` (long-term rental), `STR` (short-term/vacation rental), or
   `Appreciation` (bought primarily for equity growth, not yield). This
   changes which factors and scorecard apply.

3. **Extract into this flat schema** (all keys optional except the five
   marked required — see `investment_model/from_listing.py:REQUIRED_FIELDS`):

   ```jsonc
   {
     "name": "...",              // required -- address or listing title
     "market": "City, ST",       // required
     "category": "LTR",          // required -- LTR | STR | Appreciation
     "purchase_price": 000000,   // required -- list price (or offer price if known)
     "annual_rent_or_str_revenue": 00000,  // required -- see step 4

     // From the listing, when shown -- otherwise omit and let the model default:
     "year_built": 2015,
     "hoa": 240,
     "property_taxes": 1450,     // annual, from tax history if shown
     "closing_costs": 0,
     "down_payment_pct": 0.20,
     "interest_rate": 0.07,
     "loan_term_years": 30,

     // LTR only, when known -- otherwise the model defaults to a neutral
     // placeholder (5/10 or 0%) and flags it as needing research:
     "school_rating": 8, "crime_score": 3,
     "population_growth_pct": 0.02, "job_growth_pct": 0.02,

     // STR only, when known:
     "occupancy_pct": 0.62, "adr_growth_pct": 0.04,
     "str_regulations_stable": true,
     "nearby_attractions_score": 8, "seasonality_score": 5, "guest_rating_potential_score": 7,

     // Appreciation only, when known ("population_growth_score" below is
     // shared with the Market Evaluation Framework -- same key, one value):
     "employment_score": 7, "corporate_investment_score": 7,
     "infrastructure_score": 6, "housing_supply_score": 6,
     "median_income_growth_score": 6, "migration_trend_score": 7, "historical_appreciation_score": 7,

     // Market Evaluation Framework (1-10 each), when you have a basis to score them:
     "cash_flow_score": 6, "appreciation_score": 6, "taxes_score": 7, "landlord_laws_score": 7,
     "population_growth_score": 7, "job_growth_score": 6, "tourism_score": 7,
     "regulatory_stability_score": 7, "natural_disaster_risk_score": 7, "competition_score": 6
   }
   ```

   Don't invent numbers for fields you have no basis for — just omit them.
   `from_listing.py` fills every gap with a documented default/neutral
   placeholder and reports it as an assumption; that's the whole point of
   routing through it instead of hand-building the full nested schema.

4. **`annual_rent_or_str_revenue` cannot be reasonably defaulted** — it's
   the single most decision-critical number and varies too much by market
   to guess. Look for a rent estimate on the listing (e.g. "Rent Zestimate").
   For STR, look for any revenue/occupancy tool mentioned. If nothing is
   available, ask the user for a comp-based estimate rather than fabricating
   one; if they don't have one, say so plainly instead of proceeding.

5. **Write the flat JSON to a scratch file** (not into `examples/` unless
   the user wants to keep it), then run, from the repo root:

   ```
   python -m investment_model.cli from-listing <scratch_file.json> --save-property <optional path to keep the full property JSON>
   ```

   Add `--format json` if the user wants structured output instead of the
   markdown report. If the command exits with "Cannot evaluate: Missing
   required field(s)", that means step 4 wasn't resolved — go back to it
   rather than inventing a number to get past the error.

6. **Present the report as-is**, including the "Assumptions Used" section
   at the top. Call out explicitly which fields were placeholders (anything
   marked "NEEDS RESEARCH" or "NOT VERIFIED") and that the PURSUE/CONSIDER/
   REJECT decision is only as good as those inputs — encourage the user to
   fill in real school/crime/growth/occupancy data (they know their target
   market's specifics better than a listing page does) and re-run
   `evaluate` on the saved property file once they have it.

7. If the user wants to keep this property for later or add it to
   portfolio tracking, save it under `examples/` with a descriptive name
   (e.g. `examples/<market-slug>_<category>.json`) using `--save-property`.
