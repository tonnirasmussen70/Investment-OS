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
    minimum_trade_dkk: float = 5000.0,
) -> RebalanceResult:
    """
    Byg en handlingsorienteret rebalanceringsplan.

    Regler:
    - Øg: vægten øges med increase_factor, dog højst positionsloftet.
    - Reducer: vægten reduceres med reduce_factor.
    - Hold/Afvent: vægten ændres ikke.
    - Foreslået vægt viser altid modellens ønskede allokering.
    - Handler under minimum_trade_dkk markeres som ikke-eksekverbare ved at
      sætte Handel DKK til 0, men den ønskede vægt og ændring bevares.
    - Der normaliseres ikke automatisk tilbage til 100 %, fordi det ellers
      skaber kunstige køb/salg i positioner uden et egentligt signal.
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

    data["Portfolio_Weight"] = data["Portfolio_Weight"].fillna(0.0)
    data["Foreslået vægt"] = data["Portfolio_Weight"]

    increase_mask = data["Handling"].eq("Øg")
    reduce_mask = data["Handling"].eq("Reducer")

    data.loc[
        increase_mask,
        "Foreslået vægt",
    ] = (
        data.loc[increase_mask, "Portfolio_Weight"] * increase_factor
    ).clip(upper=max_position_weight)

    data.loc[
        reduce_mask,
        "Foreslået vægt",
    ] = (
        data.loc[reduce_mask, "Portfolio_Weight"] * reduce_factor
    ).clip(lower=0.0)

    data["Ændring"] = (
        data["Foreslået vægt"] - data["Portfolio_Weight"]
    )

    data["Handel DKK"] = (
        data["Ændring"] * float(active_market_value_dkk)
    )

    # Kun reelle signaler må skabe en ønsket ændring.
    no_signal = ~data["Handling"].isin(["Øg", "Reducer"])
    data.loc[no_signal, "Foreslået vægt"] = data.loc[
        no_signal,
        "Portfolio_Weight",
    ]
    data.loc[no_signal, "Ændring"] = 0.0
    data.loc[no_signal, "Handel DKK"] = 0.0

    # Små handler eksekveres ikke, men modelvægten bevares i visningen.
    small_trade = (
        data["Handel DKK"].abs() < minimum_trade_dkk
    ) & data["Handel DKK"].ne(0)
    data["Under minimumshandel"] = small_trade
    data.loc[small_trade, "Handel DKK"] = 0.0

    data["Rebalance handling"] = np.select(
        [
            data["Handling"].eq("Øg") & data["Handel DKK"].gt(0),
            data["Handling"].eq("Reducer") & data["Handel DKK"].lt(0),
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

    # Vis handler først, derefter ingen handel.
    action_order = {
        "Sælg": 0,
        "Køb": 1,
        "Ingen handel": 2,
    }
    data["_action_order"] = (
        data["Rebalance handling"].map(action_order).fillna(9)
    )

    data = data.rename(
        columns={
            "Name": "Aktiv",
            "Portfolio_Weight": "Nuværende vægt",
            "AI_Confidence": "AI",
        }
    ).sort_values(
        ["_action_order", "Handel DKK"],
        ascending=[True, False],
        na_position="last",
    )

    trade_count = int(data["Handel DKK"].ne(0).sum())
    gross_trade = float(data["Handel DKK"].abs().sum())

    data = data.drop(columns=["_action_order"])

    return RebalanceResult(
        data=data.reset_index(drop=True),
        increase_count=int(increase_mask.sum()),
        reduce_count=int(reduce_mask.sum()),
        trade_count=trade_count,
        gross_trade_dkk=gross_trade,
    )
