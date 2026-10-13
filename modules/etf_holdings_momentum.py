"""Lightweight breadth of the ten largest ETF constituents (informational only)."""
from __future__ import annotations

import pandas as pd

TOP_N = 10
MONTH_TRADING_DAYS = 21


def holdings_breadth(holdings: pd.DataFrame, close: pd.DataFrame) -> dict:
    """Count constituents with positive adjusted 1M return.

    Input: a manually maintained top-ten list in descending holding size,
    with a Ticker column (Yahoo-compatible). This is NOT weighted return
    attribution, and cannot change Investment OS trade signals.
    """
    if "Ticker" not in holdings.columns:
        raise ValueError("Top-10-listen mangler kolonnen Ticker.")
    tickers = holdings["Ticker"].dropna().astype(str).str.strip()
    if len(tickers) != TOP_N or tickers.eq("").any() or tickers.str.upper().duplicated().any():
        raise ValueError("Listen skal indeholde præcis 10 unikke tickere.")
    tickers = tickers.tolist()

    history = close.sort_index()
    history = history.loc[~history.index.duplicated(keep="last")]
    returns = []
    for ticker in tickers:
        if ticker not in history.columns:
            returns.append(float("nan"))
            continue
        series = pd.to_numeric(history[ticker], errors="coerce").dropna()
        # Reject stale observations relative to the latest available price date.
        if len(series) <= MONTH_TRADING_DAYS or (
            isinstance(history.index, pd.DatetimeIndex)
            and (pd.Timestamp(history.index[-1]) - pd.Timestamp(series.index[-1])).days > 7
        ):
            returns.append(float("nan"))
            continue
        earlier = float(series.iloc[-MONTH_TRADING_DAYS - 1])
        latest = float(series.iloc[-1])
        returns.append(latest / earlier - 1 if earlier > 0 and latest > 0 else float("nan"))

    data = pd.DataFrame({"Ticker": tickers, "Return_1M": returns})
    valid = data["Return_1M"].notna()
    covered = int(valid.sum())
    positive = int(data.loc[valid, "Return_1M"].gt(0).sum())
    if covered != TOP_N:
        status = "Ikke tilgængelig"
    elif positive >= 7:
        status = "Bredt"
    elif positive >= 4:
        status = "Blandet"
    else:
        status = "Smalt"
    return {
        "status": status,
        "positive": positive,
        "covered": covered,
        "total": TOP_N,
    }
