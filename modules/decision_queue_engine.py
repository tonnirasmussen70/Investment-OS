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


def build_decision_queue(
    doctor_data: pd.DataFrame,
    opportunity_data: pd.DataFrame,
    *,
    max_items: int = 5,
) -> DecisionQueueResult:
    """
    Byg handlingskøen uden at skabe en ny score.

    Investment OS 6.9 bruger Decision_Score og Decision_Status direkte fra
    den centrale Decision Engine. Portfolio Doctor leverer fortsat anbefalet
    vægtændring, beløb, Health-effekt og begrundelse, men må ikke ændre den
    investeringsmæssige rangering.
    """
    if doctor_data.empty:
        empty = pd.DataFrame(
            columns=[
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
        )
        return DecisionQueueResult(
            data=empty,
            top_action=None,
            top_asset=None,
            top_priority=np.nan,
            actionable_count=0,
        )

    queue = doctor_data.copy()

    lookup_columns = [
        column
        for column in [
            "Name",
            "Yahoo_Ticker",
            "Decision_Score",
            "Decision_Status",
            "Handling",
            "Opportunity Score",
            "Opportunity Label",
        ]
        if column in opportunity_data.columns
    ]
    lookup = opportunity_data[lookup_columns].copy()

    merge_columns = [
        column
        for column in [
            "Decision_Score",
            "Decision_Status",
            "Opportunity Score",
            "Opportunity Label",
        ]
        if column in lookup.columns
    ]

    if "Yahoo_Ticker" in queue.columns and "Yahoo_Ticker" in lookup.columns:
        queue = queue.merge(
            lookup[["Yahoo_Ticker", *merge_columns]],
            on="Yahoo_Ticker",
            how="left",
        )
    elif "Ticker" in queue.columns and "Yahoo_Ticker" in lookup.columns:
        queue = queue.merge(
            lookup[["Yahoo_Ticker", *merge_columns]].rename(
                columns={"Yahoo_Ticker": "Ticker"}
            ),
            on="Ticker",
            how="left",
        )
    else:
        queue = queue.merge(
            lookup[["Name", *merge_columns]].rename(columns={"Name": "Aktiv"}),
            on="Aktiv",
            how="left",
        )

    queue["Decision Score"] = pd.to_numeric(
        queue.get("Decision_Score"),
        errors="coerce",
    )
    queue["Decision Label"] = queue.get(
        "Decision_Status",
        pd.Series("Datamangel", index=queue.index),
    )
    queue["Opportunity Score"] = queue["Decision Score"]

    # Kun rækker med en reel Doctor-handling skal i handlingskøen.
    # Rangeringen kommer alene fra Decision Engine; Health-effekt bruges kun
    # som sekundær tie-breaker.
    queue = queue.loc[
        queue["Handling"].isin(["Øg", "Reducer", "Afvent", "Hold"])
    ].copy()

    queue = queue.sort_values(
        ["Decision Score", "Health effekt", "Confidence"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)

    queue["Prioritet"] = pd.Series(
        range(1, len(queue) + 1),
        dtype="Int64",
    )

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
        column for column in display_columns if column in queue.columns
    ]
    queue = queue[available_columns].head(max_items).copy()

    if queue.empty:
        return DecisionQueueResult(
            data=queue,
            top_action=None,
            top_asset=None,
            top_priority=np.nan,
            actionable_count=0,
        )

    top = queue.iloc[0]
    return DecisionQueueResult(
        data=queue,
        top_action=str(top["Handling"]),
        top_asset=str(top["Aktiv"]),
        top_priority=float(top["Decision Score"]),
        actionable_count=len(queue),
    )
