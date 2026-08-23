"""
CLI entry point: fetch a company's financials, run a DCF, and write an
Excel valuation report.

Examples:
    python3 main.py AAPL
    python3 main.py MSFT --years 7 --terminal-growth 0.03
    python3 main.py TSLA --wacc 0.11 --growth 0.15 --margin 0.12
"""

import argparse
import sys

from valuation.data import fetch_financials, MissingFinancialData
from valuation.forecast import derive_assumptions
from valuation.dcf import run_dcf
from valuation.sensitivity import sensitivity_table
from valuation.models import Assumptions
from valuation.report import build_excel_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pull real financials for a ticker and run a DCF valuation."
    )
    parser.add_argument("ticker", help="Stock ticker, e.g. AAPL")
    parser.add_argument("--years", type=int, default=5,
                         help="Forecast horizon in years (default: 5)")
    parser.add_argument("--growth", type=float, default=None,
                         help="Override revenue growth rate, e.g. 0.08 for 8%%. "
                              "Default: derived from historical CAGR.")
    parser.add_argument("--margin", type=float, default=None,
                         help="Override EBIT margin, e.g. 0.25. "
                              "Default: historical average.")
    parser.add_argument("--tax-rate", type=float, default=None,
                         help="Override tax rate. Default: historical effective rate.")
    parser.add_argument("--terminal-growth", type=float, default=0.025,
                         help="Terminal (perpetuity) growth rate (default: 0.025)")
    parser.add_argument("--wacc", type=float, default=None,
                         help="Override WACC directly. Default: computed via CAPM.")
    parser.add_argument("--risk-free-rate", type=float, default=0.04)
    parser.add_argument("--market-risk-premium", type=float, default=0.05)
    parser.add_argument("--cost-of-debt", type=float, default=0.05)
    parser.add_argument("--output", default=None,
                         help="Output .xlsx path (default: <TICKER>_valuation.xlsx)")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        financials = fetch_financials(args.ticker)
    except MissingFinancialData as e:
        print(f"Could not build a valuation for {args.ticker}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(
            f"Failed to fetch data for '{args.ticker}' from Yahoo Finance: {e}\n"
            "Check that the ticker is correct and that you have an internet "
            "connection.",
            file=sys.stderr,
        )
        sys.exit(1)

    overrides = Assumptions(
        forecast_years=args.years,
        revenue_growth_rate=args.growth,
        ebit_margin=args.margin,
        tax_rate=args.tax_rate,
        terminal_growth_rate=args.terminal_growth,
        wacc=args.wacc,
        risk_free_rate=args.risk_free_rate,
        market_risk_premium=args.market_risk_premium,
        cost_of_debt=args.cost_of_debt,
    )
    assumptions = derive_assumptions(financials, overrides)
    result = run_dcf(financials, assumptions)

    wacc_values, growth_values, price_grid = sensitivity_table(
        financials, assumptions, result.wacc
    )

    output_path = args.output or f"{financials.ticker}_valuation.xlsx"
    build_excel_report(
        financials, assumptions, result,
        wacc_values, growth_values, price_grid, output_path,
    )

    upside = result.upside_pct
    print(f"\n{financials.name} ({financials.ticker})")
    print(f"  Current price:        ${financials.current_price:,.2f}")
    print(f"  Implied share price:  ${result.implied_share_price:,.2f}")
    if upside is not None:
        direction = "upside" if upside >= 0 else "downside"
        print(f"  Implied {direction}:      {abs(upside):.1%}")
    print(f"  WACC used:            {result.wacc:.2%}")
    print(f"  Terminal growth:      {assumptions.terminal_growth_rate:.2%}")
    print(f"\nFull report written to {output_path}")


if __name__ == "__main__":
    main()
