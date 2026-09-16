from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tests.test_api_security import _request
from tests.test_jarvis_api import fixture_snapshot


class JarvisApiTelemetryTests(unittest.TestCase):
    @staticmethod
    def _write_snapshot(directory: str) -> Path:
        snapshot = fixture_snapshot()
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
        path = Path(directory) / "portfolio_snapshot.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        return path

    @staticmethod
    def _environment(snapshot_path: Path, audit_path: Path) -> dict[str, str]:
        return {
            "JARVIS_ENV": "development",
            "JARVIS_API_TOKEN": "",
            "JARVIS_RATE_LIMIT_PER_MINUTE": "",
            "INVESTMENT_OS_SNAPSHOT": str(snapshot_path),
            "JARVIS_AUDIT_LOG": str(audit_path),
        }

    def test_authenticated_status_request_is_audited_without_raw_request_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            with patch.dict(
                os.environ,
                self._environment(snapshot_path, audit_path),
            ), patch("api.service._current_commit", return_value="abc123"):
                status, _, headers = asyncio.run(
                    _request(
                        "/v1/system/status",
                        request_id="telemetry-completed",
                    )
                )

            audit_text = audit_path.read_text(encoding="utf-8")
            event = json.loads(audit_text)

        self.assertEqual(status, 200)
        self.assertEqual(headers["x-jarvis-audit-status"], "recorded")
        self.assertEqual(event["event_type"], "jarvis.request.completed")
        self.assertEqual(event["trace"]["request_id"], "telemetry-completed")
        self.assertEqual(event["request"]["endpoint_scope"], "system_status")
        self.assertFalse(event["request"]["path_recorded"])
        self.assertFalse(event["request"]["query_recorded"])
        self.assertFalse(event["request"]["credentials_recorded"])
        self.assertFalse(event["request"]["body_recorded"])
        self.assertNotIn("/v1/system/status", audit_text)

    def test_technical_response_is_recorded_as_failed_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_snapshot = Path(directory) / "missing-snapshot.json"
            audit_path = Path(directory) / "audit.jsonl"
            with patch.dict(
                os.environ,
                self._environment(missing_snapshot, audit_path),
            ):
                status, payload, headers = asyncio.run(
                    _request(
                        "/v1/portfolio/status",
                        request_id="telemetry-failed",
                    )
                )

            event = json.loads(audit_path.read_text(encoding="utf-8"))

        self.assertEqual(status, 503)
        self.assertEqual(payload["error"]["code"], "SNAPSHOT_UNAVAILABLE")
        self.assertEqual(headers["x-jarvis-audit-status"], "recorded")
        self.assertEqual(event["event_type"], "jarvis.request.failed")
        self.assertEqual(event["request"]["endpoint_scope"], "portfolio_status")
        self.assertEqual(event["result"]["http_status"], 503)
        self.assertEqual(event["result"]["error_code"], "HTTP_503")

    def test_command_endpoint_keeps_single_specialised_audit_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            with patch.dict(
                os.environ,
                self._environment(snapshot_path, audit_path),
            ), patch("api.service._current_commit", return_value="abc123"):
                status, payload, _ = asyncio.run(
                    _request(
                        "/v1/jarvis/command",
                        method="POST",
                        body=json.dumps(
                            {"command": "Giv mig min investeringsbrief"}
                        ).encode("utf-8"),
                        request_id="telemetry-command",
                    )
                )

            events = [
                json.loads(line)
                for line in audit_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(status, 200)
        self.assertEqual(payload["audit"]["status"], "recorded")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "jarvis.command.completed")


if __name__ == "__main__":
    unittest.main()
