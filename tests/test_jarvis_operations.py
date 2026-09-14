from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from api.app import app
from jarvis.audit import AUDIT_SCHEMA_VERSION
from jarvis.operations import build_operational_service_indicators


def _event(
    event_id: str,
    event_type: str,
    occurred_at: datetime,
    duration_ms: float,
    *,
    outcome: str,
    status_code: int,
) -> dict:
    event = {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(),
        "trace": {"request_id": event_id, "run_id": "run-1"},
        "authorization": {
            "approval_required": False,
            "approval_status": "not_required",
            "investment_execution_allowed": False,
        },
        "versions": {"jarvis": "0.1.0", "api_schema": "1.0"},
        "result": {
            "outcome": outcome,
            "http_status": status_code,
            "error_code": None,
            "duration_ms": duration_ms,
        },
    }
    if event_type.startswith("jarvis.command."):
        event["command"] = {
            "intent": "investment_brief",
            "content_recorded": False,
            "access_level": "A_READ",
        }
    else:
        event["request"] = {
            "method": "GET",
            "endpoint_scope": "investment_api",
            "path_recorded": False,
            "credentials_recorded": False,
        }
    return event


class JarvisOperationalServiceIndicatorTests(unittest.TestCase):
    def test_24_hour_indicators_and_audit_controls_are_explicit(self) -> None:
        now = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)
        events = [
            _event("event-1", "jarvis.command.completed", now - timedelta(hours=1), 10, outcome="completed", status_code=200),
            _event("event-1", "jarvis.command.rejected", now - timedelta(hours=2), 20, outcome="rejected", status_code=400),
            _event("event-3", "jarvis.access.rejected", now - timedelta(hours=3), 30, outcome="rejected", status_code=401),
            _event("event-4", "jarvis.command.failed", now - timedelta(hours=4), 40, outcome="failed", status_code=503),
        ]
        events[2]["request_body"] = "must-not-be-recorded"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            path.write_text(
                "\n".join(json.dumps(event) for event in events) + "\n{invalid-json}\n",
                encoding="utf-8",
            )
            result = build_operational_service_indicators(
                request_id="operations-test",
                now=now,
                path=path,
            )

        self.assertEqual(result["request_id"], "operations-test")
        self.assertEqual(result["window"]["hours"], 24)
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["indicators"]["availability"]["observed_pct"], 75.0)
        self.assertIsNone(result["indicators"]["availability"]["sla_target_pct"])
        self.assertEqual(result["indicators"]["availability"]["sla_status"], "unconfigured")
        self.assertEqual(result["indicators"]["latency_ms"]["p50"], 25.0)
        self.assertEqual(result["indicators"]["latency_ms"]["p95"], 38.5)
        self.assertEqual(
            result["indicators"]["events"],
            {
                "completed_commands": 1,
                "technical_failures": 1,
                "command_rejections": 1,
                "access_rejections": 1,
                "other": 0,
            },
        )
        self.assertEqual(result["audit_integrity"]["invalid_schema_records"], 1)
        self.assertEqual(result["audit_integrity"]["duplicate_event_ids"], 1)
        self.assertEqual(result["audit_integrity"]["privacy_violation_events"], 1)
        self.assertEqual(result["audit_integrity"]["privacy_target"], 0)
        self.assertFalse(result["audit_integrity"]["privacy_target_met"])
        self.assertTrue(
            any(route.path == "/v1/system/operations" for route in app.routes)
        )


if __name__ == "__main__":
    unittest.main()
