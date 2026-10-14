from __future__ import annotations

import unittest
import numpy as np
import pandas as pd

from modules.macro_rate_engine import calculate_yield_curve_risk


class YieldCurveRiskTests(unittest.TestCase):
    def history(self, ten_start: float, ten_end: float, two_start: float, two_end: float):
        idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=40)
        return pd.DataFrame({
            "US10Y": np.linspace(ten_start, ten_end, len(idx)),
            "US2Y": np.linspace(two_start, two_end, len(idx)),
        }, index=idx)

    def test_high_requires_rising_ten_year_yield(self):
        result = calculate_yield_curve_risk(self.history(4, 4.8, 3.8, 3.8))
        self.assertEqual(result["level"], "Høj")
        self.assertGreater(result["change_bp"], 30)

    def test_steepening_from_falling_short_yield_is_not_high(self):
        result = calculate_yield_curve_risk(self.history(4.5, 4.4, 4.3, 3.7))
        self.assertEqual(result["level"], "Forhøjet")

    def test_low_change_is_normal(self):
        result = calculate_yield_curve_risk(self.history(4, 4.1, 3.8, 3.85))
        self.assertEqual(result["level"], "Normal")

    def test_missing_or_stale_series_are_not_scored(self):
        self.assertEqual(calculate_yield_curve_risk(pd.DataFrame({"US10Y": [4]}))["level"], "Datagrundlag utilstrækkeligt")
        stale = self.history(4, 4.8, 3.8, 3.8).copy()
        stale.index = stale.index - pd.Timedelta(days=60)
        self.assertEqual(calculate_yield_curve_risk(stale)["level"], "Datagrundlag utilstrækkeligt")


if __name__ == "__main__":
    unittest.main()
