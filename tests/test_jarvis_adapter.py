from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jarvis.adapter import (
    JarvisCommandError,
    classify_intent,
    execute_command,
    format_investment_brief,
    format_portfolio_signals,
    format_stock_status,
)
from tests.test_jarvis_api import fixture_snapshot
from research.provider import ResearchUnavailableError


def fixture_research() -> dict:
    return {
        "research_type": "fundamental_snapshot",
        "ticker": "CLS",
        "status": "available",
        "as_of": "2026-09-13T12:00:00+00:00",
        "source": {"provider": "Yahoo Finance", "adapter": "yfinance"},
        "market": {
            "currency": "USD",
            "current_price": 301.25,
            "market_cap": 35_000_000_000,
        },
        "valuation": {"forward_pe": 24.5, "enterprise_to_ebitda": 21.0},
        "growth": {"revenue_growth": 0.22},
        "profitability": {"operating_margin": 0.09},
        "data_quality": {"status": "good", "coverage": 0.82},
        "warnings": [],
    }


class JarvisAdapterTests(unittest.TestCase):
    def test_only_approved_intents_are_classified(self) -> None:
        self.assertEqual(classify_intent("Giv mig min investeringsbrief"), "investment_brief")
        self.assertEqual(classify_intent("Hvordan ser porteføljen ud?"), "investment_brief")
        self.assertEqual(classify_intent("Hvad er status på Investment OS?"), "system_status")
        self.assertEqual(classify_intent("Vis mine investeringssignaler"), "portfolio_signals")
        self.assertEqual(classify_intent("Hvilke signaler kræver handling?"), "portfolio_signals")
        self.assertEqual(classify_intent("Analyser CLS"), "stock_analysis")
        with self.assertRaises(JarvisCommandError):
            classify_intent("Køb CLS nu")

    def test_brief_formatter_uses_structured_values(self) -> None:
        brief = {
            "run_id": "run-1",
            "as_of": "2026-09-13T12:00:00+00:00",
            "kpis": {
                "portfolio_health": 65.3,
                "confidence": 53.6,
                "confidence_label": "Moderat",
                "data_quality": 100.0,
                "macro_rate_risk": 76.8,
                "macro_rate_level": "Meget høj",
            },
            "changes": {"available": False},
            "decisions": {"count": 1, "items": [{"Aktiv": "CLS", "Handling": "Hold"}]},
            "opportunities": {"count": 1, "items": [{"Name": "Example"}]},
        }
        text = format_investment_brief(brief)
        self.assertIn("Porteføljesundhed 65,3/100", text)
        self.assertIn("CLS: Hold", text)
        self.assertIn("ændrer ikke køb/salg-logikken", text)

    def test_execute_brief_preserves_snapshot(self) -> None:
        snapshot = fixture_snapshot()
        before = json.dumps(snapshot, sort_keys=True)
        with patch("api.service._current_commit", return_value="abc123"):
            result = execute_command(
                "Jarvis, giv mig min investeringsbrief",
                snapshot,
                request_id="request-1",
            )
        self.assertEqual(result["intent"], "investment_brief")
        self.assertEqual(result["request_id"], "request-1")
        self.assertEqual(result["data"]["decisions"]["items"], snapshot["decision_queue"])
        self.assertEqual(json.dumps(snapshot, sort_keys=True), before)

    def test_stock_analysis_uses_watchlist_data(self) -> None:
        result = execute_command(
            "Jarvis, analyser aktien CLS",
            fixture_snapshot(),
            request_id="request-2",
            research_loader=lambda ticker: fixture_research(),
        )
        self.assertEqual(result["intent"], "stock_analysis")
        self.assertEqual(result["data"]["identity"]["ticker"], "CLS")
        self.assertIn("Watchlist-status Watch", result["message"])
        self.assertIn("ingen beregnede momentum", result["message"])
        self.assertIn("Ekstern research (Yahoo Finance via yfinance", result["message"])
        self.assertIn("ændrer ikke Investment OS' Decision Score", result["message"])
        self.assertEqual(result["data"]["research"]["ticker"], "CLS")

    def test_execute_signal_command_preserves_canonical_queue(self) -> None:
        snapshot = fixture_snapshot()
        with patch("api.service._current_commit", return_value="abc123"):
            result = execute_command(
                "Jarvis, vis mine investeringssignaler",
                snapshot,
                request_id="signals-command",
            )

        self.assertEqual(result["intent"], "portfolio_signals")
        self.assertEqual(result["data"]["decision_queue"], snapshot["decision_queue"])
        self.assertIn("1 autoritative positionssignaler", result["message"])
        self.assertIn("API'et beregner eller ændrer ingen signaler", result["message"])

    def test_signal_formatter_blocks_action_when_readiness_is_insufficient(self) -> None:
        text = format_portfolio_signals(
            {
                "summary": {"signal_count": 1, "handling_counts": {"Øg": 1}},
                "decision_readiness": {
                    "status": "insufficient",
                    "blocking_warning_codes": ["SNAPSHOT_STALE"],
                },
                "decision_queue": [],
                "run_id": "run-1",
            }
        )
        self.assertIn("bør ikke bruges til handling", text)
        self.assertIn("SNAPSHOT_STALE", text)

    def test_stock_formatter_discloses_scope(self) -> None:
        data = {
            "identity": {"name": "Frontline PLC", "ticker": "FRO"},
            "signals": {
                "decision_score": 84.0,
                "decision_status": "Meget stærk",
                "handling": "Øg",
                "ai_confidence": 88.0,
                "returns": {"1W": 0.02, "1M": 0.05},
            },
            "portfolio_context": {"is_position": True, "portfolio_weight": 0.06},
            "run_id": "run-1",
        }
        text = format_stock_status(data)
        self.assertIn("Decision Score 84,0/100", text)
        self.assertIn("Porteføljevægt 6,0%", text)
        self.assertIn("ikke ny fundamental research", text)

    def test_research_failure_preserves_os_stock_analysis(self) -> None:
        def unavailable(_: str) -> dict:
            raise ResearchUnavailableError("Researchdata kunne ikke hentes for CLS.")

        result = execute_command(
            "Analyser CLS",
            fixture_snapshot(),
            request_id="request-3",
            research_loader=unavailable,
        )

        self.assertEqual(result["data"]["identity"]["ticker"], "CLS")
        self.assertEqual(result["data"]["research"]["status"], "unavailable")
        self.assertIn("Ekstern fundamental research er ikke tilgængelig", result["message"])
        self.assertIn("Investment OS-dataene ovenfor er uændrede", result["message"])

    def test_schema_transition_is_not_reported_as_signal_changes(self) -> None:
        brief = {
            "run_id": "run-1",
            "as_of": "2026-09-13T12:00:00+00:00",
            "kpis": {},
            "changes": {
                "available": True,
                "decision_changes": {
                    "count": 28,
                    "items": [
                        {
                            "asset": "Alpha",
                            "changes": {
                                "Decision_Status": {"from": None, "to": "Stærk"}
                            },
                        }
                    ],
                },
            },
            "decisions": {"count": 0, "items": []},
            "opportunities": {"count": 0, "items": []},
        }
        text = format_investment_brief(brief)
        self.assertIn("nye beslutningsfelter", text)
        self.assertNotIn("28 registrerede", text)


if __name__ == "__main__":
    unittest.main()
