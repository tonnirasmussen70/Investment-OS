from __future__ import annotations

from dataclasses import dataclass, field
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
    price_dates: dict[str, pd.Timestamp] = field(default_factory=dict)


def _download_close(
    tickers: list[str],
    period: str = "18mo",
    *,
    auto_adjust: bool = True,
) -> pd.DataFrame:
    cleaned = sorted({str(t).strip() for t in tickers if str(t).strip()})
    if not cleaned:
        return pd.DataFrame()

    try:
        data = yf.download(
            cleaned,
            period=period,
            interval="1d",
            auto_adjust=auto_adjust,
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


def _latest_price(
    ticker: str,
    period: str = "10d",
) -> tuple[float, pd.Timestamp] | None:
    """Hent seneste ujusterede lukkekurs og handelsdato for én ticker."""
    history = _download_close([ticker], period=period, auto_adjust=False)
    if ticker not in history.columns:
        return None

    series = history[ticker].dropna()
    if series.empty:
        return None

    return float(series.iloc[-1]), pd.Timestamp(series.index[-1])


def fetch_price_history(tickers: list[str], period: str = "18mo") -> pd.DataFrame:
    # Momentum beregnes på justerede kurser, så udbytter og splits ikke skaber
    # kunstige kursgab i den historiske analyse.
    return _download_close(tickers, period=period, auto_adjust=True)


def fetch_market_snapshot(
    yahoo_tickers: list[str],
    currencies: list[str],
) -> MarketSnapshot:
    cleaned_tickers = [
        str(ticker).strip()
        for ticker in yahoo_tickers
        if str(ticker).strip()
    ]

    # Positioner skal matche Yahoo Finances viste officielle Close. Historiske
    # analyser bruger justerede kurser, men den aktuelle positionskurs må ikke
    # auto-justeres for udbytter eller splits.
    price_history = _download_close(
        cleaned_tickers,
        period="10d",
        auto_adjust=False,
    )
    prices: dict[str, float] = {}
    price_dates: dict[str, pd.Timestamp] = {}
    retry_prices: list[str] = []

    for ticker in cleaned_tickers:
        if ticker in price_history.columns:
            series = price_history[ticker].dropna()
            if not series.empty:
                prices[ticker] = float(series.iloc[-1])
                price_dates[ticker] = pd.Timestamp(series.index[-1])
                continue
        retry_prices.append(ticker)

    # yfinance kan lejlighedsvis mangle enkelte tickers i en ellers vellykket
    # bulk-download. Genforsøg derfor kun de manglende tickers individuelt,
    # før de klassificeres som reelt manglende markedskurser.
    missing_prices: list[str] = []
    for ticker in retry_prices:
        latest_price = _latest_price(ticker, period="10d")
        if latest_price is None:
            missing_prices.append(ticker)
        else:
            prices[ticker], price_dates[ticker] = latest_price

    fx_to_dkk = {"DKK": 1.0}
    requested_fx = {
        currency: FX_TICKERS[currency]
        for currency in sorted(set(currencies))
        if currency != "DKK" and currency in FX_TICKERS
    }

    fx_history = _download_close(
        list(requested_fx.values()),
        period="10d",
        auto_adjust=False,
    )
    retry_fx: list[tuple[str, str]] = []

    for currency, ticker in requested_fx.items():
        if ticker in fx_history.columns:
            series = fx_history[ticker].dropna()
            if not series.empty:
                fx_to_dkk[currency] = float(series.iloc[-1])
                continue
        retry_fx.append((currency, ticker))

    missing_fx: list[str] = []
    for currency, ticker in retry_fx:
        latest_price = _latest_price(ticker, period="10d")
        if latest_price is None:
            missing_fx.append(currency)
        else:
            fx_to_dkk[currency] = latest_price[0]

    return MarketSnapshot(
        prices=prices,
        fx_to_dkk=fx_to_dkk,
        updated_at=pd.Timestamp(datetime.now(timezone.utc)),
        missing_prices=missing_prices,
        missing_fx=missing_fx,
        price_dates=price_dates,
    )
