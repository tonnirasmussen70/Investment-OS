from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from modules.market_engine import fetch_market_snapshot, fetch_price_history


class MarketClosingPriceTests(unittest.TestCase):
    @staticmethod
    def yahoo_frame() -> pd.DataFrame:
        index = pd.to_datetime(["2026-09-03", "2026-09-04"])
        columns = pd.MultiIndex.from_product(
            [["Close"], ["ABB.ST", "ALSYDB.CO"]],
            names=["Price", "Ticker"],
        )
        return pd.DataFrame(
            [[912.0, 682.5], [916.0, 687.5]],
            index=index,
            columns=columns,
        )

    @patch("modules.market_engine.yf.download")
    def test_snapshot_uses_latest_unadjusted_yahoo_close(self, download) -> None:
        download.return_value = self.yahoo_frame()

        snapshot = fetch_market_snapshot(
            ["ABB.ST", "ALSYDB.CO"],
            ["DKK"],
        )

        self.assertEqual(snapshot.prices["ABB.ST"], 916.0)
        self.assertEqual(snapshot.prices["ALSYDB.CO"], 687.5)
        self.assertEqual(
            snapshot.price_dates["ABB.ST"],
            pd.Timestamp("2026-09-04"),
        )
        self.assertFalse(download.call_args.kwargs["auto_adjust"])
        self.assertEqual(download.call_args.kwargs["interval"], "1d")

    @patch("modules.market_engine.yf.download")
    def test_momentum_history_remains_adjusted(self, download) -> None:
        download.return_value = self.yahoo_frame()

        history = fetch_price_history(["ABB.ST", "ALSYDB.CO"], period="18mo")

        self.assertEqual(history.loc[pd.Timestamp("2026-09-04"), "ABB.ST"], 916.0)
        self.assertTrue(download.call_args.kwargs["auto_adjust"])

    @patch("modules.market_engine._latest_regular_market_quote")
    @patch("modules.market_engine.yf.download")
    def test_etf_quote_fills_newer_day_when_daily_close_is_empty(
        self,
        download,
        latest_quote,
    ) -> None:
        index = pd.to_datetime(["2026-09-03", "2026-09-04"])
        columns = pd.MultiIndex.from_product(
            [["Close"], ["4COP.DE", "94VE.DE"]],
            names=["Price", "Ticker"],
        )
        download.return_value = pd.DataFrame(
            [[61.68, 44.01], [float("nan"), float("nan")]],
            index=index,
            columns=columns,
        )
        quotes = {
            "4COP.DE": (61.40, pd.Timestamp("2026-09-04 15:36", tz="UTC")),
            "94VE.DE": (44.31, pd.Timestamp("2026-09-04 15:36", tz="UTC")),
        }
        latest_quote.side_effect = quotes.get

        snapshot = fetch_market_snapshot(
            ["4COP.DE", "94VE.DE"],
            ["DKK"],
        )

        self.assertEqual(snapshot.prices["4COP.DE"], 61.40)
        self.assertEqual(snapshot.prices["94VE.DE"], 44.31)
        self.assertEqual(snapshot.price_dates["4COP.DE"].date(), index[-1].date())


if __name__ == "__main__":
    unittest.main()
