from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from modules.snapshot_engine import build_snapshot_changes, write_portfolio_snapshot


def snapshot(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "generated_at": "2026-09-13T10:00:00+02:00",
        "portfolio": {"health_score": 70.0, "ai_confidence": 65.0},
        "data_quality": {"score": 95.0},
        "macro_rate_regime": {"score": 60.0},
        "positions": [
            {
                "Aktiv": "Alpha",
                "Yahoo_Ticker": "AAA",
                "Handling": "Hold",
                "Decision_Status": "Stærk",
                "Decision_Score": 75.0,
            },
            {
                "Aktiv": "Beta",
                "Yahoo_Ticker": "BBB",
                "Handling": "Reducer",
                "Decision_Status": "Svag",
                "Decision_Score": 40.0,
            },
        ],
        "opportunities": [
            {"Yahoo_Ticker": "AAA"},
            {"Yahoo_Ticker": "CCC"},
        ],
    }


class SnapshotChangesTests(unittest.TestCase):
    def test_first_snapshot_has_no_comparison_basis(self) -> None:
        result = build_snapshot_changes(None, snapshot("current"))
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "NO_PREVIOUS_SNAPSHOT")

    def test_kpi_and_decision_changes_are_observed_not_recalculated(self) -> None:
        previous = snapshot("previous")
        current = snapshot("current")
        current["generated_at"] = "2026-09-13T11:00:00+02:00"
        current["portfolio"]["health_score"] = 72.5
        current["portfolio"]["ai_confidence"] = 64.0
        current["positions"][0]["Handling"] = "Øg"
        current["positions"][0]["Decision_Score"] = 80.0

        result = build_snapshot_changes(previous, current)

        self.assertTrue(result["available"])
        self.assertEqual(result["previous_run_id"], "previous")
        self.assertEqual(result["kpi_deltas"]["portfolio_health"], 2.5)
        self.assertEqual(result["kpi_deltas"]["confidence"], -1.0)
        alpha = result["decision_changes"]["items"][0]
        self.assertEqual(alpha["changes"]["Handling"], {"from": "Hold", "to": "Øg"})
        self.assertEqual(alpha["changes"]["Decision_Score"]["delta"], 5.0)

    def test_opportunity_entry_exit_and_rank_changes(self) -> None:
        previous = snapshot("previous")
        current = snapshot("current")
        current["opportunities"] = [
            {"Yahoo_Ticker": "CCC"},
            {"Yahoo_Ticker": "DDD"},
        ]

        result = build_snapshot_changes(previous, current)["opportunity_changes"]

        self.assertEqual(result["entered"], [{"ticker": "DDD", "rank": 2}])
        self.assertEqual(result["exited"], [{"ticker": "AAA", "previous_rank": 1}])
        self.assertEqual(
            result["rank_changes"],
            [{"ticker": "CCC", "from": 2, "to": 1, "delta": 1}],
        )

    def test_writer_compares_with_the_file_it_replaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "snapshot.json"
            data_file = Path(directory) / "portfolio.xlsx"
            data_file.write_bytes(b"test")
            empty = pd.DataFrame()
            common = {
                "output_file": output,
                "data_file": data_file,
                "app_version": "test",
                "portfolio": empty,
                "analytics_portfolio": empty,
                "portfolio_metrics": {},
                "decision": {},
                "quality_score": 100.0,
                "quality_notes": [],
                "benchmark_ticker": "TEST",
                "max_position_weight": 0.12,
                "history": empty,
                "decision_queue": SimpleNamespace(data=empty),
                "opportunity_result": SimpleNamespace(data=empty),
                "rebalance_result": SimpleNamespace(data=empty),
                "stop_loss_metrics": {},
                "watchlist": empty,
            }
            write_portfolio_snapshot(
                portfolio_health=SimpleNamespace(score=70.0), **common
            )
            first = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(first["changes"]["available"])

            write_portfolio_snapshot(
                portfolio_health=SimpleNamespace(score=72.0), **common
            )
            second = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(second["changes"]["available"])
            self.assertEqual(second["changes"]["kpi_deltas"]["portfolio_health"], 2.0)


if __name__ == "__main__":
    unittest.main()
