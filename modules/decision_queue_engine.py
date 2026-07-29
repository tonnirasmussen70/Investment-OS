from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DecisionQueueResult:
    """Rangordnet kø af de vigtigste investeringsbeslutninger."""

    data: pd.DataFrame
    top_action: str | None
    top_asset: str | None
    top_priority: float
    actionable_count: int


def _normalize_0_100(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)

    minimum = numeric.min()
    maximum = numeric.max()

    if pd.isna(minimum) or pd.isna(maximum) or maximum == minimum:
        return pd.Series(50.0, index=series.index)

    return (
        (numeric - minimum)
        / (maximum - minimum)
        * 100
    ).clip(0, 100).fillna(50.0)


def build_decision_queue(
    doctor_data: pd.DataFrame,
    opportunity_data: pd.DataFrame,
    *,
    max_items: int = 5,
) -> DecisionQueueResult:
    """
    Kombinér Portfolio Doctor og Opportunity Engine i én handlingskø.

    Decision Priority vægter:
    - Portfolio Doctor-prioritet: 35 %
    - Opportunity Score: 30 %
    - AI Confidence: 20 %
    - simuleret Health-effekt: 15 %

    Reducer-signaler inverterer Opportunity Score, fordi lav conviction
    styrker argumentet for en reduktion.
    """
    if doctor_data.empty:
        empty = pd.DataFrame(
            columns=[
                "Prioritet",
                "Handling",
                "Aktiv",
                "Beløb DKK",
                "Ændring",
                "Decision Score",
                "Opportunity",
                "Confidence",
                "Health effekt",
                "Begrundelse",
            ]
        )
        return DecisionQueueResult(
            data=empty,
            top_action=None,
            top_asset=None,
            top_priority=np.nan,
            actionable_count=0,
        )

    queue = doctor_data.copy()

    opportunity_columns = [
        column
        for column in [
            "Name",
            "Yahoo_Ticker",
            "Opportunity Score",
            "Opportunity Label",
        ]
        if column in opportunity_data.columns
    ]

    opportunity_lookup = opportunity_data[
        opportunity_columns
    ].copy()

    if "Yahoo_Ticker" in queue.columns and "Yahoo_Ticker" in opportunity_lookup.columns:
        queue = queue.merge(
            opportunity_lookup[
                [
                    "Yahoo_Ticker",
                    "Opportunity Score",
                    "Opportunity Label",
                ]
            ],
            on="Yahoo_Ticker",
            how="left",
        )
    elif "Ticker" in queue.columns and "Yahoo_Ticker" in opportunity_lookup.columns:
        queue = queue.merge(
            opportunity_lookup[
                [
                    "Yahoo_Ticker",
                    "Opportunity Score",
                    "Opportunity Label",
                ]
            ].rename(columns={"Yahoo_Ticker": "Ticker"}),
            on="Ticker",
            how="left",
        )
    else:
        queue = queue.merge(
            opportunity_lookup[
                [
                    "Name",
                    "Opportunity Score",
                    "Opportunity Label",
                ]
            ].rename(columns={"Name": "Aktiv"}),
            on="Aktiv",
            how="left",
        )

    queue["Doctor Score"] = (
        pd.to_numeric(
            queue["Prioritet"],
            errors="coerce",
        )
        .div(10)
        .mul(100)
        .clip(0, 100)
        .fillna(50.0)
    )

    queue["Opportunity Component"] = pd.to_numeric(
        queue["Opportunity Score"],
        errors="coerce",
    ).fillna(50.0)

    reduce_mask = queue["Handling"].eq("Reducer")
    queue.loc[
        reduce_mask,
        "Opportunity Component",
    ] = (
        100
        - queue.loc[
            reduce_mask,
            "Opportunity Component",
        ]
    )

    queue["Confidence Component"] = pd.to_numeric(
        queue["Confidence"],
        errors="coerce",
    ).clip(0, 100).fillna(50.0)

    queue["Health Component"] = _normalize_0_100(
        pd.to_numeric(
            queue["Health effekt"],
            errors="coerce",
        ).clip(lower=0.0)
    )

    queue["Decision Score"] = (
        0.35 * queue["Doctor Score"]
        + 0.30 * queue["Opportunity Component"]
        + 0.20 * queue["Confidence Component"]
        + 0.15 * queue["Health Component"]
    ).clip(0, 100)

    queue = queue.sort_values(
        [
            "Decision Score",
            "Health effekt",
            "Confidence",
        ],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)

    queue["Prioritet"] = pd.Series(
        range(1, len(queue) + 1),
        dtype="Int64",
    )

    queue["Decision Label"] = pd.cut(
        queue["Decision Score"],
        bins=[-np.inf, 55, 70, 85, np.inf],
        labels=[
            "Lav",
            "Moderat",
            "Høj",
            "Meget høj",
        ],
    ).astype(str)

    display_columns = [
        "Prioritet",
        "Handling",
        "Aktiv",
        "Beløb DKK",
        "Anbefalet ændring",
        "Decision Score",
        "Decision Label",
        "Opportunity Score",
        "Confidence",
        "Health effekt",
        "Begrundelse",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in queue.columns
    ]

    queue = queue[available_columns].head(max_items).copy()

    top = queue.iloc[0]

    return DecisionQueueResult(
        data=queue,
        top_action=str(top["Handling"]),
        top_asset=str(top["Aktiv"]),
        top_priority=float(top["Decision Score"]),
        actionable_count=len(queue),
    )
