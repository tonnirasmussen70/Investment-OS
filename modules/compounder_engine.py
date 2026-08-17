from __future__ import annotations

from dataclasses import dataclass
import json
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

AGENT_COLUMN_MAP = {
    "ticker": "Ticker",
    "name": "Agent_Name",
    "agent_score": "Agent_Score",
    "agent_confidence": "Agent_Confidence",
    "growth_score": "Growth_Score",
    "earnings_score": "Earnings_Score",
    "momentum_score": "Agent_Momentum_Score",
    "capital_flow_score": "Capital_Flow_Score",
    "moat_score": "Moat_Score",
    "guidance_score": "Guidance_Score",
    "news_score": "News_Score",
    "prior_score": "Agent_Prior_Score",
    "score_change": "Agent_Score_Change",
    "is_new": "Is_New",
    "thesis": "Agent_Thesis",
    "risk": "Agent_Risk",
    "news_classification": "News_Classification",
    "sources": "Agent_Sources",
}


@dataclass(frozen=True)
class CompounderRadar:
    """Indlæst og valideret resultat fra Emerging Compounder Pipeline."""

    exists: bool
    data: pd.DataFrame
    source_path: Path | None
    notes: list[str]
    agent_source_path: Path | None = None
    agent_generated_at: str | None = None
    methodology_version: str | None = None


def _normalise_ticker(value: object) -> str:
    return str(value).strip().upper().replace(".", "-")


