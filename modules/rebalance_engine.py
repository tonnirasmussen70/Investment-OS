from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RebalanceResult:
    """Execution-plan baseret på det autoritative Decision Engine-output."""

    data: pd.DataFrame
    increase_count: int
    reduce_count: int
    trade_count: int
    gross_trade_dkk: float
    buy_dkk: float
    sell_dkk: float
    net_trade_dkk: float
    cash_required_dkk: float
    constrained_count: int


def _empty_result() -> RebalanceResult:
    return RebalanceResult(
        data=pd.DataFrame(),
        increase_count=0,
        reduce_count=0,
        trade_count=0,
        gross_trade_dkk=0.0,
        buy_dkk=0.0,
        sell_dkk=0.0,
        net_trade_dkk=0.0,
        cash_required_dkk=0.0,
        constrained_count=0,
    )


def _dynamic_target_step(score: pd.Series, action: pd.Series) -> pd.Series:
    """Conviction-baseret vægttrin i procentpoint."""
    score = pd.to_numeric(score, errors="coerce").fillna(50.0).clip(0, 100)
    step = pd.Series(0.0, index=score.index)

    increase = action.eq("Øg")
    increase_intensity = ((score - 70.0) / 30.0).clip(0, 1)
    step.loc[increase] = (
        0.015 + 0.025 * increase_intensity.loc[increase]
    )

    reduce = action.eq("Reducer")
    reduce_intensity = ((55.0 - score) / 55.0).clip(0, 1)
    step.loc[reduce] = -(
        0.020 + 0.040 * reduce_intensity.loc[reduce]
    )
    return step


def _apply_sector_constraint(
    data: pd.DataFrame,
    max_sector_weight: float,
) -> None:
    """
    Anvend sektorloftet som risikoadvarsel og købsgate for aktier.

    Sektorloftet må ikke alene skabe et salg af en attraktiv aktie. Hvis en
    sektors foreslåede vægt overstiger loftet, fjernes kun positive target-
    ændringer, indtil sektoren enten er under loftet eller alle nye køb er
    annulleret. Er sektoren allerede over loftet, bevares eksisterende vægte;
    overskridelsen markeres som en note fremfor at gennemtvinge salg.
    """
    if "Sector" not in data.columns or max_sector_weight <= 0:
        return

    asset_type = data.get("Asset_Type", pd.Series("", index=data.index)).astype(str)
    stock_mask = asset_type.isin(["Stock", "Equity"])
    valid_sector = (
        data["Sector"].fillna("").astype(str).str.strip().ne("")
        & ~data["Sector"].fillna("").astype(str).str.lower().isin(
            ["unknown", "ukendt", "other", "n/a", "none"]
        )
    )

    for sector, idx in data.loc[stock_mask & valid_sector].groupby("Sector").groups.items():
        indices = list(idx)
        current_sector_weight = float(data.loc[indices, "Portfolio_Weight"].sum())
        proposed_sector_weight = float(data.loc[indices, "Modelmålvægt"].sum())

        if proposed_sector_weight <= max_sector_weight + 1e-12:
            continue

        excess = proposed_sector_weight - max_sector_weight
        positive_delta = (
            data.loc[indices, "Modelmålvægt"]
            - data.loc[indices, "Portfolio_Weight"]
        ).clip(lower=0)
        positive_total = float(positive_delta.sum())

        # Sektorloftet må begrænse nye køb, men aldrig presse en position under
        # dens aktuelle vægt alene pga. sektorallokeringen.
        if positive_total > 0:
            reduction = positive_delta * min(1.0, excess / positive_total)
            data.loc[indices, "Modelmålvægt"] = (
                data.loc[indices, "Modelmålvægt"] - reduction
            )
            constrained = reduction.gt(1e-12)
            constrained_indices = constrained.index[constrained]
            data.loc[constrained_indices, "Constraint"] = data.loc[
                constrained_indices, "Constraint"
            ].apply(
                lambda value: (
                    "Sektorloft (note)"
                    if not value
                    else f"{value}, Sektorloft (note)"
                )
            )

        remaining_sector_weight = float(data.loc[indices, "Modelmålvægt"].sum())
        sector_still_over = remaining_sector_weight > max_sector_weight + 1e-12

        # Hvis sektoren allerede er over loftet, registreres overskridelsen som
        # risikonote på positionerne. Der skabes ikke et tvunget salg.
        if sector_still_over or current_sector_weight > max_sector_weight + 1e-12:
            note_indices = data.loc[indices].index
            data.loc[note_indices, "Constraint"] = data.loc[
                note_indices, "Constraint"
            ].apply(
                lambda value: (
                    value
                    if "Sektorloft" in str(value)
                    else (
                        "Sektorloft (note)"
                        if not value
                        else f"{value}, Sektorloft (note)"
                    )
                )
            )


