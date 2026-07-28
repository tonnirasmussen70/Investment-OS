from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


DEFAULT_MOMENTUM_WEIGHTS = {
    "1W": 0.20,
    "1M": 0.25,
    "3M": 0.25,
    "6M": 0.20,
    "12M": 0.10,
}


@dataclass(frozen=True)
class InvestmentConfig:
    """Central, valideret konfiguration til Investment OS."""

    momentum_weights: dict[str, float]
    risk_free_rate: float
    benchmark: str
    max_position_weight: float
    max_sector_weight: float
    high_confidence_threshold: float
    positive_flow_threshold: float
    neutral_flow_threshold: float


def _as_float(
    settings: dict,
    key: str,
    default: float,
) -> float:
    value = settings.get(key, default)

    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)

    if pd.isna(number):
        return float(default)

    return number


def _normalized_momentum_weights(
    settings: dict,
) -> dict[str, float]:
    weights = {
        "1W": _as_float(
            settings,
            "Momentum_1W",
            DEFAULT_MOMENTUM_WEIGHTS["1W"],
        ),
        "1M": _as_float(
            settings,
            "Momentum_1M",
            DEFAULT_MOMENTUM_WEIGHTS["1M"],
        ),
        "3M": _as_float(
            settings,
            "Momentum_3M",
            DEFAULT_MOMENTUM_WEIGHTS["3M"],
        ),
        "6M": _as_float(
            settings,
            "Momentum_6M",
            DEFAULT_MOMENTUM_WEIGHTS["6M"],
        ),
        "12M": _as_float(
            settings,
            "Momentum_12M",
            DEFAULT_MOMENTUM_WEIGHTS["12M"],
        ),
    }

    positive_weights = {
        key: max(0.0, value)
        for key, value in weights.items()
    }

    total = sum(positive_weights.values())

    if total <= 0:
        return DEFAULT_MOMENTUM_WEIGHTS.copy()

    return {
        key: value / total
        for key, value in positive_weights.items()
    }


def load_investment_config(
    settings: dict | None,
) -> InvestmentConfig:
    """
    Byg central konfiguration fra Settings-fanen i AI_portfolio.xlsx.

    Manglende eller ugyldige værdier erstattes med stabile standarder.
    """
    source = settings or {}

    benchmark = str(
        source.get("Benchmark", "URTH")
    ).strip() or "URTH"

    return InvestmentConfig(
        momentum_weights=_normalized_momentum_weights(source),
        risk_free_rate=_as_float(
            source,
            "Risk_Free_Rate",
            0.02,
        ),
        benchmark=benchmark,
        max_position_weight=_as_float(
            source,
            "Max_Position_Weight",
            0.12,
        ),
        max_sector_weight=_as_float(
            source,
            "Max_Sector_Weight",
            0.20,
        ),
        high_confidence_threshold=_as_float(
            source,
            "High_Confidence_Threshold",
            80.0,
        ),
        positive_flow_threshold=_as_float(
            source,
            "Positive_Flow_Threshold",
            0.65,
        ),
        neutral_flow_threshold=_as_float(
            source,
            "Neutral_Flow_Threshold",
            0.40,
        ),
    )
