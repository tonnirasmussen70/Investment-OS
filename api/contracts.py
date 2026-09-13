from __future__ import annotations

from datetime import datetime
from typing import Any


SCHEMA_VERSION = "1.0"
SIGNAL_SCHEMA_VERSION = "1.0"


def response_metadata(*, request_id: str, run_id: str, generated_at: datetime) -> dict[str, str]:
    """Return the metadata required on every Jarvis API response."""
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": run_id,
        "generated_at": generated_at.isoformat(),
    }


def warning(code: str, message: str, **details: Any) -> dict[str, Any]:
    """Create a machine-readable warning without exposing private paths."""
    payload: dict[str, Any] = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return payload
