from __future__ import annotations

import unittest

import pandas as pd

from modules.rebalance_engine import build_rebalance_plan


class RebalanceExecutionTests(unittest.TestCase):
    def _base_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "Name": "HighConviction",
                    "Portfolio_Weight": 0.08,
                    "Composite": 0.20,
                    "AI_Confidence": 90,
                    "Decision_Score": 94,
                    "Decision_Status": "Meget stærk",
                    "Handling": "Øg",
                    "Sector": "Technology",
                    "Asset_Type": "Stock",
                },
                {
                    "Name": "OverweightHold",
                    "Portfolio_Weight": 0.15,
                    "Composite": 0.08,
                    "AI_Confidence": 75,
                    "Decision_Score": 72,
                    "Decision_Status": "Stærk",
                    "Handling": "Hold",
                    "Sector": "Industrials",
                    "Asset_Type": "Stock",
                },
                {
                    "Name": "Weak",
                    "Portfolio_Weight": 0.06,
                    "Composite": -0.12,
                    "AI_Confidence": 35,
                    "Decision_Score": 20,
                    "Decision_Status": "Lav conviction",
                    "Handling": "Reducer",
                    "Sector": "Materials",
                    "Asset_Type": "Stock",
                },
            ]
        )

    def test_dynamic_target_is_stronger_for_high_conviction(self) -> None:
        result = build_rebalance_plan(
            self._base_frame(),
            active_market_value_dkk=1_000_000,
            max_position_weight=0.12,
            max_sector_weight=0.20,
            minimum_trade_dkk=5_000,
        ).data.set_index("Aktiv")

        self.assertGreater(
            result.loc["HighConviction", "Modelmålvægt"],
            result.loc["HighConviction", "Nuværende vægt"],
        )
        self.assertLess(
            result.loc["Weak", "Modelmålvægt"],
            result.loc["Weak", "Nuværende vægt"],
        )

    def test_position_cap_overrides_hold(self) -> None:
        result = build_rebalance_plan(
            self._base_frame(),
            active_market_value_dkk=1_000_000,
            max_position_weight=0.12,
            max_sector_weight=0.20,
            minimum_trade_dkk=5_000,
        ).data.set_index("Aktiv")

        self.assertAlmostEqual(result.loc["OverweightHold", "Modelmålvægt"], 0.12)
        self.assertEqual(result.loc["OverweightHold", "Rebalance handling"], "Sælg")
        self.assertIn("Positionsloft", result.loc["OverweightHold", "Constraint"])

    def test_sector_cap_limits_buy_target(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "Name": "TechLeader",
                    "Portfolio_Weight": 0.10,
                    "Composite": 0.20,
                    "AI_Confidence": 90,
                    "Decision_Score": 95,
                    "Decision_Status": "Meget stærk",
                    "Handling": "Øg",
                    "Sector": "Technology",
                    "Asset_Type": "Stock",
                },
                {
                    "Name": "TechHold",
                    "Portfolio_Weight": 0.09,
                    "Composite": 0.10,
                    "AI_Confidence": 70,
                    "Decision_Score": 68,
                    "Decision_Status": "Interessant",
                    "Handling": "Hold",
                    "Sector": "Technology",
                    "Asset_Type": "Stock",
                },
            ]
        )
        result = build_rebalance_plan(
            frame,
            active_market_value_dkk=1_000_000,
            max_position_weight=0.12,
            max_sector_weight=0.20,
            minimum_trade_dkk=1_000,
        ).data

        self.assertLessEqual(result["Modelmålvægt"].sum(), 0.20 + 1e-9)
        leader = result.set_index("Aktiv").loc["TechLeader"]
        self.assertIn("Sektorloft", leader["Constraint"])

    def test_minimum_trade_keeps_execution_weight_unchanged(self) -> None:
        frame = self._base_frame().iloc[[0]].copy()
        result = build_rebalance_plan(
            frame,
            active_market_value_dkk=100_000,
            max_position_weight=0.12,
            max_sector_weight=0.20,
            minimum_trade_dkk=5_000,
        ).data.iloc[0]

        self.assertGreater(result["Modelmålvægt"], result["Nuværende vægt"])
        self.assertEqual(result["Handel DKK"], 0.0)
        self.assertAlmostEqual(result["Foreslået vægt"], result["Nuværende vægt"])
        self.assertTrue(result["Under minimumshandel"])

    def test_execution_summary_balances_buy_sell_and_cash_need(self) -> None:
        result = build_rebalance_plan(
            self._base_frame(),
            active_market_value_dkk=1_000_000,
            max_position_weight=0.12,
            max_sector_weight=0.20,
            minimum_trade_dkk=5_000,
        )

        self.assertAlmostEqual(result.gross_trade_dkk, result.buy_dkk + result.sell_dkk)
        self.assertAlmostEqual(result.net_trade_dkk, result.buy_dkk - result.sell_dkk)
        self.assertAlmostEqual(result.cash_required_dkk, max(result.net_trade_dkk, 0.0))
        self.assertEqual(result.trade_count, int(result.data["Handel DKK"].ne(0).sum()))


if __name__ == "__main__":
    unittest.main()
