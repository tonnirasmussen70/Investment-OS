from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DecisionQueueResult:
    """Rangordnet kø af konkrete execution-beslutninger."""

    data: pd.DataFrame
    top_action: str | None
    top_asset: str | None
    top_priority: float
    actionable_count: int


def _empty_queue() -> DecisionQueueResult:
    empty = pd.DataFrame(
        columns=[
            "Prioritet",
            "Execution",
            "Handling",
            "Aktiv",
            "Beløb DKK",
            "Anbefalet ændring",
            "Decision Score",
            "Status",
            "Confidence",
            "Constraint",
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


def build_decision_queue(
    execution_data: pd.DataFrame,
    *,
    max_items: int = 5,
) -> DecisionQueueResult:
    """
    Byg handlingskøen direkte fra Rebalanceringens execution-plan.

    Investment OS 7.0 har én sammenhængende kæde:
    Decision Engine -> Rebalancering -> Decision Queue / Overblik.
    Køen må derfor ikke beregne egne scores, vægtændringer eller handelsbeløb.
    """
    if execution_data is None or execution_data.empty:
        return _empty_queue()

    required = {
        "Aktiv",
        "Handling",
        "Rebalance handling",
        "Handel DKK",
        "Ændring",
        "Decision Score",
        "Status",
    }
    missing = required.difference(execution_data.columns)
    if missing:
        raise ValueError(f"Decision Queue mangler execution-felter: {sorted(missing)}")

    queue = execution_data.copy()
    queue = queue.loc[
        queue["Rebalance handling"].isin(["Køb", "Sælg"])
        & pd.to_numeric(queue["Handel DKK"], errors="coerce").ne(0)
    ].copy()

    if queue.empty:
        return _empty_queue()

    queue["Decision Score"] = pd.to_numeric(
        queue["Decision Score"], errors="coerce"
    )
    queue["Beløb DKK"] = pd.to_numeric(
        queue["Handel DKK"], errors="coerce"
    ).abs()
    queue["Anbefalet ændring"] = pd.to_numeric(
        queue["Ændring"], errors="coerce"
    )
    queue["Execution"] = queue["Rebalance handling"]
    queue["Confidence"] = pd.to_numeric(
        queue.get("AI", pd.Series(np.nan, index=queue.index)),
        errors="coerce",
    )
    queue["Constraint"] = queue.get(
        "Constraint", pd.Series("", index=queue.index)
    ).fillna("")

    # Risiko/constraint-reduktioner kommer først. Inden for salg prioriteres
    # laveste conviction først; inden for køb højeste conviction først.
    queue["_execution_order"] = queue["Execution"].map({"Sælg": 0, "Køb": 1}).fillna(9)
    queue["_score_order"] = np.where(
        queue["Execution"].eq("Sælg"),
        queue["Decision Score"],
        -queue["Decision Score"],
    )
    queue = queue.sort_values(
        ["_execution_order", "_score_order", "Beløb DKK"],
        ascending=[True, True, False],
        na_position="last",
    ).reset_index(drop=True)

    queue["Prioritet"] = pd.Series(range(1, len(queue) + 1), dtype="Int64")

    display_columns = [
        "Prioritet",
        "Execution",
        "Handling",
        "Aktiv",
        "Beløb DKK",
        "Anbefalet ændring",
        "Decision Score",
        "Status",
        "Confidence",
        "Constraint",
        "Begrundelse",
    ]
    queue = queue[display_columns].head(max_items).copy()

    top = queue.iloc[0]
    return DecisionQueueResult(
        data=queue,
        top_action=str(top["Execution"]),
        top_asset=str(top["Aktiv"]),
        top_priority=float(top["Decision Score"]),
        actionable_count=len(queue),
    )
