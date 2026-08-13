from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from modules.decision_engine import (
    DECISION_WEIGHTS,
    apply_decision_engine,
    normalize_decision_weights,
)


# Behold navnet af hensyn til eksisterende Settings/UI-kompatibilitet.
# Der findes ikke længere en separat Opportunity-scoredefinition.
DEFAULT_OPPORTUNITY_WEIGHTS = DECISION_WEIGHTS.copy()


@dataclass(frozen=True)
class OpportunityResult:
    """Rangerede muligheder baseret på den fælles Decision Engine."""

    data: pd.DataFrame
    top_opportunity: str | None
    top_score: float
    lowest_conviction: str | None
    lowest_score: float


def normalize_opportunity_weights(
    weights: dict[str, float] | None,
) -> dict[str, float]:
    """Legacy alias til den fælles vægtnormalisering."""
    return normalize_decision_weights(weights)


def build_opportunity_scores(
    portfolio: pd.DataFrame,
    *,
    factor_weights: dict[str, float] | None = None,
    max_position_weight: float = 0.12,
) -> OpportunityResult:
    """
    Rangér Opportunities uden at beregne en separat investeringsscore.

    Investment OS 6.9 bruger Decision_Score, Decision_Status og Handling fra
    den centrale Decision Engine. Opportunity Score/Label er alene aliases,
    så eksisterende UI kan fortsætte under migrationen.
    """
    if portfolio.empty:
        return OpportunityResult(
            data=pd.DataFrame(),
            top_opportunity=None,
            top_score=np.nan,
            lowest_conviction=None,
            lowest_score=np.nan,
        )

    required = {"Decision_Score", "Decision_Status", "Handling"}
    if not required.issubset(portfolio.columns):
        raise ValueError(
            "Opportunities kræver output fra den centrale Decision Engine først."
        )
    result = portfolio.copy()

    result["Opportunity Score"] = result["Decision_Score"]
    result["Opportunity Label"] = result["Decision_Status"]
    result["Opportunity Rank"] = result["Decision_Score"].rank(
        ascending=False,
        method="min",
    ).astype("Int64")

    result = result.sort_values(
        ["Decision_Score", "AI_Confidence", "Composite"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)

    top = result.iloc[0]
    bottom = result.iloc[-1]

    return OpportunityResult(
        data=result,
        top_opportunity=str(top.get("Name", "Ukendt")),
        top_score=float(top["Decision_Score"]),
        lowest_conviction=str(bottom.get("Name", "Ukendt")),
        lowest_score=float(bottom["Decision_Score"]),
    )
