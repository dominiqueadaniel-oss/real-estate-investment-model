"""CLI entry point.

    python -m investment_model.cli evaluate examples/ltr_murfreesboro.json
    python -m investment_model.cli evaluate examples/str_sevier_county.json --format json
    python -m investment_model.cli portfolio examples/portfolio.json
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys

from investment_model.config import load_playbook
from investment_model.inputs import PropertyInput
from investment_model.portfolio import PortfolioEntry, evaluate_allocation
from investment_model.report import evaluate_property, render_markdown


def cmd_evaluate(args: argparse.Namespace) -> None:
    playbook = load_playbook(args.playbook)
    with open(args.property_file) as f:
        prop = PropertyInput.from_dict(json.load(f))

    report = evaluate_property(prop, playbook)

    if args.format == "json":
        output = json.dumps(
            {
                "decision": report.decision,
                "reasons": report.reasons,
                "financials": dataclasses.asdict(report.financials),
                "tax": dataclasses.asdict(report.tax),
                "scorecard": dataclasses.asdict(report.scorecard) if report.scorecard else None,
                "appreciation": dataclasses.asdict(report.appreciation) if report.appreciation else None,
                "market": dataclasses.asdict(report.market),
                "philosophy": dataclasses.asdict(report.philosophy),
            },
            indent=2,
        )
    else:
        output = render_markdown(report)

    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
    else:
        print(output)


def cmd_portfolio(args: argparse.Namespace) -> None:
    playbook = load_playbook(args.playbook)
    with open(args.portfolio_file) as f:
        raw = json.load(f)
    entries = [PortfolioEntry(**e) for e in raw["properties"]]
    result = evaluate_allocation(entries, playbook)

    print(f"Total portfolio value: ${result.total_value:,.0f}\n")
    print(f"{'Category':<14}{'Current':>10}{'Target':>10}{'Drift':>10}")
    for cat in result.target_pct:
        print(
            f"{cat:<14}{result.current_pct[cat]:>10.1%}{result.target_pct[cat]:>10.1%}"
            f"{result.drift_pct[cat]:>+10.1%}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Real estate investment evaluation model")
    parser.add_argument("--playbook", default=None, help="Path to playbook.yaml (default: repo root)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("evaluate", help="Evaluate a single property against the playbook")
    p_eval.add_argument("property_file", help="Path to property JSON file")
    p_eval.add_argument("--format", choices=["md", "json"], default="md")
    p_eval.add_argument("--out", default=None, help="Write output to this file instead of stdout")
    p_eval.set_defaults(func=cmd_evaluate)

    p_portfolio = sub.add_parser("portfolio", help="Check portfolio allocation vs. 40/40/20 target")
    p_portfolio.add_argument("portfolio_file", help="Path to portfolio JSON file")
    p_portfolio.set_defaults(func=cmd_portfolio)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
