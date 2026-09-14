from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


TIMEZONE = ZoneInfo("Europe/Copenhagen")


def _safe_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_value(value: Any) -> Any:
    """Convert pandas/numpy/runtime values into JSON-safe Python values."""
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _safe_number(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return [_json_value(item) for item in value.tolist()]
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _records(
    frame: pd.DataFrame | None,
    columns: list[str],
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []

    available = [column for column in columns if column in frame.columns]
    result = frame.loc[:, available].copy()

    if limit is not None:
        result = result.head(limit)

    return [
        {key: _json_value(value) for key, value in row.items()}
        for row in result.to_dict(orient="records")
    ]


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _numeric_delta(current: Any, previous: Any) -> float | None:
    current_number = _safe_number(current)
    previous_number = _safe_number(previous)
    if current_number is None or previous_number is None:
        return None
    return round(current_number - previous_number, 6)


def _record_key(record: dict[str, Any]) -> str | None:
    for field in ("Yahoo_Ticker", "Ticker", "Aktiv", "Name"):
        value = record.get(field)
        if value not in (None, ""):
            return str(value)
    return None


def build_snapshot_changes(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, Any]:
    """Compare two completed snapshots without recalculating their signals."""
    if not previous:
        return {
            "available": False,
            "reason": "NO_PREVIOUS_SNAPSHOT",
            "previous_run_id": None,
            "previous_generated_at": None,
            "kpi_deltas": {},
            "decision_changes": {"count": 0, "items": []},
            "opportunity_changes": {"entered": [], "exited": [], "rank_changes": []},
        }

    previous_portfolio = previous.get("portfolio") or {}
    current_portfolio = current.get("portfolio") or {}
    previous_quality = previous.get("data_quality") or {}
    current_quality = current.get("data_quality") or {}
    previous_macro = previous.get("macro_rate_regime") or {}
    current_macro = current.get("macro_rate_regime") or {}
    kpi_deltas = {
        "portfolio_health": _numeric_delta(
            current_portfolio.get("health_score"),
            previous_portfolio.get("health_score"),
        ),
        "confidence": _numeric_delta(
            current_portfolio.get("ai_confidence"),
            previous_portfolio.get("ai_confidence"),
        ),
        "data_quality": _numeric_delta(
            current_quality.get("score"), previous_quality.get("score")
        ),
        "macro_rate_risk": _numeric_delta(
            current_macro.get("score"), previous_macro.get("score")
        ),
    }

    previous_positions = {
        key: item
        for item in previous.get("positions") or []
        if (key := _record_key(item)) is not None
    }
    decision_changes: list[dict[str, Any]] = []
    for item in current.get("positions") or []:
        key = _record_key(item)
        before = previous_positions.get(key) if key else None
        if not before:
            continue
        field_changes: dict[str, dict[str, Any]] = {}
        for field in ("Handling", "Decision_Status"):
            if field in item and field in before and item.get(field) != before.get(field):
                field_changes[field] = {
                    "from": before.get(field),
                    "to": item.get(field),
                }
        score_delta = (
            _numeric_delta(item.get("Decision_Score"), before.get("Decision_Score"))
            if "Decision_Score" in item and "Decision_Score" in before
            else None
        )
        if score_delta not in (None, 0.0):
            field_changes["Decision_Score"] = {
                "from": _safe_number(before.get("Decision_Score")),
                "to": _safe_number(item.get("Decision_Score")),
                "delta": score_delta,
            }
        if field_changes:
            decision_changes.append(
                {
                    "asset": item.get("Aktiv") or item.get("Name") or key,
                    "ticker": item.get("Yahoo_Ticker") or item.get("Ticker"),
                    "changes": field_changes,
                }
            )

    previous_opportunities = {
        key: index + 1
        for index, item in enumerate(previous.get("opportunities") or [])
        if (key := _record_key(item)) is not None
    }
    current_opportunities = {
        key: index + 1
        for index, item in enumerate(current.get("opportunities") or [])
        if (key := _record_key(item)) is not None
    }
    entered = [
        {"ticker": key, "rank": rank}
        for key, rank in current_opportunities.items()
        if key not in previous_opportunities
    ]
    exited = [
        {"ticker": key, "previous_rank": rank}
        for key, rank in previous_opportunities.items()
        if key not in current_opportunities
    ]
    rank_changes = [
        {
            "ticker": key,
            "from": previous_opportunities[key],
            "to": rank,
            "delta": previous_opportunities[key] - rank,
        }
        for key, rank in current_opportunities.items()
        if key in previous_opportunities and rank != previous_opportunities[key]
    ]

    return {
        "available": True,
        "reason": None,
        "previous_run_id": previous.get("run_id"),
        "previous_generated_at": previous.get("generated_at"),
        "kpi_deltas": kpi_deltas,
        "decision_changes": {
            "count": len(decision_changes),
            "items": decision_changes[:10],
        },
        "opportunity_changes": {
            "entered": entered,
            "exited": exited,
            "rank_changes": rank_changes,
        },
    }


def _load_previous_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_portfolio_snapshot(
    *,
    output_file: str | Path,
    data_file: str | Path,
    app_version: str,
    portfolio: pd.DataFrame,
    analytics_portfolio: pd.DataFrame,
    portfolio_metrics: dict[str, Any],
    portfolio_health: Any,
    decision: dict[str, Any],
    quality_score: float,
    quality_notes: list[str],
    benchmark_ticker: str,
    max_position_weight: float,
    history: pd.DataFrame,
    decision_queue: Any,
    opportunity_result: Any,
    rebalance_result: Any,
    stop_loss_metrics: dict[str, Any],
    macro_rate_regime: Any | None = None,
    watchlist: pd.DataFrame | None = None,
) -> Path:
    """Write a UTF-8 JSON snapshot from already calculated Investment OS data."""

    output_path = Path(output_file)
    source_path = Path(data_file)
    generated_at = datetime.now(TIMEZONE)
    source_hash = _file_sha256(source_path)
    run_seed = "|".join(
        [generated_at.isoformat(), app_version, source_hash or ""]
    )
    run_id = "ios-" + hashlib.sha256(run_seed.encode("utf-8")).hexdigest()[:16]

    position_columns = [
        "Aktiv",
        "Name",
        "Ticker",
        "Yahoo_Ticker",
        "Aktivtype",
        "Asset_Type",
        "Sektor",
        "Sector",
        "Depot",
        "Market_Value_DKK",
        "Portfolio_Weight",
        "Total_Return_Pct",
        "1W",
        "1M",
        "3M",
        "6M",
        "12M",
        "Composite",
        "AI_Confidence",
        "Momentum Score",
        "AI Score",
        "RS Score",
        "Trend Score",
        "Risk Score",
        "Data Score",
        "Position Score",
        "Decision_Score",
        "Decision_Status",
        "Relative_Strength_3M",
        "Momentum_Acceleration",
        "Rotation_Signal",
        "Volatility",
        "Max_Drawdown",
        "Momentum_Data_Quality",
        "Handling",
    ]
    decision_columns = [
        "Prioritet",
        "Handling",
        "Aktiv",
        "Beløb DKK",
        "Decision Score",
        "Status",
        "Confidence",
        "Begrundelse",
    ]
    opportunity_columns = [
        "Name",
        "Yahoo_Ticker",
        "Decision_Score",
        "Decision_Status",
        "AI_Confidence",
        "Momentum Score",
        "AI Score",
        "RS Score",
        "Trend Score",
        "Risk Score",
        "Data Score",
        "Position Score",
        "Composite",
        "Relative_Strength_3M",
        "Portfolio_Weight",
        "Handling",
    ]
    rebalance_columns = [
        "Aktiv",
        "Yahoo_Ticker",
        "Asset_Type",
        "Sector",
        "Handling",
        "Rebalance handling",
        "Nuværende vægt",
        "Modelmålvægt",
        "Foreslået vægt",
        "Ændring",
        "Handel DKK",
        "Decision Score",
        "Status",
        "Constraint",
        "Begrundelse",
    ]
    watchlist_columns = [
        "Name",
        "Ticker",
        "Yahoo_Ticker",
        "Currency",
        "Sector",
        "Status",
        "Target_Buy",
        "Max_Price",
        "AI_Confidence",
        "Notes",
    ]

    active_positions = analytics_portfolio.copy()
    top_positions = active_positions.sort_values(
        "Portfolio_Weight",
        ascending=False,
        na_position="last",
    ) if "Portfolio_Weight" in active_positions.columns else active_positions

    payload = {
        "schema_version": "2.0",
        "run_id": run_id,
        "app_version": app_version,
        "generated_at": generated_at.isoformat(),
        "generated_at_local": generated_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "source": {
            "repository": os.getenv(
                "GITHUB_REPOSITORY",
                "tonnirasmussen70/Investment-OS",
            ),
            "branch": os.getenv("GITHUB_REF_NAME", "main"),
            "commit_sha": os.getenv("GITHUB_SHA"),
            "portfolio_file": str(source_path),
            "portfolio_file_sha256": source_hash,
        },
        "data_quality": {
            "score": _safe_number(quality_score),
            "notes": [str(note) for note in quality_notes],
            "position_count": int(len(portfolio)),
            "analytics_position_count": int(len(analytics_portfolio)),
            "history_rows": int(len(history)),
        },
        "portfolio": {
            "value_dkk": _safe_number(
                portfolio_metrics.get("Portfolio_Value_DKK")
            ),
            "active_market_value_dkk": _safe_number(
                portfolio_metrics.get("Active_Market_Value_DKK")
            ),
            "total_return_pct": _safe_number(
                portfolio_metrics.get("Total_Return_Pct")
            ),
            "health_score": _safe_number(portfolio_health.score),
            "ai_confidence": _safe_number(decision.get("AI_Confidence")),
            "ai_confidence_label": decision.get("AI_Confidence_Label"),
            "benchmark": benchmark_ticker,
            "max_position_weight": _safe_number(max_position_weight),
        },
        "macro_rate_regime": {
            "score": _safe_number(getattr(macro_rate_regime, "score", None)),
            "level": getattr(macro_rate_regime, "level", "Ukendt"),
            "primary_driver": getattr(
                macro_rate_regime, "primary_driver", "Utilstrækkelige data"
            ),
            "impact": getattr(macro_rate_regime, "impact", "Kan ikke vurderes"),
            "data_quality": _safe_number(
                getattr(macro_rate_regime, "data_quality", None)
            ),
            "as_of": _json_value(getattr(macro_rate_regime, "as_of", None)),
            "components": {
                str(key): _safe_number(value)
                for key, value in (
                    getattr(macro_rate_regime, "components", {}) or {}
                ).items()
            },
            "observations": {
                str(key): _safe_number(value)
                for key, value in (
                    getattr(macro_rate_regime, "observations", {}) or {}
                ).items()
            },
            "changes_buy_sell_logic": False,
        },
        "execution_summary": {
            "trade_count": _safe_int(getattr(rebalance_result, "trade_count", 0)),
            "gross_trade_dkk": _safe_number(
                getattr(rebalance_result, "gross_trade_dkk", 0.0)
            ),
            "buy_dkk": _safe_number(getattr(rebalance_result, "buy_dkk", 0.0)),
            "sell_dkk": _safe_number(getattr(rebalance_result, "sell_dkk", 0.0)),
            "net_trade_dkk": _safe_number(
                getattr(rebalance_result, "net_trade_dkk", 0.0)
            ),
            "cash_required_dkk": _safe_number(
                getattr(rebalance_result, "cash_required_dkk", 0.0)
            ),
            "constrained_count": _safe_int(
                getattr(rebalance_result, "constrained_count", 0)
            ),
        },
        "top_positions": _records(top_positions, position_columns, limit=10),
        "positions": _records(active_positions, position_columns),
        "decision_queue": _records(
            getattr(decision_queue, "data", None),
            decision_columns,
            limit=5,
        ),
        "opportunities": _records(
            getattr(opportunity_result, "data", None),
            opportunity_columns,
            limit=10,
        ),
        "rebalance": _records(
            getattr(rebalance_result, "data", None),
            rebalance_columns,
        ),
        "watchlist": _records(watchlist, watchlist_columns),
        "stop_loss_summary": {
            key: _json_value(value)
            for key, value in stop_loss_metrics.items()
        },
    }

    payload["changes"] = build_snapshot_changes(
        _load_previous_snapshot(output_path), payload
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_json_value(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
