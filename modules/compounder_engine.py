from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "Name",
    "Ticker",
    "Composite_Score",
    "AI_Confidence",
    "Status",
}


@dataclass(frozen=True)
class CompounderRadar:
    """Indlæst og valideret resultat fra Emerging Compounder Radar."""

    exists: bool
    data: pd.DataFrame
    source_path: Path | None
    notes: list[str]


def _read_source(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError(f"Ikke understøttet filtype: {suffix}")


def load_compounder_radar(
    data_dir: str | Path = "data",
) -> CompounderRadar:
    """
    Indlæs radarresultater fra første tilgængelige fil:

    1. data/compounder_radar.xlsx
    2. data/compounder_radar.csv

    Manglende fil giver ikke fejl i appen; der returneres blot exists=False.
    """
    directory = Path(data_dir)
    candidates = [
        directory / "compounder_radar.xlsx",
        directory / "compounder_radar.csv",
    ]

    source = next((path for path in candidates if path.exists()), None)

    if source is None:
        return CompounderRadar(
            exists=False,
            data=pd.DataFrame(),
            source_path=None,
            notes=[],
        )

    notes: list[str] = []
    data = _read_source(source).copy()

    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(
            "Compounder Radar mangler kolonner: "
            f"{sorted(missing)}"
        )

    numeric_columns = [
        "Composite_Score",
        "AI_Confidence",
        "Revenue_CAGR_5Y",
        "EPS_CAGR_5Y",
        "Gross_Margin",
        "ROIC",
        "Upside_Pct",
        "Downside_Pct",
        "Risk_Reward",
        "Market_Cap_USD",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

    data["Name"] = data["Name"].astype(str).str.strip()
    data["Ticker"] = data["Ticker"].astype(str).str.strip()
    data["Status"] = data["Status"].astype(str).str.strip()

    duplicate_count = int(
        data.duplicated(subset=["Ticker"], keep="first").sum()
    )
    if duplicate_count:
        notes.append(
            f"{duplicate_count} dublerede tickere blev fjernet."
        )
        data = data.drop_duplicates(
            subset=["Ticker"],
            keep="first",
        )

    if "Risk_Reward" not in data.columns:
        if {
            "Upside_Pct",
            "Downside_Pct",
        }.issubset(data.columns):
            downside = data["Downside_Pct"].abs().replace(0, np.nan)
            data["Risk_Reward"] = data["Upside_Pct"] / downside

    data = data.sort_values(
        ["Composite_Score", "AI_Confidence"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    return CompounderRadar(
        exists=True,
        data=data,
        source_path=source,
        notes=notes,
    )


def top_candidates(
    radar: CompounderRadar,
    limit: int = 20,
) -> pd.DataFrame:
    """Returnér de højest rangerede kandidater."""
    if not radar.exists or radar.data.empty:
        return pd.DataFrame()

    columns = [
        "Name",
        "Ticker",
        "Composite_Score",
        "AI_Confidence",
        "Status",
    ]

    optional_columns = [
        "Revenue_CAGR_5Y",
        "EPS_CAGR_5Y",
        "Gross_Margin",
        "ROIC",
        "Upside_Pct",
        "Risk_Reward",
        "Risk",
        "Reason",
    ]

    columns.extend(
        column
        for column in optional_columns
        if column in radar.data.columns
    )

    return radar.data[columns].head(limit).copy()


def radar_summary(
    radar: CompounderRadar,
) -> dict[str, object]:
    """Returnér de få KPI'er, der er relevante for radaren."""
    if not radar.exists or radar.data.empty:
        return {
            "Candidate_Count": 0,
            "High_Confidence_Count": 0,
            "Average_Confidence": np.nan,
            "Top_Candidate": None,
        }

    data = radar.data

    high_confidence = int(
        (data["AI_Confidence"] >= 80).sum()
    )
    average_confidence = float(
        data["AI_Confidence"].mean()
    )

    top_candidate = (
        data.iloc[0]["Name"]
        if not data.empty
        else None
    )

    return {
        "Candidate_Count": int(len(data)),
        "High_Confidence_Count": high_confidence,
        "Average_Confidence": average_confidence,
        "Top_Candidate": top_candidate,
    }
