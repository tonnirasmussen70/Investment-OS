from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RebalanceResult:
    """Resultat af den centrale rebalanceringsmodel."""

    data: pd.DataFrame
    increase_count: int
    reduce_count: int
    trade_count: int
    gross_trade_dkk: float


def _cap_and_redistribute(
    weights: pd.Series,
    max_weight: float,
    iterations: int = 20,
) -> pd.Series:
    """
    Begræns enkeltpositioner og fordel restvægten proportionalt.

    Metoden er pragmatisk og stabil. Den søger ikke en matematisk optimal
    portefølje, men håndhæver positionsloftet uden at ændre den relative
    rangering mere end nødvendigt.
    """
    adjusted = weights.clip(lower=0).astype(float)

    total = adjusted.sum()
    if total <= 0:
        return adjusted

    adjusted = adjusted / total

    for _ in range(iterations):
        over = adjusted > max_weight + 1e-12
        if not over.any():
            break

        excess = float(
            (adjusted.loc[over] - max_weight).sum()
        )
        adjusted.loc[over] = max_weight

        under = adjusted < max_weight - 1e-12
        under_total = float(adjusted.loc[under].sum())

        if excess <= 0 or under_total <= 0:
            break

        adjusted.loc[under] += (
            adjusted.loc[under] / under_total * excess
        )

    total = adjusted.sum()
    if total > 0:
        adjusted = adjusted / total

    return adjusted


def build_rebalance_plan(
    portfolio: pd.DataFrame,
    active_market_value_dkk: float,
    max_position_weight: float = 0.12,
    increase_factor: float = 1.10,
    reduce_factor: float = 0.75,
    minimum_trade_dkk: float = 1000.0,
) -> RebalanceResult:
    """
    Byg en handlingsorienteret rebalanceringsplan.

    Modellen:
    - Øg: nuværende vægt × increase_factor
    - Reducer: nuværende vægt × reduce_factor
    - Hold/Afvent: uændret
    - positionsloft håndhæves
    - små handler under minimum_trade_dkk sættes til 0
    """
    required = {
        "Name",
        "Portfolio_Weight",
        "Composite",
        "AI_Confidence",
        "Handling",
    }
    missing = required.difference(portfolio.columns)
    if missing:
        raise ValueError(
            f"Rebalancering mangler kolonner: {sorted(missing)}"
        )

    data = portfolio[
        [
            "Name",
            "Portfolio_Weight",
            "Composite",
            "AI_Confidence",
            "Handling",
        ]
    ].copy()

    if data.empty:
        return RebalanceResult(
            data=pd.DataFrame(),
            increase_count=0,
            reduce_count=0,
            trade_count=0,
            gross_trade_dkk=0.0,
        )

    for column in [
        "Portfolio_Weight",
        "Composite",
        "AI_Confidence",
    ]:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    data["Foreslået vægt"] = data[
        "Portfolio_Weight"
    ].fillna(0)

    increase_mask = data["Handling"].eq("Øg")
    reduce_mask = data["Handling"].eq("Reducer")

    data.loc[
        increase_mask,
        "Foreslået vægt",
    ] *= increase_factor

    data.loc[
        reduce_mask,
        "Foreslået vægt",
    ] *= reduce_factor

    data["Foreslået vægt"] = _cap_and_redistribute(
        data["Foreslået vægt"],
        max_weight=max_position_weight,
    )

    data["Ændring"] = (
        data["Foreslået vægt"]
        - data["Portfolio_Weight"].fillna(0)
    )

    data["Handel DKK"] = (
        data["Ændring"] * float(active_market_value_dkk)
    )

    small_trade = data["Handel DKK"].abs() < minimum_trade_dkk
    data.loc[small_trade, "Handel DKK"] = 0.0
    data.loc[small_trade, "Ændring"] = 0.0
    data.loc[small_trade, "Foreslået vægt"] = data.loc[
        small_trade,
        "Portfolio_Weight",
    ].fillna(0)

    data["Rebalance handling"] = np.select(
        [
            data["Handel DKK"] > 0,
            data["Handel DKK"] < 0,
        ],
        [
            "Køb",
            "Sælg",
        ],
        default="Ingen handel",
    )

    data["Positionsloft"] = np.where(
        data["Foreslået vægt"] >= max_position_weight - 1e-6,
        "Ved loft",
        "",
    )

    data = data.rename(
        columns={
            "Name": "Aktiv",
            "Portfolio_Weight": "Nuværende vægt",
            "AI_Confidence": "AI",
        }
    ).sort_values(
        ["Rebalance handling", "Handel DKK"],
        ascending=[True, False],
    )

    trade_count = int(
        data["Handel DKK"].ne(0).sum()
    )
    gross_trade = float(
        data["Handel DKK"].abs().sum()
    )

    return RebalanceResult(
        data=data.reset_index(drop=True),
        increase_count=int(increase_mask.sum()),
        reduce_count=int(reduce_mask.sum()),
        trade_count=trade_count,
        gross_trade_dkk=gross_trade,
    )
