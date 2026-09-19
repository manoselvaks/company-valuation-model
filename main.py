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
from valuation.comps import fetch_peer_snapshot, build_comps_table


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
    parser.add_argument("--comps", default=None,
                         help="Comma-separated peer tickers for a comparable "
                              "companies analysis, e.g. --comps MSFT,GOOGL,META. "
                              "Adds a Comps sheet with P/E, EV/EBITDA and "
                              "EV/Revenue multiples and a football-field chart.")
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

    comps_result = None
    if args.comps:
        peer_tickers = [t.strip() for t in args.comps.split(",") if t.strip()]
        try:
            target_snapshot = fetch_peer_snapshot(args.ticker)
            peer_snapshots = [fetch_peer_snapshot(t) for t in peer_tickers]
            comps_result = build_comps_table(
                target_snapshot, peer_snapshots,
                financials.shares_outstanding, financials.net_debt,
            )
        except Exception as e:
            print(f"Warning: comps analysis failed ({e}); continuing without it.",
                  file=sys.stderr)

    output_path = args.output or f"{financials.ticker}_valuation.xlsx"
    build_excel_report(
        financials, assumptions, result,
        wacc_values, growth_values, price_grid, output_path,
        comps_result=comps_result,
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
    if comps_result is not None:
        print("  Comps implied price:")
        if comps_result.implied_price_ev_ebitda is not None:
            print(f"    EV/EBITDA:          ${comps_result.implied_price_ev_ebitda:,.2f}")
        if comps_result.implied_price_ev_revenue is not None:
            print(f"    EV/Revenue:         ${comps_result.implied_price_ev_revenue:,.2f}")
        if comps_result.implied_price_pe is not None:
            print(f"    P/E:                ${comps_result.implied_price_pe:,.2f}")
    print(f"\nFull report written to {output_path}")


if __name__ == "__main__":
    main()
