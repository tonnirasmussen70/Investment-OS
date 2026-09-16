from __future__ import annotations

import json
import unittest

from scripts.smoke_test_jarvis_api import SmokeTestError, run_smoke_test


class _Response:
    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class JarvisSmokeTestTests(unittest.TestCase):
    def test_smoke_test_checks_public_probes_and_authenticated_status(self) -> None:
        requests = []
        responses = iter(
            [
                _Response(200, {"status": "ok"}),
                _Response(200, {"status": "ready"}),
                _Response(200, {"status": "degraded"}),
            ]
        )

        def opener(request, *, timeout):
            requests.append((request, timeout))
            return next(responses)

        checks = run_smoke_test(
            "https://jarvis.example",
            "production-token",
            timeout=3.0,
            opener=opener,
        )

        self.assertEqual([check.name for check in checks], [
            "liveness",
            "readiness",
            "authenticated_status",
        ])
        self.assertIsNone(requests[0][0].get_header("Authorization"))
        self.assertIsNone(requests[1][0].get_header("Authorization"))
        self.assertEqual(
            requests[2][0].get_header("Authorization"),
            "Bearer production-token",
        )
        self.assertEqual([item[1] for item in requests], [3.0, 3.0, 3.0])
        self.assertEqual(checks[-1].status, "degraded")

    def test_smoke_test_fails_when_readiness_is_not_ready(self) -> None:
        responses = iter(
            [
                _Response(200, {"status": "ok"}),
                _Response(503, {"status": "not_ready"}),
            ]
        )

        with self.assertRaisesRegex(SmokeTestError, "/readyz failed"):
            run_smoke_test(
                "https://jarvis.example",
                "production-token",
                opener=lambda request, timeout: next(responses),
            )


if __name__ == "__main__":
    unittest.main()
