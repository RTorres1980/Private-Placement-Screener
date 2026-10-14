import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import private_placement_screener as pps  # noqa: E402


def deal(**kw):
    d = {"deal_id": "D", "issuer": "X", "sector": "Utilities", "naic_designation": "1.F", "size_musd": 100,
         "tenor_years": 10, "coupon_pct": 5.5, "spread_bps": 140, "leverage_x": 2.5,
         "interest_coverage_x": 6.0, "financial_covenants": True, "secured": False}
    d.update(kw)
    return d


def test_each_hard_limit():
    df = pd.DataFrame([
        deal(deal_id="ok"),
        deal(deal_id="junk", naic_designation="3.A"),
        deal(deal_id="levered", leverage_x=4.5),
        deal(deal_id="thin", interest_coverage_x=2.0),
        deal(deal_id="long", tenor_years=20),
        deal(deal_id="small", size_musd=25),
        deal(deal_id="cov-lite", financial_covenants=False),
    ])
    r = pps.screen(df, pps.DEFAULT_CRITERIA).set_index("deal_id")
    assert r.loc["ok", "passes"]
    assert r["passes"].sum() == 1
    assert "NAIC below" in r.loc["junk", "fail_reasons"]
    assert "Leverage" in r.loc["levered", "fail_reasons"]
    assert "Coverage" in r.loc["thin", "fail_reasons"]
    assert "Tenor" in r.loc["long", "fail_reasons"]
    assert "Size" in r.loc["small", "fail_reasons"]
    assert "covenants" in r.loc["cov-lite", "fail_reasons"]


def test_multiple_failures_are_all_listed():
    r = pps.screen(pd.DataFrame([deal(leverage_x=5, size_musd=10)]), pps.DEFAULT_CRITERIA)
    assert r.loc[0, "fail_reasons"].count(";") == 1


def test_wider_spread_than_peers_scores_higher():
    df = pd.DataFrame([deal(deal_id="rich", spread_bps=120), deal(deal_id="cheap", spread_bps=180),
                       deal(deal_id="mid", spread_bps=150)])
    r = pps.score(pps.screen(df, pps.DEFAULT_CRITERIA), pps.DEFAULT_CRITERIA).set_index("deal_id")
    assert r.loc["cheap", "score"] > r.loc["rich", "score"]
    assert r.loc["cheap", "rank"] == 1
    assert r.loc["mid", "spread_vs_peers_bps"] == 0


def test_failing_deals_are_not_scored():
    df = pd.DataFrame([deal(deal_id="ok"), deal(deal_id="bad", leverage_x=9)])
    r = pps.score(pps.screen(df, pps.DEFAULT_CRITERIA), pps.DEFAULT_CRITERIA).set_index("deal_id")
    assert pd.isna(r.loc["bad", "score"]) and pd.isna(r.loc["bad", "rank"])


def test_custom_criteria_loosen_screen():
    df = pd.DataFrame([deal(leverage_x=4.5)])
    loose = dict(pps.DEFAULT_CRITERIA, max_leverage=5.0)
    assert pps.screen(df, loose)["passes"].all()


def test_sample_data_coupon_is_treasury_plus_spread():
    s = pps.sample_deals()
    assert ((s["coupon_pct"] - (pps.TREASURY_PCT + s["spread_bps"] / 100)).abs() < 0.001).all()
