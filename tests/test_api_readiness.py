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


class JarvisApiReadinessTests(unittest.TestCase):
    @staticmethod
    def _write_snapshot(directory: str) -> Path:
        snapshot = fixture_snapshot()
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
        path = Path(directory) / "portfolio_snapshot.json"
        path.write_text(json.dumps(snapshot), encoding="utf-8")
        return path

    @staticmethod
    def _production_environment(
        *,
        snapshot_path: Path,
        audit_path: Path,
        token: str = "test-" + "r" * 40,
        persistent: str = "true",
    ) -> dict[str, str]:
        return {
            "JARVIS_ENV": "production",
            "JARVIS_API_TOKEN": token,
            "JARVIS_RATE_LIMIT_PER_MINUTE": "60",
            "JARVIS_AUDIT_LOG": str(audit_path),
            "JARVIS_AUDIT_PERSISTENT": persistent,
            "INVESTMENT_OS_SNAPSHOT": str(snapshot_path),
        }

    def test_readyz_is_public_and_data_minimised_when_production_is_ready(self) -> None:
        token = "test-" + "s" * 40
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit" / "jarvis.jsonl"
            audit_path.parent.mkdir()
            environment = self._production_environment(
                snapshot_path=snapshot_path,
                audit_path=audit_path,
                token=token,
            )
            with patch.dict(os.environ, environment):
                status, payload, headers = asyncio.run(
                    _request("/readyz", client_host="192.0.2.10")
                )

        rendered = json.dumps(payload)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(
            payload["checks"],
            {
                "security_configuration": "ok",
                "snapshot": "ok",
                "audit_sink": "ok",
            },
        )
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertNotIn(token, rendered)
        self.assertNotIn(str(snapshot_path), rendered)
        self.assertNotIn(str(audit_path), rendered)
        self.assertNotIn("version", rendered.lower())
        self.assertNotIn("commit", rendered.lower())

    def test_readyz_fails_closed_for_invalid_security_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            environment = self._production_environment(
                snapshot_path=snapshot_path,
                audit_path=audit_path,
                token="",
            )
            with patch.dict(os.environ, environment):
                status, payload, _ = asyncio.run(
                    _request("/readyz", client_host="192.0.2.10")
                )

        self.assertEqual(status, 503)
        self.assertEqual(payload["status"], "not_ready")
        self.assertEqual(payload["checks"]["security_configuration"], "invalid")

    def test_readyz_requires_explicit_persistent_audit_storage_in_production(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = self._write_snapshot(directory)
            audit_path = Path(directory) / "audit.jsonl"
            environment = self._production_environment(
                snapshot_path=snapshot_path,
                audit_path=audit_path,
                persistent="false",
            )
            with patch.dict(os.environ, environment):
                status, payload, _ = asyncio.run(
                    _request("/readyz", client_host="192.0.2.10")
                )

        self.assertEqual(status, 503)
        self.assertEqual(payload["status"], "not_ready")
        self.assertEqual(payload["checks"]["audit_sink"], "unconfigured")


if __name__ == "__main__":
    unittest.main()
