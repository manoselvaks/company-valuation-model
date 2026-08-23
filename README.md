# Company Valuation Model

A discounted cash flow (DCF) valuation tool: give it a stock ticker, and it
pulls the company's real historical financials, projects free cash flow
forward, values the business, and writes a formatted Excel report — the
same output an analyst would build by hand in a financial model, generated
in seconds instead of an afternoon.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)

<!-- TODO: replace with a screenshot of the generated Excel report -->
<!-- ![sample report](docs/sample_report.png) -->

## What it actually does

1. **Pulls real financials** for any public ticker via Yahoo Finance
   (revenue, EBIT, D&A, capex, debt, cash, shares outstanding, beta).
2. **Derives assumptions from history** — revenue CAGR, EBIT margin, D&A
   and capex as a % of revenue, effective tax rate — any of which you can
   override.
3. **Projects unlevered free cash flow** for a configurable number of years:
   `NOPAT + D&A − Capex − Δ Net Working Capital`.
4. **Computes WACC** via CAPM (cost of equity from beta, blended with
   after-tax cost of debt), or accepts a WACC you supply directly.
5. **Discounts the cash flows** and adds a Gordon-growth terminal value to
   get enterprise value, then backs into equity value and an implied
   per-share price.
6. **Builds a sensitivity table** showing how the implied price moves
   across a range of WACC and terminal growth assumptions — because a DCF
   is only as good as its two most debatable inputs, and any real model
   should show that range rather than hide behind one number.
7. **Writes it all to a formatted Excel workbook** (Summary, Assumptions,
   FCF Projection, and a colour-scaled Sensitivity grid).

## Running it

```bash
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py AAPL
```

This prints a quick summary to the terminal and writes `AAPL_valuation.xlsx`
in the current folder.

### Overriding assumptions

Every judgment call in the model can be overridden from the command line —
useful since "what the last 4 years looked like" is rarely exactly what you
believe about the next 5:

```bash
python3 main.py MSFT --years 7 --terminal-growth 0.03
python3 main.py TSLA --wacc 0.11 --growth 0.15 --margin 0.12
python3 main.py KO --risk-free-rate 0.045 --market-risk-premium 0.055
```

Run `python3 main.py --help` for the full list of overridable assumptions.

## Running the tests

```bash
python3 -m pytest tests/ -v
```

24 tests cover statement parsing (against a hand-built DataFrame shaped
like Yahoo Finance's real output, so no network access is needed to run
the suite), the forecasting math, the DCF and WACC calculations, and the
sensitivity grid.

## Methodology notes

- **This is a simplified DCF**, not a full three-statement model — net
  working capital is approximated as a percentage of the change in
  revenue rather than built up from a full balance sheet schedule. That's
  a standard simplification for a quick valuation; a more rigorous build
  would model receivables, payables, and inventory separately.
- **Terminal value** uses the Gordon growth (perpetuity) method rather
  than an exit-multiple approach. Both are common in practice; perpetuity
  growth is more defensible when you don't want to assume a specific
  future trading multiple.
- **WACC** defaults to a CAPM-based estimate using the company's own beta
  from Yahoo Finance, a configurable risk-free rate and market risk
  premium, and a flat assumed cost of debt — all of which are simplifying
  assumptions real analysts would refine with market data on the
  company's actual bond yields.
- **This is not investment advice.** It's a demonstration of DCF
  mechanics and financial modeling automation, not a substitute for
  professional equity research.

## Project structure

```
company-valuation-model/
├── valuation/
│   ├── models.py       # CompanyFinancials, Assumptions, DCFResult dataclasses
│   ├── data.py          # Yahoo Finance fetch + pure statement parsing
│   ├── forecast.py      # Derives assumptions from history, projects FCF
│   ├── dcf.py            # WACC, discounting, terminal value, valuation
│   ├── sensitivity.py    # WACC x terminal-growth sensitivity grid
│   └── report.py         # Excel report generation (openpyxl)
├── main.py               # CLI entry point
├── tests/
└── requirements.txt
```

## Possible extensions

- A full three-statement model (income statement, balance sheet, cash
  flow statement all linked) instead of the simplified FCF build
- Exit-multiple terminal value as an alternative to Gordon growth
- Comparable company analysis (trading multiples of peer companies)
- A simple web front end (Streamlit) instead of the CLI
