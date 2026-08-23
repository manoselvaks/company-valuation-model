"""
Sensitivity analysis: a DCF's output is only as good as its two most
debatable inputs — WACC and the terminal growth rate. This builds a 2D grid
of implied share price across a range of both, which is the standard way
analysts show how much the valuation depends on those assumptions.
"""

import dataclasses

from valuation.dcf import run_dcf


def build_range(center, step, count):
    """count values centered on `center`, spaced `step` apart."""
    half = count // 2
    return [round(center + step * (i - half), 5) for i in range(count)]


def sensitivity_table(financials, base_assumptions, base_wacc,
                       wacc_step=0.01, growth_step=0.005, grid_size=5):
    """Returns (wacc_values, growth_values, price_grid) where
    price_grid[i][j] is the implied share price at
    wacc_values[i] and growth_values[j]."""
    wacc_values = build_range(base_wacc, wacc_step, grid_size)
    growth_values = build_range(
        base_assumptions.terminal_growth_rate, growth_step, grid_size
    )

    price_grid = []
    for wacc in wacc_values:
        row = []
        for growth in growth_values:
            if wacc <= growth:
                row.append(None)  # not a valid DCF combination
                continue
            variant = dataclasses.replace(
                base_assumptions, wacc=wacc, terminal_growth_rate=growth
            )
            result = run_dcf(financials, variant)
            row.append(result.implied_share_price)
        price_grid.append(row)

    return wacc_values, growth_values, price_grid
