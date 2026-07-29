from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


DEFAULT_OPPORTUNITY_WEIGHTS = {
    "Momentum": 0.25,
    "AI Confidence": 0.20,
    "Relative Strength": 0.15,
    "Trend": 0.15,
    "Risiko": 0.10,
    "Datakvalitet": 0.10,
    "Positionsbonus": 0.05,
}


@dataclass(frozen=True)
class OpportunityResult:
    """Rangerede muligheder med gennemsigtige delscorer."""

    data: pd.DataFrame
    top_opportunity: str | None
    top_score: float
    lowest_conviction: str | None
    lowest_score: float


def normalize_opportunity_weights(
    weights: dict[str, float] | None,
) -> dict[str, float]:
    source = weights or DEFAULT_OPPORTUNITY_WEIGHTS
    cleaned = {
        factor: max(0.0, float(source.get(factor, 0.0)))
        for factor in DEFAULT_OPPORTUNITY_WEIGHTS
    }
    total = sum(cleaned.values())
    if total <= 0:
        return DEFAULT_OPPORTUNITY_WEIGHTS.copy()
    return {
        factor: value / total
        for factor, value in cleaned.items()
    }


def _percentile_score(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)
    return numeric.rank(
        pct=True,
        method="average",
    ).mul(100).fillna(50.0)


def _trend_score(frame: pd.DataFrame) -> pd.Series:
    periods = {
        "1W": 0.15,
        "1M": 0.25,
        "3M": 0.30,
        "6M": 0.30,
    }
    result = pd.Series(0.0, index=frame.index)
    available_weight = pd.Series(0.0, index=frame.index)

    for column, weight in periods.items():
        values = pd.to_numeric(
            frame.get(column),
            errors="coerce",
        )
        valid = values.notna()
        result = result.add(
            valid.astype(float)
            * values.gt(0).astype(float)
            * weight
            * 100,
            fill_value=0,
        )
        available_weight = available_weight.add(
            valid.astype(float) * weight,
            fill_value=0,
        )

    return (
        result.div(available_weight.replace(0, np.nan))
        .fillna(50.0)
        .clip(0, 100)
    )


def _risk_score(frame: pd.DataFrame) -> pd.Series:
    volatility = pd.to_numeric(
        frame.get("Volatility"),
        errors="coerce",
    )
    drawdown = pd.to_numeric(
        frame.get("Max_Drawdown"),
        errors="coerce",
    ).abs()

    volatility_score = (
        (0.55 - volatility) / (0.55 - 0.18) * 100
    ).clip(0, 100).fillna(50.0)

    drawdown_score = (
        (0.45 - drawdown) / (0.45 - 0.10) * 100
    ).clip(0, 100).fillna(50.0)

    return (
        0.60 * volatility_score
        + 0.40 * drawdown_score
    ).clip(0, 100)


def _position_bonus(
    frame: pd.DataFrame,
    max_position_weight: float,
) -> pd.Series:
    weights = pd.to_numeric(
        frame.get("Portfolio_Weight"),
        errors="coerce",
    ).fillna(0.0)

    ceiling = max(float(max_position_weight), 0.01)

    # Små positioner får pladsbonus. Positioner ved loftet får 0.
    return (
        (ceiling - weights) / ceiling * 100
    ).clip(0, 100)


def _data_quality_score(frame: pd.DataFrame) -> pd.Series:
    if "Momentum_Data_Quality" not in frame.columns:
        return pd.Series(50.0, index=frame.index)

    return (
        pd.to_numeric(
            frame["Momentum_Data_Quality"],
            errors="coerce",
        )
        .mul(100)
        .clip(0, 100)
        .fillna(50.0)
    )


def _score_label(score: float) -> str:
    if pd.isna(score):
        return "Datamangel"
    if score >= 85:
        return "Meget stærk"
    if score >= 70:
        return "Stærk"
    if score >= 55:
        return "Interessant"
    if score >= 40:
        return "Neutral"
    return "Lav conviction"


def build_opportunity_scores(
    portfolio: pd.DataFrame,
    *,
    factor_weights: dict[str, float] | None = None,
    max_position_weight: float = 0.12,
) -> OpportunityResult:
    """
    Beregn Opportunity Score for alle aktive positioner.

    Modellen bruger kun tilgængelige markeds- og porteføljedata.
    Fundamental kvalitet indgår ikke, før Investment OS har et
    autoritativt fundamentalt datagrundlag.
    """
    if portfolio.empty:
        return OpportunityResult(
            data=pd.DataFrame(),
            top_opportunity=None,
            top_score=np.nan,
            lowest_conviction=None,
            lowest_score=np.nan,
        )

    weights = normalize_opportunity_weights(factor_weights)
    result = portfolio.copy()

    result["Momentum Score"] = _percentile_score(
        result["Composite"]
    )
    result["AI Score"] = pd.to_numeric(
        result["AI_Confidence"],
        errors="coerce",
    ).clip(0, 100).fillna(50.0)

    relative_strength = pd.to_numeric(
        result.get("Relative_Strength_3M"),
        errors="coerce",
    )
    result["RS Score"] = (
        (relative_strength + 0.10) / 0.20 * 100
    ).clip(0, 100).fillna(50.0)

    result["Trend Score"] = _trend_score(result)
    result["Risk Score"] = _risk_score(result)
    result["Data Score"] = _data_quality_score(result)
    result["Position Score"] = _position_bonus(
        result,
        max_position_weight=max_position_weight,
    )

    factor_columns = {
        "Momentum": "Momentum Score",
        "AI Confidence": "AI Score",
        "Relative Strength": "RS Score",
        "Trend": "Trend Score",
        "Risiko": "Risk Score",
        "Datakvalitet": "Data Score",
        "Positionsbonus": "Position Score",
    }

    result["Opportunity Score"] = sum(
        result[column] * weights[factor]
        for factor, column in factor_columns.items()
    ).clip(0, 100)

    # Hard gate bevares: negativ 1M kan ikke klassificeres som topmulighed.
    one_month = pd.to_numeric(
        result.get("1M"),
        errors="coerce",
    )
    result.loc[
        one_month.lt(0),
        "Opportunity Score",
    ] = result.loc[
        one_month.lt(0),
        "Opportunity Score",
    ].clip(upper=69.9)

    result["Opportunity Label"] = result[
        "Opportunity Score"
    ].apply(_score_label)

    result["Opportunity Rank"] = result[
        "Opportunity Score"
    ].rank(
        ascending=False,
        method="min",
    ).astype("Int64")

    result = result.sort_values(
        [
            "Opportunity Score",
            "AI_Confidence",
            "Composite",
        ],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)

    top = result.iloc[0]
    bottom = result.iloc[-1]

    return OpportunityResult(
        data=result,
        top_opportunity=str(top.get("Name", "Ukendt")),
        top_score=float(top["Opportunity Score"]),
        lowest_conviction=str(
            bottom.get("Name", "Ukendt")
        ),
        lowest_score=float(bottom["Opportunity Score"]),
    )
