from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time

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
    warnings: list[str] = field(default_factory=list)


def _normalize_close_data(
    data: pd.DataFrame | pd.Series,
    tickers: list[str],
) -> pd.DataFrame:
    """Normalisér yfinance-output til én DataFrame med tickere som kolonner."""
    if isinstance(data, pd.DataFrame) and "Close" in data.columns:
        data = data["Close"]

    if isinstance(data, pd.Series):
        name = tickers[0] if tickers else "Close"
        data = data.to_frame(name=name)

    if not isinstance(data, pd.DataFrame):
        return pd.DataFrame()

    if len(tickers) == 1 and data.shape[1] == 1:
        data.columns = tickers

    return data.sort_index().dropna(how="all")


def _download_batch(
    tickers: list[str],
    period: str,
) -> pd.DataFrame:
    """Hent et batch uden at kaste fejl videre til dashboardet."""
    try:
        data = yf.download(
            tickers,
            period=period,
            auto_adjust=True,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception:
        return pd.DataFrame()

    return _normalize_close_data(data, tickers)


def _download_single(
    ticker: str,
    period: str,
) -> pd.Series:
    """Fallback: hent én ticker ad gangen."""
    try:
        data = yf.download(
            ticker,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        return pd.Series(dtype=float)

    normalized = _normalize_close_data(data, [ticker])
    if ticker not in normalized.columns:
        return pd.Series(dtype=float)

    return normalized[ticker].dropna()


def _download_close(
    tickers: list[str],
    period: str = "18mo",
    retries: int = 2,
    retry_delay: float = 1.0,
) -> pd.DataFrame:
    """
    Robust kursindlæsning.

    1. Batch-download.
    2. Genforsøg ved manglende data.
    3. Individuel fallback for tickere, som stadig mangler.
    """
    cleaned = sorted(
        {
            str(ticker).strip()
            for ticker in tickers
            if str(ticker).strip()
        }
    )
    if not cleaned:
        return pd.DataFrame()

    combined = pd.DataFrame()

    for attempt in range(retries + 1):
        batch = _download_batch(cleaned, period)

        if not batch.empty:
            combined = batch if combined.empty else combined.combine_first(batch)

        available = set(combined.columns)
        missing = [ticker for ticker in cleaned if ticker not in available]

        if not missing:
            break

        if attempt < retries:
            time.sleep(retry_delay * (attempt + 1))

    available = set(combined.columns)
    missing = [ticker for ticker in cleaned if ticker not in available]

    for ticker in missing:
        series = _download_single(ticker, period)
        if not series.empty:
            combined[ticker] = series

    return combined.sort_index().dropna(how="all")


def fetch_price_history(
    tickers: list[str],
    period: str = "18mo",
) -> pd.DataFrame:
    """Hent historiske lukkekurser med retry og individuel fallback."""
    return _download_close(
        tickers,
        period=period,
        retries=2,
        retry_delay=1.0,
    )


def fetch_market_snapshot(
    yahoo_tickers: list[str],
    currencies: list[str],
) -> MarketSnapshot:
    """Hent aktuelle aktie-, ETF- og valutakurser."""
    warnings: list[str] = []

    unique_tickers = sorted(
        {
            str(ticker).strip()
            for ticker in yahoo_tickers
            if str(ticker).strip()
        }
    )

    price_history = _download_close(
        unique_tickers,
        period="10d",
        retries=2,
        retry_delay=1.0,
    )

    prices: dict[str, float] = {}
    missing_prices: list[str] = []

    for ticker in unique_tickers:
        if ticker in price_history.columns:
            series = price_history[ticker].dropna()
            if not series.empty:
                prices[ticker] = float(series.iloc[-1])
                continue
        missing_prices.append(ticker)

    if missing_prices:
        warnings.append(
            f"{len(missing_prices)} markedskurser kunne ikke hentes."
        )

    normalized_currencies = sorted(
        {
            str(currency).strip().upper()
            for currency in currencies
            if str(currency).strip()
        }
    )

    fx_to_dkk = {"DKK": 1.0}
    unsupported_fx = [
        currency
        for currency in normalized_currencies
        if currency != "DKK" and currency not in FX_TICKERS
    ]

    requested_fx = {
        currency: FX_TICKERS[currency]
        for currency in normalized_currencies
        if currency != "DKK" and currency in FX_TICKERS
    }

    fx_history = _download_close(
        list(requested_fx.values()),
        period="10d",
        retries=2,
        retry_delay=1.0,
    )

    missing_fx: list[str] = []

    for currency, ticker in requested_fx.items():
        if ticker in fx_history.columns:
            series = fx_history[ticker].dropna()
            if not series.empty:
                fx_to_dkk[currency] = float(series.iloc[-1])
                continue
        missing_fx.append(currency)

    missing_fx.extend(unsupported_fx)
    missing_fx = sorted(set(missing_fx))

    if unsupported_fx:
        warnings.append(
            "Ikke-understøttede valutaer: "
            + ", ".join(sorted(unsupported_fx))
        )

    if missing_fx:
        warnings.append(
            f"{len(missing_fx)} valutakurser kunne ikke hentes."
        )

    return MarketSnapshot(
        prices=prices,
        fx_to_dkk=fx_to_dkk,
        updated_at=pd.Timestamp(datetime.now(timezone.utc)),
        missing_prices=missing_prices,
        missing_fx=missing_fx,
        warnings=warnings,
    )