def build_rebalance_plan(
    portfolio: pd.DataFrame,
    active_market_value_dkk: float,
    max_position_weight: float = 0.12,
    max_sector_weight: float = 0.20,
    minimum_trade_dkk: float = 5000.0,
    minimum_execution_confidence: float = 70.0,
) -> RebalanceResult:
    """
    Omsæt Decision Engine-output til en konkret execution-plan.

    7.0-principper:
    - Decision Engine bestemmer Score, Status og Handling.
    - Rebalancering beregner dynamiske target weights ud fra conviction.
    - Øg/Reducer kræver mindst 70 pct. AI Confidence for normal execution.
    - Positionsloft er et hard constraint og kan kræve handel.
    - Sektorloft er en risikoadvarsel/købsgate og må ikke alene skabe salg.
    - Hold/Afvent ændres kun, hvis et hard constraint kræver det.
    - Handler under minimumsbeløbet eksekveres ikke.
    """
    required = {
        "Name",
        "Portfolio_Weight",
        "Composite",
        "AI_Confidence",
        "Decision_Score",
        "Decision_Status",
        "Handling",
    }
    missing = required.difference(portfolio.columns)
    if missing:
        raise ValueError(f"Rebalancering mangler kolonner: {sorted(missing)}")

    optional = [
        column for column in ["Sector", "Asset_Type", "Yahoo_Ticker"]
        if column in portfolio.columns
    ]
    data = portfolio[
        [
            "Name",
            "Portfolio_Weight",
            "Composite",
            "AI_Confidence",
            "Decision_Score",
            "Decision_Status",
            "Handling",
            *optional,
        ]
    ].copy()

    if data.empty:
        return _empty_result()

    for column in ["Portfolio_Weight", "Composite", "AI_Confidence", "Decision_Score"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data["Portfolio_Weight"] = data["Portfolio_Weight"].fillna(0.0).clip(lower=0)
    data["Constraint"] = ""
    data["Dynamisk trin"] = _dynamic_target_step(
        data["Decision_Score"], data["Handling"]
    )
    data["Modelmålvægt"] = (
        data["Portfolio_Weight"] + data["Dynamisk trin"]
    ).clip(lower=0.0)

    # Hold/Afvent skal ikke bevæges af execution-layeren alene.
    no_action = ~data["Handling"].isin(["Øg", "Reducer"])
    data.loc[no_action, "Modelmålvægt"] = data.loc[no_action, "Portfolio_Weight"]

    # Confidence execution gate: Retningen fra Decision Engine bevares, men et
    # Øg/Reducer-signal må ikke omsættes til en normal handel under tærsklen.
    # Manglende confidence behandles konservativt som utilstrækkelig confidence.
    execution_signal = data["Handling"].isin(["Øg", "Reducer"])
    confidence = pd.to_numeric(data["AI_Confidence"], errors="coerce")
    low_confidence = execution_signal & (
        confidence.isna() | confidence.lt(float(minimum_execution_confidence))
    )
    data["Konfidensgate"] = low_confidence
    data.loc[low_confidence, "Modelmålvægt"] = data.loc[
        low_confidence, "Portfolio_Weight"
    ]
    data.loc[low_confidence, "Constraint"] = "Konfidensgate"

    # Hard position constraint gælder uanset Action og uanset confidence gate.
    position_cap = data["Modelmålvægt"].gt(max_position_weight)
    data.loc[position_cap, "Modelmålvægt"] = max_position_weight
    data.loc[position_cap, "Constraint"] = data.loc[
        position_cap, "Constraint"
    ].apply(lambda value: "Positionsloft" if not value else f"{value}, Positionsloft")

    # Sektorloft er en soft constraint: nye køb kan begrænses, men attraktive
    # eksisterende positioner må ikke tvangssælges alene pga. sektorvægten.
    _apply_sector_constraint(data, max_sector_weight=max_sector_weight)

    data["Modelændring"] = data["Modelmålvægt"] - data["Portfolio_Weight"]
    data["Ønsket handel DKK"] = data["Modelændring"] * float(active_market_value_dkk)

    small_trade = (
        data["Ønsket handel DKK"].abs().lt(float(minimum_trade_dkk))
        & data["Ønsket handel DKK"].ne(0)
    )
    data["Under minimumshandel"] = small_trade
    data.loc[small_trade, "Constraint"] = data.loc[small_trade, "Constraint"].apply(
        lambda value: "Minimumshandel" if not value else f"{value}, Minimumshandel"
    )

    data["Handel DKK"] = data["Ønsket handel DKK"].where(~small_trade, 0.0)
    execution_change = data["Handel DKK"] / float(active_market_value_dkk) if active_market_value_dkk else 0.0
    data["Foreslået vægt"] = data["Portfolio_Weight"] + execution_change
    data["Ændring"] = data["Foreslået vægt"] - data["Portfolio_Weight"]

    data["Rebalance handling"] = np.select(
        [data["Handel DKK"].gt(0), data["Handel DKK"].lt(0)],
        ["Køb", "Sælg"],
        default="Ingen handel",
    )

    position_constraint = data["Constraint"].str.contains("Positionsloft", case=False, na=False)
    sector_note = data["Constraint"].str.contains("Sektorloft", case=False, na=False)
    data["Begrundelse"] = np.select(
        [
            data["Rebalance handling"].eq("Sælg") & position_constraint,
            data["Rebalance handling"].eq("Ingen handel") & sector_note & data["Handling"].eq("Øg"),
            data["Rebalance handling"].eq("Køb") & sector_note,
            data["Rebalance handling"].eq("Køb"),
            data["Rebalance handling"].eq("Sælg") & data["Handling"].eq("Reducer"),
            data["Konfidensgate"] & data["Rebalance handling"].eq("Ingen handel"),
            data["Under minimumshandel"],
        ],
        [
            "Positionsloft kræver lavere vægt",
            "Sektorloft overskredet – underliggende signal: Øg; ingen tvungen reduktion",
            "Øg-signal begrænset af sektorloft",
            "Øg-signal omsat til dynamisk target weight",
            "Reducer-signal omsat til dynamisk target weight",
            f"Signal observeres – konfidens under {float(minimum_execution_confidence):.0f}%, ingen handel",
            "Modelændring under minimumshandel",
        ],
        default="Ingen execution-ændring",
    )

    action_order = {"Sælg": 0, "Køb": 1, "Ingen handel": 2}
    data["_action_order"] = data["Rebalance handling"].map(action_order).fillna(9)

    increase_mask = data["Handling"].eq("Øg")
    reduce_mask = data["Handling"].eq("Reducer")
    buy_dkk = float(data.loc[data["Handel DKK"].gt(0), "Handel DKK"].sum())
    sell_dkk = float(-data.loc[data["Handel DKK"].lt(0), "Handel DKK"].sum())
    net_trade = buy_dkk - sell_dkk
    gross_trade = buy_dkk + sell_dkk
    constrained_count = int(data["Constraint"].astype(str).str.len().gt(0).sum())

    data = data.rename(
        columns={
            "Name": "Aktiv",
            "Portfolio_Weight": "Nuværende vægt",
            "AI_Confidence": "AI",
            "Decision_Score": "Decision Score",
            "Decision_Status": "Status",
        }
    ).sort_values(
        ["_action_order", "Decision Score", "Handel DKK"],
        ascending=[True, False, False],
        na_position="last",
    )

    data = data.drop(columns=["_action_order"])

    return RebalanceResult(
        data=data.reset_index(drop=True),
        increase_count=int(increase_mask.sum()),
        reduce_count=int(reduce_mask.sum()),
        trade_count=int(data["Handel DKK"].ne(0).sum()),
        gross_trade_dkk=float(gross_trade),
        buy_dkk=float(buy_dkk),
        sell_dkk=float(sell_dkk),
        net_trade_dkk=float(net_trade),
        cash_required_dkk=float(max(net_trade, 0.0)),
        constrained_count=constrained_count,
    )
