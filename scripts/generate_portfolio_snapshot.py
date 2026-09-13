from __future__ import annotations

from pathlib import Path

import pandas as pd

from modules.analytics_engine import add_momentum
from modules.config_engine import load_investment_config
from modules.decision_engine import DECISION_WEIGHTS, apply_decision_engine, decision_summary
from modules.decision_queue_engine import build_decision_queue
from modules.health_engine import calculate_portfolio_health
from modules.market_engine import fetch_market_snapshot, fetch_price_history
from modules.macro_rate_engine import (
    apply_macro_rate_overlay,
    calculate_macro_rate_regime,
    fetch_fred_macro_history,
)
from modules.opportunity_engine import build_opportunity_scores
from modules.portfolio_engine import (
    calculate_portfolio,
    data_quality_score,
    load_master_file,
    portfolio_summary,
)
from modules.rebalance_engine import build_rebalance_plan
from modules.risk_engine import build_stop_loss_table, stop_loss_summary
from modules.snapshot_engine import write_portfolio_snapshot
from modules.version import APP_VERSION


DATA_FILE = Path("data/AI_portfolio.xlsx")
OUTPUT_FILE = Path("data/portfolio_snapshot.json")
MINIMUM_TRADE_DKK = 5_000.0


def main() -> None:
    """Generér snapshot gennem samme standardpipeline som Streamlit-appen."""
    model = load_master_file(str(DATA_FILE))
    raw = model.portfolio

    tickers = (
        raw.loc[raw["Include_Analytics"].fillna(False), "Yahoo_Ticker"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
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

    try:
        macro_history = fetch_fred_macro_history(years=3)
    except Exception:
        macro_history = pd.DataFrame()
    treasury_history = fetch_price_history(["^TNX"], period="18mo")
    if "^TNX" in treasury_history.columns:
        yahoo_10y = pd.to_numeric(
            treasury_history["^TNX"], errors="coerce"
        ).dropna()
        yahoo_10y.index = pd.to_datetime(yahoo_10y.index).tz_localize(None).normalize()
        if macro_history.empty:
            macro_history = yahoo_10y.rename("US10Y").to_frame()
        else:
            macro_history.index = pd.to_datetime(
                macro_history.index
            ).tz_localize(None).normalize()
            macro_history = macro_history.reindex(
                macro_history.index.union(yahoo_10y.index)
            ).sort_index()
            macro_history["US10Y"] = yahoo_10y.combine_first(
                macro_history.get("US10Y", pd.Series(dtype=float))
            )
    macro_rate_regime = calculate_macro_rate_regime(macro_history)
    analytics_portfolio = apply_macro_rate_overlay(
        analytics_portfolio, macro_rate_regime
    )

    quality_score, quality_notes = data_quality_score(portfolio, market_snapshot)
    metrics = portfolio_summary(portfolio)
    decision = decision_summary(analytics_portfolio)

    stop_table = build_stop_loss_table(
        analytics_portfolio,
        history,
        lookback_days=63,
    )
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
        factor_weights=DECISION_WEIGHTS,
        max_position_weight=config.max_position_weight,
    )

    active_value = float(metrics.get("Active_Market_Value_DKK") or 0.0)
    rebalance = build_rebalance_plan(
        analytics_portfolio,
        active_market_value_dkk=active_value,
        max_position_weight=config.max_position_weight,
        max_sector_weight=config.max_sector_weight,
        minimum_trade_dkk=MINIMUM_TRADE_DKK,
    )
    queue = build_decision_queue(rebalance.data, max_items=5)

    output = write_portfolio_snapshot(
        output_file=OUTPUT_FILE,
        data_file=DATA_FILE,
        app_version=APP_VERSION,
        portfolio=portfolio,
        analytics_portfolio=analytics_portfolio,
        portfolio_metrics=metrics,
        portfolio_health=health,
        decision=decision,
        quality_score=quality_score,
        quality_notes=quality_notes,
        benchmark_ticker=benchmark_ticker,
        max_position_weight=config.max_position_weight,
        history=history,
        decision_queue=queue,
        opportunity_result=opportunity_result,
        rebalance_result=rebalance,
        stop_loss_metrics=stop_metrics,
        macro_rate_regime=macro_rate_regime,
        watchlist=model.watchlist,
    )
    print(f"Wrote {output} with {len(analytics_portfolio)} analytics positions")


if __name__ == "__main__":
    main()
