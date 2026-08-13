from __future__ import annotations

import unittest

import pandas as pd

from modules.decision_engine import apply_decision_engine, decision_summary
from modules.opportunity_engine import build_opportunity_scores


class DecisionEngineConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame(
            [
                {
                    "Name": "Strong",
                    "Composite": 0.18,
                    "AI_Confidence": 82.0,
                    "Relative_Strength_3M": 0.05,
                    "Volatility": 0.25,
                    "Max_Drawdown": -0.12,
                    "Momentum_Data_Quality": 1.0,
                    "Portfolio_Weight": 0.06,
                    "1W": 0.03,
                    "1M": 0.06,
                    "3M": 0.15,
                    "6M": 0.20,
                    "Momentum_Acceleration": 0.02,
                    "Rotation_Signal": "Accelererer",
                },
                {
                    "Name": "HoldCase",
                    "Composite": 0.14,
                    "AI_Confidence": 88.0,
                    "Relative_Strength_3M": 0.06,
                    "Volatility": 0.24,
                    "Max_Drawdown": -0.10,
                    "Momentum_Data_Quality": 1.0,
                    "Portfolio_Weight": 0.08,
                    "1W": 0.01,
                    "1M": 0.04,
                    "3M": 0.14,
                    "6M": 0.18,
                    "Momentum_Acceleration": -0.01,
                    "Rotation_Signal": "Neutral",
                },
                {
                    "Name": "Weak",
                    "Composite": -0.10,
                    "AI_Confidence": 35.0,
                    "Relative_Strength_3M": -0.08,
                    "Volatility": 0.50,
                    "Max_Drawdown": -0.38,
                    "Momentum_Data_Quality": 1.0,
                    "Portfolio_Weight": 0.05,
                    "1W": -0.04,
                    "1M": -0.07,
                    "3M": -0.12,
                    "6M": -0.10,
                    "Momentum_Acceleration": -0.02,
                    "Rotation_Signal": "Aftager",
                },
            ]
        )
        self.weights = {
            "Momentum": 0.25,
            "AI Confidence": 0.20,
            "Relative Strength": 0.15,
            "Trend": 0.15,
            "Risiko": 0.10,
            "Datakvalitet": 0.10,
            "Positionsbonus": 0.05,
        }

    def test_opportunities_only_rank_existing_decision_output(self) -> None:
        scored = apply_decision_engine(
            self.frame,
            factor_weights=self.weights,
            max_position_weight=0.12,
        ).data
        canonical = scored.set_index("Name")

        opportunities = build_opportunity_scores(
            scored.copy(),
            factor_weights=self.weights,
            max_position_weight=0.12,
        ).data.set_index("Name")

        pd.testing.assert_series_equal(
            canonical["Decision_Score"].sort_index(),
            opportunities["Decision_Score"].sort_index(),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            canonical["Decision_Status"].sort_index(),
            opportunities["Decision_Status"].sort_index(),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            canonical["Handling"].sort_index(),
            opportunities["Handling"].sort_index(),
            check_names=False,
        )

    def test_opportunities_reject_unscored_input(self) -> None:
        with self.assertRaises(ValueError):
            build_opportunity_scores(
                self.frame.copy(),
                factor_weights=self.weights,
                max_position_weight=0.12,
            )

    def test_summary_is_read_only(self) -> None:
        scored = apply_decision_engine(
            self.frame,
            factor_weights=self.weights,
            max_position_weight=0.12,
        ).data
        before = scored[["Decision_Score", "Decision_Status", "Handling"]].copy(deep=True)

        summary = decision_summary(scored)

        after = scored[["Decision_Score", "Decision_Status", "Handling"]]
        pd.testing.assert_frame_equal(before, after)
        self.assertIn(summary["Top_Decision_Asset"], scored["Name"].tolist())

    def test_action_logic_is_canonical(self) -> None:
        scored = apply_decision_engine(
            self.frame,
            factor_weights=self.weights,
            max_position_weight=0.12,
        ).data.set_index("Name")

        self.assertEqual(scored.loc["Strong", "Handling"], "Øg")
        self.assertEqual(scored.loc["HoldCase", "Handling"], "Hold")
        self.assertEqual(scored.loc["Weak", "Handling"], "Reducer")

    def test_negative_one_month_hard_gate_caps_score(self) -> None:
        scored = apply_decision_engine(
            self.frame,
            factor_weights=self.weights,
            max_position_weight=0.12,
        ).data.set_index("Name")

        self.assertLessEqual(float(scored.loc["Weak", "Decision_Score"]), 69.9)
        self.assertNotIn(
            scored.loc["Weak", "Decision_Status"],
            {"Stærk", "Meget stærk"},
        )


if __name__ == "__main__":
    unittest.main()
