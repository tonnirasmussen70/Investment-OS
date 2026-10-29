from __future__ import annotations

import unittest

from modules.config_engine import (
    DEFAULT_MOMENTUM_WEIGHTS,
    load_investment_config,
    load_raw_momentum_weights,
)


class MomentumDefaultWeightsTests(unittest.TestCase):
    def test_approved_raw_default_weights(self) -> None:
        expected = {"1W": 0.40, "1M": 0.35, "3M": 0.15, "6M": 0.10, "12M": 0.05}
        self.assertEqual(DEFAULT_MOMENTUM_WEIGHTS, expected)
        self.assertEqual(load_raw_momentum_weights({}), expected)
        self.assertAlmostEqual(sum(expected.values()), 1.05)

    def test_defaults_normalize_to_100_percent(self) -> None:
        actual = load_investment_config({}).momentum_weights
        for period, value in DEFAULT_MOMENTUM_WEIGHTS.items():
            self.assertAlmostEqual(actual[period], value / 1.05)
        self.assertAlmostEqual(sum(actual.values()), 1.0)

    def test_excel_settings_override_defaults_without_losing_relative_weights(self) -> None:
        settings = {"Momentum_1W": 0.6, "Momentum_1M": 0.4}
        raw = load_raw_momentum_weights(settings)
        self.assertEqual(raw["1W"], 0.6)
        self.assertEqual(raw["1M"], 0.4)
        self.assertEqual(raw["3M"], 0.15)
        normalized = load_investment_config(settings).momentum_weights
        self.assertAlmostEqual(sum(normalized.values()), 1.0)
        self.assertAlmostEqual(normalized["1W"] / normalized["1M"], 1.5)

    def test_all_zero_inputs_fall_back_to_normalized_defaults(self) -> None:
        settings = {f"Momentum_{period}": 0 for period in DEFAULT_MOMENTUM_WEIGHTS}
        self.assertEqual(load_raw_momentum_weights(settings), DEFAULT_MOMENTUM_WEIGHTS)
        self.assertEqual(
            load_investment_config(settings).momentum_weights,
            load_investment_config({}).momentum_weights,
        )

    def test_negative_and_invalid_values_never_break_normalization(self) -> None:
        settings = {
            "Momentum_1W": -1,
            "Momentum_1M": float("inf"),
            "Momentum_3M": "not-a-number",
        }
        raw = load_raw_momentum_weights(settings)
        self.assertEqual(raw["1W"], 0)
        self.assertEqual(raw["1M"], DEFAULT_MOMENTUM_WEIGHTS["1M"])
        self.assertEqual(raw["3M"], DEFAULT_MOMENTUM_WEIGHTS["3M"])
        normalized = load_investment_config(settings).momentum_weights
        self.assertAlmostEqual(sum(normalized.values()), 1.0)


if __name__ == "__main__":
    unittest.main()
