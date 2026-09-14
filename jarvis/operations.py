"""Operational service indicators derived from the privacy-minimised audit log."""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from api.contracts import response_metadata, warning
from jarvis.audit import AUDIT_SCHEMA_VERSION, audit_log_path


DEFAULT_WINDOW_HOURS = 24
_REQUIRED_FIELDS = {
    "audit_schema_version",
    "event_id",
    "event_type",
    "occurred_at",
    "trace",
    "authorization",
    "versions",
    "result",
}
_PRIVATE_KEYS = {
    "api_token",
    "authorization_header",
    "command_text",
    "credentials",
    "file_path",
    "headers",
    "password",
    "payload",
    "portfolio",
    "positions",
    "raw_command",
    "raw_url",
    "request_body",
    "response_body",
    "secret",
    "token",
}


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 3)
    fraction = position - lower
    value = ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
    return round(value, 3)


def _contains_private_data(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            rendered = str(key).strip().lower()
            if rendered in _PRIVATE_KEYS:
                return True
            if _contains_private_data(child):
                return True
    elif isinstance(value, list):
        return any(_contains_private_data(item) for item in value)
    return False


def _schema_valid(event: Any) -> bool:
    if not isinstance(event, dict) or not _REQUIRED_FIELDS.issubset(event):
        return False
    if event.get("audit_schema_version") != AUDIT_SCHEMA_VERSION:
        return False
    if not all(isinstance(event.get(field), dict) for field in ("trace", "authorization", "versions", "result")):
        return False
    return bool(str(event.get("event_id") or "").strip()) and _parse_timestamp(event.get("occurred_at")) is not None


def _empty_indicators() -> dict[str, Any]:
    return {
        "availability": {
            "observed_pct": None,
            "available_requests": 0,
            "requests_observed": 0,
            "sla_target_pct": None,
            "sla_status": "unconfigured",
        },
        "latency_ms": {
            "p50": None,
            "p95": None,
            "sample_count": 0,
        },
        "events": {
            "completed_commands": 0,
            "technical_failures": 0,
            "command_rejections": 0,
            "access_rejections": 0,
            "other": 0,
        },
    }


def build_operational_service_indicators(
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    path: str | Path | None = None,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> dict[str, Any]:
    """Aggregate operational evidence without exposing raw audit events."""
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = timestamp - timedelta(hours=window_hours)
    payload: dict[str, Any] = response_metadata(
        request_id=request_id or str(uuid.uuid4()),
        run_id="operations-24h",
        generated_at=timestamp,
    )
    payload.update(
        {
            "status": "ok",
            "window": {
                "hours": window_hours,
                "from": start.isoformat(),
                "to": timestamp.isoformat(),
            },
            "indicators": _empty_indicators(),
            "audit_integrity": {
                "status": "ok",
                "records_checked": 0,
                "valid_events": 0,
                "invalid_schema_records": 0,
                "duplicate_event_ids": 0,
                "privacy_violation_events": 0,
                "privacy_target": 0,
                "privacy_target_met": True,
            },
            "warnings": [],
        }
    )

    target = Path(path) if path is not None else audit_log_path()
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, OSError, UnicodeError):
        payload["status"] = "unavailable"
        payload["audit_integrity"]["status"] = "unavailable"
        payload["warnings"].append(
            warning(
                "AUDIT_LOG_UNAVAILABLE",
                "Operational indicators are unavailable because the audit log could not be read.",
            )
        )
        return payload

    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    integrity = payload["audit_integrity"]
    for line in lines:
        if not line.strip():
            continue
        integrity["records_checked"] += 1
        try:
            event = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            integrity["invalid_schema_records"] += 1
            continue

        occurred_at = _parse_timestamp(event.get("occurred_at")) if isinstance(event, dict) else None
        if occurred_at is not None and not (start <= occurred_at <= timestamp):
            continue
        if not _schema_valid(event):
            integrity["invalid_schema_records"] += 1
            continue

        event_id = str(event["event_id"])
        if event_id in seen_ids:
            integrity["duplicate_event_ids"] += 1
        else:
            seen_ids.add(event_id)
        if _contains_private_data(event):
            integrity["privacy_violation_events"] += 1
        events.append(event)
        integrity["valid_events"] += 1

    durations: list[float] = []
    counts = payload["indicators"]["events"]
    technical_failures = 0
    for event in events:
        event_type = str(event.get("event_type") or "")
        result = event.get("result") or {}
        status_code = result.get("http_status")
        outcome = str(result.get("outcome") or "")
        if event_type == "jarvis.command.completed":
            counts["completed_commands"] += 1
        elif event_type == "jarvis.command.rejected":
            counts["command_rejections"] += 1
        elif event_type == "jarvis.access.rejected":
            counts["access_rejections"] += 1
        elif event_type == "jarvis.command.failed":
            counts["technical_failures"] += 1
        else:
            counts["other"] += 1

        is_failure = event_type == "jarvis.command.failed" or outcome == "failed"
        try:
            is_failure = is_failure or int(status_code) >= 500
        except (TypeError, ValueError):
            pass
        if is_failure:
            technical_failures += 1

        try:
            duration = float(result.get("duration_ms"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(duration) and duration >= 0:
            durations.append(duration)

    total = len(events)
    available = max(0, total - technical_failures)
    availability = payload["indicators"]["availability"]
    availability["available_requests"] = available
    availability["requests_observed"] = total
    if total:
        availability["observed_pct"] = round(available / total * 100, 3)

    latency = payload["indicators"]["latency_ms"]
    latency["p50"] = _percentile(durations, 0.50)
    latency["p95"] = _percentile(durations, 0.95)
    latency["sample_count"] = len(durations)

    privacy_violations = integrity["privacy_violation_events"]
    integrity["privacy_target_met"] = privacy_violations == integrity["privacy_target"]
    integrity_degraded = any(
        integrity[key] > 0
        for key in (
            "invalid_schema_records",
            "duplicate_event_ids",
            "privacy_violation_events",
        )
    )
    if integrity_degraded:
        integrity["status"] = "degraded"
        payload["status"] = "degraded"
        payload["warnings"].append(
            warning(
                "AUDIT_INTEGRITY_DEGRADED",
                "Audit schema, uniqueness, or privacy checks found deviations.",
                invalid_schema_records=integrity["invalid_schema_records"],
                duplicate_event_ids=integrity["duplicate_event_ids"],
                privacy_violation_events=privacy_violations,
            )
        )
    if not events:
        payload["status"] = "degraded"
        payload["warnings"].append(
            warning(
                "NO_OPERATIONAL_EVENTS",
                "No valid operational audit events were observed in the selected window.",
            )
        )
    return payload
