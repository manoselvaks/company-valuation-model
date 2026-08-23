"""
Discounted cash flow valuation: discounts projected unlevered FCF back to
the present using WACC, adds a terminal value, and backs into an implied
per-share price.
"""

from valuation.forecast import project_unlevered_fcf
from valuation.models import DCFResult


def cost_of_equity_capm(risk_free_rate, beta, market_risk_premium):
    """CAPM: cost of equity = risk-free rate + beta x equity risk premium."""
    return risk_free_rate + beta * market_risk_premium


def compute_wacc(financials, assumptions):
    """Weighted-average cost of capital, weighting cost of equity and
    after-tax cost of debt by their share of total capital (market cap +
    debt). If assumptions.wacc is set directly, that overrides this
    calculation entirely."""
    if assumptions.wacc is not None:
        return assumptions.wacc

    cost_of_equity = cost_of_equity_capm(
        assumptions.risk_free_rate, financials.beta, assumptions.market_risk_premium
    )
    after_tax_cost_of_debt = assumptions.cost_of_debt * (1 - assumptions.tax_rate)

    market_cap = financials.market_cap
    debt = financials.total_debt
    total_capital = market_cap + debt

    if total_capital <= 0:
        return cost_of_equity  # degenerate case: no market cap/debt data

    weight_equity = market_cap / total_capital
    weight_debt = debt / total_capital

    return weight_equity * cost_of_equity + weight_debt * after_tax_cost_of_debt


def terminal_value_gordon(last_year_fcf, wacc, terminal_growth_rate):
    """Gordon growth (perpetuity) terminal value as of the end of the
    explicit forecast period."""
    if wacc <= terminal_growth_rate:
        raise ValueError(
            "WACC must be greater than the terminal growth rate, otherwise "
            "the perpetuity value is infinite/negative."
        )
    next_year_fcf = last_year_fcf * (1 + terminal_growth_rate)
    return next_year_fcf / (wacc - terminal_growth_rate)


def run_dcf(financials, assumptions):
    """Runs the full DCF and returns a DCFResult."""
    wacc = compute_wacc(financials, assumptions)
    projections = project_unlevered_fcf(financials, assumptions)

    present_values = [
        proj.unlevered_fcf / ((1 + wacc) ** proj.year) for proj in projections
    ]

    terminal_value = terminal_value_gordon(
        projections[-1].unlevered_fcf, wacc, assumptions.terminal_growth_rate
    )
    pv_terminal_value = terminal_value / ((1 + wacc) ** projections[-1].year)

    enterprise_value = sum(present_values) + pv_terminal_value
    equity_value = enterprise_value - financials.net_debt
    implied_share_price = equity_value / financials.shares_outstanding

    return DCFResult(
        wacc=wacc,
        projections=projections,
        present_values=present_values,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        implied_share_price=implied_share_price,
        current_price=financials.current_price,
    )
