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


def _json_value(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _safe_number(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
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
) -> Path:
    """Write a UTF-8 JSON snapshot from already calculated Investment OS data."""

    output_path = Path(output_file)
    source_path = Path(data_file)
    generated_at = datetime.now(TIMEZONE)

    position_columns = [
        "Aktiv",
        "Ticker",
        "Yahoo_Ticker",
        "Aktivtype",
        "Sektor",
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
        "Relative_Strength_3M",
        "Momentum_Acceleration",
        "Rotation_Signal",
        "Handling",
    ]
    decision_columns = [
        "Prioritet",
        "Handling",
        "Aktiv",
        "Beløb DKK",
        "Decision Score",
        "Confidence",
        "Begrundelse",
    ]
    opportunity_columns = [
        "Aktiv",
        "Ticker",
        "Opportunity Score",
        "AI_Confidence",
        "Composite",
        "Relative_Strength_3M",
        "Portfolio_Weight",
        "Handling",
    ]
    rebalance_columns = [
        "Aktiv",
        "Ticker",
        "Handling",
        "Nuværende vægt",
        "Målvægt",
        "Ændring vægt",
        "Beløb DKK",
        "Begrundelse",
    ]

    active_positions = analytics_portfolio.copy()
    top_positions = active_positions.sort_values(
        "Portfolio_Weight",
        ascending=False,
        na_position="last",
    ) if "Portfolio_Weight" in active_positions.columns else active_positions

    payload = {
        "schema_version": "1.0",
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
            "portfolio_file_sha256": _file_sha256(source_path),
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
        "stop_loss_summary": {
            key: _json_value(value)
            for key, value in stop_loss_metrics.items()
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path
