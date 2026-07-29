from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ChangeResult:
    """Vigtigste forbedringer, forværringer og signalskift."""

    data: pd.DataFrame
    improvements: pd.DataFrame
    deteriorations: pd.DataFrame
    signal_changes: pd.DataFrame


def build_change_engine(
    current: pd.DataFrame,
    previous: pd.DataFrame,
) -> ChangeResult:
    """
    Sammenlign aktuelle signaler med forrige handelsdag.

    Change Score kombinerer ændringen i:
    - Composite momentum: 45 %
    - AI Confidence: 35 %
    - Relative Strength 3M: 20 %

    Modellen måler ændring i signalstyrke, ikke forventet afkast.
    """
    if current.empty or previous.empty:
        empty = pd.DataFrame()
        return ChangeResult(
            data=empty,
            improvements=empty,
            deteriorations=empty,
            signal_changes=empty,
        )

    current_columns = [
        "Yahoo_Ticker",
        "Name",
        "Handling",
        "Composite",
        "AI_Confidence",
        "Relative_Strength_3M",
        "Momentum_Acceleration",
        "Rotation_Signal",
    ]
    previous_columns = [
        "Yahoo_Ticker",
        "Handling",
        "Composite",
        "AI_Confidence",
        "Relative_Strength_3M",
        "Momentum_Acceleration",
        "Rotation_Signal",
    ]

    current_data = current[
        [column for column in current_columns if column in current.columns]
    ].copy()

    previous_data = previous[
        [column for column in previous_columns if column in previous.columns]
    ].copy()

    merged = current_data.merge(
        previous_data,
        on="Yahoo_Ticker",
        how="inner",
        suffixes=("", "_Previous"),
    )

    if merged.empty:
        empty = pd.DataFrame()
        return ChangeResult(
            data=empty,
            improvements=empty,
            deteriorations=empty,
            signal_changes=empty,
        )

    for column in [
        "Composite",
        "AI_Confidence",
        "Relative_Strength_3M",
        "Momentum_Acceleration",
    ]:
        merged[f"Delta_{column}"] = (
            pd.to_numeric(
                merged.get(column),
                errors="coerce",
            )
            - pd.to_numeric(
                merged.get(f"{column}_Previous"),
                errors="coerce",
            )
        )

    merged["Change Score"] = (
        0.45
        * merged["Delta_Composite"].fillna(0)
        * 100
        + 0.35
        * merged["Delta_AI_Confidence"].fillna(0)
        + 0.20
        * merged["Delta_Relative_Strength_3M"].fillna(0)
        * 100
    )

    merged["Signal Changed"] = (
        merged["Handling"].astype(str)
        != merged["Handling_Previous"].astype(str)
    )

    merged["Signal Change"] = np.where(
        merged["Signal Changed"],
        (
            merged["Handling_Previous"].astype(str)
            + " → "
            + merged["Handling"].astype(str)
        ),
        "",
    )

    merged["Rotation Changed"] = (
        merged["Rotation_Signal"].astype(str)
        != merged["Rotation_Signal_Previous"].astype(str)
    )

    merged["Rotation Change"] = np.where(
        merged["Rotation Changed"],
        (
            merged["Rotation_Signal_Previous"].astype(str)
            + " → "
            + merged["Rotation_Signal"].astype(str)
        ),
        "",
    )

    improvements = (
        merged.loc[merged["Change Score"] > 0]
        .sort_values("Change Score", ascending=False)
        .head(3)
        .copy()
    )

    deteriorations = (
        merged.loc[merged["Change Score"] < 0]
        .sort_values("Change Score", ascending=True)
        .head(3)
        .copy()
    )

    signal_changes = (
        merged.loc[
            merged["Signal Changed"]
            | merged["Rotation Changed"]
        ]
        .sort_values(
            "Change Score",
            ascending=False,
        )
        .copy()
    )

    return ChangeResult(
        data=merged,
        improvements=improvements,
        deteriorations=deteriorations,
        signal_changes=signal_changes,
    )
