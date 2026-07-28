from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


FX_TICKERS = {
    "EUR": "EURDKK=X",
    "USD": "USDDKK=X",
    "SEK": "SEKDKK=X",
    "NOK": "NOKDKK=X",
    "GBP": "GBPDKK=X",
    "CHF": "CHFDKK=X",
    "CAD": "CADDKK=X",
    "JPY": "JPYDKK=X",
}


@dataclass
class MarketSnapshot:
    prices: dict[str, float]
    fx_to_dkk: dict[str, float]
    updated_at: pd.Timestamp
    missing_prices: list[str]
    missing_fx: list[str]


def _download_close(tickers: list[str], period: str = "18mo") -> pd.DataFrame:
    cleaned = sorted({str(t).strip() for t in tickers if str(t).strip()})
    if not cleaned:
        return pd.DataFrame()

    try:
        data = yf.download(
            cleaned,
            period=period,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    if isinstance(data, pd.DataFrame) and "Close" in data.columns:
        data = data["Close"]

    if isinstance(data, pd.Series):
        data = data.to_frame(name=cleaned[0])

    if not isinstance(data, pd.DataFrame):
        return pd.DataFrame()

    if len(cleaned) == 1 and data.shape[1] == 1:
        data.columns = cleaned

    return data.sort_index().dropna(how="all")


def fetch_price_history(tickers: list[str], period: str = "18mo") -> pd.DataFrame:
    return _download_close(tickers, period=period)


def fetch_market_snapshot(
    yahoo_tickers: list[str],
    currencies: list[str],
) -> MarketSnapshot:
    price_history = _download_close(yahoo_tickers, period="10d")
    prices: dict[str, float] = {}
    missing_prices: list[str] = []

    for ticker in yahoo_tickers:
        if ticker in price_history.columns:
            series = price_history[ticker].dropna()
            if not series.empty:
                prices[ticker] = float(series.iloc[-1])
                continue
        missing_prices.append(ticker)

    fx_to_dkk = {"DKK": 1.0}
    requested_fx = {
        currency: FX_TICKERS[currency]
        for currency in sorted(set(currencies))
        if currency != "DKK" and currency in FX_TICKERS
    }

    fx_history = _download_close(list(requested_fx.values()), period="10d")
    missing_fx: list[str] = []

    for currency, ticker in requested_fx.items():
        if ticker in fx_history.columns:
            series = fx_history[ticker].dropna()
            if not series.empty:
                fx_to_dkk[currency] = float(series.iloc[-1])
                continue
        missing_fx.append(currency)

    return MarketSnapshot(
        prices=prices,
        fx_to_dkk=fx_to_dkk,
        updated_at=pd.Timestamp(datetime.now(timezone.utc)),
        missing_prices=missing_prices,
        missing_fx=missing_fx,
    )
