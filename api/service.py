from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.contracts import response_metadata, warning
from modules.version import APP_VERSION


DEFAULT_SNAPSHOT = Path("data/portfolio_snapshot.json")
DEFAULT_MAX_AGE_SECONDS = 4 * 60 * 60
NON_CODE_SNAPSHOT_PATHS = {"data/portfolio_snapshot.json"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _current_commit() -> str | None:
    configured = os.getenv("GITHUB_SHA") or os.getenv("INVESTMENT_OS_COMMIT")
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def _code_matches_snapshot(snapshot_commit: str, current_commit: str) -> bool:
    """Accept a data-only snapshot commit made after its calculation run."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{snapshot_commit}..{current_commit}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    changed = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return bool(changed) and changed.issubset(NON_CODE_SNAPSHOT_PATHS)


def load_snapshot(path: str | Path = DEFAULT_SNAPSHOT) -> dict[str, Any]:
    """Load the app-generated read model without invoking calculation engines."""
    snapshot_path = Path(path)
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("Portfolio snapshot is unavailable") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Portfolio snapshot is invalid") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Portfolio snapshot must be a JSON object")
    return payload


def _legacy_run_id(snapshot: dict[str, Any]) -> str:
    source = snapshot.get("source") or {}
    seed = "|".join(
        str(value or "")
        for value in (
            snapshot.get("generated_at"),
            source.get("commit_sha"),
            source.get("portfolio_file_sha256"),
        )
    )
    return "legacy-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _freshness(
    snapshot: dict[str, Any],
    *,
    now: datetime,
    max_age_seconds: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    generated_at = _parse_datetime(snapshot.get("generated_at"))
    warnings: list[dict[str, Any]] = []
    if generated_at is None:
        warnings.append(warning("SNAPSHOT_TIME_MISSING", "Snapshot time is missing or invalid."))
        return {"status": "unknown", "as_of": None, "age_seconds": None}, warnings

    age_seconds = max(0, int((now - generated_at).total_seconds()))
    status = "fresh" if age_seconds <= max_age_seconds else "stale"
    if status == "stale":
        warnings.append(
            warning(
                "SNAPSHOT_STALE",
                "Portfolio snapshot is older than the configured freshness limit.",
                age_seconds=age_seconds,
                max_age_seconds=max_age_seconds,
            )
        )
    return {
        "status": status,
        "as_of": generated_at.isoformat(),
        "age_seconds": age_seconds,
    }, warnings


def _snapshot_warnings(
    snapshot: dict[str, Any],
    *,
    current_commit: str | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    snapshot_version = snapshot.get("app_version")
    if snapshot_version != APP_VERSION:
        result.append(
            warning(
                "APP_VERSION_MISMATCH",
                "Snapshot and running application versions differ.",
                snapshot_version=snapshot_version,
                application_version=APP_VERSION,
            )
        )
    snapshot_commit = (snapshot.get("source") or {}).get("commit_sha")
    if (
        current_commit
        and snapshot_commit
        and current_commit != snapshot_commit
        and not _code_matches_snapshot(snapshot_commit, current_commit)
    ):
        result.append(
            warning(
                "COMMIT_MISMATCH",
                "Snapshot was generated from a different commit.",
                snapshot_commit=snapshot_commit,
                application_commit=current_commit,
            )
        )
    return result


def build_system_status(
    snapshot: dict[str, Any],
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    current_commit: str | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    timestamp = now or _now()
    commit = current_commit if current_commit is not None else _current_commit()
    run_id = str(snapshot.get("run_id") or _legacy_run_id(snapshot))
    freshness, warnings = _freshness(
        snapshot, now=timestamp, max_age_seconds=max_age_seconds
    )
    warnings.extend(_snapshot_warnings(snapshot, current_commit=commit))
    payload: dict[str, Any] = response_metadata(
        request_id=request_id or str(uuid.uuid4()),
        run_id=run_id,
        generated_at=timestamp,
    )
    payload.update(
        {
            "status": "ok" if not warnings else "degraded",
            "app_version": APP_VERSION,
            "commit": commit,
            "data_freshness": freshness,
            "warnings": warnings,
        }
    )
    return payload


def build_portfolio_status(
    snapshot: dict[str, Any],
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    """Project canonical snapshot fields; never recalculate investment signals."""
    timestamp = now or _now()
    run_id = str(snapshot.get("run_id") or _legacy_run_id(snapshot))
    freshness, warnings = _freshness(
        snapshot, now=timestamp, max_age_seconds=max_age_seconds
    )
    warnings.extend(_snapshot_warnings(snapshot, current_commit=_current_commit()))
    portfolio = snapshot.get("portfolio") or {}
    quality = snapshot.get("data_quality") or {}
    macro = snapshot.get("macro_rate_regime") or {}

    payload: dict[str, Any] = response_metadata(
        request_id=request_id or str(uuid.uuid4()),
        run_id=run_id,
        generated_at=timestamp,
    )
    payload.update(
        {
            "as_of": freshness["as_of"],
            "health": {"score": portfolio.get("health_score")},
            "confidence": {
                "score": portfolio.get("ai_confidence"),
                "label": portfolio.get("ai_confidence_label"),
            },
            "data_quality": {
                "score": quality.get("score"),
                "notes": list(quality.get("notes") or []),
            },
            "macro_rate_risk": {
                "score": macro.get("score"),
                "level": macro.get("level"),
                "primary_driver": macro.get("primary_driver"),
                "impact": macro.get("impact"),
                "data_quality": macro.get("data_quality"),
                "as_of": macro.get("as_of"),
                "changes_buy_sell_logic": bool(
                    macro.get("changes_buy_sell_logic", False)
                ),
            },
            "data_freshness": freshness,
            "warnings": warnings,
        }
    )
    return payload


def build_investment_brief(
    snapshot: dict[str, Any],
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    """Build Jarvis' first brief solely from canonical snapshot output."""
    timestamp = now or _now()
    run_id = str(snapshot.get("run_id") or _legacy_run_id(snapshot))
    freshness, warnings = _freshness(
        snapshot, now=timestamp, max_age_seconds=max_age_seconds
    )
    warnings.extend(_snapshot_warnings(snapshot, current_commit=_current_commit()))

    portfolio = snapshot.get("portfolio") or {}
    quality = snapshot.get("data_quality") or {}
    macro = snapshot.get("macro_rate_regime") or {}
    decisions = list(snapshot.get("decision_queue") or [])
    opportunities = list(snapshot.get("opportunities") or [])
    stop_loss = snapshot.get("stop_loss_summary") or {}
    changes = snapshot.get("changes")

    attention: list[dict[str, Any]] = []
    for item in warnings:
        attention.append(
            {
                "code": item["code"],
                "severity": "warning",
                "message": item["message"],
            }
        )
    for note in list(quality.get("notes") or []):
        attention.append(
            {
                "code": "DATA_QUALITY_NOTE",
                "severity": "info",
                "message": str(note),
            }
        )
    if macro.get("level") not in (None, "Ukendt"):
        attention.append(
            {
                "code": "MACRO_RATE_REGIME",
                "severity": "risk",
                "message": str(macro.get("impact") or macro.get("level")),
                "level": macro.get("level"),
                "score": macro.get("score"),
                "changes_buy_sell_logic": bool(
                    macro.get("changes_buy_sell_logic", False)
                ),
            }
        )

    payload: dict[str, Any] = response_metadata(
        request_id=request_id or str(uuid.uuid4()),
        run_id=run_id,
        generated_at=timestamp,
    )
    payload.update(
        {
            "brief_type": "investment",
            "as_of": freshness["as_of"],
            "kpis": {
                "portfolio_health": portfolio.get("health_score"),
                "confidence": portfolio.get("ai_confidence"),
                "confidence_label": portfolio.get("ai_confidence_label"),
                "data_quality": quality.get("score"),
                "macro_rate_risk": macro.get("score"),
                "macro_rate_level": macro.get("level"),
            },
            "changes": {
                "available": isinstance(changes, (dict, list)),
                "items": changes if isinstance(changes, list) else [],
                "summary": changes if isinstance(changes, dict) else None,
            },
            "decisions": {
                "count": len(decisions),
                "items": decisions[:5],
            },
            "opportunities": {
                "count": len(opportunities),
                "items": opportunities[:3],
            },
            "attention": attention,
            "stop_loss_summary": stop_loss,
            "data_freshness": freshness,
            "warnings": warnings,
        }
    )
    return payload
