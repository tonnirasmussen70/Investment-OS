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

from modules.analytics_engine import add_momentum
from modules.config_engine import load_investment_config
from modules.decision_engine import DECISION_WEIGHTS, apply_decision_engine, decision_summary
from modules.decision_queue_engine import build_decision_queue
from modules.health_engine import calculate_portfolio_health
from modules.market_engine import fetch_market_snapshot, fetch_price_history
from modules.opportunity_engine import build_opportunity_scores
from modules.portfolio_doctor_engine import build_portfolio_doctor
from modules.portfolio_engine import (
    calculate_portfolio,
    data_quality_score,
    load_master_file,
    portfolio_summary,
)
from modules.rebalance_engine import build_rebalance_plan
from modules.risk_engine import build_stop_loss_table, stop_loss_summary

DATA_FILE = Path("data/AI_portfolio.xlsx")
OUTPUT_FILE = Path("data/portfolio_snapshot.json")
MINIMUM_TRADE_DKK = 5_000.0
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


def _records(frame: pd.DataFrame, columns: list[str], limit: int | None = None) -> list[dict[str, Any]]:
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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    generated_at = datetime.now(TIMEZONE)
    model = load_master_file(str(DATA_FILE))
    raw = model.portfolio

    tickers = (
        raw.loc[raw["Include_Analytics"].fillna(False), "Yahoo_Ticker"]
        .dropna().astype(str).unique().tolist()
    )
    currencies = raw["Currency"].dropna().astype(str).unique().tolist()

    market_snapshot = fetch_market_snapshot(tickers, currencies)
    portfolio = calculate_portfolio(model, market_snapshot)
    config = load_investment_config(model.settings)

    analytics_portfolio = portfolio.loc[
        portfolio["Include_Analytics"].fillna(False)
    ].copy()
    benchmark_ticker = config.benchmark
    history_tickers = sorted(set([*tickers, benchmark_ticker]))
    history = fetch_price_history(history_tickers, period="18mo")
    analytics_portfolio = add_momentum(
        analytics_portfolio,
        history,
        config.momentum_weights,
        benchmark_ticker=benchmark_ticker,
    )

    analytics_portfolio = apply_decision_engine(
        analytics_portfolio,
        factor_weights=DECISION_WEIGHTS,
        max_position_weight=config.max_position_weight,
    ).data

    quality_score, quality_notes = data_quality_score(portfolio, market_snapshot)
    metrics = portfolio_summary(portfolio)
    decision = decision_summary(analytics_portfolio)

    stop_table = build_stop_loss_table(analytics_portfolio, history, lookback_days=63)
    stop_metrics = stop_loss_summary(stop_table)
    health = calculate_portfolio_health(
        analytics_portfolio,
        stop_loss_metrics=stop_metrics,
        data_quality_score=quality_score,
        max_position_weight=config.max_position_weight,
        factor_weights=config.health_weights,
    )

    opportunity_result = build_opportunity_scores(
        analytics_portfolio,
        factor_weights=DEFAULT_OPPORTUNITY_WEIGHTS,
        max_position_weight=config.max_position_weight,
    )
    active_value = _safe_number(metrics.get("Active_Market_Value_DKK")) or 0.0
    doctor = build_portfolio_doctor(
        analytics_portfolio,
        active_market_value_dkk=active_value,
        stop_loss_metrics=stop_metrics,
        data_quality_score=quality_score,
        max_position_weight=config.max_position_weight,
        factor_weights=config.health_weights,
        current_health=health.score,
        default_step=0.02,
        minimum_trade_dkk=MINIMUM_TRADE_DKK,
    )
    queue = build_decision_queue(doctor.data, opportunity_result.data, max_items=5)
    rebalance = build_rebalance_plan(
        analytics_portfolio,
        active_market_value_dkk=active_value,
        max_position_weight=config.max_position_weight,
        max_sector_weight=config.max_sector_weight,
        minimum_trade_dkk=MINIMUM_TRADE_DKK,
    )

    position_columns = [
        "Aktiv", "Ticker", "Yahoo_Ticker", "Aktivtype", "Sektor", "Depot",
        "Market_Value_DKK", "Portfolio_Weight", "Total_Return_Pct", "1W", "1M",
        "3M", "6M", "12M", "Composite", "AI_Confidence",
        "Relative_Strength_3M", "Momentum_Acceleration", "Rotation_Signal", "Handling",
    ]
    decision_columns = [
        "Prioritet", "Handling", "Aktiv", "Beløb DKK", "Decision Score",
        "Confidence", "Begrundelse",
    ]
    opportunity_columns = [
        "Name", "Yahoo_Ticker", "Decision_Score", "Decision_Status",
        "AI_Confidence", "Composite", "Relative_Strength_3M",
        "Portfolio_Weight", "Handling",
    ]
    rebalance_columns = [
        "Aktiv", "Ticker", "Handling", "Nuværende vægt", "Målvægt",
        "Ændring vægt", "Beløb DKK", "Begrundelse",
    ]

    payload = {
        "schema_version": "1.0",
        "generated_at": generated_at.isoformat(),
        "generated_at_local": generated_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "source": {
            "repository": os.getenv("GITHUB_REPOSITORY", "tonnirasmussen70/Investment-OS"),
            "branch": os.getenv("GITHUB_REF_NAME", "main"),
            "commit_sha": os.getenv("GITHUB_SHA"),
            "portfolio_file": str(DATA_FILE),
            "portfolio_file_sha256": _file_sha256(DATA_FILE),
        },
        "data_quality": {
            "score": _safe_number(quality_score),
            "notes": [str(note) for note in quality_notes],
            "ticker_count": len(tickers),
            "history_rows": int(len(history)),
        },
        "portfolio": {
            "value_dkk": _safe_number(metrics.get("Portfolio_Value_DKK")),
            "active_market_value_dkk": _safe_number(metrics.get("Active_Market_Value_DKK")),
            "total_return_pct": _safe_number(metrics.get("Total_Return_Pct")),
            "health_score": _safe_number(health.score),
            "ai_confidence": _safe_number(decision.get("AI_Confidence")),
            "ai_confidence_label": decision.get("AI_Confidence_Label"),
            "benchmark": benchmark_ticker,
            "max_position_weight": _safe_number(config.max_position_weight),
        },
        "positions": _records(analytics_portfolio, position_columns),
        "decision_queue": _records(queue.data, decision_columns, limit=5),
        "opportunities": _records(opportunity_result.data, opportunity_columns, limit=10),
        "rebalance": _records(rebalance.data, rebalance_columns),
        "stop_loss_summary": {
            key: _json_value(value) for key, value in stop_metrics.items()
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_FILE} with {len(payload['positions'])} positions")


if __name__ == "__main__":
    main()
