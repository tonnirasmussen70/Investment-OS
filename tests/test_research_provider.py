from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from research.provider import ResearchUnavailableError, YahooFinanceResearchProvider


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def rich_info() -> dict:
    return {
        "longName": "Celestica Inc.",
        "sector": "Technology",
        "industry": "Electronic Components",
        "country": "Canada",
        "currency": "USD",
        "currentPrice": 301.25,
        "marketCap": 35_000_000_000,
        "enterpriseValue": 36_000_000_000,
        "totalRevenue": 12_000_000_000,
        "trailingPE": 32.0,
        "forwardPE": 24.5,
        "priceToSalesTrailing12Months": 2.9,
        "enterpriseToEbitda": 21.0,
        "revenueGrowth": 0.22,
        "earningsGrowth": 0.31,
        "grossMargins": 0.18,
        "operatingMargins": 0.09,
        "profitMargins": 0.07,
        "returnOnEquity": 0.28,
        "totalCash": 900_000_000,
        "totalDebt": 1_200_000_000,
        "operatingCashflow": 850_000_000,
        "freeCashflow": 620_000_000,
        "targetMeanPrice": 330.0,
        "recommendationKey": "buy",
        "numberOfAnalystOpinions": 14,
        "mostRecentQuarter": 1_767_139_200,
    }


class FakeTicker:
    def __init__(self, info: object, calls: list[str], ticker: str) -> None:
        self._info = info
        self._calls = calls
        self._ticker = ticker

    def get_info(self) -> object:
        self._calls.append(self._ticker)
        if isinstance(self._info, Exception):
            raise self._info
        return self._info


class ResearchProviderTests(unittest.TestCase):
    def test_provider_maps_fields_and_discloses_source(self) -> None:
        calls: list[str] = []
        provider = YahooFinanceResearchProvider(
            ticker_factory=lambda ticker: FakeTicker(rich_info(), calls, ticker),
            now=lambda: NOW,
        )
        result = provider.get_stock_research("cls")

        self.assertEqual(result["ticker"], "CLS")
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["source"]["provider"], "Yahoo Finance")
        self.assertEqual(result["source"]["adapter"], "yfinance")
        self.assertEqual(result["market"]["current_price"], 301.25)
        self.assertEqual(result["growth"]["revenue_growth"], 0.22)
        self.assertEqual(result["reporting_period_end"], "2025-12-31")
        self.assertNotIn("decision_score", result)
        self.assertEqual(calls, ["CLS"])

    def test_provider_uses_ttl_cache_without_sharing_mutable_payloads(self) -> None:
        calls: list[str] = []
        clock = [NOW]
        provider = YahooFinanceResearchProvider(
            ttl_seconds=3600,
            ticker_factory=lambda ticker: FakeTicker(rich_info(), calls, ticker),
            now=lambda: clock[0],
        )

        first = provider.get_stock_research("CLS")
        first["market"]["current_price"] = -1
        clock[0] = NOW + timedelta(minutes=10)
        second = provider.get_stock_research("CLS")

        self.assertEqual(calls, ["CLS"])
        self.assertEqual(second["market"]["current_price"], 301.25)
        self.assertTrue(second["freshness"]["cache_hit"])
        self.assertEqual(second["freshness"]["age_seconds"], 600)

    def test_partial_data_is_explicitly_marked(self) -> None:
        provider = YahooFinanceResearchProvider(
            ticker_factory=lambda ticker: FakeTicker(
                {"shortName": "Example", "currentPrice": 10.0}, [], ticker
            ),
            now=lambda: NOW,
        )
        result = provider.get_stock_research("EX")

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["data_quality"]["status"], "partial")
        self.assertIn(
            "RESEARCH_PARTIAL",
            {item["code"] for item in result["warnings"]},
        )

    def test_expired_cache_is_used_when_refresh_fails(self) -> None:
        calls: list[str] = []
        clock = [NOW]
        responses: list[object] = [rich_info(), RuntimeError("rate limited")]

        def ticker_factory(ticker: str) -> FakeTicker:
            return FakeTicker(responses.pop(0), calls, ticker)

        provider = YahooFinanceResearchProvider(
            ttl_seconds=60,
            ticker_factory=ticker_factory,
            now=lambda: clock[0],
        )
        provider.get_stock_research("CLS")
        clock[0] = NOW + timedelta(minutes=10)
        result = provider.get_stock_research("CLS")

        self.assertEqual(calls, ["CLS", "CLS"])
        self.assertEqual(result["freshness"]["status"], "stale")
        self.assertEqual(result["market"]["current_price"], 301.25)
        self.assertIn(
            "RESEARCH_STALE_CACHE",
            {item["code"] for item in result["warnings"]},
        )

    def test_provider_failure_becomes_domain_error(self) -> None:
        provider = YahooFinanceResearchProvider(
            ticker_factory=lambda ticker: FakeTicker(RuntimeError("network"), [], ticker),
            now=lambda: NOW,
        )
        with self.assertRaises(ResearchUnavailableError):
            provider.get_stock_research("CLS")

    def test_invalid_ticker_is_rejected_before_provider_call(self) -> None:
        provider = YahooFinanceResearchProvider(
            ticker_factory=lambda ticker: self.fail("provider should not be called"),
            now=lambda: NOW,
        )
        with self.assertRaises(ResearchUnavailableError):
            provider.get_stock_research("../secret")


if __name__ == "__main__":
    unittest.main()
