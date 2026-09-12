from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO, StringIO
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

import numpy as np
import pandas as pd


FRED_SERIES = {
    "US10Y": "DGS10",
    "US2Y": "DGS2",
    "Inflation_10Y": "T10YIE",
    "HY_Spread": "BAMLH0A0HYM2",
}

COMPONENT_WEIGHTS = {
    "US 10Y niveau": 0.25,
    "US 10Y trend": 0.20,
    "2Y–10Y rentekurve": 0.15,
    "Inflationspres": 0.20,
    "Kredit-/likviditetsstress": 0.20,
}


@dataclass(frozen=True)
class MacroRateRegime:
    """Markedsdækkende risiko-overlay; aldrig et køb/salg-signal."""

    score: float
    level: str
    primary_driver: str
    impact: str
    data_quality: float
    components: dict[str, float]
    observations: dict[str, float]
    as_of: pd.Timestamp | None


def _clean_series(values: pd.Series | None) -> pd.Series:
    if values is None:
        return pd.Series(dtype=float)
    result = pd.to_numeric(values, errors="coerce").dropna().sort_index()
    return result.loc[~result.index.duplicated(keep="last")]


def _linear_score(value: float, anchors: list[tuple[float, float]]) -> float:
    if pd.isna(value):
        return np.nan
    x = [anchor[0] for anchor in anchors]
    y = [anchor[1] for anchor in anchors]
    return float(np.interp(float(value), x, y))


def _period_change(series: pd.Series, periods: int) -> float:
    clean = _clean_series(series)
    if len(clean) <= periods:
        return np.nan
    return float(clean.iloc[-1] - clean.iloc[-(periods + 1)])


def _rate_level_score(us10y: pd.Series) -> float:
    clean = _clean_series(us10y)
    if clean.empty:
        return np.nan
    return _linear_score(
        float(clean.iloc[-1]),
        [(3.50, 15), (4.25, 40), (4.75, 60), (5.00, 75), (5.25, 90), (5.50, 100)],
    )


def _rate_trend_score(us10y: pd.Series) -> float:
    clean = _clean_series(us10y)
    if len(clean) < 22:
        return np.nan

    change_1m = _period_change(clean, 21)
    change_3m = _period_change(clean, 63)
    acceleration = np.nan
    if len(clean) >= 43:
        current_month = float(clean.iloc[-1] - clean.iloc[-22])
        previous_month = float(clean.iloc[-22] - clean.iloc[-43])
        acceleration = current_month - previous_month

    parts = {
        "1M": (_linear_score(change_1m, [(-0.50, 0), (0.00, 50), (0.50, 100)]), 0.40),
        "3M": (_linear_score(change_3m, [(-0.75, 0), (0.00, 50), (0.75, 100)]), 0.40),
        "Acceleration": (
            _linear_score(acceleration, [(-0.35, 0), (0.00, 50), (0.35, 100)]),
            0.20,
        ),
    }
    available = [(score, weight) for score, weight in parts.values() if pd.notna(score)]
    if not available:
        return np.nan
    return float(sum(score * weight for score, weight in available) / sum(weight for _, weight in available))


def _curve_score(us10y: pd.Series, us2y: pd.Series) -> tuple[float, float]:
    ten = _clean_series(us10y)
    two = _clean_series(us2y)
    aligned = pd.concat([ten.rename("10Y"), two.rename("2Y")], axis=1).dropna()
    if aligned.empty:
        return np.nan, np.nan
    spread = float(aligned.iloc[-1]["10Y"] - aligned.iloc[-1]["2Y"])
    score = _linear_score(
        spread,
        [(-1.00, 95), (-0.50, 85), (0.00, 65), (0.50, 35), (1.00, 20), (2.00, 10)],
    )
    return score, spread


def _inflation_score(inflation: pd.Series) -> float:
    clean = _clean_series(inflation)
    if clean.empty:
        return np.nan
    level = _linear_score(
        float(clean.iloc[-1]),
        [(1.75, 10), (2.00, 25), (2.40, 50), (2.70, 75), (3.00, 95)],
    )
    trend = _linear_score(
        _period_change(clean, 63),
        [(-0.40, 0), (0.00, 50), (0.40, 100)],
    )
    return float(level if pd.isna(trend) else 0.70 * level + 0.30 * trend)


def _credit_score(hy_spread: pd.Series) -> float:
    clean = _clean_series(hy_spread)
    if clean.empty:
        return np.nan
    level = _linear_score(
        float(clean.iloc[-1]),
        [(2.50, 10), (3.00, 25), (4.00, 50), (5.50, 75), (7.00, 95), (9.00, 100)],
    )
    trend = _linear_score(
        _period_change(clean, 63),
        [(-1.00, 0), (0.00, 50), (1.50, 100)],
    )
    return float(level if pd.isna(trend) else 0.70 * level + 0.30 * trend)


def macro_risk_level(score: float) -> str:
    if pd.isna(score):
        return "Ukendt"
    if score <= 25:
        return "Lav"
    if score <= 50:
        return "Moderat"
    if score <= 75:
        return "Høj"
    return "Meget høj"


