# Private Placement Screener

Screens and ranks private placement note offerings the way an institutional buyer, such as an insurance company investment team, would. It applies hard credit limits first, then ranks the remaining deals on relative value, credit strength and structure.

Private placements don't trade on an exchange, so the screen works from the offering terms and issuer financials rather than market prices or trading volume.

## How it works

**1. Hard limits** (any failure removes the deal, and every reason is recorded)

| Limit | Default |
|---|---|
| NAIC designation | 2.C or better (investment grade) |
| Leverage (total debt / EBITDA) | 4.0x or less |
| Interest coverage (EBITDA / interest) | 3.0x or more |
| Tenor | 15 years or less |
| Deal size | $50M or more |
| Financial covenants | Required |

**2. Score (0–100)** for deals that pass

- **Relative value (50%)**: spread compared with the median spread of deals with the same NAIC designation. Extra spread for the same rating is the main source of value.
- **Credit (35%)**: lower leverage and higher interest coverage
- **Structure (15%)**: secured notes and shorter tenors score higher

Limits and weights can be changed with a JSON file:

```bash
echo '{"max_leverage": 4.5, "worst_naic": "2.B"}' > criteria.json
python private_placement_screener.py --config criteria.json
```

## Run it

```bash
pip install -r requirements.txt
python private_placement_screener.py
pytest -q
```

On the 30 sample offerings in `deals.csv`, 17 pass the screen. The most common reasons for failing are tenor over 15 years, missing financial covenants and deal size. Outputs:

- `screener_results.csv`: every deal with pass/fail, reasons, spread versus peers, score and rank
- `screener_chart.html`: interactive spread vs leverage chart, sized by deal size and marked by pass/fail and security

## Using your own deals

Replace `deals.csv` with a file that has these columns:

`deal_id, issuer, sector, naic_designation, size_musd, tenor_years, coupon_pct, spread_bps, leverage_x, interest_coverage_x, financial_covenants, secured`

Deal terms usually come from offering memoranda or a placement agent's deal sheet. Issuer leverage and coverage come from the financial statements in the data room. If no `deals.csv` exists, the script creates a synthetic sample.

## Tests

The tests check each hard limit, that every failure reason is recorded, that a wider spread than peers scores higher, that failing deals are never scored, that criteria can be overridden, and that sample coupons equal the Treasury rate plus the spread.

**Author:** Robert Torres · MIT License
