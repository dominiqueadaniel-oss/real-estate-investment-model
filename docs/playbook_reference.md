# Playbook reference

Condensed from the source investment strategy document. Full prose lives
there; this is the numeric/criteria subset that `playbook.yaml` encodes.

## Investment philosophy
A property should satisfy at least 2 of 3: appreciates, produces cash flow,
creates tax benefits.

## Portfolio allocation
40% STR / 40% LTR / 20% Appreciation.

## LTR purchase criteria (reject if 2+ fail)
Cash-on-cash > 8%, cap rate > 6%, DSCR > 1.30, vacancy < 6%, population
growth positive, job growth above national average, school ratings good,
crime low, property age < 30 years preferred.

## STR purchase criteria (reject if 2+ fail)
Occupancy > 60% annually, ADR growth increasing, revenue multiple strong
relative to acquisition cost, local STR regulations stable, nearby
attractions significant, seasonality moderate, guest rating potential high.

## Appreciation criteria (qualitative, no fixed numeric targets)
Population growth, employment, corporate investment, infrastructure,
housing supply, median income growth, migration trends, historical
appreciation.

## Market Evaluation Framework
Score 1-10 each: cash flow, appreciation, taxes, landlord laws, population
growth, job growth, tourism (STR only), regulatory stability, natural
disaster risk, competition. Total /100 (or /90 when tourism doesn't apply).

## Tax model caveats
- STR material participation requires average guest stay <=7 days (or <=30
  days with substantial services), documented under an IRS test each year.
- Cost segregation first-year deduction ($50k-$80k plausible on a $500k
  property) depends on construction type, land/improvement allocation,
  rules in effect when placed in service, and the engineering study.
- REPS must be satisfied every tax year individually, not a one-time
  threshold.

All of this is configurable in `playbook.yaml`, not hardcoded in the model.
