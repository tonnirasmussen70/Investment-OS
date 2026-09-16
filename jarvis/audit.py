"""Privacy-minimised audit trail for the read-only Jarvis command endpoint."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.contracts import SCHEMA_VERSION
from modules.version import APP_VERSION


AUDIT_SCHEMA_VERSION = "1.0"
JARVIS_VERSION = "0.1.0"
DEFAULT_AUDIT_LOG = Path("logs/jarvis_audit.jsonl")
DEFAULT_AUDIT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_AUDIT_BACKUP_COUNT = 7
MAX_AUDIT_BACKUP_COUNT = 100

_WRITE_LOCK = threading.Lock()


class AuditLogError(RuntimeError):
    """Raised when an audit event cannot be persisted safely."""


@dataclass(frozen=True)
class AuditStorageSettings:
    max_bytes: int
    backup_count: int
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def audit_log_path() -> Path:
    """Return the configured audit sink without exposing it in API responses."""
    configured = os.getenv("JARVIS_AUDIT_LOG")
    return Path(configured) if configured else DEFAULT_AUDIT_LOG


def load_audit_storage_settings() -> AuditStorageSettings:
    """Load bounded audit retention settings without silently accepting errors."""
    errors: list[str] = []

    def positive_integer(
        name: str,
        default: int,
        *,
        maximum: int | None = None,
    ) -> int:
        raw_value = str(os.getenv(name) or "").strip()
        if not raw_value:
            return default
        try:
            value = int(raw_value)
        except ValueError:
            errors.append(f"{name} must be a positive integer.")
            return default
        if value <= 0:
            errors.append(f"{name} must be a positive integer.")
            return default
        if maximum is not None and value > maximum:
            errors.append(f"{name} must not exceed {maximum}.")
            return default
        return value

    return AuditStorageSettings(
        max_bytes=positive_integer("JARVIS_AUDIT_MAX_BYTES", DEFAULT_AUDIT_MAX_BYTES),
        backup_count=positive_integer(
            "JARVIS_AUDIT_BACKUP_COUNT",
            DEFAULT_AUDIT_BACKUP_COUNT,
            maximum=MAX_AUDIT_BACKUP_COUNT,
        ),
        errors=tuple(errors),
    )


def audit_log_paths(
    path: str | Path | None = None,
    *,
    settings: AuditStorageSettings | None = None,
) -> tuple[Path, ...]:
    """Return the active audit log followed by its bounded backup family."""
    storage = settings or load_audit_storage_settings()
    if not storage.valid:
        raise AuditLogError("Jarvis audit storage configuration is invalid.")
    target = Path(path) if path is not None else audit_log_path()
    backups = tuple(
        Path(f"{target}.{index}")
        for index in range(1, storage.backup_count + 1)
    )
    return (target, *backups)


def _require_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise OSError("Audit storage entry is not a regular file.")


def _prune_excess_audit_backups(target: Path, backup_count: int) -> None:
    prefix = f"{target.name}."
    for candidate in target.parent.iterdir():
        if not candidate.name.startswith(prefix):
            continue
        suffix = candidate.name[len(prefix) :]
        if not suffix.isdigit() or int(suffix) <= backup_count:
            continue
        if candidate.is_symlink():
            candidate.unlink()
            continue
        _require_regular_file(candidate)
        candidate.unlink()


def _rotate_audit_log(target: Path, backup_count: int) -> None:
    """Rotate existing regular files while retaining a bounded backup family."""
    _require_regular_file(target)
    for index in range(1, backup_count + 1):
        candidate = Path(f"{target}.{index}")
        if candidate.exists() or candidate.is_symlink():
            _require_regular_file(candidate)

    for index in range(backup_count - 1, 0, -1):
        source = Path(f"{target}.{index}")
        if not source.exists():
            continue
        source.replace(Path(f"{target}.{index + 1}"))

    target.replace(Path(f"{target}.1"))


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


def build_access_audit_event(
    *,
    request_id: str,
    error_code: str,
    http_status: int,
    duration_ms: float,
    method: str,
    endpoint_scope: str,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a data-minimised event for an authentication or rate-limit denial."""
    event_time = (occurred_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "event_type": "jarvis.access.rejected",
        "occurred_at": event_time.isoformat(),
        "trace": {
            "request_id": _safe_identifier(request_id),
            "run_id": "unavailable",
        },
        "request": {
            "method": str(method or "unknown").upper(),
            "endpoint_scope": str(endpoint_scope or "unknown"),
            "path_recorded": False,
            "credentials_recorded": False,
        },
        "authorization": {
            "approval_required": False,
            "approval_status": "not_applicable",
            "investment_execution_allowed": False,
        },
        "versions": {
            "jarvis": JARVIS_VERSION,
            "response_mode": "deterministic",
            "model": None,
            "api_schema": SCHEMA_VERSION,
            "investment_os": APP_VERSION,
        },
        "result": {
            "outcome": "rejected",
            "http_status": int(http_status),
            "error_code": str(error_code),
            "duration_ms": round(max(0.0, float(duration_ms)), 3),
        },
    }


def build_request_audit_event(
    *,
    request_id: str,
    outcome: str,
    http_status: int,
    duration_ms: float,
    method: str,
    endpoint_scope: str,
    error_code: str | None = None,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a privacy-safe event for an authenticated non-command API call."""
    event_time = (occurred_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    safe_outcome = "failed" if outcome == "failed" else "completed"
    return {
        "audit_schema_version": AUDIT_SCHEMA_VERSION,
        "event_id": str(uuid.uuid4()),
        "event_type": f"jarvis.request.{safe_outcome}",
        "occurred_at": event_time.isoformat(),
        "trace": {
            "request_id": _safe_identifier(request_id),
            "run_id": "unavailable",
        },
        "request": {
            "method": str(method or "unknown").upper(),
            "endpoint_scope": str(endpoint_scope or "unknown"),
            "path_recorded": False,
            "query_recorded": False,
            "credentials_recorded": False,
            "body_recorded": False,
        },
        "authorization": {
            "approval_required": False,
            "approval_status": "not_applicable",
            "investment_execution_allowed": False,
        },
        "versions": {
            "jarvis": JARVIS_VERSION,
            "response_mode": "deterministic",
            "model": None,
            "api_schema": SCHEMA_VERSION,
            "investment_os": APP_VERSION,
        },
        "result": {
            "outcome": safe_outcome,
            "http_status": int(http_status),
            "error_code": str(error_code) if error_code else None,
            "duration_ms": round(max(0.0, float(duration_ms)), 3),
        },
    }


def append_audit_event(event: dict[str, Any], path: str | Path | None = None) -> None:
    """Append one compact event and rotate the bounded owner-only log family."""
    target = Path(path) if path is not None else audit_log_path()
    storage = load_audit_storage_settings()
    if not storage.valid:
        raise AuditLogError("Jarvis audit storage configuration is invalid.")
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
            _prune_excess_audit_backups(target, storage.backup_count)
            if target.exists() or target.is_symlink():
                _require_regular_file(target)
                event_bytes = len((line + "\n").encode("utf-8"))
                current_bytes = target.stat().st_size
                if current_bytes > 0 and current_bytes + event_bytes > storage.max_bytes:
                    _rotate_audit_log(target, storage.backup_count)
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
