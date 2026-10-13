"""ETF holdings momentum breadth; diagnostic only, never a trading signal."""
from __future__ import annotations

import numpy as np
import pandas as pd

PERIODS = {"1W": 5, "1M": 21, "3M": 63}


def holdings_breadth(holdings: pd.DataFrame, close: pd.DataFrame, *, top_n: int = 20) -> dict:
    """Analyze constituent momentum using historical adjusted closing prices.

    holdings columns: Ticker, Weight (fraction 0..1), optionally Name.
    close: date-indexed prices, columns named after Ticker; same currency per
    security across time. Returns are local-currency proxy contributions, not
    FX-adjusted official ETF performance attribution.
    """
    required = {"Ticker", "Weight"}
    if not required.issubset(holdings.columns):
        raise ValueError("Holdings kræver kolonnerne Ticker og Weight.")
    if not 10 <= top_n <= 20:
        raise ValueError("top_n skal være mellem 10 og 20.")
    h = holdings.copy()
    h["Ticker"] = h["Ticker"].astype(str).str.strip().str.upper()
    h["Weight"] = pd.to_numeric(h["Weight"], errors="coerce")
    h = h.dropna(subset=["Weight"])
    h = h[(h.Ticker != "") & h.Weight.gt(0) & h.Weight.le(1)]
    h = h.drop_duplicates("Ticker", keep="first").sort_values("Weight", ascending=False).head(top_n)
    if h.empty:
        return {"status": "Ingen gyldige beholdninger", "table": pd.DataFrame()}
    if h.Weight.sum() > 1.01:
        raise ValueError("Vægte skal angives som decimaler, fx 0.065 for 6,5%.")
    p = close.sort_index().copy()
    p = p.loc[~p.index.duplicated(keep="last")]
    output = h.copy()
    for label, days in PERIODS.items():
        returns = {}
        for ticker in h["Ticker"]:
            if ticker not in p.columns:
                continue
            series = pd.to_numeric(p[ticker], errors="coerce").dropna()
            if len(series) <= days:
                continue
            start, end = float(series.iloc[-days-1]), float(series.iloc[-1])
            if np.isfinite(start) and np.isfinite(end) and start > 0 and end > 0:
                returns[ticker] = end / start - 1
        output[label] = output["Ticker"].map(returns)
        output[f"Contribution_{label}"] = output["Weight"] * output[label]

    period = "1M"
    valid = output.dropna(subset=[period]).copy()
    weight_coverage = float(valid.Weight.sum() / h.Weight.sum()) if h.Weight.sum() else 0.0
    positive_weight = float(valid.loc[valid[period] > 0, "Weight"].sum())
    breadth = positive_weight / float(valid.Weight.sum()) if len(valid) else np.nan
    pos_contributions = valid[f"Contribution_{period}"].clip(lower=0)
    total_pos = float(pos_contributions.sum())
    top3_share = float(pos_contributions.nlargest(3).sum() / total_pos) if total_pos > 0 else np.nan
    effective = float(total_pos**2 / (pos_contributions.pow(2).sum())) if total_pos > 0 else np.nan
    # Minimum coverage gates protect against misleading labels.
    sufficiently_covered = len(valid) >= min(10, len(h)) and weight_coverage >= 0.80
    if not sufficiently_covered:
        category = "Utilstrækkelige data"
    elif total_pos <= 0:
        category = "Ingen positive bidrag"
    elif breadth >= 0.70 and top3_share <= 0.50:
        category = "Bredt"
    elif breadth < 0.40 or top3_share >= 0.75:
        category = "Smalt"
    else:
        category = "Blandet"
    return {
        "status": category, "table": output,
        "holdings_count": len(h), "priced_count": len(valid),
        "weight_coverage": weight_coverage, "positive_weight_breadth": breadth,
        "top3_positive_contribution_share": top3_share,
        "effective_positive_contributors": effective,
        "proxy_contribution_1m": float(valid[f"Contribution_{period}"].sum()),
    }
