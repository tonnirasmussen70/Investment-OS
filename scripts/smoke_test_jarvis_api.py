from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    status_code: int
    status: str


class SmokeTestError(RuntimeError):
    """Raised when the deployed Jarvis API does not satisfy its contract."""


def _get_json(
    base_url: str,
    path: str,
    *,
    token: str | None,
    timeout: float,
    opener: Callable = urlopen,
) -> tuple[int, dict]:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers, method="GET")
    try:
        with opener(request, timeout=timeout) as response:
            status_code = int(response.status)
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SmokeTestError(f"{path} could not be verified.") from exc
    if not isinstance(payload, dict):
        raise SmokeTestError(f"{path} returned an invalid JSON contract.")
    return status_code, payload


def run_smoke_test(
    base_url: str,
    token: str,
    *,
    timeout: float = 10.0,
    opener: Callable = urlopen,
) -> list[SmokeCheck]:
    if not token.strip():
        raise SmokeTestError("A production bearer token is required.")

    checks: list[SmokeCheck] = []
    cases = (
        ("liveness", "/healthz", None, {"ok"}),
        ("readiness", "/readyz", None, {"ready"}),
        ("authenticated_status", "/v1/system/status", token, {"ok", "degraded"}),
    )
    for name, path, request_token, expected_statuses in cases:
        status_code, payload = _get_json(
            base_url,
            path,
            token=request_token,
            timeout=timeout,
            opener=opener,
        )
        actual_status = str(payload.get("status") or "")
        if status_code != 200 or actual_status not in expected_statuses:
            raise SmokeTestError(
                f"{path} failed: HTTP {status_code}, status {actual_status or 'missing'}."
            )
        checks.append(SmokeCheck(name, status_code, actual_status))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a deployed Jarvis API.")
    parser.add_argument(
        "--base-url",
        default=os.getenv("JARVIS_BASE_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--token", default=os.getenv("JARVIS_API_TOKEN", ""))
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    try:
        checks = run_smoke_test(
            args.base_url,
            args.token,
            timeout=args.timeout,
        )
    except SmokeTestError as exc:
        print(f"FAILED: {exc}")
        return 1

    for check in checks:
        print(f"OK: {check.name} ({check.status_code}, {check.status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
