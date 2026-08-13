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
    """Håndhæv sektorloft for aktier uden at ændre ETF-targets."""
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
        proposed = float(data.loc[indices, "Modelmålvægt"].sum())
        if proposed <= max_sector_weight + 1e-12:
            continue

        excess = proposed - max_sector_weight
        positive_delta = (
            data.loc[indices, "Modelmålvægt"]
            - data.loc[indices, "Portfolio_Weight"]
        ).clip(lower=0)
        positive_total = float(positive_delta.sum())

        if positive_total > 0:
            reduction = positive_delta * min(1.0, excess / positive_total)
            data.loc[indices, "Modelmålvægt"] = (
                data.loc[indices, "Modelmålvægt"] - reduction
            )
            constrained = reduction.gt(1e-12)
            constrained_indices = constrained.index[constrained]
            data.loc[constrained_indices, "Constraint"] = data.loc[
                constrained_indices, "Constraint"
            ].apply(lambda value: "Sektorloft" if not value else f"{value}, Sektorloft")
            excess = max(
                0.0,
                float(data.loc[indices, "Modelmålvægt"].sum()) - max_sector_weight,
            )

        # Hvis sektoren allerede var over loftet, skal hard constraint stadig
        # bringe target ned. Laveste Decision Score reduceres først.
        if excess > 1e-12:
            ranked = data.loc[indices].sort_values(
                ["Decision_Score", "Portfolio_Weight"],
                ascending=[True, False],
                na_position="first",
            )
            for row_index in ranked.index:
                if excess <= 1e-12:
                    break
                current_target = float(data.at[row_index, "Modelmålvægt"])
                cut = min(current_target, excess)
                if cut <= 0:
                    continue
                data.at[row_index, "Modelmålvægt"] = current_target - cut
                existing = str(data.at[row_index, "Constraint"] or "")
                data.at[row_index, "Constraint"] = (
                    "Sektorloft" if not existing else f"{existing}, Sektorloft"
                )
                excess -= cut


def build_rebalance_plan(
    portfolio: pd.DataFrame,
    active_market_value_dkk: float,
    max_position_weight: float = 0.12,
    max_sector_weight: float = 0.20,
    minimum_trade_dkk: float = 5000.0,
) -> RebalanceResult:
    """
    Omsæt Decision Engine-output til en konkret execution-plan.

    7.0-principper:
    - Decision Engine bestemmer Score, Status og Handling.
    - Rebalancering beregner dynamiske target weights ud fra conviction.
    - Positionsloft og sektorloft er hard constraints.
    - Hold/Afvent ændres kun, hvis en hard constraint kræver det.
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

    # Hard position constraint gælder uanset Action.
    position_cap = data["Modelmålvægt"].gt(max_position_weight)
    data.loc[position_cap, "Modelmålvægt"] = max_position_weight
    data.loc[position_cap, "Constraint"] = "Positionsloft"

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

    data["Begrundelse"] = np.select(
        [
            data["Rebalance handling"].eq("Køb"),
            data["Rebalance handling"].eq("Sælg") & data["Handling"].eq("Reducer"),
            data["Rebalance handling"].eq("Sælg") & data["Constraint"].str.contains("loft", case=False, na=False),
            data["Under minimumshandel"],
        ],
        [
            "Øg-signal omsat til dynamisk target weight",
            "Reducer-signal omsat til dynamisk target weight",
            "Hard constraint kræver lavere vægt",
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
