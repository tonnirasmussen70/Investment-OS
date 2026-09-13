from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from jarvis.adapter import (
    JarvisCommandError,
    classify_intent,
    execute_command,
    format_investment_brief,
    format_stock_status,
)
from tests.test_jarvis_api import fixture_snapshot


class JarvisAdapterTests(unittest.TestCase):
    def test_only_approved_intents_are_classified(self) -> None:
        self.assertEqual(classify_intent("Giv mig min investeringsbrief"), "investment_brief")
        self.assertEqual(classify_intent("Hvordan ser porteføljen ud?"), "investment_brief")
        self.assertEqual(classify_intent("Hvad er status på Investment OS?"), "system_status")
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
        )
        self.assertEqual(result["intent"], "stock_analysis")
        self.assertEqual(result["data"]["identity"]["ticker"], "CLS")
        self.assertIn("Watchlist-status Watch", result["message"])
        self.assertIn("ingen beregnede momentum", result["message"])

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
