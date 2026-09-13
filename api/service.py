from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from api.contracts import SIGNAL_SCHEMA_VERSION, response_metadata, warning
from modules.version import APP_VERSION
from research.provider import get_stock_research


DEFAULT_SNAPSHOT = Path("data/portfolio_snapshot.json")
DEFAULT_MAX_AGE_SECONDS = 4 * 60 * 60
NON_CODE_SNAPSHOT_PATHS = {"data/portfolio_snapshot.json"}


class StockNotFoundError(LookupError):
    """Raised when a ticker is absent from every Investment OS snapshot section."""


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


def _canonical_ticker(record: dict[str, Any]) -> str | None:
    value = record.get("Yahoo_Ticker") or record.get("Ticker")
    rendered = str(value or "").strip().upper()
    return rendered or None


def _signal_direction(handling: Any) -> str:
    return {
        "Øg": "increase",
        "Reducer": "decrease",
        "Hold": "hold",
        "Afvent": "wait",
    }.get(str(handling or ""), "unknown")


def _signal_id(run_id: str, ticker: str, index: int) -> str:
    seed = f"{run_id}|positions|{index}|{ticker}"
    return "signal-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _queue_reason(snapshot: dict[str, Any], name: str | None) -> str | None:
    if not name:
        return None
    for item in snapshot.get("decision_queue") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("Aktiv") or "").strip() == name:
            value = str(item.get("Begrundelse") or "").strip()
            return value or None
    return None


