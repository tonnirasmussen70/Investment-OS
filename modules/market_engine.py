from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from urllib.parse import quote
from urllib.request import Request, urlopen

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
    drop_empty_rows: bool = True,
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

    data = data.sort_index()
    return data.dropna(how="all") if drop_empty_rows else data


def _timestamp(value) -> pd.Timestamp | None:
    """Normalisér Yahoo-tid til et UTC timestamp."""
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return pd.to_datetime(value, unit="s", utc=True)
        timestamp = pd.Timestamp(value)
        return (
            timestamp.tz_localize("UTC")
            if timestamp.tzinfo is None
            else timestamp.tz_convert("UTC")
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _latest_regular_market_quote(
    ticker: str,
) -> tuple[float, pd.Timestamp] | None:
    """
    Hent Yahoo-quote som fallback, når seneste dagsbar har tom Close.

    Nogle mindre likvide ETF'er får en dagsbar med Open/High/Low og volumen,
    men uden Close. Yahoo-siden viser samtidig den afsluttede kurs i
    regularMarketPrice. Den anvendes kun efter den ordinære handelssessions
    sluttid, så en intradag-kurs ikke fejlagtigt vises som lukkekurs.
    """
    encoded_ticker = quote(str(ticker).strip(), safe="")
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{encoded_ticker}?range=5d&interval=1d&events=div%2Csplits"
    )
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
        result = payload["chart"]["result"][0]
        metadata = result["meta"]
        price = float(metadata["regularMarketPrice"])
    except (KeyError, IndexError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return None

    quote_time = _timestamp(metadata.get("regularMarketTime"))
    market_end = _timestamp(
        metadata.get("currentTradingPeriod", {})
        .get("regular", {})
        .get("end")
    )
    if quote_time is None:
        return None
    if market_end is not None and pd.Timestamp.now(tz="UTC") < market_end:
        return None

    return price, quote_time


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
        # Bevar også den seneste Yahoo-række, når alle Close-værdier er tomme.
        # Datoen bruges til at opdage forsinkede ETF-dagsbarer nedenfor.
        drop_empty_rows=False,
    )
    prices: dict[str, float] = {}
    price_dates: dict[str, pd.Timestamp] = {}
    retry_prices: list[str] = []
    quote_retry_prices: list[str] = []
    latest_batch_date = (
        pd.Timestamp(price_history.index[-1]).date()
        if not price_history.empty
        else None
    )

    for ticker in cleaned_tickers:
        if ticker in price_history.columns:
            series = price_history[ticker].dropna()
            if not series.empty:
                prices[ticker] = float(series.iloc[-1])
                price_dates[ticker] = pd.Timestamp(series.index[-1])
                if (
                    latest_batch_date is not None
                    and price_dates[ticker].date() < latest_batch_date
                ):
                    quote_retry_prices.append(ticker)
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

    # Yahoo kan publicere fredagens regularMarketPrice, mens Close stadig er
    # tom for enkelte ETF'er. Opgradér kun kursen, når quote-datoen er nyere
    # end den seneste udfyldte dagsbar.
    for ticker in sorted(set([*retry_prices, *quote_retry_prices])):
        latest_quote = _latest_regular_market_quote(ticker)
        if latest_quote is None:
            continue
        quote_price, quote_time = latest_quote
        history_date = price_dates.get(ticker)
        if history_date is None or quote_time.date() > history_date.date():
            prices[ticker] = quote_price
            price_dates[ticker] = quote_time

    missing_prices = [
        ticker for ticker in missing_prices if ticker not in prices
    ]

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
