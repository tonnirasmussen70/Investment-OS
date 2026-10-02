from __future__ import annotations

import unittest

import pandas as pd

from modules.decision_engine import _decision_action


class HoldAfventSemanticsTests(unittest.TestCase):
    def test_existing_position_holds_when_no_increase_or_reduce_signal(self) -> None:
        frame = pd.DataFrame([{
            "Decision_Score": 62.0,
            "Portfolio_Weight": 0.08,
            "1W": 0.01,
            "1M": -0.01,
            "3M": 0.12,
            "Momentum_Acceleration": -0.01,
            "Composite": 0.10,
            "Rotation_Signal": "Neutral",
        }])
        self.assertEqual(_decision_action(frame).iloc[0], "Hold")

    def test_non_position_waits_when_signal_is_not_ready_for_new_capital(self) -> None:
        frame = pd.DataFrame([{
            "Decision_Score": 62.0,
            "Portfolio_Weight": 0.0,
            "1W": 0.01,
            "1M": -0.01,
            "3M": 0.12,
            "Momentum_Acceleration": -0.01,
            "Composite": 0.10,
            "Rotation_Signal": "Neutral",
        }])
        self.assertEqual(_decision_action(frame).iloc[0], "Afvent")

    def test_non_position_never_gets_hold(self) -> None:
        frame = pd.DataFrame([{
            "Decision_Score": 65.0,
            "Portfolio_Weight": 0.0,
            "1W": 0.02,
            "1M": 0.03,
            "3M": 0.10,
            "Momentum_Acceleration": -0.01,
            "Composite": 0.12,
            "Rotation_Signal": "Neutral",
        }])
        self.assertEqual(_decision_action(frame).iloc[0], "Afvent")

    def test_existing_position_can_still_reduce(self) -> None:
        frame = pd.DataFrame([{
            "Decision_Score": 35.0,
            "Portfolio_Weight": 0.05,
            "1W": -0.03,
            "1M": -0.05,
            "3M": -0.08,
            "Momentum_Acceleration": -0.02,
            "Composite": -0.10,
            "Rotation_Signal": "Aftager",
        }])
        self.assertEqual(_decision_action(frame).iloc[0], "Reducer")


if __name__ == "__main__":
    unittest.main()
