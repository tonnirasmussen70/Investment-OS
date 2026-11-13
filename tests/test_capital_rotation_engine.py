from __future__ import annotations

import unittest

import pandas as pd

from modules.capital_rotation_engine import (
    build_rotation_scenario,
    review_rotation_sources,
)


class CapitalRotationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame([
            {
                "Aktiv": "NKT", "Nuværende vægt": 0.073, "Modelmålvægt": 0.073,
                "Decision Score": 46, "Handling": "Hold", "Rebalance handling": "Ingen handel",
                "Handel DKK": 0, "Asset_Type": "Stock", "Account": "Aktier ASK",
                "Sector": "Industrials", "AI": 40,
            },
            {
                "Aktiv": "Sydbank", "Nuværende vægt": 0.072, "Modelmålvægt": 0.108,
                "Decision Score": 96, "Handling": "Øg", "Rebalance handling": "Køb",
                "Handel DKK": 36_000, "Asset_Type": "Stock", "Account": "Aktier ASK",
                "Sector": "Financials", "AI": 95,
            },
            {
                "Aktiv": "Danske Bank", "Nuværende vægt": 0.046, "Modelmålvægt": 0.076,
                "Decision Score": 89, "Handling": "Øg", "Rebalance handling": "Køb",
                "Handel DKK": 30_000, "Asset_Type": "Stock", "Account": "Aktier ASK",
                "Sector": "Financials", "AI": 90,
            },
        ])

    def scenario(self, frame=None, **kwargs):
        return build_rotation_scenario(
            self.frame if frame is None else frame,
            source_asset="NKT",
            buy_assets=["Sydbank", "Danske Bank"],
            active_market_value_dkk=1_000_000,
            **kwargs,
        )

    def test_low_score_hold_is_a_manual_review_candidate(self) -> None:
        candidates = review_rotation_sources(self.frame)
        self.assertEqual(candidates["Aktiv"].tolist(), ["NKT"])
        self.assertEqual(candidates.iloc[0]["Handling"], "Hold")

    def test_cash_neutral_two_buy_rotation(self) -> None:
        scenario = self.scenario()
        self.assertEqual(len(scenario.trades), 3)
        self.assertAlmostEqual(scenario.sell_dkk, 20_000)
        self.assertAlmostEqual(scenario.buy_dkk, 20_000)
        self.assertAlmostEqual(scenario.trades["Handel DKK"].sum(), 0)
        weights = scenario.trades.set_index("Aktiv")["Scenarievægt"]
        self.assertAlmostEqual(weights.loc["NKT"], 0.053)
        self.assertGreater(weights.loc["Sydbank"], 0.072)
        self.assertGreater(weights.loc["Danske Bank"], 0.046)
        self.assertLessEqual(weights.loc["Sydbank"] + weights.loc["Danske Bank"], 0.20)

    def test_no_cross_account_rotation(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("Sydbank"), "Account"] = "ETF ASK"
        result = self.scenario(frame=frame)
        self.assertTrue(result.trades.empty)
        self.assertIn("konti", result.status)

    def test_no_cross_asset_class_rotation(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("Sydbank"), "Asset_Type"] = "ETF"
        self.assertTrue(self.scenario(frame=frame).trades.empty)

    def test_no_buy_when_sector_at_cap(self) -> None:
        scenario = self.scenario(maximum_sector_weight=0.119)
        self.assertTrue(scenario.trades.empty)
        self.assertEqual(scenario.sell_dkk, 0)

    def test_cap_before_model_target(self) -> None:
        result = self.scenario(maximum_position_weight=0.09)
        trades = result.trades.set_index("Aktiv")
        self.assertLessEqual(trades.loc["Sydbank", "Scenarievægt"], 0.09 + 1e-9)

    def test_unconfirmed_buy_never_funded(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("Danske Bank"), "AI"] = 35
        self.assertTrue(self.scenario(frame=frame).trades.empty)

    def test_minimum_position_weight_protected(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("NKT"), "Nuværende vægt"] = 0.03
        scenario = self.scenario(frame=frame)
        self.assertFalse(scenario.trades.empty)
        source = scenario.trades.set_index("Aktiv").loc["NKT"]
        self.assertGreaterEqual(source["Scenarievægt"], 0.02 - 1e-9)

    def test_no_source_without_valid_account(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("NKT"), "Account"] = ""
        self.assertTrue(self.scenario(frame=frame).trades.empty)

    def test_do_not_sell_existing_buy_candidate(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("NKT"), "Handling"] = "Øg"
        self.assertTrue(self.scenario(frame=frame).trades.empty)

    def test_small_sale_funds_one_eligible_trade_instead_of_tiny_orders(self) -> None:
        result = self.scenario(sale_weight=0.005)
        self.assertAlmostEqual(result.sell_dkk, 5_000)
        buys = result.trades.loc[result.trades["Handel DKK"].gt(0)]
        self.assertEqual(len(buys), 1)
        self.assertAlmostEqual(float(buys.iloc[0]["Handel DKK"]), 5_000)

    def test_missing_sector_blocks_trade(self) -> None:
        frame = self.frame.copy()
        frame.loc[frame["Aktiv"].eq("Sydbank"), "Sector"] = ""
        self.assertTrue(self.scenario(frame=frame).trades.empty)


if __name__ == "__main__":
    unittest.main()
