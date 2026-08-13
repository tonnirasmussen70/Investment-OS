from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# Investment OS 6.9: én autoritativ scoredefinition.
# Disse vægte bruges af Momentum, Opportunities, Rebalancering og Overblik.
DECISION_WEIGHTS = {
    "Momentum": 0.25,
    "AI Confidence": 0.20,
    "Relative Strength": 0.15,
    "Trend": 0.15,
    "Risiko": 0.10,
    "Datakvalitet": 0.10,
    "Positionsbonus": 0.05,
}

ACTION_PRIORITY = {
    "Reducer": 0,
    "Afvent": 1,
    "Øg": 2,
    "Hold": 3,
    "Uden for analyse": 4,
}


@dataclass(frozen=True)
class DecisionResult:
    """Autoritativt output fra Investment OS Decision Engine."""

    data: pd.DataFrame
    top_asset: str | None
    top_score: float


def normalize_decision_weights(
    weights: dict[str, float] | None = None,
) -> dict[str, float]:
    source = weights or DECISION_WEIGHTS
    cleaned = {
        factor: max(0.0, float(source.get(factor, 0.0)))
        for factor in DECISION_WEIGHTS
    }
    total = sum(cleaned.values())
    if total <= 0:
        return DECISION_WEIGHTS.copy()
    return {factor: value / total for factor, value in cleaned.items()}


