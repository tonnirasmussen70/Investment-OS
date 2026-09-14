from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from api.app import app
from jarvis.audit import AuditLogError, append_audit_event, build_command_audit_event
from research import provider as research_provider
from tests.test_jarvis_adapter import fixture_research
from tests.test_jarvis_api import fixture_snapshot


async def _post_command(command: str, request_id: str) -> tuple[int, dict]:
    request_body = json.dumps({"command": command}).encode("utf-8")
    request_sent = False
    messages: list[dict] = []

    async def receive() -> dict:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": request_body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/jarvis/command",
        "raw_path": b"/v1/jarvis/command",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"content-type", b"application/json"),
            (b"x-request-id", request_id.encode("ascii")),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return int(start["status"]), json.loads(body)


class JarvisAuditTests(unittest.TestCase):
    def _write_snapshot(self, directory: str) -> Path:
        snapshot = fixture_snapshot()
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
        path = Path(directory) / "portfolio_snapshot.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        return path

    def test_event_is_allow_listed_and_excludes_private_content(self) -> None:
        payload = {
            "schema_version": "1.0",
            "request_id": "request-1",
            "run_id": "run-1",
            "intent": "investment_brief",
            "message": "PRIVATE_PORTFOLIO_TEXT",
            "data": {
                "positions": [{"ticker": "SECRET_POSITION"}],
                "data_freshness": {"status": "fresh", "as_of": "2026-09-14"},
                "kpis": {"data_quality": 98.0},
                "warnings": [{"code": "SOURCE_WARNING", "message": "private"}],
            },
        }
        event = build_command_audit_event(
            request_id="request-1",
            payload=payload,
            outcome="completed",
            http_status=200,
            duration_ms=12.3456,
            snapshot={
                "schema_version": "2.0",
                "app_version": "7.3.3",
                "source": {"commit_sha": "abc123"},
            },
        )
        rendered = json.dumps(event)
        self.assertNotIn("PRIVATE_PORTFOLIO_TEXT", rendered)
        self.assertNotIn("SECRET_POSITION", rendered)
        self.assertFalse(event["command"]["content_recorded"])
        self.assertEqual(event["observability"]["reason_codes"], ["SOURCE_WARNING"])
        self.assertEqual(event["result"]["duration_ms"], 12.346)

    def test_append_audit_event_uses_owner_only_file_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit" / "events.jsonl"
            append_audit_event({"event_id": "one"}, path)
            append_audit_event({"event_id": "two"}, path)

            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["event_id"] for record in records], ["one", "two"])
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejected_command_is_audited_without_command_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            with patch.dict(
                os.environ,
                {
                    "INVESTMENT_OS_SNAPSHOT": str(snapshot_path),
                    "JARVIS_AUDIT_LOG": str(audit_path),
                },
            ):
                status, payload = asyncio.run(
                    _post_command("Køb SECRET_TOKEN_123 nu", "rejected-1")
                )

            event_text = audit_path.read_text(encoding="utf-8")
            event = json.loads(event_text)
            self.assertEqual(status, 400)
            self.assertEqual(payload["error"]["code"], "COMMAND_UNSUPPORTED")
            self.assertEqual(payload["audit"]["status"], "recorded")
            self.assertNotIn("SECRET_TOKEN_123", event_text)
            self.assertEqual(event["event_type"], "jarvis.command.rejected")
            self.assertEqual(event["result"]["error_code"], "COMMAND_UNSUPPORTED")

    def test_audit_failure_is_visible_without_changing_read_only_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            with patch.dict(
                os.environ,
                {"INVESTMENT_OS_SNAPSHOT": str(snapshot_path)},
            ), patch("api.service._current_commit", return_value="abc123"), patch(
                "api.app.append_audit_event",
                side_effect=AuditLogError("unavailable"),
            ):
                status, payload = asyncio.run(
                    _post_command("Giv mig min investeringsbrief", "audit-failure")
                )

            self.assertEqual(status, 200)
            self.assertEqual(payload["intent"], "investment_brief")
            self.assertEqual(payload["audit"]["status"], "unavailable")
            self.assertIn(
                "AUDIT_LOG_UNAVAILABLE",
                {item["code"] for item in payload["warnings"]},
            )

    def test_three_mvp_commands_pass_end_to_end_and_create_linked_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            commands = [
                ("Giv mig min investeringsbrief", "mvp-brief", "investment_brief"),
                ("Hvad er status på Investment OS?", "mvp-system", "system_status"),
                ("Analyser CLS", "mvp-stock", "stock_analysis"),
            ]
            responses: list[dict] = []
            with patch.dict(
                os.environ,
                {
                    "INVESTMENT_OS_SNAPSHOT": str(snapshot_path),
                    "JARVIS_AUDIT_LOG": str(audit_path),
                },
            ), patch("api.service._current_commit", return_value="abc123"), patch.object(
                research_provider._DEFAULT_PROVIDER,
                "get_stock_research",
                return_value=fixture_research(),
            ):
                for command, request_id, expected_intent in commands:
                    status, payload = asyncio.run(_post_command(command, request_id))
                    self.assertEqual(status, 200)
                    self.assertEqual(payload["intent"], expected_intent)
                    self.assertEqual(payload["request_id"], request_id)
                    self.assertEqual(payload["run_id"], "ios-test-run")
                    self.assertEqual(payload["audit"]["status"], "recorded")
                    responses.append(payload)

            self.assertEqual(
                responses[0]["data"]["decisions"]["items"],
                fixture_snapshot()["decision_queue"],
            )
            self.assertEqual(responses[2]["data"]["identity"]["ticker"], "CLS")
            self.assertIsNone(responses[2]["data"]["signals"]["decision_score"])

            events = [
                json.loads(line)
                for line in audit_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(events), 3)
            self.assertEqual(
                [event["command"]["intent"] for event in events],
                [item[2] for item in commands],
            )
            self.assertEqual(
                [event["trace"]["request_id"] for event in events],
                [item[1] for item in commands],
            )
            self.assertTrue(
                all(
                    event["authorization"]["investment_execution_allowed"] is False
                    for event in events
                )
            )


if __name__ == "__main__":
    unittest.main()
