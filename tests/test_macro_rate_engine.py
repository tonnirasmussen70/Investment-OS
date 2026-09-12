from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from modules.decision_engine import apply_decision_engine, decision_summary
from modules.macro_rate_engine import calculate_macro_rate_regime


class MacroRateEngineTests(unittest.TestCase):
    def _history(self, *, high_risk: bool) -> pd.DataFrame:
        index = pd.bdate_range("2026-01-02", periods=130)
        if high_risk:
            return pd.DataFrame(
                {
                    "US10Y": np.linspace(4.35, 5.35, len(index)),
                    "US2Y": np.linspace(4.75, 5.65, len(index)),
                    "Inflation_10Y": np.linspace(2.35, 2.90, len(index)),
                    "HY_Spread": np.linspace(3.40, 5.80, len(index)),
                },
                index=index,
            )
        return pd.DataFrame(
            {
                "US10Y": np.linspace(4.00, 3.55, len(index)),
                "US2Y": np.linspace(3.50, 2.95, len(index)),
                "Inflation_10Y": np.linspace(2.15, 1.95, len(index)),
                "HY_Spread": np.linspace(3.20, 2.75, len(index)),
            },
            index=index,
        )

    def _portfolio(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Name": "Testaktiv",
                    "Composite": 0.15,
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
                }
            ]
        )

    def test_high_and_low_regimes_are_distinct(self) -> None:
        high = calculate_macro_rate_regime(self._history(high_risk=True))
        low = calculate_macro_rate_regime(self._history(high_risk=False))

        self.assertGreater(high.score, 75)
        self.assertEqual(high.level, "Meget høj")
        self.assertLess(low.score, 40)
        self.assertIn(low.level, {"Lav", "Moderat"})
        self.assertEqual(high.data_quality, 100.0)

    def test_missing_components_are_disclosed_and_reweighted(self) -> None:
        history = self._history(high_risk=True)[["US10Y"]]
        regime = calculate_macro_rate_regime(history)

        self.assertTrue(pd.notna(regime.score))
        self.assertEqual(regime.data_quality, 45.0)
        self.assertTrue(pd.isna(regime.components["2Y–10Y rentekurve"]))

    def test_overlay_does_not_change_buy_sell_outputs(self) -> None:
        portfolio = self._portfolio()
        regime = calculate_macro_rate_regime(self._history(high_risk=True))

        baseline = apply_decision_engine(portfolio).data
        with_overlay = apply_decision_engine(
            portfolio,
            macro_rate_regime=regime,
        ).data

        pd.testing.assert_frame_equal(
            baseline[["Decision_Score", "Decision_Status", "Handling"]],
            with_overlay[["Decision_Score", "Decision_Status", "Handling"]],
        )
        self.assertEqual(
            float(with_overlay.loc[0, "Macro_Rate_Risk_Score"]),
            regime.score,
        )
        self.assertEqual(
            with_overlay.loc[0, "Macro_Rate_Risk_Level"],
            "Meget høj",
        )
        summary = decision_summary(with_overlay)
        self.assertEqual(summary["Macro_Rate_Risk_Level"], "Meget høj")
        self.assertEqual(
            float(summary["Macro_Rate_Risk_Score"]),
            regime.score,
        )


if __name__ == "__main__":
    unittest.main()
