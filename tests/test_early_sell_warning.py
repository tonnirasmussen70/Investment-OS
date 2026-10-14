import unittest

import pandas as pd

from modules.early_sell_warning import build_early_sell_warnings


class EarlySellWarningTests(unittest.TestCase):
    def setUp(self):
        self.current = pd.DataFrame([
            {"Name": "Warning", "Yahoo_Ticker": "WARN", "Asset_Type": "Stock",
             "Portfolio_Weight": 0.08, "Handling": "Hold", "1W": -0.03, "1M": -0.07, "Decision_Score": 52},
            {"Name": "Already reduce", "Yahoo_Ticker": "RED", "Asset_Type": "ETF",
             "Portfolio_Weight": 0.08, "Handling": "Reducer", "1W": -0.03, "1M": -0.07, "Decision_Score": 35},
            {"Name": "No position", "Yahoo_Ticker": "NONE", "Asset_Type": "Stock",
             "Portfolio_Weight": 0, "Handling": "Afvent", "1W": -0.03, "1M": -0.07, "Decision_Score": 52},
            {"Name": "Momentum recovering", "Yahoo_Ticker": "UP", "Asset_Type": "Stock",
             "Portfolio_Weight": 0.05, "Handling": "Hold", "1W": 0.02, "1M": -0.02, "Decision_Score": 55},
            {"Name": "Score improving", "Yahoo_Ticker": "BETTER", "Asset_Type": "ETF",
             "Portfolio_Weight": 0.05, "Handling": "Hold", "1W": -0.02, "1M": -0.03, "Decision_Score": 55},
        ])
        self.previous = pd.DataFrame({
            "Yahoo_Ticker": ["WARN", "RED", "NONE", "UP", "BETTER"],
            "Decision_Score": [56, 40, 58, 61, 50],
        })

    def test_only_held_deteriorating_position_warns(self):
        result = build_early_sell_warnings(self.current, self.previous)
        self.assertEqual(result["Yahoo_Ticker"].tolist(), ["WARN"])
        self.assertAlmostEqual(result.iloc[0]["Score_Change"], -4)

    def test_missing_prior_day_does_not_create_warning(self):
        result = build_early_sell_warnings(self.current, pd.DataFrame())
        self.assertTrue(result.empty)

    def test_missing_score_does_not_create_warning(self):
        previous = self.previous.copy()
        previous.loc[previous["Yahoo_Ticker"] == "WARN", "Decision_Score"] = float("nan")
        self.assertTrue(build_early_sell_warnings(self.current, previous).empty)

    def test_input_is_not_mutated(self):
        before = self.current.copy(deep=True)
        build_early_sell_warnings(self.current, self.previous)
        pd.testing.assert_frame_equal(self.current, before)


if __name__ == "__main__":
    unittest.main()
