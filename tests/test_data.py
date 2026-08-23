import pandas as pd
import pytest

from valuation.data import parse_financials, MissingFinancialData

# yfinance's statement DataFrames are indexed by line item, with columns as
# period-end dates ordered NEWEST first — mirrored here so the parser is
# tested against the real shape of the data, not a convenient stand-in.
COLUMNS = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"])


def _income_statement():
    return pd.DataFrame(
        {
            COLUMNS[0]: [1331.0, 266.2, 55.902, 266.2],
            COLUMNS[1]: [1210.0, 242.0, 50.82, 242.0],
            COLUMNS[2]: [1100.0, 220.0, 46.2, 220.0],
            COLUMNS[3]: [1000.0, 200.0, 42.0, 200.0],
        },
        index=["Total Revenue", "EBIT", "Tax Provision", "Pretax Income"],
    )


def _balance_sheet():
    return pd.DataFrame(
        {
            COLUMNS[0]: [20000.0, 5000.0],
            COLUMNS[1]: [19000.0, 4800.0],
            COLUMNS[2]: [18000.0, 4600.0],
            COLUMNS[3]: [17000.0, 4400.0],
        },
        index=["Total Debt", "Cash And Cash Equivalents"],
    )


def _cashflow():
    return pd.DataFrame(
        {
            COLUMNS[0]: [66.55, -93.17],
            COLUMNS[1]: [60.5, -84.7],
            COLUMNS[2]: [55.0, -77.0],
            COLUMNS[3]: [50.0, -70.0],
        },
        index=["Depreciation And Amortization", "Capital Expenditure"],
    )


def _info():
    return {
        "shortName": "Test Co",
        "sharesOutstanding": 1000.0,
        "currentPrice": 150.0,
        "beta": 1.2,
    }


def test_parse_financials_orders_history_oldest_first():
    financials = parse_financials(
        "test", _info(), _income_statement(), _balance_sheet(), _cashflow()
    )
    assert financials.revenue_history == [1000.0, 1100.0, 1210.0, 1331.0]
    assert financials.ebit_history == [200.0, 220.0, 242.0, 266.2]


def test_parse_financials_takes_most_recent_balance_sheet_values():
    financials = parse_financials(
        "test", _info(), _income_statement(), _balance_sheet(), _cashflow()
    )
    assert financials.total_debt == 20000.0
    assert financials.cash_and_equivalents == 5000.0


def test_parse_financials_capex_is_stored_as_positive():
    financials = parse_financials(
        "test", _info(), _income_statement(), _balance_sheet(), _cashflow()
    )
    assert all(c > 0 for c in financials.capex_history)
    assert financials.capex_history[-1] == pytest.approx(93.17)


def test_parse_financials_computes_effective_tax_rate():
    financials = parse_financials(
        "test", _info(), _income_statement(), _balance_sheet(), _cashflow()
    )
    # Tax Provision / Pretax Income = 42/200 = 0.21 in every year here
    assert financials.tax_rate == pytest.approx(0.21, abs=1e-6)


def test_parse_financials_raises_when_shares_outstanding_missing():
    info = _info()
    del info["sharesOutstanding"]
    with pytest.raises(MissingFinancialData):
        parse_financials("test", info, _income_statement(), _balance_sheet(), _cashflow())


def test_parse_financials_raises_when_required_statement_row_missing():
    bad_income_statement = _income_statement().drop(index="Total Revenue")
    with pytest.raises(MissingFinancialData):
        parse_financials(
            "test", _info(), bad_income_statement, _balance_sheet(), _cashflow()
        )
