from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class AttributionResult:
    """Performance-attribution for den aktive portefølje."""

    data: pd.DataFrame
    total_return_dkk: float
    total_cost_dkk: float


def calculate_attribution(
    portfolio: pd.DataFrame,
) -> AttributionResult:
    """
    Beregn simpel siden-køb attribution.

    Contribution_Pct viser positionens bidrag til det samlede aktive
    porteføljeafkast målt mod samlet aktiv kostpris.
    """
    required = {
        "Name",
        "Asset_Type",
        "Include_Weight",
        "Cost_Value_DKK",
        "Market_Value_DKK",
        "Return_DKK",
        "Return_Pct",
        "Portfolio_Weight",
    }

    missing = required.difference(portfolio.columns)
    if missing:
        raise ValueError(
            "Performance attribution mangler kolonner: "
            f"{sorted(missing)}"
        )

    data = portfolio.loc[
        portfolio["Include_Weight"].fillna(False)
    ].copy()

    if data.empty:
        return AttributionResult(
            data=pd.DataFrame(),
            total_return_dkk=0.0,
            total_cost_dkk=0.0,
        )

    for column in [
        "Cost_Value_DKK",
        "Market_Value_DKK",
        "Return_DKK",
        "Return_Pct",
        "Portfolio_Weight",
    ]:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    total_cost = float(data["Cost_Value_DKK"].sum(skipna=True))
    total_return = float(data["Return_DKK"].sum(skipna=True))

    data["Contribution_Pct"] = np.where(
        total_cost > 0,
        data["Return_DKK"] / total_cost,
        np.nan,
    )

    data["Gain_Share"] = np.where(
        total_return != 0,
        data["Return_DKK"] / abs(total_return),
        np.nan,
    )

    data = data.rename(
        columns={
            "Name": "Aktiv",
            "Asset_Type": "Type",
            "Portfolio_Weight": "Vægt",
            "Return_DKK": "Afkast DKK",
            "Return_Pct": "Afkast %",
            "Contribution_Pct": "Bidrag",
            "Gain_Share": "Andel af resultat",
        }
    )

    data = data[
        [
            "Aktiv",
            "Type",
            "Vægt",
            "Afkast DKK",
            "Afkast %",
            "Bidrag",
            "Andel af resultat",
        ]
    ].sort_values(
        "Bidrag",
        ascending=False,
        na_position="last",
    )

    return AttributionResult(
        data=data.reset_index(drop=True),
        total_return_dkk=total_return,
        total_cost_dkk=total_cost,
    )


def top_contributors(
    result: AttributionResult,
    limit: int = 5,
) -> pd.DataFrame:
    """Returnér største positive bidrag."""
    if result.data.empty:
        return pd.DataFrame()

    return (
        result.data.loc[result.data["Bidrag"] > 0]
        .head(limit)
        .copy()
    )


def top_detractors(
    result: AttributionResult,
    limit: int = 5,
) -> pd.DataFrame:
    """Returnér største negative bidrag."""
    if result.data.empty:
        return pd.DataFrame()

    return (
        result.data.loc[result.data["Bidrag"] < 0]
        .sort_values("Bidrag", ascending=True)
        .head(limit)
        .copy()
    )
