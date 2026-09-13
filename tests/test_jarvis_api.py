from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from api.service import build_portfolio_status, build_system_status, load_snapshot
from api.app import _unavailable_payload
from starlette.requests import Request


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def fixture_snapshot() -> dict:
    return {
        "schema_version": "2.0",
        "run_id": "ios-test-run",
        "app_version": "7.3.3",
        "generated_at": "2026-09-13T13:30:00+02:00",
        "source": {"commit_sha": "abc123", "portfolio_file_sha256": "hash"},
        "portfolio": {
            "health_score": 81.25,
            "ai_confidence": 76.5,
            "ai_confidence_label": "Høj",
        },
        "data_quality": {"score": 96.0, "notes": ["Fallback used"]},
        "macro_rate_regime": {
            "score": 68.0,
            "level": "Høj",
            "primary_driver": "US10Y",
            "impact": "Modvind",
            "data_quality": 90.0,
            "as_of": "2026-09-12T00:00:00",
            "changes_buy_sell_logic": False,
        },
    }


class JarvisApiContractTests(unittest.TestCase):
    def test_system_status_contract_and_request_id(self) -> None:
        result = build_system_status(
            fixture_snapshot(),
            request_id="request-1",
            now=NOW,
            current_commit="abc123",
        )
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["request_id"], "request-1")
        self.assertEqual(result["run_id"], "ios-test-run")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data_freshness"]["status"], "fresh")
        self.assertEqual(result["warnings"], [])

    def test_portfolio_status_is_a_read_only_snapshot_projection(self) -> None:
        snapshot = fixture_snapshot()
        before = json.dumps(snapshot, sort_keys=True)
        result = build_portfolio_status(
            snapshot,
            request_id="request-2",
            now=NOW,
        )
        self.assertEqual(result["health"]["score"], snapshot["portfolio"]["health_score"])
        self.assertEqual(result["confidence"]["score"], snapshot["portfolio"]["ai_confidence"])
        self.assertEqual(result["data_quality"]["score"], snapshot["data_quality"]["score"])
        self.assertEqual(result["macro_rate_risk"]["score"], snapshot["macro_rate_regime"]["score"])
        self.assertFalse(result["macro_rate_risk"]["changes_buy_sell_logic"])
        self.assertEqual(json.dumps(snapshot, sort_keys=True), before)

    def test_stale_and_version_mismatch_are_machine_readable(self) -> None:
        snapshot = fixture_snapshot()
        snapshot["generated_at"] = "2026-09-12T00:00:00+00:00"
        snapshot["app_version"] = "7.0.0"
        result = build_system_status(
            snapshot,
            now=NOW,
            current_commit="different",
        )
        codes = {item["code"] for item in result["warnings"]}
        self.assertEqual(result["status"], "degraded")
        self.assertIn("SNAPSHOT_STALE", codes)
        self.assertIn("APP_VERSION_MISMATCH", codes)
        self.assertIn("COMMIT_MISMATCH", codes)

    def test_snapshot_loader_rejects_non_object_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_snapshot(path)

    def test_unavailable_response_keeps_required_metadata(self) -> None:
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/v1/system/status",
                "headers": [(b"x-request-id", b"request-error")],
            }
        )
        result = _unavailable_payload(request, RuntimeError("Portfolio snapshot is unavailable"))
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["request_id"], "request-error")
        self.assertEqual(result["run_id"], "unavailable")
        self.assertEqual(result["error"]["code"], "SNAPSHOT_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
