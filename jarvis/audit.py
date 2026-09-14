"""Privacy-minimised audit trail for the read-only Jarvis command endpoint."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.contracts import SCHEMA_VERSION
from modules.version import APP_VERSION


AUDIT_SCHEMA_VERSION = "1.0"
JARVIS_VERSION = "0.1.0"
DEFAULT_AUDIT_LOG = Path("logs/jarvis_audit.jsonl")

_WRITE_LOCK = threading.Lock()


class AuditLogError(RuntimeError):
    """Raised when an audit event cannot be persisted safely."""


def audit_log_path() -> Path:
    """Return the configured audit sink without exposing it in API responses."""
    configured = os.getenv("JARVIS_AUDIT_LOG")
    return Path(configured) if configured else DEFAULT_AUDIT_LOG


def _safe_identifier(value: Any) -> str:
    """Keep normal trace IDs, but hash unusual values that may contain secrets."""
    rendered = str(value or "unavailable")
    if (
        1 <= len(rendered) <= 128
        and all(character.isalnum() or character in "-_.:" for character in rendered)
    ):
        return rendered
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:24]
    return f"redacted-{digest}"


def _codes(items: Any) -> set[str]:
    result: set[str] = set()
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if code:
            result.add(str(code))
    return result


def _observability(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    research = data.get("research") if isinstance(data.get("research"), dict) else {}
    freshness = data.get("data_freshness")
    if not isinstance(freshness, dict):
        freshness = data.get("freshness") if isinstance(data.get("freshness"), dict) else {}

    quality = data.get("data_quality") if isinstance(data.get("data_quality"), dict) else {}
    kpis = data.get("kpis") if isinstance(data.get("kpis"), dict) else {}
    research_quality = (
        research.get("data_quality")
        if isinstance(research.get("data_quality"), dict)
        else {}
    )
    research_freshness = (
        research.get("freshness")
        if isinstance(research.get("freshness"), dict)
        else {}
    )

    reason_codes = _codes(payload.get("warnings"))
    reason_codes.update(_codes(data.get("warnings")))
    reason_codes.update(_codes(data.get("attention")))
    reason_codes.update(_codes(research.get("warnings")))
    readiness = (
        data.get("decision_readiness")
        if isinstance(data.get("decision_readiness"), dict)
        else {}
    )
    reason_codes.update(str(code) for code in readiness.get("blocking_warning_codes") or [])

    return {
        "freshness": {
            "status": freshness.get("status"),
            "as_of": freshness.get("as_of") or data.get("as_of"),
        },
        "data_quality": {
            "score": quality.get("score", kpis.get("data_quality")),
            "status": quality.get("status"),
        },
        "research": {
            "status": research.get("status"),
            "freshness": research_freshness.get("status"),
            "data_quality": research_quality.get("status"),
            "coverage": research_quality.get("coverage"),
        },
        "decision_readiness": readiness.get("status"),
        "reason_codes": sorted(reason_codes),
    }


def build_command_audit_event(
    *,
    request_id: str,
    payload: dict[str, Any],
    outcome: str,
    http_status: int,
    duration_ms: float,
    snapshot: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    """Build an allow-listed event; command text and response data are excluded."""
    source = (snapshot or {}).get("source") or {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    event_time = (occurred_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "event_type": f"jarvis.command.{outcome}",
        "occurred_at": event_time.isoformat(),
        "trace": {
            "request_id": _safe_identifier(request_id),
            "run_id": _safe_identifier(payload.get("run_id")),
        },
        "command": {
            "intent": payload.get("intent"),
            "content_recorded": False,
            "access_level": "A_READ",
        },
        "authorization": {
            "approval_required": False,
            "approval_status": "not_required",
            "side_effect": "audit_only",
            "investment_execution_allowed": False,
        },
        "versions": {
            "jarvis": JARVIS_VERSION,
            "response_mode": "deterministic",
            "model": None,
            "api_schema": payload.get("schema_version") or SCHEMA_VERSION,
            "signal_schema": data.get("signal_schema_version"),
            "investment_os": (snapshot or {}).get("app_version") or APP_VERSION,
            "snapshot_schema": (snapshot or {}).get("schema_version"),
            "snapshot_commit": source.get("commit_sha"),
        },
        "observability": _observability(payload),
        "result": {
            "outcome": outcome,
            "http_status": int(http_status),
            "error_code": error.get("code"),
            "duration_ms": round(max(0.0, float(duration_ms)), 3),
        },
    }


def append_audit_event(event: dict[str, Any], path: str | Path | None = None) -> None:
    """Append one compact event with owner-only permissions where supported."""
    target = Path(path) if path is not None else audit_log_path()
    try:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise AuditLogError("Jarvis audit event could not be serialized.") from exc
    try:
        with _WRITE_LOCK:
            parent_existed = target.parent.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            if not parent_existed:
                try:
                    target.parent.chmod(0o700)
                except OSError:
                    pass
            flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(target, flags, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                target.chmod(0o600)
            except OSError:
                pass
    except OSError as exc:
        raise AuditLogError("Jarvis audit event could not be persisted.") from exc
