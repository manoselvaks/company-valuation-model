import dataclasses

import pytest

from valuation.sensitivity import build_range, sensitivity_table
from valuation.forecast import derive_assumptions
from valuation.dcf import run_dcf
from valuation.models import Assumptions


def test_build_range_centers_correctly():
    values = build_range(center=0.09, step=0.01, count=5)
    assert values == [0.07, 0.08, 0.09, 0.10, 0.11]


def test_sensitivity_table_shape(sample_financials):
    assumptions = derive_assumptions(sample_financials, Assumptions(wacc=0.09))
    wacc_values, growth_values, grid = sensitivity_table(
        sample_financials, assumptions, base_wacc=0.09, grid_size=5
    )
    assert len(wacc_values) == 5
    assert len(growth_values) == 5
    assert len(grid) == 5
    assert all(len(row) == 5 for row in grid)


def test_sensitivity_table_center_matches_base_case(sample_financials):
    assumptions = derive_assumptions(
        sample_financials, Assumptions(wacc=0.09, terminal_growth_rate=0.025)
    )
    base_result = run_dcf(sample_financials, assumptions)

    wacc_values, growth_values, grid = sensitivity_table(
        sample_financials, assumptions, base_wacc=0.09,
        wacc_step=0.01, growth_step=0.005, grid_size=5,
    )

    center = 5 // 2
    assert wacc_values[center] == pytest.approx(0.09)
    assert growth_values[center] == pytest.approx(0.025)
    assert grid[center][center] == pytest.approx(base_result.implied_share_price)


def test_sensitivity_table_marks_invalid_combinations_as_none(sample_financials):
    assumptions = derive_assumptions(sample_financials, Assumptions(wacc=0.03))
    # With a low base WACC and default growth step, some combinations should
    # have growth >= wacc, which is not a valid perpetuity.
    wacc_values, growth_values, grid = sensitivity_table(
        sample_financials, assumptions, base_wacc=0.03,
        wacc_step=0.01, growth_step=0.02, grid_size=5,
    )
    flat = [price for row in grid for price in row]
    assert None in flat


def test_higher_wacc_lowers_implied_price(sample_financials):
    assumptions = derive_assumptions(sample_financials, Assumptions(terminal_growth_rate=0.025))
    low_wacc_result = run_dcf(sample_financials, dataclasses.replace(assumptions, wacc=0.08))
    high_wacc_result = run_dcf(sample_financials, dataclasses.replace(assumptions, wacc=0.12))
    assert high_wacc_result.implied_share_price < low_wacc_result.implied_share_price
