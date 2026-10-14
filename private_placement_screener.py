"""Private Placement Screener.

Screens and ranks private placement note offerings the way an institutional buyer would:
apply hard credit limits first, then rank what's left on relative value (spread versus other
deals of the same NAIC designation), credit strength and structure.

Input:  deals.csv (one row per offering; see README for columns). A sample file is created if missing.
Output: screener_results.csv (every deal with pass/fail reasons and score)
        screener_chart.html (interactive spread vs leverage chart)

Usage: python private_placement_screener.py [--deals deals.csv] [--config criteria.json]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
TREASURY_PCT = 4.10   # matched-maturity Treasury yield used to set sample coupons
NAIC_ORDER = ["1.A", "1.B", "1.C", "1.D", "1.E", "1.F", "1.G", "2.A", "2.B", "2.C", "3.A", "3.B", "3.C"]
DEFAULT_CRITERIA = {
    "worst_naic": "2.C",            # investment grade only
    "max_leverage": 4.0,            # total debt / EBITDA
    "min_interest_coverage": 3.0,   # EBITDA / interest
    "max_tenor_years": 15,
    "min_size_musd": 50,
    "require_financial_covenants": True,
    "weights": {"relative_value": 0.5, "credit": 0.35, "structure": 0.15},
}


def sample_deals(n=30, seed=8):
    rng = np.random.default_rng(seed)
    sectors = ["Utilities", "Industrials", "Infrastructure", "Healthcare", "Consumer", "Technology", "Real Estate"]
    naic = rng.choice(NAIC_ORDER[:12], n, p=np.array([1, 1, 2, 3, 4, 5, 5, 8, 8, 6, 3, 2]) / 48)
    notch = np.array([NAIC_ORDER.index(x) for x in naic])
    base_spread = 85 + 14 * notch            # wider spreads for weaker designations
    spread = np.round(base_spread + rng.normal(0, 18, n)).astype(int)
    leverage = np.round(np.clip(1.2 + 0.28 * notch + rng.normal(0, 0.6, n), 0.5, 6.5), 2)
    return pd.DataFrame({
        "deal_id": [f"PP-{i:03d}" for i in range(1, n + 1)],
        "issuer": [f"Issuer {chr(65 + i % 26)}{i // 26 + 1}" for i in range(n)],
        "sector": rng.choice(sectors, n),
        "naic_designation": naic,
        "size_musd": rng.choice([25, 50, 75, 100, 150, 200, 300], n),
        "tenor_years": rng.choice([5, 7, 10, 12, 15, 20], n),
        "coupon_pct": np.round(TREASURY_PCT + spread / 100, 3),   # fixed coupon = Treasury + spread at pricing
        "spread_bps": spread,
        "leverage_x": leverage,
        "interest_coverage_x": np.round(np.clip(9.5 - 1.3 * leverage + rng.normal(0, 0.8, n), 1.2, 14), 2),
        "financial_covenants": rng.random(n) > 0.15,
        "secured": rng.random(n) > 0.6,
    })


def screen(df, c):
    """Apply hard limits. Returns a copy with 'passes' and 'fail_reasons'."""
    worst = NAIC_ORDER.index(c["worst_naic"])
    rules = [
        (df["naic_designation"].map(NAIC_ORDER.index) > worst, f"NAIC below {c['worst_naic']}"),
        (df["leverage_x"] > c["max_leverage"], f"Leverage above {c['max_leverage']}x"),
        (df["interest_coverage_x"] < c["min_interest_coverage"], f"Coverage below {c['min_interest_coverage']}x"),
        (df["tenor_years"] > c["max_tenor_years"], f"Tenor over {c['max_tenor_years']} years"),
        (df["size_musd"] < c["min_size_musd"], f"Size under ${c['min_size_musd']}M"),
    ]
    if c.get("require_financial_covenants"):
        rules.append((~df["financial_covenants"].astype(bool), "No financial covenants"))
    out = df.copy()
    reasons = pd.Series([[] for _ in range(len(df))], index=df.index)
    for mask, msg in rules:
        for i in df.index[mask]:
            reasons[i] = reasons[i] + [msg]
    out["fail_reasons"] = reasons.map("; ".join)
    out["passes"] = reasons.map(len) == 0
    return out


def _pct_rank(s, higher_is_better=True):
    return s.rank(pct=True, ascending=higher_is_better)


def score(df, c):
    """Score 0-100 for deals that pass the screen."""
    out = df.copy()
    peer_median = out.groupby("naic_designation")["spread_bps"].transform("median")
    out["spread_vs_peers_bps"] = out["spread_bps"] - peer_median
    p = out["passes"]
    w = c["weights"]
    rv = _pct_rank(out.loc[p, "spread_vs_peers_bps"])
    credit = (_pct_rank(out.loc[p, "leverage_x"], higher_is_better=False)
              + _pct_rank(out.loc[p, "interest_coverage_x"])) / 2
    structure = (out.loc[p, "secured"].astype(float) * 0.6
                 + _pct_rank(out.loc[p, "tenor_years"], higher_is_better=False) * 0.4)
    out.loc[p, "score"] = (100 * (w["relative_value"] * rv + w["credit"] * credit
                                  + w["structure"] * structure)).round(1)
    out = out.sort_values(["passes", "score"], ascending=[False, False]).reset_index(drop=True)
    out["rank"] = pd.array([pd.NA] * len(out), dtype="Int64")
    out.loc[out["passes"], "rank"] = np.arange(1, out["passes"].sum() + 1)
    return out


def chart(results, path):
    import plotly.express as px
    r = results.assign(status=np.where(results["passes"], "Passes screen", "Fails screen"))
    fig = px.scatter(r, x="leverage_x", y="spread_bps", color="status", size="size_musd", symbol="secured",
                     hover_name="issuer",
                     hover_data=["deal_id", "naic_designation", "interest_coverage_x", "score", "fail_reasons"],
                     labels={"leverage_x": "Leverage (debt / EBITDA)", "spread_bps": "Spread (bps)"},
                     title="Private placement offerings: spread vs leverage")
    fig.write_html(path, include_plotlyjs="cdn")


def run(deals_path, criteria):
    if not Path(deals_path).exists():
        sample_deals().to_csv(deals_path, index=False)
        print(f"No deal file found; wrote sample offerings to {deals_path}")
    deals = pd.read_csv(deals_path)
    results = score(screen(deals, criteria), criteria)
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deals", default=str(ROOT / "deals.csv"))
    p.add_argument("--config", help="JSON file overriding the default criteria")
    args = p.parse_args()
    criteria = dict(DEFAULT_CRITERIA)
    if args.config:
        criteria.update(json.loads(Path(args.config).read_text()))

    results = run(args.deals, criteria)
    results.to_csv(ROOT / "screener_results.csv", index=False)
    chart(results, ROOT / "screener_chart.html")

    pd.set_option("display.width", 160)
    passed = results[results["passes"]]
    print(f"{len(passed)} of {len(results)} offerings pass the screen\n")
    print(passed[["rank", "deal_id", "issuer", "sector", "naic_designation", "spread_bps", "spread_vs_peers_bps",
                  "leverage_x", "interest_coverage_x", "secured", "score"]].head(10).to_string(index=False))
    fails = results.loc[~results["passes"], "fail_reasons"].str.split("; ").explode().value_counts()
    print("\nMost common reasons for failing:\n" + fails.to_string())
    print("\nWrote screener_results.csv and screener_chart.html")


if __name__ == "__main__":
    main()
