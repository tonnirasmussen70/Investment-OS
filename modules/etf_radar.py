"""EUR UCITS ETF momentum/risk research ranking and last-good snapshot.

No live values are bundled. All funds must pass validation before replacing a
snapshot, so a missing fund cannot silently change the relative ranking.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import numpy as np
import pandas as pd
import yfinance as yf


METHOD = "etf-momentum-risk-v1"
REFRESH_HOURS = 6
MAX_AGE_DAYS = 7
WEIGHTS = {"Return_1M": .20, "Return_3M": .25, "Return_6M": .25,
           "Volatility_3M": .15, "Max_Drawdown_6M": .15}
METRICS = list(WEIGHTS)


@dataclass(frozen=True)
class ETFRadar:
    data: pd.DataFrame
    as_of: str | None = None
    generated_at: str | None = None
    notes: tuple[str, ...] = ()
    refreshed: bool = False
    persisted: bool = False


def _now(value=None) -> pd.Timestamp:
    timestamp = pd.Timestamp.now(tz="UTC") if value is None else pd.Timestamp(value)
    return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")


def load_universe(path) -> list[dict]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    funds = payload.get("funds", [])
    if not isinstance(funds, list) or len(funds) < 2:
        raise ValueError("ETF-universet skal indeholde mindst to fonde.")
    for fund in funds:
        for field in ("Name", "Ticker", "ISIN", "Currency", "Exposure", "Issuer_Source"):
            if not isinstance(fund.get(field), str) or not fund[field].strip():
                raise ValueError(f"ETF-universet mangler {field}.")
        if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", fund["ISIN"]):
            raise ValueError("Ugyldigt ISIN i ETF-universet.")
        if fund["Currency"] != "EUR" or not fund["Ticker"].endswith(".DE"):
            raise ValueError("ETF-universet skal bruge EUR-noteringer på Xetra.")
        if "UCITS" not in fund["Name"]:
            raise ValueError("ETF-universet må kun indeholde UCITS-fonde.")
    for field in ("ISIN", "Ticker"):
        if len({f[field] for f in funds}) != len(funds):
            raise ValueError(f"Dubleret {field} i ETF-universet.")
    return funds


def universe_hash(funds) -> str:
    canonical = sorted(funds, key=lambda f: f["ISIN"])
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


def yahoo_history(fund: dict) -> pd.Series:
    ticker = yf.Ticker(fund["Ticker"])
    frame = ticker.history(period="1y", interval="1d", auto_adjust=True,
                           actions=False, timeout=10, raise_errors=True)
    metadata = ticker.get_history_metadata()
    if metadata.get("currency") != "EUR":
        raise ValueError("Yahoo-noteringen er ikke bekræftet i EUR.")
    if metadata.get("instrumentType") != "ETF":
        raise ValueError("Yahoo-instrumenttypen er ikke ETF.")
    if str(metadata.get("symbol", "")).upper() != fund["Ticker"]:
        raise ValueError("Yahoo-symbol matcher ikke ETF-universet.")
    if frame.empty or "Close" not in frame:
        raise ValueError("Yahoo returnerede ingen justerede lukkekurser.")
    return frame["Close"]


def _clean_history(history, today) -> pd.Series:
    if not isinstance(history, pd.Series) or history.empty:
        raise ValueError("Tom kurshistorik.")
    prices = pd.to_numeric(history, errors="coerce").copy()
    dates = pd.DatetimeIndex(pd.to_datetime(prices.index))
    # Daily bars carry the exchange's local date. Strip timezone without shifting it.
    prices.index = dates.tz_localize(None).normalize()
    prices = prices.loc[prices.index < today].sort_index()
    if prices.index.has_duplicates or prices.index.hasnans:
        raise ValueError("Dublerede eller ugyldige kursdatoer.")
    prices = prices.dropna()
    if len(prices) < 127 or not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Kræver mindst 127 gyldige positive lukkekurser.")
    if (today - prices.index[-1]).days > MAX_AGE_DAYS:
        raise ValueError("Seneste lukkekurs er mere end 7 dage gammel.")
    if prices.index[-127:].to_series().diff().dt.days.max() > 7:
        raise ValueError("Kurshistorikken har et hul på mere end 7 dage.")
    return prices


def rank_etfs(funds: list[dict], histories: dict[str, pd.Series], *, now=None) -> pd.DataFrame:
    """Compare all funds on an identical date grid, using completed sessions.

    1/3/6 months = 21/63/126 common trading sessions. Returns are fractions.
    Score = weighted cross-sectional percentile ranks, not expected returns.
    """
    today = _now(now).tz_convert("Europe/Berlin").tz_localize(None).normalize()
    cleaned = {}
    for fund in funds:
        symbol = fund["Ticker"]
        try:
            cleaned[symbol] = _clean_history(histories.get(symbol), today)
        except ValueError as exc:
            raise ValueError(f"{symbol}: {exc}") from exc
    grid = pd.concat(cleaned, axis=1, join="inner").dropna().sort_index()
    if len(grid) < 127:
        raise ValueError("Utilstrækkelig fælles kurshistorik til 6 måneders sammenligning.")
    if (today - grid.index[-1]).days > MAX_AGE_DAYS:
        raise ValueError("Den fælles kursdato er mere end 7 dage gammel.")
    if grid.index[-127:].to_series().diff().dt.days.max() > 7:
        raise ValueError("Huller i den fælles kurshistorik.")
    if (grid.index[-1] - grid.index[-127]).days > 195:
        raise ValueError("For mange manglende handelsdage i den fælles historik.")
    rows = []
    for fund in funds:
        prices = grid[fund["Ticker"]]
        returns = prices.pct_change(fill_method=None).iloc[-63:]
        window = prices.iloc[-127:]
        row = dict(fund)
        row.update({f"Return_{label}": float(prices.iloc[-1] / prices.iloc[-(days + 1)] - 1)
                    for label, days in (("1M", 21), ("3M", 63), ("6M", 126))})
        row["Volatility_3M"] = float(returns.std(ddof=1) * np.sqrt(252))
        row["Max_Drawdown_6M"] = float((window / window.cummax() - 1).min())
        row["As_Of"] = grid.index[-1].date().isoformat()
        row["Research_Status"] = "Positivt momentum" if row["Return_3M"] > 0 and row["Return_6M"] > 0 else "Afvent – svagt momentum"
        row["justETF"] = "https://www.justetf.com/en/etf-profile.html?isin=" + fund["ISIN"]
        row["Yahoo"] = "https://finance.yahoo.com/quote/" + fund["Ticker"] + "/"
        rows.append(row)
    result = pd.DataFrame(rows)
    if not np.isfinite(result[METRICS].to_numpy()).all():
        raise ValueError("Rangeringen indeholder ugyldige tal.")
    # Equal values receive equal ranks. Best/worst map to 100/0; all equal -> 50.
    score = pd.Series(0.0, index=result.index)
    for column, weight in WEIGHTS.items():
        values = -result[column] if column == "Volatility_3M" else result[column]
        rank = (values.rank(method="average") - 1) / (len(values) - 1)
        score += rank * weight * 100
    result["Score"] = score.round(2)
    return result.sort_values(["Score", "Return_6M", "ISIN"], ascending=[False, False, True]).reset_index(drop=True)


def _validate_snapshot(payload, funds, now):
    if payload.get("methodology") != METHOD or payload.get("universe_sha256") != universe_hash(funds):
        raise ValueError("Snapshot matcher ikke ETF-univers eller metode.")
    generated = _now(payload["generated_at"])
    as_of = pd.Timestamp(payload["as_of"])
    today = now.tz_convert("Europe/Berlin").tz_localize(None).normalize()
    if pd.isna(generated) or pd.isna(as_of) or as_of.isoformat()[:10] != payload["as_of"] or len(payload["as_of"]) != 10:
        raise ValueError("Snapshot har ugyldige datoer.")
    if generated > now + pd.Timedelta(minutes=5) or as_of.tzinfo is not None or as_of >= today or as_of > generated.tz_convert("Europe/Berlin").tz_localize(None):
        raise ValueError("Snapshot har ugyldige datoer.")
    data = pd.DataFrame(payload["candidates"])
    expected = {fund["ISIN"]: fund for fund in funds}
    if len(data) != len(funds) or set(data["ISIN"]) != set(expected) or data["ISIN"].duplicated().any():
        raise ValueError("Snapshot dækker ikke hele ETF-universet.")
    if not np.isfinite(data[METRICS + ["Score"]].to_numpy(dtype=float)).all():
        raise ValueError("Snapshot har ugyldige tal.")
    if not data["Score"].between(0, 100).all() or (data["Volatility_3M"] < 0).any() or not data["Max_Drawdown_6M"].between(-1, 0).all():
        raise ValueError("Snapshot har ugyldige score- eller risikoværdier.")
    if (data[["Return_1M", "Return_3M", "Return_6M"]] <= -1).any().any():
        raise ValueError("Snapshot har ugyldige afkast.")
    for row in data.to_dict("records"):
        if row["As_Of"] != payload["as_of"]:
            raise ValueError("Snapshot har blandede kursdatoer.")
        fund = expected[row["ISIN"]]
        if any(row[key] != fund[key] for key in fund):
            raise ValueError("Snapshot-identitet matcher ikke ETF-universet.")
    return data.sort_values(["Score", "Return_6M", "ISIN"], ascending=[False, False, True]).reset_index(drop=True)


def _save_snapshot(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".etf-radar-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_or_refresh_etf_radar(data_dir="data", *, force=False, now=None, fetch_history=None) -> ETFRadar:
    """Refresh all funds or retain the unmodified last-good snapshot on failure."""
    now = _now(now)
    path = Path(data_dir) / "etf_radar.json"
    notes = []
    try:
        funds = load_universe(Path(data_dir) / "etf_universe.json")
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return ETFRadar(pd.DataFrame(), notes=(f"ETF-universet kunne ikke indlæses: {exc}",))
    previous = None
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            previous = ETFRadar(_validate_snapshot(payload, funds, now), payload["as_of"], payload["generated_at"], persisted=True)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            notes.append("Tidligere ETF-snapshot er ugyldigt og vises ikke.")
    if previous and not force:
        if now - _now(previous.generated_at) < pd.Timedelta(hours=REFRESH_HOURS) and (now.normalize() - pd.Timestamp(previous.as_of, tz="UTC")).days <= MAX_AGE_DAYS:
            return previous
    histories, errors = {}, []
    fetch = fetch_history or yahoo_history
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, fund): fund["Ticker"] for fund in funds}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                histories[symbol] = future.result()
            except Exception as exc:
                errors.append(f"{symbol}: {type(exc).__name__}")
    try:
        if errors:
            raise ValueError("Manglende Yahoo-data: " + ", ".join(sorted(errors)))
        ranked = rank_etfs(funds, histories, now=now)
        payload = {"methodology": METHOD, "universe_sha256": universe_hash(funds),
                   "generated_at": now.isoformat(), "as_of": ranked.iloc[0]["As_Of"],
                   "source": "Yahoo Finance via yfinance", "currency": "EUR",
                   "candidates": ranked.to_dict("records")}
        _validate_snapshot(payload, funds, now)
    except (ValueError, KeyError, TypeError) as exc:
        notes.append(f"Yahoo-opdatering mislykkedes. {exc}")
        if previous:
            notes.append("Viser seneste gyldige ETF-data. Rangeringen er ikke opdateret.")
            return ETFRadar(previous.data, previous.as_of, previous.generated_at, tuple(notes), persisted=True)
        return ETFRadar(pd.DataFrame(), notes=tuple(notes))
    persisted = True
    try:
        _save_snapshot(path, payload)
    except OSError:
        persisted = False
        notes.append("Nye ETF-data vises, men kunne ikke gemmes til næste opstart.")
    return ETFRadar(ranked, payload["as_of"], payload["generated_at"], tuple(notes), refreshed=True, persisted=persisted)
