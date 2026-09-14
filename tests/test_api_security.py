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
from api.security import RATE_LIMITER, load_security_settings
from tests.test_jarvis_api import fixture_snapshot


async def _request(
    path: str,
    *,
    method: str = "GET",
    body: bytes = b"",
    client_host: str = "127.0.0.1",
    request_id: str = "security-test",
    authorization: str | None = None,
) -> tuple[int, dict, dict[str, str]]:
    request_sent = False
    messages: list[dict] = []
    headers = [(b"x-request-id", request_id.encode("ascii"))]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode("utf-8")))

    async def receive() -> dict:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in start["headers"]
    }
    return int(start["status"]), json.loads(body), response_headers


class JarvisApiSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        RATE_LIMITER.clear()

    def _write_snapshot(self, directory: str) -> Path:
        snapshot = fixture_snapshot()
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
        path = Path(directory) / "portfolio_snapshot.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        return path

    @staticmethod
    def _environment(
        *,
        mode: str,
        token: str = "",
        rate_limit: str = "",
        snapshot_path: Path | None = None,
        audit_path: Path | None = None,
    ) -> dict[str, str]:
        result = {
            "JARVIS_ENV": mode,
            "JARVIS_API_TOKEN": token,
            "JARVIS_RATE_LIMIT_PER_MINUTE": rate_limit,
        }
        if snapshot_path is not None:
            result["INVESTMENT_OS_SNAPSHOT"] = str(snapshot_path)
        if audit_path is not None:
            result["JARVIS_AUDIT_LOG"] = str(audit_path)
        return result

    def test_development_without_token_is_localhost_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            environment = self._environment(
                mode="development",
                snapshot_path=snapshot_path,
                audit_path=audit_path,
            )
            with patch.dict(os.environ, environment), patch(
                "api.service._current_commit", return_value="abc123"
            ):
                local_status, _, local_headers = asyncio.run(
                    _request("/v1/system/status", client_host="127.0.0.1")
                )
                remote_status, remote_payload, _ = asyncio.run(
                    _request(
                        "/v1/system/status",
                        client_host="192.0.2.10",
                        request_id="remote-denied",
                    )
                )

            self.assertEqual(local_status, 200)
            self.assertEqual(local_headers["cache-control"], "no-store")
            self.assertEqual(local_headers["x-content-type-options"], "nosniff")
            self.assertEqual(remote_status, 403)
            self.assertEqual(remote_payload["error"]["code"], "REMOTE_ACCESS_DENIED")
            self.assertEqual(remote_payload["audit"]["status"], "recorded")

    def test_production_fails_closed_when_security_config_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            with patch.dict(
                os.environ,
                self._environment(mode="production", audit_path=audit_path),
            ):
                status, payload, _ = asyncio.run(
                    _request("/v1/system/status", client_host="192.0.2.10")
                )

            self.assertEqual(status, 503)
            self.assertEqual(payload["error"]["code"], "SECURITY_CONFIGURATION_INVALID")
            self.assertNotIn("JARVIS_API_TOKEN", json.dumps(payload))

    def test_bearer_token_is_required_and_never_logged(self) -> None:
        token = "test-" + "a" * 40
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            environment = self._environment(
                mode="production",
                token=token,
                rate_limit="10",
                snapshot_path=snapshot_path,
                audit_path=audit_path,
            )
            with patch.dict(os.environ, environment), patch(
                "api.service._current_commit", return_value="abc123"
            ):
                rejected_status, rejected_payload, rejected_headers = asyncio.run(
                    _request(
                        "/v1/system/status",
                        client_host="192.0.2.10",
                        authorization="Bearer wrong-token",
                    )
                )
                accepted_status, accepted_payload, accepted_headers = asyncio.run(
                    _request(
                        "/v1/system/status",
                        client_host="192.0.2.10",
                        authorization=f"Bearer {token}",
                    )
                )

            audit_text = audit_path.read_text(encoding="utf-8")
            self.assertEqual(rejected_status, 401)
            self.assertEqual(rejected_payload["error"]["code"], "AUTH_INVALID")
            self.assertEqual(rejected_headers["www-authenticate"], "Bearer")
            self.assertEqual(accepted_status, 200)
            self.assertEqual(accepted_payload["status"], "ok")
            self.assertEqual(accepted_headers["x-ratelimit-limit"], "10")
            self.assertNotIn(token, audit_text)
            self.assertNotIn("wrong-token", audit_text)

    def test_rejected_command_body_is_not_read_or_audited(self) -> None:
        token = "test-" + "b" * 40
        private_command = b'{"command":"PRIVATE_COMMAND_CONTENT"}'
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            environment = self._environment(
                mode="production",
                token=token,
                rate_limit="10",
                audit_path=audit_path,
            )
            with patch.dict(os.environ, environment):
                status, payload, _ = asyncio.run(
                    _request(
                        "/v1/jarvis/command",
                        method="POST",
                        body=private_command,
                        client_host="192.0.2.10",
                        authorization="Bearer wrong-token",
                    )
                )

            audit_text = audit_path.read_text(encoding="utf-8")
            self.assertEqual(status, 401)
            self.assertEqual(payload["error"]["code"], "AUTH_INVALID")
            self.assertNotIn("PRIVATE_COMMAND_CONTENT", audit_text)
            self.assertNotIn("wrong-token", audit_text)
            self.assertEqual(
                json.loads(audit_text)["request"]["endpoint_scope"],
                "jarvis_command",
            )

    def test_explicit_rate_limit_rejects_excess_requests(self) -> None:
        token = "test-" + "c" * 40
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            environment = self._environment(
                mode="production",
                token=token,
                rate_limit="2",
                snapshot_path=snapshot_path,
                audit_path=audit_path,
            )
            with patch.dict(os.environ, environment), patch(
                "api.service._current_commit", return_value="abc123"
            ):
                results = [
                    asyncio.run(
                        _request(
                            "/v1/system/status",
                            client_host="192.0.2.10",
                            request_id=f"rate-{index}",
                            authorization=f"Bearer {token}",
                        )
                    )
                    for index in range(3)
                ]

            self.assertEqual([item[0] for item in results], [200, 200, 429])
            self.assertEqual(results[2][1]["error"]["code"], "RATE_LIMIT_EXCEEDED")
            self.assertEqual(results[2][2]["x-ratelimit-remaining"], "0")
            self.assertGreaterEqual(int(results[2][2]["retry-after"]), 1)

    def test_health_probe_is_public_and_contains_no_private_metadata(self) -> None:
        with patch.dict(os.environ, self._environment(mode="production")):
            status, payload, headers = asyncio.run(
                _request("/healthz", client_host="192.0.2.10")
            )

        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertNotIn("version", json.dumps(payload).lower())
        self.assertNotIn("commit", json.dumps(payload).lower())

    def test_invalid_rate_limit_is_configuration_error(self) -> None:
        token = "test-" + "d" * 40
        with patch.dict(
            os.environ,
            self._environment(mode="production", token=token, rate_limit="unlimited"),
        ):
            settings = load_security_settings()

        self.assertFalse(settings.valid)
        self.assertIsNone(settings.rate_limit_per_minute)
        self.assertTrue(any("positive integer" in item for item in settings.errors))


if __name__ == "__main__":
    unittest.main()
