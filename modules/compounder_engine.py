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


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype=object)
    return frame[column].fillna("").astype(str).str.strip()


def apply_promotion_gate(data: pd.DataFrame) -> pd.DataFrame:
    """
    Klassificér Emerging Compounders i en kontrolleret research-pipeline.

    Promotion Gate er ikke et købssignal. Den afgør kun, hvor langt en kandidat
    må bevæge sig i analyseflowet:

    Monitor -> Deep Research -> Fair Value Review -> Decision Review.

    Decision Review kræver dokumenteret valuation og risikogates. Først efter
    separat Investment OS-analyse kan kandidaten blive en egentlig Opportunity.
    """
    if data.empty:
        return data.copy()

    result = data.copy()

    discovery = _numeric(result, "Discovery_Score")
    confidence = _numeric(result, "Unified_Confidence")
    quant_quality = _numeric(result, "Data_Quality")
    agent_confidence = _numeric(result, "Agent_Confidence")

    revenue_growth = _numeric(result, "Revenue_CAGR_5Y")
    eps_growth = _numeric(result, "EPS_CAGR_5Y")
    gross_margin = _numeric(result, "Gross_Margin")
    growth_score = _numeric(result, "Growth_Score")
    earnings_score = _numeric(result, "Earnings_Score")
    moat_score = _numeric(result, "Moat_Score")

    momentum_3m = _numeric(result, "Momentum_3M")
    momentum_6m = _numeric(result, "Momentum_6M")
    agent_momentum = _numeric(result, "Agent_Momentum_Score")

    upside = _numeric(result, "Upside_Pct")
    downside = _numeric(result, "Downside_Pct")
    risk_reward = _numeric(result, "Risk_Reward")
    quant_risk = _text(result, "Risk").str.lower()
    agent_risk = _text(result, "Agent_Risk").str.lower()

    # Deep Research skal være relativt åben: formålet er netop at udfylde
    # manglende viden på lovende discovery-kandidater.
    deep_research_ready = discovery.ge(75) & confidence.ge(70)

    data_quality_ok = quant_quality.ge(60) | agent_confidence.ge(80)
    growth_ok = revenue_growth.ge(0.10) | growth_score.ge(70)
    earnings_ok = eps_growth.ge(0.12) | earnings_score.ge(70)
    moat_ok = gross_margin.ge(0.40) | moat_score.ge(70)
    risk_ok = ~quant_risk.eq("high") & ~agent_risk.eq("high")

    fair_value_ready = (
        discovery.ge(80)
        & confidence.ge(75)
        & data_quality_ok
        & growth_ok
        & earnings_ok
        & moat_ok
        & risk_ok
    )

    momentum_ok = (momentum_3m.gt(0) & momentum_6m.gt(0)) | agent_momentum.ge(70)
    valuation_available = upside.notna() & risk_reward.notna()
    valuation_ok = valuation_available & upside.ge(0.15) & risk_reward.ge(1.5)
    downside_ok = downside.isna() | downside.gt(-0.35)

    decision_review_ready = (
        fair_value_ready
        & discovery.ge(85)
        & confidence.ge(80)
        & momentum_ok
        & valuation_ok
        & downside_ok
    )

    result["Deep_Research_Ready"] = deep_research_ready
    result["Fair_Value_Ready"] = fair_value_ready
    result["Decision_Review_Ready"] = decision_review_ready

    result["Promotion_Stage"] = np.select(
        [decision_review_ready, fair_value_ready, deep_research_ready],
        ["Decision Review", "Fair Value Review", "Deep Research"],
        default="Monitor",
    )
    result["Next_Action"] = np.select(
        [decision_review_ready, fair_value_ready, deep_research_ready],
        [
            "Send til Decision Review",
            "Lav/validér fair value",
            "Start dybdeanalyse",
        ],
        default="Overvåg",
    )

    reason_rows: list[str] = []
    for idx in result.index:
        reasons: list[str] = []
        if bool(decision_review_ready.loc[idx]):
            reasons.append("Discovery ≥85 og confidence ≥80")
            reasons.append("Vækst, moat, momentum og risiko består")
            reasons.append("Upside ≥15% og risk/reward ≥1,5")
        elif bool(fair_value_ready.loc[idx]):
            reasons.append("Kvalitet består Promotion Gate")
            if not bool(valuation_available.loc[idx]):
                reasons.append("Fair value mangler")
            elif not bool(valuation_ok.loc[idx]):
                reasons.append("Valuation består ikke gate")
            elif not bool(momentum_ok.loc[idx]):
                reasons.append("Momentum består ikke Decision Review-gate")
            else:
                reasons.append("Decision Score-gate endnu ikke opfyldt")
        elif bool(deep_research_ready.loc[idx]):
            reasons.append("Discovery ≥75 og confidence ≥70")
            missing: list[str] = []
            if not bool(data_quality_ok.loc[idx]):
                missing.append("datakvalitet")
            if not bool(growth_ok.loc[idx]):
                missing.append("vækst")
            if not bool(earnings_ok.loc[idx]):
                missing.append("indtjening")
            if not bool(moat_ok.loc[idx]):
                missing.append("moat")
            if not bool(risk_ok.loc[idx]):
                missing.append("risiko")
            if missing:
                reasons.append("Mangler: " + ", ".join(missing))
        else:
            reasons.append("Discovery/confidence under Deep Research-gate")
        reason_rows.append(" · ".join(reasons))

    result["Promotion_Reasons"] = reason_rows
    return result


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

    result = apply_promotion_gate(result)

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
        "Promotion_Stage",
        "Next_Action",
        "Promotion_Reasons",
        "Deep_Research_Ready",
        "Fair_Value_Ready",
        "Decision_Review_Ready",
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
            "Deep_Research_Count": 0,
            "Fair_Value_Count": 0,
            "Decision_Review_Count": 0,
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
    deep_count = int(
        data.get("Deep_Research_Ready", pd.Series(False, index=data.index))
        .fillna(False)
        .sum()
    )
    fair_value_count = int(
        data.get("Fair_Value_Ready", pd.Series(False, index=data.index))
        .fillna(False)
        .sum()
    )
    decision_review_count = int(
        data.get("Decision_Review_Ready", pd.Series(False, index=data.index))
        .fillna(False)
        .sum()
    )

    top_candidate = data.iloc[0]["Name"] if not data.empty else None

    return {
        "Candidate_Count": int(len(data)),
        "High_Confidence_Count": high_confidence,
        "Average_Confidence": average_confidence,
        "Top_Candidate": top_candidate,
        "New_Candidate_Count": new_count,
        "Deep_Research_Count": deep_count,
        "Fair_Value_Count": fair_value_count,
        "Decision_Review_Count": decision_review_count,
        "Agent_Generated_At": radar.agent_generated_at,
    }
