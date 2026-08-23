import pytest

from valuation.dcf import cost_of_equity_capm, compute_wacc, terminal_value_gordon, run_dcf
from valuation.forecast import derive_assumptions
from valuation.models import Assumptions


def test_capm():
    # rf 4% + beta 1.2 * ERP 5% = 10%
    assert cost_of_equity_capm(0.04, 1.2, 0.05) == pytest.approx(0.10)


def test_compute_wacc_uses_explicit_override(sample_financials):
    assumptions = Assumptions(wacc=0.0777)
    assert compute_wacc(sample_financials, assumptions) == 0.0777


def test_compute_wacc_blends_equity_and_debt(sample_financials):
    assumptions = derive_assumptions(sample_financials)
    wacc = compute_wacc(sample_financials, assumptions)
    cost_of_equity = cost_of_equity_capm(0.04, sample_financials.beta, 0.05)
    # WACC should sit strictly between after-tax cost of debt and cost of
    # equity, since it's a weighted blend of the two.
    after_tax_cod = assumptions.cost_of_debt * (1 - assumptions.tax_rate)
    assert after_tax_cod < wacc < cost_of_equity


def test_terminal_value_requires_wacc_above_growth():
    with pytest.raises(ValueError):
        terminal_value_gordon(last_year_fcf=100, wacc=0.03, terminal_growth_rate=0.03)


def test_terminal_value_gordon_formula():
    # next year FCF = 100 * 1.02 = 102; TV = 102 / (0.10 - 0.02) = 1275
    tv = terminal_value_gordon(last_year_fcf=100, wacc=0.10, terminal_growth_rate=0.02)
    assert tv == pytest.approx(1275.0)


def test_run_dcf_end_to_end(sample_financials):
    assumptions = derive_assumptions(
        sample_financials, Assumptions(forecast_years=5, wacc=0.09, terminal_growth_rate=0.025)
    )
    result = run_dcf(sample_financials, assumptions)

    assert result.wacc == 0.09
    assert len(result.projections) == 5
    assert len(result.present_values) == 5
    assert result.enterprise_value == pytest.approx(
        sum(result.present_values) + result.pv_terminal_value
    )
    assert result.equity_value == pytest.approx(
        result.enterprise_value - sample_financials.net_debt
    )
    assert result.implied_share_price == pytest.approx(
        result.equity_value / sample_financials.shares_outstanding
    )
    assert result.implied_share_price > 0


def test_upside_pct_calculation(sample_financials):
    assumptions = derive_assumptions(sample_financials, Assumptions(wacc=0.09))
    result = run_dcf(sample_financials, assumptions)
    expected = (result.implied_share_price / sample_financials.current_price) - 1
    assert result.upside_pct == pytest.approx(expected)
