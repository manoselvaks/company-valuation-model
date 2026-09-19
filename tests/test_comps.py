import pytest

from valuation.comps import (
    PeerSnapshot,
    build_comps_table,
    parse_peer_snapshot,
)


def _peer(ticker, pe, ev_ebitda, ev_revenue):
    """Small helper: build a PeerSnapshot directly with just the ratios a
    test cares about, skipping the raw market_cap/ebitda/revenue fields."""
    return PeerSnapshot(
        ticker=ticker, name=ticker, pe=pe, ev_ebitda=ev_ebitda, ev_revenue=ev_revenue,
    )


def test_parse_peer_snapshot_computes_multiples_from_info():
    info = {
        "shortName": "Test Co",
        "marketCap": 1000.0,
        "enterpriseValue": 1100.0,
        "ebitda": 200.0,
        "totalRevenue": 500.0,
        "trailingEps": 2.0,
        "trailingPE": 15.0,
    }
    snap = parse_peer_snapshot("TEST", info)
    assert snap.name == "Test Co"
    assert snap.ev_ebitda == pytest.approx(5.5)   # 1100 / 200
    assert snap.ev_revenue == pytest.approx(2.2)  # 1100 / 500
    assert snap.pe == 15.0


def test_parse_peer_snapshot_handles_missing_fields():
    # Yahoo Finance doesn't always populate every field (e.g. EBITDA can be
    # missing for financials/REITs) — the parser shouldn't blow up.
    snap = parse_peer_snapshot("TEST", {"shortName": "Sparse Co"})
    assert snap.ev_ebitda is None
    assert snap.ev_revenue is None
    assert snap.pe is None


def test_build_comps_table_averages_and_applies_multiples():
    target = PeerSnapshot(
        ticker="TGT", name="Target Co", ebitda=200.0, revenue=800.0, eps=3.0,
    )
    peers = [
        _peer("A", pe=10.0, ev_ebitda=8.0, ev_revenue=2.0),
        _peer("B", pe=20.0, ev_ebitda=12.0, ev_revenue=4.0),
    ]
    result = build_comps_table(target, peers, shares_outstanding=100.0, net_debt=100.0)

    assert result.avg_pe == pytest.approx(15.0)
    assert result.median_pe == pytest.approx(15.0)
    assert result.avg_ev_ebitda == pytest.approx(10.0)
    assert result.avg_ev_revenue == pytest.approx(3.0)

    # EV/EBITDA: implied EV = 10.0 * 200 = 2000; equity = 2000 - 100 = 1900;
    # price = 1900 / 100 shares = 19.0
    assert result.implied_price_ev_ebitda == pytest.approx(19.0)
    # EV/Revenue: implied EV = 3.0 * 800 = 2400; equity = 2300; price = 23.0
    assert result.implied_price_ev_revenue == pytest.approx(23.0)
    # P/E applies directly to EPS, no share count / net debt involved
    assert result.implied_price_pe == pytest.approx(45.0)  # 15.0 * 3.0


def test_build_comps_table_ignores_negative_and_missing_multiples():
    # A distressed peer with a negative EV/EBITDA (negative EBITDA) or a
    # peer missing a field entirely shouldn't skew the average.
    target = PeerSnapshot(ticker="TGT", name="Target Co", ebitda=100.0)
    peers = [
        _peer("A", pe=10.0, ev_ebitda=10.0, ev_revenue=2.0),
        _peer("B", pe=None, ev_ebitda=-5.0, ev_revenue=2.0),  # excluded
    ]
    result = build_comps_table(target, peers, shares_outstanding=10.0, net_debt=0.0)

    assert result.avg_ev_ebitda == pytest.approx(10.0)  # only peer A counted
    assert result.avg_pe == pytest.approx(10.0)          # only peer A had a P/E at all


def test_build_comps_table_handles_no_valid_peers():
    target = PeerSnapshot(ticker="TGT", name="Target Co")
    result = build_comps_table(target, peers=[], shares_outstanding=10.0, net_debt=0.0)

    assert result.avg_pe is None
    assert result.implied_price_ev_ebitda is None
    assert result.implied_price_ev_revenue is None
    assert result.implied_price_pe is None
