"""Authentication, rate limiting, and response hardening for the Jarvis API."""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api.contracts import response_metadata, warning
from jarvis.audit import (
    AuditLogError,
    append_audit_event,
    audit_log_path,
    build_access_audit_event,
)


PROTECTED_PREFIX = "/v1/"
PUBLIC_PATHS = {"/healthz"}
LOCAL_CLIENTS = {"127.0.0.1", "::1", "localhost", "testclient"}
WINDOW_SECONDS = 60


@dataclass(frozen=True)
class SecuritySettings:
    environment: str
    api_token: str | None
    rate_limit_per_minute: int | None
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def load_security_settings() -> SecuritySettings:
    """Load security configuration from the environment and fail closed on errors."""
    environment = str(os.getenv("JARVIS_ENV") or "development").strip().lower()
    token = str(os.getenv("JARVIS_API_TOKEN") or "").strip() or None
    raw_limit = str(os.getenv("JARVIS_RATE_LIMIT_PER_MINUTE") or "").strip()
    errors: list[str] = []

    if environment not in {"development", "production"}:
        errors.append("JARVIS_ENV must be development or production.")

    rate_limit: int | None = None
    if raw_limit:
        try:
            rate_limit = int(raw_limit)
        except ValueError:
            errors.append("JARVIS_RATE_LIMIT_PER_MINUTE must be a positive integer.")
        else:
            if rate_limit <= 0:
                errors.append("JARVIS_RATE_LIMIT_PER_MINUTE must be a positive integer.")
                rate_limit = None

    if environment == "production":
        if token is None or len(token) < 32:
            errors.append("Production requires JARVIS_API_TOKEN with at least 32 characters.")
        if rate_limit is None:
            errors.append("Production requires an explicit positive rate limit.")

    return SecuritySettings(
        environment=environment,
        api_token=token,
        rate_limit_per_minute=rate_limit,
        errors=tuple(errors),
    )


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    """Small in-process limiter for the single-user Jarvis MVP."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def check(self, key: str, limit: int) -> RateLimitDecision:
        now = self._clock()
        cutoff = now - WINDOW_SECONDS
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, math.ceil(WINDOW_SECONDS - (now - events[0])))
                return RateLimitDecision(False, limit, 0, retry_after)
            events.append(now)
            return RateLimitDecision(True, limit, limit - len(events), 0)


RATE_LIMITER = SlidingWindowRateLimiter()


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _bearer_token(request: Request) -> tuple[str | None, str | None]:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None, "AUTH_REQUIRED"
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        return None, "AUTH_INVALID"
    return token.strip(), None


def _authorization_error(
    request: Request,
    settings: SecuritySettings,
) -> tuple[str, int] | None:
    if not settings.valid:
        return "SECURITY_CONFIGURATION_INVALID", 503

    if settings.api_token is None:
        if settings.environment == "development" and _client_host(request) in LOCAL_CLIENTS:
            return None
        return "REMOTE_ACCESS_DENIED", 403

    supplied, parsing_error = _bearer_token(request)
    if parsing_error:
        return parsing_error, 401
    if not hmac.compare_digest(supplied or "", settings.api_token):
        return "AUTH_INVALID", 401
    return None


def _rate_limit_key(request: Request, settings: SecuritySettings) -> str:
    if settings.api_token:
        digest = hashlib.sha256(settings.api_token.encode("utf-8")).hexdigest()
        return f"token:{digest}"
    return f"local:{_client_host(request)}"


def _security_payload(request_id: str, code: str) -> dict:
    messages = {
        "SECURITY_CONFIGURATION_INVALID": "Jarvis API security is not configured correctly.",
        "REMOTE_ACCESS_DENIED": "Unauthenticated development access is limited to localhost.",
        "AUTH_REQUIRED": "A bearer token is required.",
        "AUTH_INVALID": "The supplied bearer token is invalid.",
        "RATE_LIMIT_EXCEEDED": "The configured request limit has been exceeded.",
    }
    payload = response_metadata(
        request_id=request_id,
        run_id="unavailable",
        generated_at=datetime.now(timezone.utc),
    )
    payload.update(
        {
            "status": "rejected" if code != "SECURITY_CONFIGURATION_INVALID" else "unavailable",
            "error": {"code": code, "message": messages[code]},
            "warnings": [],
        }
    )
    return payload


def _apply_security_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


async def _rejection_response(
    request: Request,
    *,
    code: str,
    status_code: int,
    started: float,
) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    payload = _security_payload(request_id, code)
    event = build_access_audit_event(
        request_id=request_id,
        error_code=code,
        http_status=status_code,
        duration_ms=(time.perf_counter() - started) * 1000,
        method=request.method,
        endpoint_scope=(
            "jarvis_command"
            if request.url.path == "/v1/jarvis/command"
            else "investment_api"
        ),
    )
    try:
        await run_in_threadpool(append_audit_event, event, audit_log_path())
    except AuditLogError:
        payload["warnings"].append(
            warning(
                "AUDIT_LOG_UNAVAILABLE",
                "Adgang blev afvist, men audit-eventet kunne ikke gemmes.",
            )
        )
        payload["audit"] = {"status": "unavailable"}
    else:
        payload["audit"] = {"status": "recorded", "event_id": event["event_id"]}

    response = JSONResponse(payload, status_code=status_code)
    if status_code == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
    return _apply_security_headers(response)


class JarvisSecurityMiddleware(BaseHTTPMiddleware):
    """Protect private API routes while keeping a data-free health probe public."""

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        path = request.url.path
        if path in PUBLIC_PATHS or not path.startswith(PROTECTED_PREFIX):
            return _apply_security_headers(await call_next(request))

        settings = load_security_settings()
        authorization_error = _authorization_error(request, settings)
        if authorization_error:
            code, status_code = authorization_error
            return await _rejection_response(
                request,
                code=code,
                status_code=status_code,
                started=started,
            )

        decision: RateLimitDecision | None = None
        if settings.rate_limit_per_minute is not None:
            decision = RATE_LIMITER.check(
                _rate_limit_key(request, settings),
                settings.rate_limit_per_minute,
            )
            if not decision.allowed:
                response = await _rejection_response(
                    request,
                    code="RATE_LIMIT_EXCEEDED",
                    status_code=429,
                    started=started,
                )
                response.headers["Retry-After"] = str(decision.retry_after_seconds)
                response.headers["X-RateLimit-Limit"] = str(decision.limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                return response

        response = _apply_security_headers(await call_next(request))
        if decision is not None:
            response.headers["X-RateLimit-Limit"] = str(decision.limit)
            response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response