def _read_source(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError(f"Ikke understøttet filtype: {suffix}")


def _load_agent_intelligence(path: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    if not path.exists():
        return pd.DataFrame(), {}

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("compounder_agent.json: 'candidates' skal være en liste")

    rows: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        row = {
            AGENT_COLUMN_MAP[key]: value
            for key, value in candidate.items()
            if key in AGENT_COLUMN_MAP
        }
        if row.get("Ticker"):
            row["Ticker"] = _normalise_ticker(row["Ticker"])
            rows.append(row)

    data = pd.DataFrame(rows)
    if not data.empty:
        for column in [
            "Agent_Score",
            "Agent_Confidence",
            "Growth_Score",
            "Earnings_Score",
            "Agent_Momentum_Score",
            "Capital_Flow_Score",
            "Moat_Score",
            "Guidance_Score",
            "News_Score",
            "Agent_Prior_Score",
            "Agent_Score_Change",
        ]:
            if column in data.columns:
                data[column] = pd.to_numeric(data[column], errors="coerce")

        if "Is_New" in data.columns:
            data["Is_New"] = data["Is_New"].fillna(False).astype(bool)

        if "Agent_Sources" in data.columns:
            data["Agent_Sources"] = data["Agent_Sources"].apply(
                lambda value: " | ".join(map(str, value))
                if isinstance(value, list)
                else str(value or "")
            )

        data = data.drop_duplicates("Ticker", keep="first")

    metadata = {
        "generated_at": payload.get("generated_at"),
        "methodology_version": payload.get("methodology_version"),
    }
    return data, metadata


def _merge_pipeline(
    quant_data: pd.DataFrame,
    agent_data: pd.DataFrame,
) -> pd.DataFrame:
    if quant_data.empty and agent_data.empty:
        return pd.DataFrame()

    if quant_data.empty:
        result = agent_data.copy()
        result["Name"] = result.get("Agent_Name", result["Ticker"])
        result["Composite_Score"] = np.nan
        result["AI_Confidence"] = np.nan
        result["Status"] = "Agent Candidate"
    elif agent_data.empty:
        result = quant_data.copy()
    else:
        result = quant_data.merge(agent_data, on="Ticker", how="outer")
        if "Agent_Name" in result.columns:
            result["Name"] = result["Name"].fillna(result["Agent_Name"])
        result["Name"] = result["Name"].fillna(result["Ticker"])
        result["Status"] = result["Status"].fillna("Agent Candidate")

    if "Agent_Score" not in result.columns:
        result["Agent_Score"] = np.nan
    if "Agent_Confidence" not in result.columns:
        result["Agent_Confidence"] = np.nan
    if "Is_New" not in result.columns:
        result["Is_New"] = False
    result["Is_New"] = result["Is_New"].fillna(False).astype(bool)

    quant_score = pd.to_numeric(result.get("Composite_Score"), errors="coerce")
    agent_score = pd.to_numeric(result.get("Agent_Score"), errors="coerce")
    quant_conf = pd.to_numeric(result.get("AI_Confidence"), errors="coerce")
    agent_conf = pd.to_numeric(result.get("Agent_Confidence"), errors="coerce")

    both_scores = quant_score.notna() & agent_score.notna()
    result["Discovery_Score"] = quant_score.combine_first(agent_score)
    result.loc[both_scores, "Discovery_Score"] = (
        0.60 * quant_score[both_scores] + 0.40 * agent_score[both_scores]
    )

    both_conf = quant_conf.notna() & agent_conf.notna()
    result["Unified_Confidence"] = quant_conf.combine_first(agent_conf)
    result.loc[both_conf, "Unified_Confidence"] = (
        0.60 * quant_conf[both_conf] + 0.40 * agent_conf[both_conf]
    )

    result["Pipeline_Source"] = np.select(
        [
            quant_score.notna() & agent_score.notna(),
            quant_score.notna(),
            agent_score.notna(),
        ],
        ["Kvant + Agent", "Kvant", "Agent"],
        default="Ukendt",
    )

    result["Research_Priority"] = np.select(
        [
            result["Discovery_Score"].ge(85)
            & result["Unified_Confidence"].ge(75),
            result["Discovery_Score"].ge(75),
        ],
        ["Høj", "Middel"],
        default="Monitor",
    )

    return result.sort_values(
        ["Discovery_Score", "Unified_Confidence", "Name"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)


def load_compounder_radar(
    data_dir: str | Path = "data",
) -> CompounderRadar:
    """
    Indlæs og saml Emerging Compounder Pipeline.

    Kvant-lag:
    1. data/compounder_radar.xlsx
    2. data/compounder_radar.csv

    Intelligence-lag:
    3. data/compounder_agent.json

    Agent-only kandidater bevares, så radarens univers ikke er begrænset til
    S&P 500/Nasdaq-100. Discovery Score er ikke et købssignal eller Decision Score.
    """
    directory = Path(data_dir)
    candidates = [
        directory / "compounder_radar.xlsx",
        directory / "compounder_radar.csv",
    ]
    agent_path = directory / "compounder_agent.json"

    source = next((path for path in candidates if path.exists()), None)
    notes: list[str] = []

    quant_data = pd.DataFrame()
    if source is not None:
        quant_data = _read_source(source).copy()
        missing = REQUIRED_COLUMNS.difference(quant_data.columns)
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
            if column in quant_data.columns:
                quant_data[column] = pd.to_numeric(
                    quant_data[column],
                    errors="coerce",
                )

        quant_data["Name"] = quant_data["Name"].astype(str).str.strip()
        quant_data["Ticker"] = quant_data["Ticker"].map(_normalise_ticker)
        quant_data["Status"] = quant_data["Status"].astype(str).str.strip()

        duplicate_count = int(
            quant_data.duplicated(subset=["Ticker"], keep="first").sum()
        )
        if duplicate_count:
            notes.append(
                f"{duplicate_count} dublerede tickere blev fjernet fra kvant-radaren."
            )
            quant_data = quant_data.drop_duplicates(
                subset=["Ticker"],
                keep="first",
            )

        if "Risk_Reward" not in quant_data.columns:
            if {
                "Upside_Pct",
                "Downside_Pct",
            }.issubset(quant_data.columns):
                downside = quant_data["Downside_Pct"].abs().replace(0, np.nan)
                quant_data["Risk_Reward"] = quant_data["Upside_Pct"] / downside

    try:
        agent_data, metadata = _load_agent_intelligence(agent_path)
    except Exception as exc:
        notes.append(f"Agent-intelligence kunne ikke indlæses: {exc}")
        agent_data, metadata = pd.DataFrame(), {}

    pipeline = _merge_pipeline(quant_data, agent_data)
    exists = not pipeline.empty

    if source is None and agent_data.empty:
        return CompounderRadar(
            exists=False,
            data=pd.DataFrame(),
            source_path=None,
            notes=notes,
            agent_source_path=None,
        )

    if source is None and not agent_data.empty:
        notes.append("Kvant-radaren mangler; viser agent-intelligence alene.")
    if source is not None and agent_data.empty:
        notes.append("Mandags-agentens JSON mangler; viser kvant-radaren alene.")

    return CompounderRadar(
        exists=exists,
        data=pipeline,
        source_path=source,
        notes=notes,
        agent_source_path=agent_path if agent_path.exists() else None,
        agent_generated_at=str(metadata.get("generated_at") or "") or None,
        methodology_version=str(metadata.get("methodology_version") or "") or None,
    )


def top_candidates(
    radar: CompounderRadar,
    limit: int = 20,
) -> pd.DataFrame:
    """Returnér de højest rangerede discovery-kandidater."""
    if not radar.exists or radar.data.empty:
        return pd.DataFrame()

    preferred_columns = [
        "Name",
        "Ticker",
        "Discovery_Score",
        "Research_Priority",
        "Pipeline_Source",
        "Composite_Score",
        "Agent_Score",
        "Unified_Confidence",
        "Is_New",
        "Agent_Score_Change",
        "Status",
        "Revenue_CAGR_5Y",
        "EPS_CAGR_5Y",
        "Gross_Margin",
        "ROIC",
        "Upside_Pct",
        "Risk_Reward",
        "Risk",
        "Agent_Risk",
        "Reason",
        "Agent_Thesis",
        "News_Classification",
    ]
    columns = [column for column in preferred_columns if column in radar.data.columns]
    return radar.data[columns].head(limit).copy()


def radar_summary(
    radar: CompounderRadar,
) -> dict[str, object]:
    """Returnér KPI'er for den samlede Compounder Pipeline."""
    if not radar.exists or radar.data.empty:
        return {
            "Candidate_Count": 0,
            "High_Confidence_Count": 0,
            "Average_Confidence": np.nan,
            "Top_Candidate": None,
            "New_Candidate_Count": 0,
            "Agent_Generated_At": radar.agent_generated_at,
        }

    data = radar.data
    confidence = pd.to_numeric(
        data.get("Unified_Confidence", data.get("AI_Confidence")),
        errors="coerce",
    )
    high_confidence = int((confidence >= 80).sum())
    average_confidence = float(confidence.mean()) if confidence.notna().any() else np.nan
    new_count = int(data.get("Is_New", pd.Series(False, index=data.index)).fillna(False).sum())

    top_candidate = data.iloc[0]["Name"] if not data.empty else None

    return {
        "Candidate_Count": int(len(data)),
        "High_Confidence_Count": high_confidence,
        "Average_Confidence": average_confidence,
        "Top_Candidate": top_candidate,
        "New_Candidate_Count": new_count,
        "Agent_Generated_At": radar.agent_generated_at,
    }
