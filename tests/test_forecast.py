import pytest

from valuation.forecast import derive_assumptions, project_unlevered_fcf, _cagr
from valuation.models import Assumptions


def test_cagr_basic():
    # 100 -> 110 -> 121 is exactly 2 periods of 10% growth
    assert _cagr([100, 110, 121]) == pytest.approx(0.10, abs=1e-6)


def test_cagr_single_value_is_zero():
    assert _cagr([100]) == 0.0


def test_derive_assumptions_matches_synthetic_ratios(sample_financials):
    assumptions = derive_assumptions(sample_financials)
    assert assumptions.revenue_growth_rate == pytest.approx(0.10, abs=1e-6)
    assert assumptions.ebit_margin == pytest.approx(0.20, abs=1e-9)
    assert assumptions.da_pct_revenue == pytest.approx(0.05, abs=1e-9)
    assert assumptions.capex_pct_revenue == pytest.approx(0.07, abs=1e-9)
    assert assumptions.tax_rate == pytest.approx(0.21, abs=1e-9)


def test_derive_assumptions_respects_overrides(sample_financials):
    overrides = Assumptions(revenue_growth_rate=0.50, ebit_margin=0.99)
    assumptions = derive_assumptions(sample_financials, overrides)
    assert assumptions.revenue_growth_rate == 0.50
    assert assumptions.ebit_margin == 0.99
    # Fields not overridden still get derived from history
    assert assumptions.da_pct_revenue == pytest.approx(0.05, abs=1e-9)


def test_project_unlevered_fcf_first_year_math(sample_financials):
    assumptions = derive_assumptions(sample_financials, Assumptions(forecast_years=3))
    projections = project_unlevered_fcf(sample_financials, assumptions)

    assert len(projections) == 3

    year1 = projections[0]
    expected_revenue = 1331.0 * 1.10
    assert year1.revenue == pytest.approx(expected_revenue)
    assert year1.ebit == pytest.approx(expected_revenue * 0.20)
    assert year1.nopat == pytest.approx(expected_revenue * 0.20 * (1 - 0.21))
    assert year1.da == pytest.approx(expected_revenue * 0.05)
    assert year1.capex == pytest.approx(expected_revenue * 0.07)

    # Revenue should keep compounding at the same growth rate
    assert projections[1].revenue == pytest.approx(year1.revenue * 1.10)


def test_project_unlevered_fcf_is_positive_for_healthy_company(sample_financials):
    assumptions = derive_assumptions(sample_financials)
    projections = project_unlevered_fcf(sample_financials, assumptions)
    assert all(p.unlevered_fcf > 0 for p in projections)
