from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

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


# Relative input weights sum to 1.05 by design; calculations normalize to 1.00.
DEFAULT_MOMENTUM_WEIGHTS = {
    "1W": 0.40,
    "1M": 0.35,
    "3M": 0.15,
    "6M": 0.10,
    "12M": 0.05,
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
    health_weights: dict[str, float]


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


def load_raw_momentum_weights(
    settings: dict | None,
) -> dict[str, float]:
    """Return the editable, unnormalized momentum inputs.

    Explicit Settings-sheet values take precedence over code defaults. Missing,
    non-finite or invalid values fall back to the default for that period.
    """
    source = settings or {}
    raw = {
        period: _as_float(source, f"Momentum_{period}", default)
        for period, default in DEFAULT_MOMENTUM_WEIGHTS.items()
    }
    weights = {
        period: max(0.0, value) if isfinite(value) else DEFAULT_MOMENTUM_WEIGHTS[period]
        for period, value in raw.items()
    }
    if sum(weights.values()) <= 0:
        return DEFAULT_MOMENTUM_WEIGHTS.copy()
    return weights


def _normalized_momentum_weights(
    settings: dict,
) -> dict[str, float]:
    weights = load_raw_momentum_weights(settings)
    total = sum(weights.values())
    return {period: value / total for period, value in weights.items()}


def _normalized_health_weights(
    settings: dict,
) -> dict[str, float]:
    key_map = {
        "Momentum": "Health_Momentum",
        "Relative Strength": "Health_Relative_Strength",
        "AI Confidence": "Health_AI_Confidence",
        "Diversifikation": "Health_Diversification",
        "Risiko": "Health_Risk",
        "Stop-loss": "Health_Stop_Loss",
        "Datakvalitet": "Health_Data_Quality",
    }

    weights = {
        label: max(
            0.0,
            _as_float(
                settings,
                setting_key,
                DEFAULT_HEALTH_WEIGHTS[label],
            ),
        )
        for label, setting_key in key_map.items()
    }

    total = sum(weights.values())

    if total <= 0:
        return DEFAULT_HEALTH_WEIGHTS.copy()

    return {
        label: value / total
        for label, value in weights.items()
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
        health_weights=_normalized_health_weights(source),
    )
