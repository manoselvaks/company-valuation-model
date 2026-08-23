"""Shared data structures used across the valuation pipeline."""

from dataclasses import dataclass, field


@dataclass
class CompanyFinancials:
    """Historical financials for one company, most-recent-year last."""

    ticker: str
    name: str
    current_price: float
    shares_outstanding: float
    total_debt: float
    cash_and_equivalents: float
    beta: float
    tax_rate: float

    revenue_history: list       # e.g. [2022, 2023, 2024, 2025] revenue, oldest first
    ebit_history: list
    da_history: list            # depreciation & amortization
    capex_history: list         # positive numbers = cash spent on capex

    @property
    def market_cap(self):
        return self.current_price * self.shares_outstanding

    @property
    def net_debt(self):
        return self.total_debt - self.cash_and_equivalents


@dataclass
class Assumptions:
    """All the judgment calls a DCF requires. Any field left as None is
    derived from historicals by forecast.derive_assumptions()."""

    forecast_years: int = 5
    revenue_growth_rate: float = None
    ebit_margin: float = None
    tax_rate: float = None
    da_pct_revenue: float = None
    capex_pct_revenue: float = None
    nwc_pct_of_revenue_change: float = 0.10  # simplifying assumption: NWC moves
                                              # with 10% of the change in revenue
    terminal_growth_rate: float = 0.025

    # WACC inputs (used only if wacc is not supplied directly)
    wacc: float = None
    risk_free_rate: float = 0.04
    market_risk_premium: float = 0.05
    cost_of_debt: float = 0.05


@dataclass
class YearProjection:
    year: int
    revenue: float
    ebit: float
    nopat: float          # net operating profit after tax
    da: float
    capex: float
    change_in_nwc: float
    unlevered_fcf: float


@dataclass
class DCFResult:
    wacc: float
    projections: list        # list[YearProjection]
    present_values: list      # PV of each year's FCF
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    equity_value: float
    implied_share_price: float
    current_price: float

    @property
    def upside_pct(self):
        if self.current_price == 0:
            return None
        return (self.implied_share_price / self.current_price) - 1
