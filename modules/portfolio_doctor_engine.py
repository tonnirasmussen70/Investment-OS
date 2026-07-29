from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from modules.decision_engine import action_reason
from modules.health_engine import calculate_portfolio_health


@dataclass(frozen=True)
class PortfolioDoctorResult:
    """Resultat fra Portfolio Doctor-simuleringen."""

    data: pd.DataFrame
    current_health: float
    best_simulated_health: float
    actionable_count: int


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(min(max(value, lower), upper))


def _recommended_weight_change(
    row: pd.Series,
    max_position_weight: float,
    default_step: float,
) -> float:
    """
    Foreslå en moderat vægtændring.

    Modellen er bevidst konservativ:
    - Øg: normalt +2 procentpoint, men aldrig over positionsloftet.
    - Reducer: normalt -2 procentpoint.
    - Hold/Afvent: ingen handel.
    """
    action = str(row.get("Handling", "Hold"))
    current_weight = float(
        pd.to_numeric(row.get("Portfolio_Weight"), errors="coerce")
        or 0.0
    )

    if action == "Øg":
        available = max(0.0, max_position_weight - current_weight)
        return min(default_step, available)

    if action == "Reducer":
        return -min(default_step, current_weight)

    return 0.0


def _simulate_weights(
    portfolio: pd.DataFrame,
    row_index,
    weight_change: float,
) -> pd.DataFrame:
    """
    Justér én position og finansier ændringen pro rata i resten af porteføljen.

    Det sikrer, at de samlede aktive vægte fortsat summerer til 100 %.
    """
    simulated = portfolio.copy()
    weights = pd.to_numeric(
        simulated["Portfolio_Weight"],
        errors="coerce",
    ).fillna(0.0)

    total = float(weights.sum())
    if total <= 0:
        return simulated

    weights = weights / total
    current = float(weights.loc[row_index])
    target = _clamp(current + weight_change, 0.0, 1.0)
    actual_change = target - current

    other_mask = weights.index != row_index
    other_total = float(weights.loc[other_mask].sum())

    if abs(actual_change) < 1e-12 or other_total <= 0:
        simulated["Portfolio_Weight"] = weights
        return simulated

    # Ved køb reduceres resten pro rata. Ved salg øges resten pro rata.
    adjustment_factor = (other_total - actual_change) / other_total
    weights.loc[other_mask] = (
        weights.loc[other_mask] * adjustment_factor
    )
    weights.loc[row_index] = target

    weights = weights.clip(lower=0.0)
    weights = weights / weights.sum()

    simulated["Portfolio_Weight"] = weights
    return simulated


def _priority_score(
    row: pd.Series,
    health_delta: float,
    weight_change: float,
) -> float:
    """
    Prioritet 1-10.

    Vægter:
    - forventet forbedring i Portfolio Health
    - AI Confidence
    - signalets styrke
    - om handlingen er Øg eller Reducer
    """
    confidence = pd.to_numeric(
        row.get("AI_Confidence"),
        errors="coerce",
    )
    confidence = 50.0 if pd.isna(confidence) else float(confidence)

    composite = pd.to_numeric(
        row.get("Composite"),
        errors="coerce",
    )
    composite = 0.0 if pd.isna(composite) else float(composite)

    action = str(row.get("Handling", "Hold"))
    action_strength = {
        "Reducer": 1.00,
        "Øg": 0.90,
        "Afvent": 0.35,
        "Hold": 0.20,
    }.get(action, 0.20)

    signal_strength = min(abs(composite) / 0.20, 1.0)
    health_strength = min(max(health_delta, 0.0) / 3.0, 1.0)
    trade_strength = min(abs(weight_change) / 0.03, 1.0)

    raw = (
        0.35 * health_strength
        + 0.25 * (confidence / 100.0)
        + 0.20 * signal_strength
        + 0.10 * action_strength
        + 0.10 * trade_strength
    )

    return round(_clamp(1.0 + raw * 9.0, 1.0, 10.0), 1)


def build_portfolio_doctor(
    portfolio: pd.DataFrame,
    *,
    active_market_value_dkk: float,
    stop_loss_metrics: dict[str, int],
    data_quality_score: float,
    max_position_weight: float,
    factor_weights: dict[str, float],
    current_health: float,
    default_step: float = 0.02,
    minimum_trade_dkk: float = 5000.0,
) -> PortfolioDoctorResult:
    """
    Simulér én moderat ændring pr. position og beregn effekten på Health.

    Dette er beslutningsstøtte, ikke en afkastprognose. Modellen estimerer
    kun effekten på den nuværende Portfolio Health-model.
    """
    if portfolio.empty:
        empty = pd.DataFrame(
            columns=[
                "Aktiv",
                "Handling",
                "Anbefalet ændring",
                "Beløb DKK",
                "Health før",
                "Health efter",
                "Health effekt",
                "Confidence",
                "Prioritet",
                "Begrundelse",
            ]
        )
        return PortfolioDoctorResult(
            data=empty,
            current_health=current_health,
            best_simulated_health=current_health,
            actionable_count=0,
        )

    rows: list[dict[str, object]] = []

    for row_index, row in portfolio.iterrows():
        action = str(row.get("Handling", "Hold"))

        if action not in {"Øg", "Reducer"}:
            continue

        weight_change = _recommended_weight_change(
            row,
            max_position_weight=max_position_weight,
            default_step=default_step,
        )

        trade_dkk = abs(weight_change) * float(
            active_market_value_dkk
        )

        if (
            abs(weight_change) < 1e-12
            or trade_dkk < minimum_trade_dkk
        ):
            continue

        simulated = _simulate_weights(
            portfolio,
            row_index=row_index,
            weight_change=weight_change,
        )

        simulated_health = calculate_portfolio_health(
            simulated,
            stop_loss_metrics=stop_loss_metrics,
            data_quality_score=data_quality_score,
            max_position_weight=max_position_weight,
            factor_weights=factor_weights,
        )

        after_score = simulated_health.score
        health_delta = (
            float(after_score - current_health)
            if pd.notna(after_score)
            and pd.notna(current_health)
            else np.nan
        )

        confidence = pd.to_numeric(
            row.get("AI_Confidence"),
            errors="coerce",
        )

        priority = _priority_score(
            row,
            health_delta=(
                health_delta
                if pd.notna(health_delta)
                else 0.0
            ),
            weight_change=weight_change,
        )

        rows.append(
            {
                "Aktiv": row.get("Name", row.get("Yahoo_Ticker", "Ukendt")),
                "Ticker": row.get("Yahoo_Ticker", ""),
                "Handling": action,
                "Anbefalet ændring": weight_change,
                "Beløb DKK": (
                    trade_dkk
                    if action == "Øg"
                    else -trade_dkk
                ),
                "Health før": current_health,
                "Health efter": after_score,
                "Health effekt": health_delta,
                "Confidence": confidence,
                "Prioritet": priority,
                "Begrundelse": action_reason(row),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        best_health = current_health
    else:
        result = result.sort_values(
            [
                "Prioritet",
                "Health effekt",
                "Confidence",
            ],
            ascending=[False, False, False],
            na_position="last",
        ).reset_index(drop=True)

        valid_after = result["Health efter"].dropna()
        best_health = (
            float(valid_after.max())
            if not valid_after.empty
            else current_health
        )

    return PortfolioDoctorResult(
        data=result,
        current_health=current_health,
        best_simulated_health=best_health,
        actionable_count=len(result),
    )
