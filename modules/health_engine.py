from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


DEFAULT_HEALTH_WEIGHTS = {
    "Momentum": 0.30,
    "Relative Strength": 0.20,
    "AI Confidence": 0.20,
    "Diversifikation": 0.10,
    "Risiko": 0.10,
    "Stop-loss": 0.05,
    "Datakvalitet": 0.05,
}


@dataclass(frozen=True)
class HealthResult:
    """Samlet Portfolio Health med gennemsigtige delscorer."""

    score: float
    label: str
    factor_scores: dict[str, float]
    weighted_contributions: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]


def normalize_weights(
    weights: dict[str, float] | None,
) -> dict[str, float]:
    """Normalisér positive faktorvægte til 100 %."""
    source = weights or DEFAULT_HEALTH_WEIGHTS

    cleaned = {
        key: max(0.0, float(source.get(key, 0.0)))
        for key in DEFAULT_HEALTH_WEIGHTS
    }

    total = sum(cleaned.values())
    if total <= 0:
        return DEFAULT_HEALTH_WEIGHTS.copy()

    return {
        key: value / total
        for key, value in cleaned.items()
    }


def _weighted_average(
    values: pd.Series,
    weights: pd.Series,
) -> float:
    valid = values.notna() & weights.notna() & weights.gt(0)

    if not valid.any():
        return np.nan

    return float(
        np.average(
            values.loc[valid],
            weights=weights.loc[valid],
        )
    )


def _momentum_score(portfolio: pd.DataFrame) -> float:
    if portfolio.empty:
        return np.nan

    weights = portfolio["Portfolio_Weight"].fillna(0)
    positive = portfolio["Composite"].fillna(0).gt(0).astype(float)

    return 100.0 * _weighted_average(positive, weights)


def _relative_strength_score(portfolio: pd.DataFrame) -> float:
    if (
        portfolio.empty
        or "Relative_Strength_3M" not in portfolio.columns
    ):
        return np.nan

    weights = portfolio["Portfolio_Weight"].fillna(0)
    rs = portfolio["Relative_Strength_3M"]

    # -10 % relativ styrke = 0 point, +10 % = 100 point.
    scaled = ((rs + 0.10) / 0.20 * 100).clip(0, 100)

    return _weighted_average(scaled, weights)


def _ai_score(portfolio: pd.DataFrame) -> float:
    if portfolio.empty:
        return np.nan

    return _weighted_average(
        portfolio["AI_Confidence"],
        portfolio["Portfolio_Weight"].fillna(0),
    )


def _diversification_score(
    portfolio: pd.DataFrame,
    max_position_weight: float,
) -> float:
    if portfolio.empty:
        return np.nan

    weights = portfolio["Portfolio_Weight"].fillna(0)
    weights = weights.loc[weights.gt(0)]

    if weights.empty:
        return np.nan

    weights = weights / weights.sum()
    largest = float(weights.max())
    hhi = float((weights.pow(2)).sum())

    # 50 % baseret på største position og 50 % på koncentration.
    position_score = (
        100.0
        if largest <= max_position_weight
        else max(
            0.0,
            100.0
            * (
                1
                - (
                    largest - max_position_weight
                )
                / max(max_position_weight, 0.01)
            ),
        )
    )

    # HHI <= 0,08 giver fuld score. HHI >= 0,25 giver 0.
    hhi_score = float(
        np.clip(
            (0.25 - hhi) / (0.25 - 0.08) * 100,
            0,
            100,
        )
    )

    return 0.50 * position_score + 0.50 * hhi_score


def _risk_score(portfolio: pd.DataFrame) -> float:
    if portfolio.empty:
        return np.nan

    weights = portfolio["Portfolio_Weight"].fillna(0)
    volatility = _weighted_average(
        portfolio["Volatility"],
        weights,
    )

    drawdown = _weighted_average(
        portfolio["Max_Drawdown"].abs(),
        weights,
    )

    if pd.isna(volatility) and pd.isna(drawdown):
        return np.nan

    volatility_score = (
        100.0
        if pd.isna(volatility)
        else float(
            np.clip(
                (0.50 - volatility) / (0.50 - 0.18) * 100,
                0,
                100,
            )
        )
    )

    drawdown_score = (
        100.0
        if pd.isna(drawdown)
        else float(
            np.clip(
                (0.45 - drawdown) / (0.45 - 0.10) * 100,
                0,
                100,
            )
        )
    )

    return 0.60 * volatility_score + 0.40 * drawdown_score


def _stop_score(
    stop_loss_metrics: dict[str, int],
    position_count: int,
) -> float:
    if position_count <= 0:
        return np.nan

    broken = int(stop_loss_metrics.get("Stop_Broken", 0))
    alarms = int(stop_loss_metrics.get("Alarm", 0))
    tighten = int(stop_loss_metrics.get("Tighten", 0))

    penalty = (
        broken * 35
        + alarms * 15
        + tighten * 7
    ) / position_count

    return float(np.clip(100 - penalty, 0, 100))


def health_label(score: float) -> str:
    if pd.isna(score):
        return "Datamangel"
    if score >= 85:
        return "Meget stærk"
    if score >= 70:
        return "Stærk"
    if score >= 55:
        return "Acceptabel"
    if score >= 40:
        return "Kræver opmærksomhed"
    return "Svag"


def calculate_portfolio_health(
    portfolio: pd.DataFrame,
    stop_loss_metrics: dict[str, int],
    data_quality_score: float,
    max_position_weight: float,
    factor_weights: dict[str, float] | None = None,
) -> HealthResult:
    """Beregn samlet Portfolio Health og de enkelte delscorer."""
    weights = normalize_weights(factor_weights)

    factor_scores = {
        "Momentum": _momentum_score(portfolio),
        "Relative Strength": _relative_strength_score(portfolio),
        "AI Confidence": _ai_score(portfolio),
        "Diversifikation": _diversification_score(
            portfolio,
            max_position_weight=max_position_weight,
        ),
        "Risiko": _risk_score(portfolio),
        "Stop-loss": _stop_score(
            stop_loss_metrics,
            position_count=len(portfolio),
        ),
        "Datakvalitet": float(
            np.clip(data_quality_score, 0, 100)
        ),
    }

    valid_weight = sum(
        weights[key]
        for key, value in factor_scores.items()
        if pd.notna(value)
    )

    weighted_contributions: dict[str, float] = {}

    if valid_weight <= 0:
        score = np.nan
    else:
        for key, value in factor_scores.items():
            if pd.isna(value):
                weighted_contributions[key] = 0.0
            else:
                effective_weight = weights[key] / valid_weight
                weighted_contributions[key] = (
                    float(value) * effective_weight
                )

        score = float(sum(weighted_contributions.values()))

    ranked = sorted(
        (
            (key, value)
            for key, value in factor_scores.items()
            if pd.notna(value)
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    strengths = [
        f"{key}: {value:.0f}"
        for key, value in ranked[:2]
        if value >= 65
    ]

    weaknesses = [
        f"{key}: {value:.0f}"
        for key, value in reversed(ranked[-2:])
        if value < 65
    ]

    return HealthResult(
        score=score,
        label=health_label(score),
        factor_scores=factor_scores,
        weighted_contributions=weighted_contributions,
        strengths=strengths,
        weaknesses=weaknesses,
    )
