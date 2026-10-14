from __future__ import annotations

import pandas as pd


def build_early_sell_warnings(current: pd.DataFrame, previous: pd.DataFrame) -> pd.DataFrame:
    """Diagnostic-only: held positions with weakening near-term momentum and score.

    This does not modify Decision Engine actions, trading targets or execution.
    A previous trading-day score is mandatory: no history means no warning.
    """
    columns = ["Name", "Yahoo_Ticker", "Asset_Type", "1W", "1M",
               "Decision_Score", "Previous_Decision_Score", "Score_Change"]
    empty = pd.DataFrame(columns=columns)
    required_current = {"Name", "Yahoo_Ticker", "Portfolio_Weight", "Handling", "1W", "1M", "Decision_Score"}
    required_previous = {"Yahoo_Ticker", "Decision_Score"}
    if (current.empty or previous.empty
            or not required_current.issubset(current.columns)
            or not required_previous.issubset(previous.columns)):
        return empty

    old = previous[["Yahoo_Ticker", "Decision_Score"]].dropna(subset=["Yahoo_Ticker"])
    old = old.drop_duplicates("Yahoo_Ticker").rename(columns={"Decision_Score": "Previous_Decision_Score"})
    candidates = current.copy().merge(old, on="Yahoo_Ticker", how="inner", validate="many_to_one")
    for column in ("Portfolio_Weight", "1W", "1M", "Decision_Score", "Previous_Decision_Score"):
        candidates[column] = pd.to_numeric(candidates[column], errors="coerce")
    candidates["Score_Change"] = candidates["Decision_Score"] - candidates["Previous_Decision_Score"]

    mask = (
        candidates["Portfolio_Weight"].gt(0)
        & candidates["Handling"].eq("Hold")
        & candidates["1W"].lt(0)
        & candidates["1M"].lt(0)
        & candidates["Score_Change"].lt(0)
    )
    if not mask.any():
        return empty
    if "Asset_Type" not in candidates:
        candidates["Asset_Type"] = "Ukendt"
    return candidates.loc[mask, columns].sort_values(
        ["Score_Change", "Decision_Score"], ascending=[True, True]
    ).reset_index(drop=True)
