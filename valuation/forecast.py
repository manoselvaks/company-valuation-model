"""
Derives forward-looking assumptions from a company's history, and projects
unlevered free cash flow forward using those assumptions.

Unlevered FCF here is the standard DCF build:
    NOPAT (EBIT x (1 - tax rate))
    + D&A
    - Capex
    - increase in net working capital
    = unlevered FCF
"""

import dataclasses

from valuation.models import Assumptions, YearProjection


def _cagr(values):
    """Compound annual growth rate from the first to the last value."""
    start, end = values[0], values[-1]
    periods = len(values) - 1
    if periods <= 0 or start <= 0:
        return 0.0
    return (end / start) ** (1 / periods) - 1


def _average_ratio(numerators, denominators):
    ratios = [n / d for n, d in zip(numerators, denominators) if d]
    return sum(ratios) / len(ratios) if ratios else 0.0


def derive_assumptions(financials, overrides=None):
    """Fill in any assumption left as None using the company's own
    historical averages, so a user only needs to override what they
    actually want to change."""
    assumptions = overrides or Assumptions()

    derived = dataclasses.replace(assumptions)

    if derived.revenue_growth_rate is None:
        derived.revenue_growth_rate = _cagr(financials.revenue_history)

    if derived.ebit_margin is None:
        derived.ebit_margin = _average_ratio(
            financials.ebit_history, financials.revenue_history
        )

    if derived.tax_rate is None:
        derived.tax_rate = financials.tax_rate

    if derived.da_pct_revenue is None:
        derived.da_pct_revenue = _average_ratio(
            financials.da_history, financials.revenue_history
        )

    if derived.capex_pct_revenue is None:
        derived.capex_pct_revenue = _average_ratio(
            financials.capex_history, financials.revenue_history
        )

    return derived


def project_unlevered_fcf(financials, assumptions):
    """Project unlevered FCF for assumptions.forecast_years, returning a
    list[YearProjection] in chronological order."""
    projections = []
    prior_revenue = financials.revenue_history[-1]

    for i in range(1, assumptions.forecast_years + 1):
        revenue = prior_revenue * (1 + assumptions.revenue_growth_rate)
        ebit = revenue * assumptions.ebit_margin
        nopat = ebit * (1 - assumptions.tax_rate)
        da = revenue * assumptions.da_pct_revenue
        capex = revenue * assumptions.capex_pct_revenue
        change_in_nwc = (revenue - prior_revenue) * assumptions.nwc_pct_of_revenue_change
        unlevered_fcf = nopat + da - capex - change_in_nwc

        projections.append(YearProjection(
            year=i,
            revenue=revenue,
            ebit=ebit,
            nopat=nopat,
            da=da,
            capex=capex,
            change_in_nwc=change_in_nwc,
            unlevered_fcf=unlevered_fcf,
        ))
        prior_revenue = revenue

    return projections
