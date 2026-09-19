"""
Comparable companies analysis ("comps"): values the target by applying
peer trading multiples (EV/EBITDA, EV/Revenue, P/E) to the target's own
financials, giving a second, independent valuation to set against the DCF.

Unlike the DCF, comps don't need multi-year statements — they need today's
snapshot multiples, which Yahoo Finance already computes and exposes on
`Ticker.info`. So this module reads `info` directly (for peers and for the
target) rather than re-deriving EV/EBITDA from raw financial statements.
"""

import dataclasses
from statistics import median

import yfinance as yf


@dataclasses.dataclass
class PeerSnapshot:
    """Today's trading multiples for one company (peer or target)."""

    ticker: str
    name: str
    market_cap: float = None
    enterprise_value: float = None
    ebitda: float = None
    revenue: float = None
    eps: float = None
    pe: float = None
    ev_ebitda: float = None
    ev_revenue: float = None


@dataclasses.dataclass
class CompsResult:
    target: PeerSnapshot
    peers: list                    # list[PeerSnapshot]

    avg_ev_ebitda: float = None
    median_ev_ebitda: float = None
    avg_ev_revenue: float = None
    median_ev_revenue: float = None
    avg_pe: float = None
    median_pe: float = None

    implied_price_ev_ebitda: float = None
    implied_price_ev_revenue: float = None
    implied_price_pe: float = None


def fetch_raw_info(ticker):
    """I/O boundary: hits Yahoo Finance via yfinance."""
    return yf.Ticker(ticker).info


def parse_peer_snapshot(ticker, info):
    """Pure function: turns a raw yfinance `info` dict into a PeerSnapshot.
    No network access here — easy to unit test with a hand-built dict."""
    market_cap = info.get("marketCap")
    enterprise_value = info.get("enterpriseValue")
    ebitda = info.get("ebitda")
    revenue = info.get("totalRevenue")
    eps = info.get("trailingEps")
    pe = info.get("trailingPE")

    ev_ebitda = (
        enterprise_value / ebitda
        if enterprise_value and ebitda and ebitda > 0 else None
    )
    ev_revenue = (
        enterprise_value / revenue
        if enterprise_value and revenue and revenue > 0 else None
    )

    return PeerSnapshot(
        ticker=ticker.upper(),
        name=info.get("shortName", ticker.upper()),
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        ebitda=ebitda,
        revenue=revenue,
        eps=eps,
        pe=pe,
        ev_ebitda=ev_ebitda,
        ev_revenue=ev_revenue,
    )


def fetch_peer_snapshot(ticker):
    """Convenience wrapper: fetch + parse in one call. Works for peers and
    for the target company alike — both just need today's multiples."""
    return parse_peer_snapshot(ticker, fetch_raw_info(ticker))


def _clean(values):
    """Drop missing/zero/negative multiples before averaging — one peer
    with a distressed or negative EBITDA would otherwise skew the mean
    wildly, which is why real comps screens exclude them too."""
    return [v for v in values if v is not None and v > 0]


def build_comps_table(target, peers, shares_outstanding, net_debt):
    """Applies peer average/median multiples to the target's own EBITDA,
    revenue and EPS to back into an implied share price under each
    method. `target` is the target's own PeerSnapshot (for its EBITDA,
    revenue and EPS); `peers` is a list[PeerSnapshot] for the comp set."""
    ev_ebitda_vals = _clean([p.ev_ebitda for p in peers])
    ev_revenue_vals = _clean([p.ev_revenue for p in peers])
    pe_vals = _clean([p.pe for p in peers])

    avg_ev_ebitda = sum(ev_ebitda_vals) / len(ev_ebitda_vals) if ev_ebitda_vals else None
    median_ev_ebitda = median(ev_ebitda_vals) if ev_ebitda_vals else None
    avg_ev_revenue = sum(ev_revenue_vals) / len(ev_revenue_vals) if ev_revenue_vals else None
    median_ev_revenue = median(ev_revenue_vals) if ev_revenue_vals else None
    avg_pe = sum(pe_vals) / len(pe_vals) if pe_vals else None
    median_pe = median(pe_vals) if pe_vals else None

    implied_price_ev_ebitda = None
    if avg_ev_ebitda and target.ebitda and shares_outstanding:
        implied_ev = avg_ev_ebitda * target.ebitda
        implied_price_ev_ebitda = (implied_ev - net_debt) / shares_outstanding

    implied_price_ev_revenue = None
    if avg_ev_revenue and target.revenue and shares_outstanding:
        implied_ev = avg_ev_revenue * target.revenue
        implied_price_ev_revenue = (implied_ev - net_debt) / shares_outstanding

    implied_price_pe = avg_pe * target.eps if avg_pe and target.eps else None

    return CompsResult(
        target=target,
        peers=peers,
        avg_ev_ebitda=avg_ev_ebitda,
        median_ev_ebitda=median_ev_ebitda,
        avg_ev_revenue=avg_ev_revenue,
        median_ev_revenue=median_ev_revenue,
        avg_pe=avg_pe,
        median_pe=median_pe,
        implied_price_ev_ebitda=implied_price_ev_ebitda,
        implied_price_ev_revenue=implied_price_ev_revenue,
        implied_price_pe=implied_price_pe,
    )


def run_comps(target_ticker, peer_tickers, shares_outstanding, net_debt):
    """Convenience wrapper: fetches the target + all peers and builds the
    comps table in one call."""
    target = fetch_peer_snapshot(target_ticker)
    peers = [fetch_peer_snapshot(t) for t in peer_tickers]
    return build_comps_table(target, peers, shares_outstanding, net_debt)