def build_portfolio_signals(
    snapshot: dict[str, Any],
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    """Project canonical Decision Engine outputs without recalculating them."""
    timestamp = now or _now()
    run_id = str(snapshot.get("run_id") or _legacy_run_id(snapshot))
    freshness, warnings = _freshness(
        snapshot, now=timestamp, max_age_seconds=max_age_seconds
    )
    warnings.extend(_snapshot_warnings(snapshot, current_commit=_current_commit()))
    source = snapshot.get("source") or {}
    positions = list(snapshot.get("positions") or [])
    critical_fields = (
        "Decision_Score",
        "Decision_Status",
        "Handling",
        "AI_Confidence",
    )
    factor_fields = {
        "momentum": "Momentum Score",
        "ai_confidence": "AI Score",
        "relative_strength": "RS Score",
        "trend": "Trend Score",
        "risk": "Risk Score",
        "data_quality": "Data Score",
        "position": "Position Score",
    }
    momentum_fields = (
        "1W",
        "1M",
        "3M",
        "6M",
        "12M",
        "Composite",
        "Relative_Strength_3M",
        "Momentum_Acceleration",
        "Rotation_Signal",
    )

    signals: list[dict[str, Any]] = []
    missing_critical: list[dict[str, Any]] = []
    missing_factor_evidence = 0
    seen_tickers: set[str] = set()
    duplicate_tickers: set[str] = set()
    for index, record in enumerate(positions):
        if not isinstance(record, dict):
            missing_critical.append({"index": index, "fields": ["record"]})
            continue
        ticker = _canonical_ticker(record) or f"UNKNOWN-{index + 1}"
        name_value = record.get("Aktiv") or record.get("Name")
        name = str(name_value).strip() if name_value not in (None, "") else ticker
        missing = [
            field for field in critical_fields if record.get(field) is None
        ]
        if missing:
            missing_critical.append(
                {"ticker": ticker, "index": index, "fields": missing}
            )

        if ticker in seen_tickers:
            duplicate_tickers.add(ticker)
        else:
            seen_tickers.add(ticker)

        factors = {
            key: record.get(field)
            for key, field in factor_fields.items()
            if record.get(field) is not None
        }
        if len(factors) < len(factor_fields):
            missing_factor_evidence += 1
        momentum = {
            field: record.get(field)
            for field in momentum_fields
            if field in record
        }
        evidence = [
            {
                "ref": f"positions[{index}].{field}",
                "field": field,
                "value": record.get(field),
            }
            for field in (
                *critical_fields,
                *momentum_fields,
                *factor_fields.values(),
            )
            if field in record
        ]
        signals.append(
            {
                "signal_id": _signal_id(run_id, ticker, index),
                "signal_type": "investment_decision",
                "ticker": ticker,
                "name": name,
                "direction": _signal_direction(record.get("Handling")),
                "horizon": "current_snapshot",
                "generated_at": freshness.get("as_of"),
                "decision": {
                    "score": record.get("Decision_Score"),
                    "status": record.get("Decision_Status"),
                    "handling": record.get("Handling"),
                    "confidence": record.get("AI_Confidence"),
                },
                "factor_scores": factors,
                "momentum": momentum,
                "rationale": _queue_reason(snapshot, name),
                "evidence": evidence,
                "source": {
                    "authority": "Investment OS Decision Engine",
                    "section": "positions",
                    "index": index,
                },
            }
        )

    if not positions:
        warnings.append(
            warning(
                "SIGNALS_MISSING",
                "Snapshot'et indeholder ingen positionssignaler.",
            )
        )
    if missing_critical:
        warnings.append(
            warning(
                "SIGNAL_FIELDS_MISSING",
                "Et eller flere signaler mangler autoritative beslutningsfelter.",
                items=missing_critical,
            )
        )
    if duplicate_tickers:
        warnings.append(
            warning(
                "DUPLICATE_TICKER_SIGNALS",
                "Snapshot'et indeholder flere positionssignaler for samme ticker.",
                tickers=sorted(duplicate_tickers),
            )
        )
    if signals and missing_factor_evidence:
        warnings.append(
            warning(
                "SIGNAL_EVIDENCE_PARTIAL",
                "Faktorscorer mangler i et eller flere signaler; de tilgængelige "
                "Decision Engine-resultater er ikke genberegnet.",
                affected_signals=missing_factor_evidence,
                total_signals=len(signals),
            )
        )

    blocking_codes = {
        "SNAPSHOT_TIME_MISSING",
        "SNAPSHOT_STALE",
        "APP_VERSION_MISMATCH",
        "COMMIT_MISMATCH",
        "SIGNALS_MISSING",
        "SIGNAL_FIELDS_MISSING",
        "DUPLICATE_TICKER_SIGNALS",
    }
    warning_codes = {item.get("code") for item in warnings}
    blocking = sorted(code for code in warning_codes if code in blocking_codes)
    readiness = "insufficient" if blocking else (
        "limited" if "SIGNAL_EVIDENCE_PARTIAL" in warning_codes else "ready"
    )
    handling_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for signal in signals:
        decision = signal["decision"]
        handling = str(decision.get("handling") or "Ukendt")
        status = str(decision.get("status") or "Ukendt")
        handling_counts[handling] = handling_counts.get(handling, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    payload: dict[str, Any] = response_metadata(
        request_id=request_id or str(uuid.uuid4()),
        run_id=run_id,
        generated_at=timestamp,
    )
    payload.update(
        {
            "signal_schema_version": SIGNAL_SCHEMA_VERSION,
            "status": "ok" if readiness == "ready" else "degraded",
            "as_of": freshness.get("as_of"),
            "decision_readiness": {
                "status": readiness,
                "blocking_warning_codes": blocking,
            },
            "summary": {
                "signal_count": len(signals),
                "handling_counts": handling_counts,
                "status_counts": status_counts,
                "decision_queue_count": len(snapshot.get("decision_queue") or []),
            },
            "authority": {
                "system": "Investment OS",
                "engine": "Decision Engine",
                "app_version": snapshot.get("app_version"),
                "ruleset_version": snapshot.get("app_version"),
                "calculation_performed_by_api": False,
                "research_changes_signals": False,
            },
            "source": {
                "section": "positions",
                "snapshot_run_id": run_id,
                "snapshot_schema_version": snapshot.get("schema_version"),
                "snapshot_commit": source.get("commit_sha"),
                "snapshot_sha256": source.get("portfolio_file_sha256"),
                "repository": source.get("repository"),
                "branch": source.get("branch"),
            },
            "signals": signals,
            "decision_queue": list(snapshot.get("decision_queue") or []),
            "data_quality": dict(snapshot.get("data_quality") or {}),
            "data_freshness": freshness,
            "warnings": warnings,
        }
    )
    return payload


def _ticker_match(record: dict[str, Any], ticker: str) -> bool:
    requested = ticker.strip().upper()
    return any(
        str(record.get(field) or "").strip().upper() == requested
        for field in ("Ticker", "Yahoo_Ticker")
    )


def _find_stock_record(records: Any, ticker: str) -> dict[str, Any] | None:
    for record in records or []:
        if isinstance(record, dict) and _ticker_match(record, ticker):
            return record
    return None


def build_stock_status(
    snapshot: dict[str, Any],
    ticker: str,
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> dict[str, Any]:
    """Return existing OS fields for one ticker without calculating new signals."""
    requested = ticker.strip().upper()
    if not requested:
        raise StockNotFoundError("Ticker mangler.")

    position = _find_stock_record(snapshot.get("positions"), requested)
    opportunity = _find_stock_record(snapshot.get("opportunities"), requested)
    watchlist = _find_stock_record(snapshot.get("watchlist"), requested)
    if position is None and opportunity is None and watchlist is None:
        raise StockNotFoundError(
            f"{requested} findes ikke i det aktuelle Investment OS-snapshot."
        )

    timestamp = now or _now()
    run_id = str(snapshot.get("run_id") or _legacy_run_id(snapshot))
    freshness, warnings = _freshness(
        snapshot, now=timestamp, max_age_seconds=max_age_seconds
    )
    warnings.extend(_snapshot_warnings(snapshot, current_commit=_current_commit()))
    quality = snapshot.get("data_quality") or {}
    source_records = [
        name
        for name, record in (
            ("portfolio", position),
            ("opportunities", opportunity),
            ("watchlist", watchlist),
        )
        if record is not None
    ]
    name = next(
        (
            record.get("Aktiv") or record.get("Name")
            for record in (position, opportunity, watchlist)
            if record is not None and (record.get("Aktiv") or record.get("Name"))
        ),
        requested,
    )
    signal_source = position or opportunity or {}
    payload: dict[str, Any] = response_metadata(
        request_id=request_id or str(uuid.uuid4()),
        run_id=run_id,
        generated_at=timestamp,
    )
    payload.update(
        {
            "as_of": freshness["as_of"],
            "identity": {
                "ticker": requested,
                "name": name,
                "source_sections": source_records,
            },
            "signals": {
                "decision_score": signal_source.get("Decision_Score"),
                "decision_status": signal_source.get("Decision_Status"),
                "handling": signal_source.get("Handling"),
                "ai_confidence": signal_source.get("AI_Confidence"),
                "composite": signal_source.get("Composite"),
                "relative_strength_3m": signal_source.get("Relative_Strength_3M"),
                "momentum_acceleration": signal_source.get("Momentum_Acceleration"),
                "rotation_signal": signal_source.get("Rotation_Signal"),
                "returns": {
                    period: signal_source.get(period)
                    for period in ("1W", "1M", "3M", "6M", "12M")
                },
            },
            "portfolio_context": {
                "is_position": position is not None,
                "portfolio_weight": position.get("Portfolio_Weight") if position else None,
                "market_value_dkk": position.get("Market_Value_DKK") if position else None,
            },
            "watchlist_context": watchlist,
            "opportunity_context": opportunity,
            "data_quality": {
                "score": quality.get("score"),
                "notes": list(quality.get("notes") or []),
            },
            "data_freshness": freshness,
            "warnings": warnings,
        }
    )
    return payload


def build_stock_research(
    ticker: str,
    *,
    request_id: str | None = None,
    now: datetime | None = None,
    research_loader: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Wrap a separate external research snapshot in the common API contract."""
    timestamp = now or _now()
    loader = research_loader or get_stock_research
    research = loader(ticker)
    research_as_of = str(research.get("as_of") or "unavailable")
    seed = f"{research.get('ticker') or ticker}|{research_as_of}"
    run_id = "research-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    payload = dict(research)
    payload.update(
        response_metadata(
            request_id=request_id or str(uuid.uuid4()),
            run_id=run_id,
            generated_at=timestamp,
        )
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
    changes = snapshot.get("changes") or {}

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
                "available": bool(changes.get("available", False)),
                "reason": changes.get("reason"),
                "previous_run_id": changes.get("previous_run_id"),
                "previous_generated_at": changes.get("previous_generated_at"),
                "kpi_deltas": changes.get("kpi_deltas") or {},
                "decision_changes": changes.get("decision_changes")
                or {"count": 0, "items": []},
                "opportunity_changes": changes.get("opportunity_changes")
                or {"entered": [], "exited": [], "rank_changes": []},
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
