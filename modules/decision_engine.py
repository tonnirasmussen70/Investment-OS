from __future__ import annotations

import numpy as np
import pandas as pd


ACTION_PRIORITY = {
    "Reducer": 0,
    "Afvent": 1,
    "Øg": 2,
    "Hold": 3,
    "Uden for analyse": 4,
}


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
    """
    Beregn et enkelt kapitalflow-signal ud fra andelen af porteføljevægten
    med positiv Composite-score.
    """
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
    """Forklar kort hvorfor modellen foreslår en handling."""
    handling = row.get("Handling", "Hold")
    one_week = row.get("1W", np.nan)
    one_month = row.get("1M", np.nan)
    three_months = row.get("3M", np.nan)
    six_months = row.get("6M", np.nan)
    composite = row.get("Composite", np.nan)
    confidence = row.get("AI_Confidence", np.nan)
    volatility = row.get("Volatility", np.nan)
    max_drawdown = row.get("Max_Drawdown", np.nan)

    reasons: list[str] = []

    if handling == "Øg":
        if pd.notna(one_week) and one_week > 0:
            reasons.append("positivt 1W-momentum")
        if pd.notna(one_month) and one_month > 0:
            reasons.append("positivt 1M-momentum")
        if pd.notna(confidence) and confidence >= 65:
            reasons.append("stærk AI Confidence")

    elif handling == "Reducer":
        if pd.notna(one_week) and one_week < 0:
            reasons.append("negativt 1W-momentum")
        if pd.notna(one_month) and one_month < 0:
            reasons.append("negativt 1M-momentum")
        if pd.notna(three_months) and three_months < 0:
            reasons.append("negativ 3M-trend")

    elif handling == "Afvent":
        if pd.notna(one_week) and pd.notna(one_month):
            if one_week > 0 and one_month < 0:
                reasons.append("mulig tidlig vending")
            elif one_week < 0 and one_month > 0:
                reasons.append("svækket kort momentum")
        if pd.notna(composite) and composite < 0:
            reasons.append("negativ Composite-score")

    elif handling == "Hold":
        if pd.notna(three_months) and three_months > 0:
            reasons.append("positiv mellemfristet trend")
        if pd.notna(six_months) and six_months > 0:
            reasons.append("positiv 6M-trend")
        if pd.notna(confidence) and confidence >= 50:
            reasons.append("acceptabel AI Confidence")

    if pd.notna(volatility) and volatility > 0.45:
        reasons.append("høj volatilitet")
    if pd.notna(max_drawdown) and max_drawdown < -0.30:
        reasons.append("stort drawdown")

    if not reasons:
        return "Ingen væsentlig ændring"

    return ", ".join(reasons[:3]).capitalize()


def action_priority(handling: str) -> str:
    """Returnér en visuel prioritet til handlingstabeller."""
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
    """
    Byg den centrale handlingstabel til Overblik og andre faner.
    """
    required = {
        "Name",
        "Handling",
        "Composite",
        "AI_Confidence",
        "1W",
        "1M",
        "3M",
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
                "Prioritet",
                "Aktiv",
                "Handling",
                "Composite",
                "AI Confidence",
                "Begrundelse",
            ]
        )

    actions["Begrundelse"] = actions.apply(action_reason, axis=1)
    actions["Prioritet"] = actions["Handling"].map(action_priority)
    actions["_priority_order"] = (
        actions["Handling"].map(ACTION_PRIORITY).fillna(99)
    )

    actions = (
        actions.sort_values(
            ["_priority_order", "AI_Confidence", "Composite"],
            ascending=[True, False, False],
            na_position="last",
        )
        .head(max_rows)
        .rename(
            columns={
                "Name": "Aktiv",
                "AI_Confidence": "AI Confidence",
            }
        )
    )

    return actions[
        [
            "Prioritet",
            "Aktiv",
            "Handling",
            "Composite",
            "AI Confidence",
            "Begrundelse",
        ]
    ].reset_index(drop=True)


def portfolio_ai_confidence(portfolio: pd.DataFrame) -> float:
    """Beregn vægtet AI Confidence for den aktive portefølje."""
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

    return float(
        np.average(
            valid["AI_Confidence"],
            weights=valid["Portfolio_Weight"],
        )
    )


def decision_summary(portfolio: pd.DataFrame) -> dict[str, object]:
    """Returnér de få centrale beslutningssignaler til dashboardet."""
    ai_confidence = portfolio_ai_confidence(portfolio)
    flow_label, positive_share = capital_flow_label(portfolio)

    return {
        "AI_Confidence": ai_confidence,
        "AI_Confidence_Label": confidence_label(ai_confidence),
        "Capital_Flow": flow_label,
        "Positive_Momentum_Share": positive_share,
        "Actions": build_action_table(portfolio),
    }
