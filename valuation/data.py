"""
Fetches a company's historical financials from Yahoo Finance (via yfinance)
and turns them into a CompanyFinancials object.

The I/O (network calls through yfinance) is kept separate from the parsing
logic (`parse_financials`), so the parsing can be unit-tested with a
hand-built pandas DataFrame instead of a live network call.
"""

import yfinance as yf

from valuation.models import CompanyFinancials

# Yahoo Finance has renamed line items across versions/data providers, so we
# try a list of known aliases for each field rather than a single hard-coded
# label.
REVENUE_LABELS = ["Total Revenue", "TotalRevenue"]
EBIT_LABELS = ["EBIT", "Operating Income"]
TAX_LABELS = ["Tax Provision", "Income Tax Expense"]
PRETAX_LABELS = ["Pretax Income", "Income Before Tax"]
DA_LABELS = ["Depreciation And Amortization", "Depreciation Amortization Depletion",
             "Depreciation"]
CAPEX_LABELS = ["Capital Expenditure", "Capital Expenditures", "Purchase Of PPE"]
DEBT_LABELS = ["Total Debt"]
CASH_LABELS = ["Cash And Cash Equivalents",
               "Cash Cash Equivalents And Short Term Investments"]


class MissingFinancialData(Exception):
    """Raised when a required line item can't be found under any known label."""


def _get_row(df, candidates, required=True):
    """Return a row from `df` as a list ordered oldest->newest, trying each
    label in `candidates` in turn. yfinance's statement DataFrames are
    indexed by line-item name with columns as period-end dates, newest
    first."""
    if df is not None:
        for label in candidates:
            if label in df.index:
                row = df.loc[label]
                row = row.dropna()
                # yfinance columns come newest-first; reverse to oldest-first
                # so callers can treat index -1 as "most recent".
                return list(reversed(row.tolist()))
    if required:
        raise MissingFinancialData(
            f"Could not find any of {candidates} in the statement. "
            "Yahoo Finance may have renamed this line item — you can supply "
            "assumptions manually via CLI flags instead."
        )
    return []


def fetch_raw_data(ticker):
    """I/O boundary: hits Yahoo Finance via yfinance. Returns the raw
    (info, income_statement, balance_sheet, cashflow) yfinance objects."""
    t = yf.Ticker(ticker)
    info = t.info
    income_statement = t.financials
    balance_sheet = t.balance_sheet
    cashflow = t.cashflow
    return info, income_statement, balance_sheet, cashflow


def parse_financials(ticker, info, income_statement, balance_sheet, cashflow):
    """Pure function: turns yfinance's raw statements into a
    CompanyFinancials. No network access here — easy to unit test with a
    hand-built DataFrame standing in for `income_statement` etc."""

    revenue_history = _get_row(income_statement, REVENUE_LABELS)
    ebit_history = _get_row(income_statement, EBIT_LABELS)
    da_history = _get_row(cashflow, DA_LABELS, required=False)
    capex_history_raw = _get_row(cashflow, CAPEX_LABELS)
    # Yahoo reports capex as a cash outflow (negative); store as a positive
    # "amount spent" for readability downstream.
    capex_history = [abs(x) for x in capex_history_raw]

    tax_history = _get_row(income_statement, TAX_LABELS, required=False)
    pretax_history = _get_row(income_statement, PRETAX_LABELS, required=False)
    if tax_history and pretax_history:
        rates = [t / p for t, p in zip(tax_history, pretax_history) if p]
        tax_rate = sum(rates) / len(rates) if rates else 0.21
    else:
        tax_rate = 0.21  # reasonable US statutory-ish default if unavailable

    total_debt_row = _get_row(balance_sheet, DEBT_LABELS, required=False)
    total_debt = total_debt_row[-1] if total_debt_row else 0.0

    cash_row = _get_row(balance_sheet, CASH_LABELS, required=False)
    cash = cash_row[-1] if cash_row else 0.0

    shares_outstanding = (
        info.get("sharesOutstanding")
        or info.get("impliedSharesOutstanding")
    )
    if not shares_outstanding:
        raise MissingFinancialData("Could not determine shares outstanding.")

    current_price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )
    if not current_price:
        raise MissingFinancialData("Could not determine the current share price.")

    beta = info.get("beta") or 1.0  # market beta as a neutral fallback

    if not da_history:
        # If D&A truly isn't available, approximate as 0 rather than fail —
        # it's a smaller line item than revenue/EBIT/capex.
        da_history = [0.0] * len(revenue_history)

    return CompanyFinancials(
        ticker=ticker.upper(),
        name=info.get("shortName", ticker.upper()),
        current_price=float(current_price),
        shares_outstanding=float(shares_outstanding),
        total_debt=float(total_debt),
        cash_and_equivalents=float(cash),
        beta=float(beta),
        tax_rate=float(tax_rate),
        revenue_history=[float(x) for x in revenue_history],
        ebit_history=[float(x) for x in ebit_history],
        da_history=[float(x) for x in da_history],
        capex_history=[float(x) for x in capex_history],
    )


def fetch_financials(ticker):
    """Convenience wrapper: fetch + parse in one call."""
    info, income_statement, balance_sheet, cashflow = fetch_raw_data(ticker)
    return parse_financials(ticker, info, income_statement, balance_sheet, cashflow)
