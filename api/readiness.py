"""Data-minimised deployment readiness checks for the Jarvis API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from api.security import load_security_settings
from api.service import load_snapshot
from jarvis.audit import audit_log_path


REQUIRED_SNAPSHOT_FIELDS = {"app_version", "generated_at", "portfolio"}


def _snapshot_status(path: str | Path) -> str:
    try:
        snapshot = load_snapshot(path)
    except RuntimeError:
        return "unavailable"
    if not REQUIRED_SNAPSHOT_FIELDS.issubset(snapshot):
        return "invalid"
    if not isinstance(snapshot.get("portfolio"), dict):
        return "invalid"
    return "ok"


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _audit_sink_status(environment: str) -> str:
    configured = str(os.getenv("JARVIS_AUDIT_LOG") or "").strip()
    persistent = str(os.getenv("JARVIS_AUDIT_PERSISTENT") or "").strip().lower()
    target = audit_log_path()

    if environment == "production":
        if persistent != "true":
            return "unconfigured"
        if not configured or not target.is_absolute():
            return "invalid"

    if target.exists():
        if target.is_symlink() or not target.is_file():
            return "invalid"
        return "ok" if os.access(target, os.W_OK) else "unavailable"

    parent = target.parent
    if environment == "production" and not parent.exists():
        return "unavailable"
    writable_parent = _nearest_existing_parent(parent)
    if not writable_parent.is_dir() or not os.access(writable_parent, os.W_OK):
        return "unavailable"
    return "ok"


def build_readiness_status(snapshot_path: str | Path) -> dict[str, Any]:
    """Return only coarse deployment checks; never expose paths or secrets."""
    settings = load_security_settings()
    checks = {
        "security_configuration": "ok" if settings.valid else "invalid",
        "snapshot": _snapshot_status(snapshot_path),
        "audit_sink": _audit_sink_status(settings.environment),
    }
    ready = all(value == "ok" for value in checks.values())
    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
