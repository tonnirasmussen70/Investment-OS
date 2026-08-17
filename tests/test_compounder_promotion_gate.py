from __future__ import annotations

import numpy as np
import pandas as pd

from modules.compounder_engine import apply_promotion_gate


def _candidate(**overrides) -> dict[str, object]:
    row: dict[str, object] = {
        "Name": "Test Compounder",
        "Ticker": "TEST",
        "Discovery_Score": 86.0,
        "Unified_Confidence": 82.0,
        "Data_Quality": 85.0,
        "Revenue_CAGR_5Y": 0.18,
        "EPS_CAGR_5Y": 0.20,
        "Gross_Margin": 0.55,
        "Growth_Score": 82.0,
        "Earnings_Score": 82.0,
        "Moat_Score": 80.0,
        "Agent_Momentum_Score": 78.0,
        "Momentum_3M": 0.12,
        "Momentum_6M": 0.22,
        "Upside_Pct": 0.24,
        "Downside_Pct": -0.14,
        "Risk_Reward": 1.7,
        "Risk": "Low",
        "Agent_Risk": "Medium",
    }
    row.update(overrides)
    return row


def test_high_quality_candidate_reaches_decision_review() -> None:
    result = apply_promotion_gate(pd.DataFrame([_candidate()]))
    row = result.iloc[0]

    assert bool(row["Deep_Research_Ready"])
    assert bool(row["Fair_Value_Ready"])
    assert bool(row["Decision_Review_Ready"])
    assert row["Promotion_Stage"] == "Decision Review"
    assert row["Next_Action"] == "Send til Decision Review"


def test_missing_valuation_stops_at_fair_value_review() -> None:
    result = apply_promotion_gate(
        pd.DataFrame([
            _candidate(Upside_Pct=np.nan, Risk_Reward=np.nan)
        ])
    )
    row = result.iloc[0]

    assert bool(row["Deep_Research_Ready"])
    assert bool(row["Fair_Value_Ready"])
    assert not bool(row["Decision_Review_Ready"])
    assert row["Promotion_Stage"] == "Fair Value Review"
    assert row["Next_Action"] == "Lav/validér fair value"


def test_agent_only_candidate_can_enter_deep_research_but_not_decision_review() -> None:
    result = apply_promotion_gate(
        pd.DataFrame([
            _candidate(
                Discovery_Score=78.0,
                Unified_Confidence=76.0,
                Data_Quality=np.nan,
                Revenue_CAGR_5Y=np.nan,
                EPS_CAGR_5Y=np.nan,
                Gross_Margin=np.nan,
                Upside_Pct=np.nan,
                Risk_Reward=np.nan,
                Agent_Confidence=84.0,
            )
        ])
    )
    row = result.iloc[0]

    assert bool(row["Deep_Research_Ready"])
    assert not bool(row["Fair_Value_Ready"])
    assert not bool(row["Decision_Review_Ready"])
    assert row["Promotion_Stage"] == "Deep Research"


def test_high_risk_blocks_fair_value_and_decision_review() -> None:
    result = apply_promotion_gate(
        pd.DataFrame([_candidate(Agent_Risk="High")])
    )
    row = result.iloc[0]

    assert bool(row["Deep_Research_Ready"])
    assert not bool(row["Fair_Value_Ready"])
    assert not bool(row["Decision_Review_Ready"])
    assert row["Promotion_Stage"] == "Deep Research"


def test_low_discovery_score_remains_monitor() -> None:
    result = apply_promotion_gate(
        pd.DataFrame([_candidate(Discovery_Score=69.0)])
    )
    row = result.iloc[0]

    assert not bool(row["Deep_Research_Ready"])
    assert row["Promotion_Stage"] == "Monitor"
    assert row["Next_Action"] == "Overvåg"