def macro_risk_impact(score: float) -> str:
    if pd.isna(score):
        return "Kan ikke vurderes"
    if score <= 25:
        return "Begrænset risiko-overlay"
    if score <= 50:
        return "Moderat risiko-overlay"
    if score <= 75:
        return "Forhøjet risiko-overlay"
    return "Markant risiko-overlay"


def calculate_macro_rate_regime(history: pd.DataFrame) -> MacroRateRegime:
    """Beregn en 0–100 risikofaktor fra observerede makro- og rentedata."""
    source = history if history is not None else pd.DataFrame()
    us10y = _clean_series(source.get("US10Y"))
    us2y = _clean_series(source.get("US2Y"))
    inflation = _clean_series(source.get("Inflation_10Y"))
    credit = _clean_series(source.get("HY_Spread"))

    curve_score, curve_spread = _curve_score(us10y, us2y)
    components = {
        "US 10Y niveau": _rate_level_score(us10y),
        "US 10Y trend": _rate_trend_score(us10y),
        "2Y–10Y rentekurve": curve_score,
        "Inflationspres": _inflation_score(inflation),
        "Kredit-/likviditetsstress": _credit_score(credit),
    }
    available = {
        name: value for name, value in components.items() if pd.notna(value)
    }
    available_weight = sum(COMPONENT_WEIGHTS[name] for name in available)
    score = (
        sum(value * COMPONENT_WEIGHTS[name] for name, value in available.items())
        / available_weight
        if available_weight > 0
        else np.nan
    )
    score = float(np.clip(score, 0, 100)) if pd.notna(score) else np.nan

    if available:
        primary_driver = max(
            available,
            key=lambda name: available[name] * COMPONENT_WEIGHTS[name],
        )
    else:
        primary_driver = "Utilstrækkelige data"

    observations = {
        "US10Y": float(us10y.iloc[-1]) if not us10y.empty else np.nan,
        "US2Y": float(us2y.iloc[-1]) if not us2y.empty else np.nan,
        "Curve_2Y10Y": curve_spread,
        "Inflation_10Y": float(inflation.iloc[-1]) if not inflation.empty else np.nan,
        "HY_Spread": float(credit.iloc[-1]) if not credit.empty else np.nan,
        "US10Y_1M_Change": _period_change(us10y, 21),
        "US10Y_3M_Change": _period_change(us10y, 63),
    }
    latest_dates = [
        series.index[-1]
        for series in [us10y, us2y, inflation, credit]
        if not series.empty
    ]
    as_of = pd.Timestamp(max(latest_dates)) if latest_dates else None

    return MacroRateRegime(
        score=score,
        level=macro_risk_level(score),
        primary_driver=primary_driver,
        impact=macro_risk_impact(score),
        data_quality=float(available_weight * 100),
        components=components,
        observations=observations,
        as_of=as_of,
    )


def fetch_fred_macro_history(years: int = 3) -> pd.DataFrame:
    """Hent de fire offentlige FRED-serier uden API-nøgle."""
    start = date.today() - timedelta(days=max(1, int(years)) * 366)
    query = urlencode(
        {
            "id": ",".join(FRED_SERIES.values()),
            "cosd": start.isoformat(),
        }
    )
    request = Request(
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?{query}",
        headers={"User-Agent": "Investment-OS/7.3"},
    )
    with urlopen(request, timeout=15) as response:
        payload = response.read()

    frames: list[pd.DataFrame] = []
    if payload.startswith(b"PK"):
        with ZipFile(BytesIO(payload)) as archive:
            csv_files = [name for name in archive.namelist() if name.endswith(".csv")]
            for name in csv_files:
                frames.append(pd.read_csv(BytesIO(archive.read(name))))
    else:
        frames.append(pd.read_csv(StringIO(payload.decode("utf-8"))))

    normalized: list[pd.DataFrame] = []
    for frame in frames:
        date_column = (
            "observation_date" if "observation_date" in frame.columns else "DATE"
        )
        if date_column not in frame.columns:
            continue
        frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
        normalized.append(
            frame.dropna(subset=[date_column]).set_index(date_column).sort_index()
        )
    if not normalized:
        raise ValueError("FRED-svaret mangler datokolonne")
    frame = pd.concat(normalized, axis=1)
    reverse_names = {fred_name: name for name, fred_name in FRED_SERIES.items()}
    frame = frame.rename(columns=reverse_names)
    for column in FRED_SERIES:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.loc[frame.index.date >= start]
    return frame[list(FRED_SERIES)].dropna(how="all")


def apply_macro_rate_overlay(
    portfolio: pd.DataFrame,
    regime: MacroRateRegime | None,
) -> pd.DataFrame:
    """Tilføj forklarende risikofelter uden at ændre beslutningssignaler."""
    result = portfolio.copy()
    if regime is None:
        return result
    result["Macro_Rate_Risk_Score"] = regime.score
    result["Macro_Rate_Risk_Level"] = regime.level
    result["Macro_Rate_Primary_Driver"] = regime.primary_driver
    result["Macro_Rate_Risk_Impact"] = regime.impact
    result["Macro_Rate_Data_Quality"] = regime.data_quality
    return result
