import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from valuation.models import CompanyFinancials


@pytest.fixture
def sample_financials():
    """A clean synthetic company: 10% revenue growth, 20% EBIT margin,
    5% D&A, 7% capex, all as a percent of revenue, held perfectly constant
    across 4 historical years so tests can assert exact derived ratios."""
    revenue = [1000.0, 1100.0, 1210.0, 1331.0]
    return CompanyFinancials(
        ticker="TEST",
        name="Test Co",
        current_price=15.0,
        shares_outstanding=1000.0,
        total_debt=1000.0,
        cash_and_equivalents=500.0,
        beta=1.2,
        tax_rate=0.21,
        revenue_history=revenue,
        ebit_history=[r * 0.20 for r in revenue],
        da_history=[r * 0.05 for r in revenue],
        capex_history=[r * 0.07 for r in revenue],
    )
