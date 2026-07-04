"""Portfolio Allocation tracking against the playbook's 40% STR / 40% LTR /
20% Appreciation target.

Takes a list of properties (existing holdings and/or a proposed new
acquisition) with a category and a dollar value, and reports current vs.
target allocation and the drift a new acquisition would introduce.
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORY_KEY = {"LTR": "long_term_rental_pct", "STR": "short_term_rental_pct", "Appreciation": "appreciation_pct"}


@dataclass
class PortfolioEntry:
    name: str
    category: str
    value: float


@dataclass
class AllocationResult:
    current_pct: dict[str, float]
    target_pct: dict[str, float]
    drift_pct: dict[str, float]  # current - target, positive = overweight
    total_value: float


def evaluate_allocation(entries: list[PortfolioEntry], playbook: dict) -> AllocationResult:
    target = {
        cat: playbook["portfolio_allocation"][key] for cat, key in CATEGORY_KEY.items()
    }
    total = sum(e.value for e in entries)
    current = {cat: 0.0 for cat in CATEGORY_KEY}
    for e in entries:
        current[e.category] = current.get(e.category, 0.0) + e.value
    current_pct = {cat: (v / total if total else 0.0) for cat, v in current.items()}
    drift = {cat: current_pct[cat] - target[cat] for cat in CATEGORY_KEY}
    return AllocationResult(current_pct, target, drift, total)