def _percentile_score(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() <= 1:
        return pd.Series(50.0, index=series.index)
    return numeric.rank(pct=True, method="average").mul(100).fillna(50.0)


def _trend_score(frame: pd.DataFrame) -> pd.Series:
    periods = {
        "1W": 0.15,
        "1M": 0.25,
        "3M": 0.30,
        "6M": 0.30,
    }
    result = pd.Series(0.0, index=frame.index)
    available_weight = pd.Series(0.0, index=frame.index)

    for column, weight in periods.items():
        values = pd.to_numeric(frame.get(column), errors="coerce")
        valid = values.notna()
        result = result.add(
            valid.astype(float) * values.gt(0).astype(float) * weight * 100,
            fill_value=0,
        )
        available_weight = available_weight.add(
            valid.astype(float) * weight,
            fill_value=0,
        )

    return (
        result.div(available_weight.replace(0, np.nan))
        .fillna(50.0)
        .clip(0, 100)
    )


def _risk_score(frame: pd.DataFrame) -> pd.Series:
    volatility = pd.to_numeric(frame.get("Volatility"), errors="coerce")
    drawdown = pd.to_numeric(frame.get("Max_Drawdown"), errors="coerce").abs()

    volatility_score = (
        (0.55 - volatility) / (0.55 - 0.18) * 100
    ).clip(0, 100).fillna(50.0)
    drawdown_score = (
        (0.45 - drawdown) / (0.45 - 0.10) * 100
    ).clip(0, 100).fillna(50.0)

    return (0.60 * volatility_score + 0.40 * drawdown_score).clip(0, 100)


def _position_score(
    frame: pd.DataFrame,
    max_position_weight: float,
) -> pd.Series:
    weights = pd.to_numeric(frame.get("Portfolio_Weight"), errors="coerce").fillna(0.0)
    ceiling = max(float(max_position_weight), 0.01)
    return ((ceiling - weights) / ceiling * 100).clip(0, 100)


def _data_quality_score(frame: pd.DataFrame) -> pd.Series:
    if "Momentum_Data_Quality" not in frame.columns:
        return pd.Series(50.0, index=frame.index)
    return (
        pd.to_numeric(frame["Momentum_Data_Quality"], errors="coerce")
        .mul(100)
        .clip(0, 100)
        .fillna(50.0)
    )


def decision_status(score: float) -> str:
    """Én statusdefinition for hele Investment OS."""
    if pd.isna(score):
        return "Datamangel"
    if score >= 85:
        return "Meget stærk"
    if score >= 70:
        return "Stærk"
    if score >= 55:
        return "Interessant"
    if score >= 40:
        return "Neutral"
    return "Lav conviction"


def _decision_action(frame: pd.DataFrame) -> pd.Series:
    """
    Én Action-logik for hele Investment OS.

    Status beskriver kvalitet/conviction. Handling beskriver timing.
    Derfor kan en Meget stærk position godt være Hold, hvis den kortsigtede
    acceleration ikke understøtter et nyt køb.
    """
    score = pd.to_numeric(frame["Decision_Score"], errors="coerce")
    one_week = pd.to_numeric(frame.get("1W"), errors="coerce")
    one_month = pd.to_numeric(frame.get("1M"), errors="coerce")
    three_months = pd.to_numeric(frame.get("3M"), errors="coerce")
    acceleration = pd.to_numeric(
        frame.get("Momentum_Acceleration"),
        errors="coerce",
    )
    composite = pd.to_numeric(frame.get("Composite"), errors="coerce")

    increase = (
        score.ge(70)
        & one_week.gt(0)
        & one_month.gt(0)
        & acceleration.gt(0)
    )
    reduce = (
        one_week.lt(0)
        & one_month.lt(0)
        & three_months.lt(0)
    ) | score.lt(40)
    wait = (
        one_month.lt(0)
        | composite.lt(0)
        | frame.get("Rotation_Signal", pd.Series("Neutral", index=frame.index)).eq("Aftager")
        | score.lt(55)
    )

    return pd.Series(
        np.select(
            [increase, reduce, wait],
            ["Øg", "Reducer", "Afvent"],
            default="Hold",
        ),
        index=frame.index,
    )


def apply_decision_engine(
    portfolio: pd.DataFrame,
    *,
    factor_weights: dict[str, float] | None = None,
    max_position_weight: float = 0.12,
    inplace: bool = False,
) -> DecisionResult:
    """
    Beregn det autoritative Decision Engine-output.

    Outputkolonnerne er fælles for alle views:
    Decision_Score, Decision_Status, Handling samt syv scorekomponenter.
    Legacy Opportunity-kolonner oprettes som aliases, så resten af 6.8-UI'et
    kan migreres gradvist uden parallel beregningslogik.
    """
    if portfolio.empty:
        return DecisionResult(data=portfolio.copy(), top_asset=None, top_score=np.nan)

    required = {"Composite", "AI_Confidence"}
    missing = required.difference(portfolio.columns)
    if missing:
        raise ValueError(
            f"Decision Engine mangler kolonner: {sorted(missing)}"
        )

    result = portfolio if inplace else portfolio.copy()
    weights = normalize_decision_weights(factor_weights)

    result["Momentum Score"] = _percentile_score(result["Composite"])
    result["AI Score"] = (
        pd.to_numeric(result["AI_Confidence"], errors="coerce")
        .clip(0, 100)
        .fillna(50.0)
    )

    relative_strength = pd.to_numeric(
        result.get("Relative_Strength_3M"),
        errors="coerce",
    )
    result["RS Score"] = (
        (relative_strength + 0.10) / 0.20 * 100
    ).clip(0, 100).fillna(50.0)
    result["Trend Score"] = _trend_score(result)
    result["Risk Score"] = _risk_score(result)
    result["Data Score"] = _data_quality_score(result)
    result["Position Score"] = _position_score(
        result,
        max_position_weight=max_position_weight,
    )

    factor_columns = {
        "Momentum": "Momentum Score",
        "AI Confidence": "AI Score",
        "Relative Strength": "RS Score",
        "Trend": "Trend Score",
        "Risiko": "Risk Score",
        "Datakvalitet": "Data Score",
        "Positionsbonus": "Position Score",
    }

    result["Decision_Score"] = sum(
        result[column] * weights[factor]
        for factor, column in factor_columns.items()
    ).clip(0, 100)

    # Hard gate: negativ 1M kan ikke klassificeres som Stærk/Meget stærk.
    one_month = pd.to_numeric(result.get("1M"), errors="coerce")
    result.loc[one_month.lt(0), "Decision_Score"] = result.loc[
        one_month.lt(0), "Decision_Score"
    ].clip(upper=69.9)

    result["Decision_Status"] = result["Decision_Score"].apply(decision_status)
    result["Handling"] = _decision_action(result)

    # Compatibility aliases. Ingen separat Opportunity-beregning.
    result["Opportunity Score"] = result["Decision_Score"]
    result["Opportunity Label"] = result["Decision_Status"]
    result["Opportunity Rank"] = result["Decision_Score"].rank(
        ascending=False,
        method="min",
    ).astype("Int64")

    ordered = result.sort_values(
        ["Decision_Score", "AI_Confidence", "Composite"],
        ascending=[False, False, False],
        na_position="last",
    )
    top = ordered.iloc[0]

    return DecisionResult(
        data=result,
        top_asset=str(top.get("Name", "Ukendt")),
        top_score=float(top["Decision_Score"]),
    )


def confidence_label(score: float) -> str:
    """Returnér en kort fortolkning af AI Confidence."""
    if pd.isna(score):
        return "Datamangel"
    if score >= 80:
        return "Høj"
    if score >= 65:
        return "Moderat-høj"
    if score >= 50:
        return "Moderat"
    if score >= 35:
        return "Lav"
    return "Meget lav"


def capital_flow_label(
    portfolio: pd.DataFrame,
    positive_threshold: float = 0.65,
    neutral_threshold: float = 0.40,
) -> tuple[str, float]:
    if portfolio.empty or "Portfolio_Weight" not in portfolio.columns:
        return "Ukendt", np.nan

    total_weight = portfolio["Portfolio_Weight"].fillna(0).sum()
    if total_weight <= 0:
        return "Ukendt", np.nan

    positive_share = portfolio.loc[
        portfolio["Composite"].fillna(0) > 0,
        "Portfolio_Weight",
    ].fillna(0).sum()

    normalized_share = float(positive_share / total_weight)
    if normalized_share >= positive_threshold:
        return "Positiv", normalized_share
    if normalized_share >= neutral_threshold:
        return "Neutral", normalized_share
    return "Negativ", normalized_share


def action_reason(row: pd.Series) -> str:
    handling = row.get("Handling", "Hold")
    status = row.get("Decision_Status", row.get("Opportunity Label", "Ukendt"))
    one_week = row.get("1W", np.nan)
    one_month = row.get("1M", np.nan)
    three_months = row.get("3M", np.nan)
    confidence = row.get("AI_Confidence", np.nan)
    volatility = row.get("Volatility", np.nan)
    max_drawdown = row.get("Max_Drawdown", np.nan)

    reasons: list[str] = []
    if handling == "Øg":
        reasons.append(f"{status.lower()} samlet score")
        if pd.notna(one_week) and one_week > 0:
            reasons.append("positivt 1W-momentum")
        if pd.notna(one_month) and one_month > 0:
            reasons.append("positivt 1M-momentum")
    elif handling == "Reducer":
        if pd.notna(one_week) and one_week < 0:
            reasons.append("negativt 1W-momentum")
        if pd.notna(one_month) and one_month < 0:
            reasons.append("negativt 1M-momentum")
        if pd.notna(three_months) and three_months < 0:
            reasons.append("negativ 3M-trend")
    elif handling == "Afvent":
        reasons.append(f"{status.lower()} samlet score")
        if pd.notna(one_month) and one_month < 0:
            reasons.append("negativt 1M-momentum")
    else:
        reasons.append(f"{status.lower()} samlet score")
        if pd.notna(confidence) and confidence >= 50:
            reasons.append("acceptabel AI Confidence")

    if pd.notna(volatility) and volatility > 0.45:
        reasons.append("høj volatilitet")
    if pd.notna(max_drawdown) and max_drawdown < -0.30:
        reasons.append("stort drawdown")

    return ", ".join(reasons[:3]).capitalize() if reasons else "Ingen væsentlig ændring"


def action_priority(handling: str) -> str:
    return {
        "Reducer": "🔴 Høj",
        "Øg": "🟢 Mulighed",
        "Afvent": "🟡 Afvent",
        "Hold": "⚪ Neutral",
        "Uden for analyse": "⚪ Udenfor",
    }.get(str(handling), "⚪ Neutral")


def build_action_table(
    portfolio: pd.DataFrame,
    max_rows: int = 5,
    include_hold: bool = False,
) -> pd.DataFrame:
    required = {
        "Name", "Handling", "Composite", "AI_Confidence", "1W", "1M", "3M"
    }
    missing = required.difference(portfolio.columns)
    if missing:
        raise ValueError(
            f"Kan ikke bygge handlingstabel. Mangler kolonner: {sorted(missing)}"
        )

    actions = portfolio.copy()
    if not include_hold:
        actions = actions.loc[actions["Handling"].ne("Hold")].copy()

    if actions.empty:
        return pd.DataFrame(
            columns=[
                "Prioritet", "Aktiv", "Handling", "Decision Score",
                "Status", "AI Confidence", "Begrundelse",
            ]
        )

    actions["Begrundelse"] = actions.apply(action_reason, axis=1)
    actions["Prioritet"] = actions["Handling"].map(action_priority)
    actions["_priority_order"] = actions["Handling"].map(ACTION_PRIORITY).fillna(99)

    actions = (
        actions.sort_values(
            ["_priority_order", "Decision_Score", "AI_Confidence"],
            ascending=[True, False, False],
            na_position="last",
        )
        .head(max_rows)
        .rename(
            columns={
                "Name": "Aktiv",
                "Decision_Score": "Decision Score",
                "Decision_Status": "Status",
                "AI_Confidence": "AI Confidence",
            }
        )
    )

    return actions[
        [
            "Prioritet", "Aktiv", "Handling", "Decision Score",
            "Status", "AI Confidence", "Begrundelse",
        ]
    ].reset_index(drop=True)


def portfolio_ai_confidence(portfolio: pd.DataFrame) -> float:
    if portfolio.empty:
        return np.nan
    required = {"AI_Confidence", "Portfolio_Weight"}
    if not required.issubset(portfolio.columns):
        return np.nan

    valid = portfolio[
        portfolio["AI_Confidence"].notna()
        & portfolio["Portfolio_Weight"].fillna(0).gt(0)
    ].copy()
    if valid.empty:
        return np.nan

    return float(np.average(valid["AI_Confidence"], weights=valid["Portfolio_Weight"]))


def decision_summary(portfolio: pd.DataFrame) -> dict[str, object]:
    """Kør Decision Engine og returnér dashboardets centrale signaler."""
    decision_result = apply_decision_engine(portfolio, inplace=True)
    scored = decision_result.data
    ai_confidence = portfolio_ai_confidence(scored)
    flow_label, positive_share = capital_flow_label(scored)

    return {
        "AI_Confidence": ai_confidence,
        "AI_Confidence_Label": confidence_label(ai_confidence),
        "Capital_Flow": flow_label,
        "Positive_Momentum_Share": positive_share,
        "Top_Decision_Asset": decision_result.top_asset,
        "Top_Decision_Score": decision_result.top_score,
        "Actions": build_action_table(scored),
    }
