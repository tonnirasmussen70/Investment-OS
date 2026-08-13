from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from modules.analytics_engine import (
    add_momentum,
    beta,
    period_return,
    portfolio_returns,
    rolling_sharpe,
)
from modules.attribution_engine import (
    calculate_attribution,
    top_contributors,
    top_detractors,
)
from modules.change_engine import build_change_engine
from modules.compounder_engine import (
    load_compounder_radar,
    radar_summary,
    top_candidates,
)
from modules.config_engine import load_investment_config
from modules.decision_engine import DECISION_WEIGHTS, apply_decision_engine, decision_summary
from modules.decision_queue_engine import build_decision_queue
from modules.formatting import format_dkk, format_pct, format_score
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
from modules.snapshot_engine import write_portfolio_snapshot
from modules.styling import table_style
from modules.watchlist_engine import (
    format_watchlist_table,
    prepare_watchlist,
    watchlist_summary,
)


st.set_page_config(
    page_title="Investment OS 6.9",
    page_icon="📈",
    layout="wide",
)

DATA_FILE = Path("data/AI_portfolio.xlsx")
APP_VERSION = "6.9.0"
MINIMUM_TRADE_DKK = 5_000.0
SNAPSHOT_ONLY = os.getenv("INVESTMENT_OS_SNAPSHOT_ONLY") == "1"

TOOLTIPS = {
    "portfolio_value": (
        "Den samlede markedsværdi af alle positioner. Grundfos er medregnet "
        "i værdien, men ikke i porteføljevægte eller analyser."
    ),
    "total_return": (
        "Samlet gevinst eller tab i forhold til kostprisen for de aktive "
        "positioner."
    ),
    "portfolio_health": (
        "Et samlet mål for porteføljens momentum, relative styrke, risiko, "
        "stop-loss, diversifikation og datakvalitet."
    ),
    "confidence": (
        "Hvor sikkert modellen vurderer dagens signalbillede. Høj værdi "
        "betyder, at flere signaler peger i samme retning."
    ),
    "data_quality": (
        "Hvor komplet og pålideligt datagrundlaget er. Lav datakvalitet "
        "reducerer tilliden til anbefalingerne."
    ),
    "decision_score": (
        "Fælles score 0-100 fra Decision Engine baseret på momentum, AI "
        "Confidence, relativ styrke, trend, risiko, datakvalitet og plads "
        "under positionsloftet."
    ),
    "momentum": (
        "Måler kursudviklingen på tværs af flere perioder. Bruges til at "
        "identificere vedvarende styrke og svaghed."
    ),
    "relative_strength": (
        "Viser om aktivet klarer sig bedre eller dårligere end benchmark."
    ),
    "opportunity_score": (
        "Rangerer attraktiviteten ud fra momentum, AI Confidence, relativ "
        "styrke, trend, risiko, datakvalitet og plads under positionsloftet."
    ),
}


def compact_dkk(value: float) -> str:
    """Dansk heltalsformat uden valutaangivelse."""
    if pd.isna(value):
        return "N/A"
    return f"{float(value):,.0f}".replace(",", ".")


def percentage_points(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:+.1f} %-point"


def score_text(value: float, decimals: int = 0) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.{decimals}f}"


def no_scroll_height(dataframe: pd.DataFrame, row_px: int = 38) -> int:
    return max(100, (len(dataframe) + 1) * row_px + 4)


def quality_label(score: float) -> tuple[str, str]:
    if score >= 90:
        return "🟢", "Høj"
    if score >= 75:
        return "🟡", "Acceptabel"
    return "🔴", "Lav"


def conviction_label(score: float) -> str:
    if pd.isna(score):
        return "Ukendt"
    if score >= 85:
        return "Høj"
    if score >= 70:
        return "Middel"
    return "Lav"


def safe_optional_load(loader, fallback, label: str):
    try:
        return loader(), None
    except Exception as exc:
        return fallback, f"{label} kunne ikke indlæses: {exc}"


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(path: str):
    return load_master_file(path)


@st.cache_data(ttl=3600, show_spinner=True)
def load_market_data(tickers, currencies):
    snapshot = fetch_market_snapshot(tickers, currencies)
    fetched_at = datetime.now(ZoneInfo("Europe/Copenhagen"))
    return snapshot, fetched_at


@st.cache_data(ttl=3600, show_spinner=True)
def load_history(tickers, period):
    return fetch_price_history(tickers, period=period)


st.title("📈 Investment OS 6.9")

try:
    model = load_data(str(DATA_FILE))
except Exception as exc:
    st.error(f"Kunne ikke indlæse {DATA_FILE}: {exc}")
    st.stop()

raw = model.portfolio
tickers = (
    raw.loc[raw["Include_Analytics"].fillna(False), "Yahoo_Ticker"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)
currencies = raw["Currency"].dropna().astype(str).unique().tolist()

snapshot, data_updated_at = load_market_data(tickers, currencies)
st.caption(
    f"Version {APP_VERSION} · Data sidst opdateret: "
    f"{data_updated_at:%d-%m-%Y kl. %H:%M}"
)
portfolio = calculate_portfolio(model, snapshot)
base_config = load_investment_config(model.settings)

# Redigerbare modelindstillinger for den aktuelle Streamlit-session.
st.session_state.setdefault("model_benchmark", base_config.benchmark)
st.session_state.setdefault(
    "model_max_position_weight", float(base_config.max_position_weight)
)
st.session_state.setdefault(
    "model_max_sector_weight", float(base_config.max_sector_weight)
)
st.session_state.setdefault("model_minimum_trade_dkk", float(MINIMUM_TRADE_DKK))
st.session_state.setdefault("model_risk_free_rate", float(base_config.risk_free_rate))

# Redigeringsfelterne holdes adskilt fra de aktive modelværdier.
# Modellen ændres først, når brugeren vælger "Anvend modelændringer".
st.session_state.setdefault("draft_model_benchmark", st.session_state["model_benchmark"])
st.session_state.setdefault(
    "draft_model_max_position_weight",
    float(st.session_state["model_max_position_weight"]),
)
st.session_state.setdefault(
    "draft_model_max_sector_weight",
    float(st.session_state["model_max_sector_weight"]),
)
st.session_state.setdefault(
    "draft_model_minimum_trade_dkk",
    float(st.session_state["model_minimum_trade_dkk"]),
)
st.session_state.setdefault(
    "draft_model_risk_free_rate",
    float(st.session_state["model_risk_free_rate"]),
)

for period, default_value in base_config.momentum_weights.items():
    st.session_state.setdefault(f"momentum_weight_{period}", float(default_value))

raw_momentum_weights = {
    period: max(0.0, float(st.session_state[f"momentum_weight_{period}"]))
    for period in base_config.momentum_weights
}
momentum_total = sum(raw_momentum_weights.values())
momentum_session_weights = (
    {
        period: value / momentum_total
        for period, value in raw_momentum_weights.items()
    }
    if momentum_total > 0
    else base_config.momentum_weights.copy()
)

config = replace(
    base_config,
    benchmark=str(st.session_state["model_benchmark"]).strip() or base_config.benchmark,
    max_position_weight=float(st.session_state["model_max_position_weight"]),
    max_sector_weight=float(st.session_state["model_max_sector_weight"]),
    risk_free_rate=float(st.session_state["model_risk_free_rate"]),
    momentum_weights=momentum_session_weights,
)
MINIMUM_TRADE_DKK = float(st.session_state["model_minimum_trade_dkk"])

for factor, default_value in config.health_weights.items():
    key = f"health_weight_{factor}"
    st.session_state.setdefault(key, float(default_value))

health_factor_weights = {
    factor: float(st.session_state[f"health_weight_{factor}"])
    for factor in config.health_weights
}

for factor, default_value in DECISION_WEIGHTS.items():
    key = f"decision_weight_{factor}"
    st.session_state.setdefault(key, float(default_value))

decision_factor_weights = {
    factor: float(st.session_state[f"decision_weight_{factor}"])
    for factor in DECISION_WEIGHTS
}

momentum_weights = config.momentum_weights
benchmark_ticker = config.benchmark
history_tickers = sorted(set([*tickers, benchmark_ticker]))
history = load_history(history_tickers, "18mo")

analytics_portfolio = portfolio.loc[
    portfolio["Include_Analytics"].fillna(False)
].copy()

analytics_portfolio = add_momentum(
    analytics_portfolio,
    history,
    momentum_weights,
    benchmark_ticker=benchmark_ticker,
)
analytics_portfolio = apply_decision_engine(
    analytics_portfolio,
    factor_weights=decision_factor_weights,
    max_position_weight=config.max_position_weight,
).data

previous_history = history.iloc[:-1] if len(history) > 1 else history.iloc[0:0]
analysis_columns_to_remove = {
    "1W", "1M", "3M", "6M", "12M", "Volatility", "Max_Drawdown",
    "Relative_Strength_3M", "RS_Signal", "Composite",
    "Momentum_Data_Quality", "AI_Confidence", "Momentum_Acceleration",
    "Rotation_Signal", "Handling",
}
previous_source = analytics_portfolio[
    [c for c in analytics_portfolio.columns if c not in analysis_columns_to_remove]
].copy()

previous_analytics = (
    add_momentum(
        previous_source,
        previous_history,
        momentum_weights,
        benchmark_ticker=benchmark_ticker,
    )
    if not previous_history.empty
    else pd.DataFrame()
)
if not previous_analytics.empty:
    previous_analytics = apply_decision_engine(
        previous_analytics,
        factor_weights=decision_factor_weights,
        max_position_weight=config.max_position_weight,
    ).data

change_result = build_change_engine(analytics_portfolio, previous_analytics)

daily_returns = portfolio_returns(analytics_portfolio, history)
benchmark_prices = (
    history[benchmark_ticker].dropna()
    if benchmark_ticker in history.columns
    else pd.Series(dtype=float)
)
benchmark_returns = benchmark_prices.pct_change().dropna()

portfolio_return_12m = (
    float((1 + daily_returns.tail(252)).prod() - 1)
    if len(daily_returns) >= 20 else np.nan
)
benchmark_return_12m = (
    period_return(benchmark_prices, min(252, max(len(benchmark_prices) - 1, 0)))
    if len(benchmark_prices) > 1 else np.nan
)
relative_return_12m = (
    portfolio_return_12m - benchmark_return_12m
    if pd.notna(portfolio_return_12m) and pd.notna(benchmark_return_12m)
    else np.nan
)
portfolio_beta = beta(daily_returns, benchmark_returns)
sharpe_history = rolling_sharpe(
    daily_returns,
    risk_free_rate=config.risk_free_rate,
)
current_sharpe = (
    sharpe_history["Sharpe 252D"].dropna().iloc[-1]
    if "Sharpe 252D" in sharpe_history
    and not sharpe_history["Sharpe 252D"].dropna().empty
    else np.nan
)

quality_score, quality_notes = data_quality_score(portfolio, snapshot)
portfolio_metrics = portfolio_summary(portfolio)
portfolio_total = portfolio_metrics["Portfolio_Value_DKK"]
return_market_value = portfolio_metrics["Active_Market_Value_DKK"]
total_return = portfolio_metrics["Total_Return_Pct"]

decision = decision_summary(analytics_portfolio)
avg_confidence = decision["AI_Confidence"]

stop_loss_table = build_stop_loss_table(
    analytics_portfolio,
    history,
    lookback_days=63,
)
stop_loss_metrics = stop_loss_summary(stop_loss_table)

portfolio_health = calculate_portfolio_health(
    analytics_portfolio,
    stop_loss_metrics=stop_loss_metrics,
    data_quality_score=quality_score,
    max_position_weight=config.max_position_weight,
    factor_weights=health_factor_weights,
)

opportunity_result = build_opportunity_scores(
    analytics_portfolio,
    factor_weights=decision_factor_weights,
    max_position_weight=config.max_position_weight,
)

portfolio_doctor = build_portfolio_doctor(
    analytics_portfolio,
    active_market_value_dkk=return_market_value,
    stop_loss_metrics=stop_loss_metrics,
    data_quality_score=quality_score,
    max_position_weight=config.max_position_weight,
    factor_weights=health_factor_weights,
    current_health=portfolio_health.score,
    default_step=0.02,
    minimum_trade_dkk=MINIMUM_TRADE_DKK,
)

decision_queue = build_decision_queue(
    portfolio_doctor.data,
    opportunity_result.data,
    max_items=5,
)

rebalance_result = build_rebalance_plan(
    analytics_portfolio,
    active_market_value_dkk=return_market_value,
    max_position_weight=config.max_position_weight,
    minimum_trade_dkk=MINIMUM_TRADE_DKK,
)

snapshot_output = write_portfolio_snapshot(
    output_file="data/portfolio_snapshot.json",
    data_file=DATA_FILE,
    app_version=APP_VERSION,
    portfolio=portfolio,
    analytics_portfolio=analytics_portfolio,
    portfolio_metrics=portfolio_metrics,
    portfolio_health=portfolio_health,
    decision=decision,
    quality_score=quality_score,
    quality_notes=quality_notes,
    benchmark_ticker=benchmark_ticker,
    max_position_weight=config.max_position_weight,
    history=history,
    decision_queue=decision_queue,
    opportunity_result=opportunity_result,
    rebalance_result=rebalance_result,
    stop_loss_metrics=stop_loss_metrics,
)

if SNAPSHOT_ONLY:
    print(f"Snapshot skrevet til {snapshot_output}")
    raise SystemExit(0)


attribution = calculate_attribution(portfolio)
contributors = top_contributors(attribution, limit=5)
detractors = top_detractors(attribution, limit=5)

compounder_radar, compounder_error = safe_optional_load(
    lambda: load_compounder_radar("data"),
    None,
    "Emerging Compounder Radar",
)
compounder_summary = (
    radar_summary(compounder_radar)
    if compounder_radar is not None
    else {
        "Candidate_Count": 0,
        "High_Confidence_Count": 0,
        "Average_Confidence": np.nan,
        "Top_Candidate": None,
    }
)

watchlist_result, watchlist_error = safe_optional_load(
    lambda: prepare_watchlist(model.watchlist),
    None,
    "Watchlist",
)
watchlist_metrics = (
    watchlist_summary(watchlist_result)
    if watchlist_result is not None
    else {"Count": 0, "High_Confidence": 0, "Top_Candidate": None}
)

tabs = st.tabs([
    "🏠 Overblik",
    "📈 Momentum",
    "📋 Positioner",
    "🔄 Rebalancering",
    "💰 Kapitalflow",
    "🩺 Portfolio Doctor",
    "🎯 Opportunities",
    "🚀 Emerging Compounders",
    "👀 Watchlist",
    "⚙️ Settings",
])
(
    tab_overview, tab_momentum, tab_positions, tab_rebalance, tab_capital_flow,
    tab_doctor, tab_opportunity, tab_compounders, tab_watchlist, tab_settings,
) = tabs


with tab_overview:
    quality_icon, quality_text = quality_label(quality_score)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric(
        "Porteføljeværdi",
        compact_dkk(portfolio_total),
        help=TOOLTIPS["portfolio_value"],
    )
    k2.metric(
        "Samlet afkast",
        format_pct(total_return),
        help=TOOLTIPS["total_return"],
    )
    k3.metric(
        "Porteføljesundhed",
        score_text(portfolio_health.score, 0),
        help=TOOLTIPS["portfolio_health"],
    )
    k4.metric(
        "Konfidens",
        f"{avg_confidence:.0f}%" if pd.notna(avg_confidence) else "N/A",
        decision.get("AI_Confidence_Label"),
        help=TOOLTIPS["confidence"],
    )
    k5.metric(
        "Datakvalitet",
        f"{quality_score:.0f}%",
        f"{quality_icon} {quality_text}",
        help=TOOLTIPS["data_quality"],
    )

    st.divider()
    st.subheader("Næste anbefalede handling")
    st.caption(
        "Aktier og ETF'er vurderes separat, fordi de ligger på hver sin ASK. "
        "Derfor vises den højest prioriterede handling i hvert investeringsunivers."
    )

    # Overblik bruger en bredere kø end morgenbrief/snapshot, så både Aktie-
    # og ETF-universet får mulighed for at levere sin egen topanbefaling.
    overview_queue = build_decision_queue(
        portfolio_doctor.data,
        opportunity_result.data,
        max_items=max(20, len(analytics_portfolio)),
    ).data.copy()

    asset_type_lookup = (
        analytics_portfolio[["Name", "Asset_Type"]]
        .dropna(subset=["Name"])
        .drop_duplicates(subset=["Name"], keep="first")
        .set_index("Name")["Asset_Type"]
        .to_dict()
    )

    if not overview_queue.empty:
        overview_queue["Aktivklasse"] = overview_queue["Aktiv"].map(asset_type_lookup)
        overview_queue["Aktivklasse"] = overview_queue["Aktivklasse"].replace({
            "Stock": "Aktie",
            "Equity": "Aktie",
            "ETF": "ETF",
            "Fund": "ETF",
        })

    def render_recommended_action(
        source: pd.DataFrame,
        asset_class: str,
        heading: str,
    ) -> None:
        st.markdown(f"### {heading}")

        candidates = (
            source.loc[source["Aktivklasse"] == asset_class].copy()
            if not source.empty and "Aktivklasse" in source.columns
            else pd.DataFrame()
        )

        if candidates.empty:
            st.success("**Ingen ændringer anbefales.**")
            st.write(
                f"Ingen {heading.lower()} opfylder aktuelt modellens krav til "
                "signalstyrke, konfidens og minimumshandel."
            )
            return

        best = candidates.iloc[0]
        action = str(best.get("Handling", "Afvent"))
        asset = str(best.get("Aktiv", asset_class))
        amount = abs(float(best.get("Beløb DKK", 0) or 0))
        decision_score = pd.to_numeric(best.get("Decision Score"), errors="coerce")
        confidence = pd.to_numeric(best.get("Confidence"), errors="coerce")
        if pd.isna(confidence):
            confidence = avg_confidence

        action_text = f"{action} {asset}"
        if amount >= MINIMUM_TRADE_DKK:
            action_text += f" med ca. {compact_dkk(amount)}"

        st.markdown(f"## {action_text}")
        a1, a2, a3 = st.columns(3)
        a1.metric(
            "Status",
            str(best.get("Status", "Datamangel")),
            help="Den fælles status fra Decision Engine for denne investeringscase.",
        )
        a2.metric(
            "Konfidens",
            f"{confidence:.0f}%" if pd.notna(confidence) else "N/A",
            help=TOOLTIPS["confidence"],
        )
        a3.metric(
            "Prioritet",
            str(best.get("Prioritet", "Normal")),
            help="Viser hvor hurtigt handlingen bør vurderes.",
        )

        st.markdown("**Begrundelse**")
        st.write(
            best.get(
                "Begrundelse",
                "Ingen yderligere begrundelse tilgængelig.",
            )
        )

        with st.expander("Vis beslutningsdetaljer"):
            d1, d2 = st.columns(2)
            d1.metric(
                "Decision Score",
                score_text(decision_score, 0),
                help=TOOLTIPS["decision_score"],
            )
            d2.metric(
                "Anbefalet vægtændring",
                percentage_points(best.get("Anbefalet ændring", np.nan)),
            )

    stock_col, etf_col = st.columns(2, gap="large")
    with stock_col:
        render_recommended_action(overview_queue, "Aktie", "Aktie")
    with etf_col:
        render_recommended_action(overview_queue, "ETF", "ETF")

    # Bevar den eksisterende korte decision queue til tabellen nedenfor.
    queue = decision_queue.data.copy()

    st.markdown("### Øvrige prioriterede handlinger")
    queue_overview = queue.head(3).copy()
    if queue_overview.empty:
        st.caption("Ingen yderligere handlinger.")
    else:
        action_table = queue_overview[
            ["Prioritet", "Handling", "Aktiv", "Beløb DKK", "Decision Score", "Begrundelse"]
        ].copy()
        action_table["Beløb DKK"] = action_table["Beløb DKK"].apply(compact_dkk)
        action_table["Decision Score"] = action_table["Decision Score"].apply(
            lambda value: score_text(value, 0)
        )
        action_table = action_table.rename(
            columns={"Beløb DKK": "Beløb", "Decision Score": "Score"}
        )
        st.dataframe(
            table_style(action_table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(action_table),
        )

    st.markdown("### Ændringer siden seneste handelsdag")
    if change_result.data.empty:
        st.caption("Der er ikke tilstrækkelige data til at beregne ændringer.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Forbedringer**")
            improvements = change_result.improvements[["Name", "Change Score"]].head(3).copy()
            improvements.columns = ["Aktiv", "Ændring"]
            improvements["Ændring"] = improvements["Ændring"].apply(
                lambda value: f"{value:+.1f}" if pd.notna(value) else "N/A"
            )
            if improvements.empty:
                st.caption("Ingen tydelige forbedringer.")
            else:
                st.dataframe(
                    table_style(improvements), use_container_width=True,
                    hide_index=True, height=no_scroll_height(improvements),
                )
        with c2:
            st.markdown("**Forværringer**")
            deteriorations = change_result.deteriorations[
                ["Name", "Change Score"]
            ].head(3).copy()
            deteriorations.columns = ["Aktiv", "Ændring"]
            deteriorations["Ændring"] = deteriorations["Ændring"].apply(
                lambda value: f"{value:+.1f}" if pd.notna(value) else "N/A"
            )
            if deteriorations.empty:
                st.caption("Ingen tydelige forværringer.")
            else:
                st.dataframe(
                    table_style(deteriorations), use_container_width=True,
                    hide_index=True, height=no_scroll_height(deteriorations),
                )
        with c3:
            st.markdown("**Nye signaler**")
            signals = change_result.signal_changes.head(3).copy()
            if signals.empty:
                st.caption("Ingen ændrede signaler.")
            else:
                signals["Signal"] = signals.apply(
                    lambda row: row.get("Signal Change")
                    if str(row.get("Signal Change", "")).strip()
                    else row.get("Rotation Change", ""),
                    axis=1,
                )
                signals = signals[["Name", "Signal"]]
                signals.columns = ["Aktiv", "Signal"]
                st.dataframe(
                    table_style(signals), use_container_width=True,
                    hide_index=True, height=no_scroll_height(signals),
                )

    st.markdown("### Kræver opmærksomhed")
    attention_rows = []

    if not stop_loss_table.empty:
        critical_stops = stop_loss_table.loc[
            stop_loss_table["Risikohandling"].isin(
                ["Stop brudt", "Alarmniveau", "Stram stop"]
            )
        ]
        for _, row in critical_stops.head(5).iterrows():
            attention_rows.append({
                "Prioritet": "Høj" if row.get("Risikohandling") == "Stop brudt" else "Normal",
                "Aktiv": row.get("Aktiv", "Ukendt"),
                "Årsag": row.get("Risikohandling", "Stop-loss"),
                "Næste skridt": "Kontrollér position og stopniveau",
            })

    weights = pd.to_numeric(
        analytics_portfolio["Portfolio_Weight"], errors="coerce"
    )
    overweight = analytics_portfolio.loc[weights > config.max_position_weight]
    for _, row in overweight.head(5).iterrows():
        attention_rows.append({
            "Prioritet": "Normal",
            "Aktiv": row.get("Name", "Ukendt"),
            "Årsag": (
                f"Vægt {row.get('Portfolio_Weight', 0):.1%} "
                f"over loft {config.max_position_weight:.0%}"
            ),
            "Næste skridt": "Vurder reduktion",
        })

    for note in quality_notes[:3]:
        attention_rows.append({
            "Prioritet": "Høj",
            "Aktiv": "System",
            "Årsag": note,
            "Næste skridt": "Kontrollér datakilden",
        })

    attention_table = pd.DataFrame(attention_rows)
    if attention_table.empty:
        st.success("Ingen forhold kræver opmærksomhed.")
    else:
        st.dataframe(
            table_style(attention_table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(attention_table),
        )

    with st.expander("Vis porteføljegrafer og performance"):
        left, right = st.columns(2)
        with left:
            st.markdown("#### Porteføljeudvikling")
            if not daily_returns.empty:
                portfolio_curve = (1 + daily_returns).cumprod() * 100
                comparison = portfolio_curve.rename("Portefølje").to_frame()
                if not benchmark_returns.empty:
                    benchmark_curve = (1 + benchmark_returns).cumprod() * 100
                    comparison = comparison.join(
                        benchmark_curve.rename(benchmark_ticker), how="inner"
                    )
                curve_df = (
                    comparison.reset_index()
                    .rename(columns={comparison.index.name or "index": "Dato"})
                    .melt(id_vars="Dato", var_name="Serie", value_name="Indeks")
                )
                fig = px.line(
                    curve_df, x="Dato", y="Indeks", color="Serie",
                    title=f"Portefølje vs. {benchmark_ticker} – indeks 100",
                )
                fig.update_layout(height=390, yaxis_title="Indeks")
                st.plotly_chart(fig, use_container_width=True)
                p1, p2, p3 = st.columns(3)
                p1.metric("Relativt afkast 12M", format_pct(relative_return_12m))
                p2.metric(f"{benchmark_ticker} 12M", format_pct(benchmark_return_12m))
                p3.metric("Beta", format_score(portfolio_beta, 2))
            else:
                st.info("Porteføljeudviklingen kan ikke vises endnu.")

        with right:
            st.markdown("#### Sharpe-udvikling")
            if not sharpe_history.empty:
                sharpe_long = (
                    sharpe_history.reset_index()
                    .rename(columns={sharpe_history.index.name or "index": "Dato"})
                    .melt(id_vars="Dato", var_name="Periode", value_name="Sharpe")
                    .dropna()
                )
                fig = px.line(
                    sharpe_long, x="Dato", y="Sharpe", color="Periode",
                    title="Rullende Sharpe",
                )
                fig.add_hline(y=1.0, line_dash="dash")
                fig.update_layout(height=390)
                st.plotly_chart(fig, use_container_width=True)
                st.metric("Sharpe 12M", format_score(current_sharpe, 2))
            else:
                st.info("Sharpe-historikken kan ikke vises endnu.")

        st.markdown("#### Performance attribution")

        def attribution_table(dataframe: pd.DataFrame) -> pd.DataFrame:
            table = dataframe.copy()
            if table.empty:
                return table
            table["Vægt"] = table["Vægt"].apply(lambda x: format_pct(x, 1))
            table["Afkast DKK"] = table["Afkast DKK"].apply(compact_dkk)
            table["Afkast %"] = table["Afkast %"].apply(lambda x: format_pct(x, 1))
            table["Bidrag"] = table["Bidrag"].apply(lambda x: format_pct(x, 1))
            return table[["Aktiv", "Vægt", "Afkast DKK", "Afkast %", "Bidrag"]].rename(
                columns={"Afkast DKK": "Afkast"}
            )

        a1, a2 = st.columns(2)
        with a1:
            st.markdown("**Største bidrag**")
            table = attribution_table(contributors)
            if table.empty:
                st.caption("Ingen positive bidrag.")
            else:
                st.dataframe(
                    table_style(table), use_container_width=True,
                    hide_index=True, height=no_scroll_height(table),
                )
        with a2:
            st.markdown("**Største negative bidrag**")
            table = attribution_table(detractors)
            if table.empty:
                st.caption("Ingen negative bidrag.")
            else:
                st.dataframe(
                    table_style(table), use_container_width=True,
                    hide_index=True, height=no_scroll_height(table),
                )


with tab_momentum:
    st.subheader("Momentum")
    st.caption(
        "Aktier og ETF'er vises separat, fordi de ligger på hver sin ASK og "
        "derfor skal vurderes som to selvstændige investeringsuniverser."
    )

    momentum_source = analytics_portfolio[
        [
            "Asset_Type", "Name", "1W", "1M", "3M", "6M", "12M",
            "Composite", "Momentum_Acceleration", "Relative_Strength_3M",
            "AI_Confidence", "Decision_Score", "Decision_Status", "Handling",
        ]
    ].copy()

    momentum_source["Aktivklasse"] = momentum_source["Asset_Type"].replace({
        "Stock": "Aktie",
        "Equity": "Aktie",
        "Fund": "ETF",
        "ETF": "ETF",
    })

    def show_momentum_section(
        source: pd.DataFrame,
        asset_class: str,
        heading: str,
    ) -> None:
        section = source.loc[source["Aktivklasse"] == asset_class].copy()

        st.markdown(f"### {heading}")

        if section.empty:
            st.info(f"Ingen {heading.lower()} indgår aktuelt i momentum-analysen.")
            return

        section = section.sort_values(
            ["Composite", "Name"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)

        # Behold numeriske værdier til grafen, før tabellen formateres.
        chart_data = section[["Name", "Composite"]].copy()
        chart_data["Composite"] = pd.to_numeric(
            chart_data["Composite"], errors="coerce"
        )
        chart_data = chart_data.dropna(subset=["Composite"])

        table = section[
            [
                "Name", "1W", "1M", "3M", "6M", "12M", "Composite",
                "Momentum_Acceleration", "Relative_Strength_3M",
                "AI_Confidence", "Decision_Score", "Decision_Status", "Handling",
            ]
        ].copy()

        table = table.rename(columns={
            "Name": "Navn",
            "Composite": "Momentum",
            "Momentum_Acceleration": "Acceleration",
            "Relative_Strength_3M": "RS 3M",
            "AI_Confidence": "AI",
            "Decision_Score": "Score",
            "Decision_Status": "Status",
        })
        for col in [
            "1W", "1M", "3M", "6M", "12M",
            "Momentum", "Acceleration", "RS 3M",
        ]:
            table[col] = table[col].apply(lambda x: format_pct(x, 1))

        table["AI"] = table["AI"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
        )
        table["Score"] = table["Score"].apply(lambda x: score_text(x, 0))

        st.dataframe(
            table_style(table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(table),
        )

        st.markdown(f"#### Samlet momentum pr. {asset_class.lower()}")
        if chart_data.empty:
            st.info("Der er ikke tilstrækkelige data til momentumgrafen.")
        else:
            chart_data = chart_data.rename(
                columns={"Name": "Navn", "Composite": "Momentum"}
            )
            fig = px.bar(
                chart_data,
                x="Navn",
                y="Momentum",
                title=f"Samlet momentum – {heading}",
                text_auto=".1%",
            )
            fig.update_layout(
                height=max(390, min(700, 300 + len(chart_data) * 18)),
                xaxis_title=None,
                yaxis_title="Samlet momentum",
                yaxis_tickformat=".0%",
                showlegend=False,
            )
            fig.update_xaxes(
                categoryorder="array",
                categoryarray=chart_data["Navn"].tolist(),
                tickangle=-45 if len(chart_data) > 8 else 0,
            )
            fig.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig, use_container_width=True)

    show_momentum_section(momentum_source, "Aktie", "Aktier")

    st.divider()

    show_momentum_section(momentum_source, "ETF", "ETF'er")

    st.caption(
        "Grundfos kan vises i positionsoversigten, men indgår ikke i momentum, "
        "aktiv vægtning eller rebalancering."
    )


with tab_capital_flow:
    st.subheader("Kapitalflow – sektorrotation")
    st.caption(
        "Måler kortsigtet kapitalrotation mellem porteføljens ETF'er. "
        "1W vægtes højest, så nye bevægelser opdages tidligere."
    )

    capital_flow = analytics_portfolio.loc[
        analytics_portfolio["Asset_Type"].isin(["ETF", "Fund"]),
        ["Name", "Portfolio_Weight", "1W", "1M", "3M", "Rotation_Signal"],
    ].copy()

    if capital_flow.empty:
        st.info("Ingen ETF'er med tilstrækkelige data til kapitalflow-analysen.")
    else:
        for column in ["Portfolio_Weight", "1W", "1M", "3M"]:
            capital_flow[column] = pd.to_numeric(capital_flow[column], errors="coerce")

        capital_flow["Flow råscore"] = (
            capital_flow["1W"].fillna(0) * 0.50
            + capital_flow["1M"].fillna(0) * 0.30
            + capital_flow["3M"].fillna(0) * 0.20
        )
        capital_flow["Kapitalflow Score"] = (
            capital_flow["Flow råscore"].rank(pct=True, method="average") * 100
        )
        capital_flow["Kapitalflow Signal"] = pd.cut(
            capital_flow["Kapitalflow Score"],
            bins=[-np.inf, 25, 45, 55, 75, np.inf],
            labels=[
                "Stærkt udflow", "Udflow", "Neutral", "Indflow", "Stærkt indflow"
            ],
            include_lowest=True,
        ).astype(str)

        capital_flow = capital_flow.sort_values(
            ["Kapitalflow Score", "Name"],
            ascending=[False, True],
        ).reset_index(drop=True)

        k1, k2, k3 = st.columns(3)
        leader = capital_flow.iloc[0]
        k1.metric("Stærkeste kapitalflow", str(leader["Name"]))
        k2.metric("Flow-score", f"{leader['Kapitalflow Score']:.0f}/100")
        k3.metric(
            "Positive flows",
            int(capital_flow["Kapitalflow Signal"].isin(["Indflow", "Stærkt indflow"]).sum()),
        )

        display = capital_flow[
            [
                "Name", "Portfolio_Weight", "1W", "1M", "3M",
                "Rotation_Signal", "Kapitalflow Score", "Kapitalflow Signal",
            ]
        ].copy()
        display.columns = [
            "ETF", "Vægt", "1W", "1M", "3M", "Rotationssignal",
            "Kapitalflow-score", "Kapitalflow-signal",
        ]
        display["Vægt"] = display["Vægt"].apply(lambda x: format_pct(x, 1))
        for column in ["1W", "1M", "3M"]:
            display[column] = display[column].apply(lambda x: format_pct(x, 1))
        display["Kapitalflow-score"] = display["Kapitalflow-score"].apply(
            lambda x: f"{x:.0f}/100" if pd.notna(x) else "N/A"
        )

        st.dataframe(
            table_style(display),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(display),
        )

        st.markdown("### Kapitalflow-score pr. ETF")
        chart_data = capital_flow[["Name", "Kapitalflow Score"]].rename(
            columns={"Name": "ETF", "Kapitalflow Score": "Score"}
        )
        fig = px.bar(
            chart_data,
            x="ETF",
            y="Score",
            title="Relativ kapitalrotation mellem ETF'er",
            text_auto=".0f",
        )
        fig.update_layout(
            height=max(390, min(700, 300 + len(chart_data) * 18)),
            xaxis_title=None,
            yaxis_title="Kapitalflow-score",
            yaxis_range=[0, 100],
            showlegend=False,
        )
        fig.update_xaxes(tickangle=-45 if len(chart_data) > 8 else 0)
        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Scoren er relativ inden for ETF-universet og bygger på 50% 1W, "
            "30% 1M og 20% 3M. Den viser rotation – ikke faktisk fondskapital."
        )

with tab_positions:
    st.subheader("Positioner")
    st.caption(
        "Aktier og ETF'er vises separat, men vægten beregnes for begge tabeller "
        "mod den samlede porteføljeværdi ekskl. Grundfos. Grundfos vises uden vægt."
    )

    merge_key = (
        "Asset_ID"
        if "Asset_ID" in portfolio.columns and "Asset_ID" in analytics_portfolio.columns
        else "Yahoo_Ticker"
    )
    analysis_lookup = analytics_portfolio[
        [merge_key, "Composite", "AI_Confidence"]
    ].drop_duplicates(subset=[merge_key])
    position_source = portfolio.merge(
        analysis_lookup, on=merge_key, how="left", suffixes=("", "_analysis")
    )

    if "Sector" not in position_source.columns:
        position_source["Sector"] = "Ikke angivet"
    position_source["Sector"] = (
        position_source["Sector"].fillna("Ikke angivet").astype(str)
    )
    position_source["Aktivklasse"] = position_source["Asset_Type"].replace({
        "Stock": "Aktie",
        "Equity": "Aktie",
        "Fund": "ETF",
        "ETF": "ETF",
    })

    # Alle viste positionsvægte bruger samme nævner: hele porteføljen ekskl. Grundfos.
    position_source["Market_Value_DKK"] = pd.to_numeric(
        position_source["Market_Value_DKK"], errors="coerce"
    ).fillna(0)
    grundfos_portfolio_mask = position_source["Name"].astype(str).str.contains(
        "Grundfos", case=False, na=False
    )
    portfolio_value_ex_grundfos = position_source.loc[
        ~grundfos_portfolio_mask, "Market_Value_DKK"
    ].sum()

    def show_position_section(
        source: pd.DataFrame,
        asset_class: str,
        heading: str,
    ) -> None:
        section = source.loc[source["Aktivklasse"] == asset_class].copy()
        st.markdown(f"### {heading}")

        if section.empty:
            st.info(f"Ingen {heading.lower()} er registreret.")
            return

        grundfos_mask = section["Name"].astype(str).str.contains(
            "Grundfos", case=False, na=False
        )
        section["Portfolio_Weight_Ex_Grundfos"] = np.where(
            ~grundfos_mask & (portfolio_value_ex_grundfos > 0),
            section["Market_Value_DKK"] / portfolio_value_ex_grundfos,
            np.nan,
        )
        section = section.sort_values(
            ["Portfolio_Weight_Ex_Grundfos", "Name"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)

        table = section[
            [
                "Name", "Quantity", "Purchase_Price", "Current_Price", "Sector",
                "Market_Value_DKK", "Portfolio_Weight_Ex_Grundfos", "Return_Pct", "Composite",
                "AI_Confidence",
            ]
        ].copy()
        table.columns = [
            "Navn", "Antal", "Åben kurs", "Dags kurs", "Sektor",
            "Markedsværdi", "Vægt", "Afkast", "Momentum", "AI",
        ]

        table["Antal"] = table["Antal"].apply(
            lambda x: compact_dkk(x) if pd.notna(x) else "N/A"
        )
        for col in ["Åben kurs", "Dags kurs"]:
            table[col] = table[col].apply(
                lambda x: compact_dkk(x) if pd.notna(x) else "N/A"
            )
        table["Markedsværdi"] = table["Markedsværdi"].apply(compact_dkk)
        table["Vægt"] = table["Vægt"].apply(
            lambda x: format_pct(x, 1) if pd.notna(x) else "-"
        )
        table["Afkast"] = table["Afkast"].apply(lambda x: format_pct(x, 1))
        table["Momentum"] = table["Momentum"].apply(lambda x: format_pct(x, 1))
        table["AI"] = table["AI"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
        )

        st.dataframe(
            table_style(table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(table),
        )

        chart_data = section.loc[
            section["Portfolio_Weight_Ex_Grundfos"].notna(),
            ["Name", "Portfolio_Weight_Ex_Grundfos"],
        ].copy()
        st.markdown(f"#### Vægtning pr. {asset_class.lower()}")
        if chart_data.empty:
            st.info("Der er ikke tilstrækkelige data til vægtningsgrafen.")
        else:
            chart_data = chart_data.rename(
                columns={"Name": "Navn", "Portfolio_Weight_Ex_Grundfos": "Vægt"}
            )
            fig = px.bar(
                chart_data,
                x="Navn",
                y="Vægt",
                title=f"Vægtning – {heading}",
                text_auto=".1%",
            )
            fig.update_layout(
                height=max(390, min(700, 300 + len(chart_data) * 18)),
                xaxis_title=None,
                yaxis_title="Vægt af portefølje ekskl. Grundfos",
                yaxis_tickformat=".0%",
                showlegend=False,
            )
            fig.update_xaxes(
                categoryorder="array",
                categoryarray=chart_data["Navn"].tolist(),
                tickangle=-45 if len(chart_data) > 8 else 0,
            )
            st.plotly_chart(fig, use_container_width=True)

        if asset_class == "Aktie":
            sector_data = section.loc[
                section["Portfolio_Weight_Ex_Grundfos"].notna(),
                ["Sector", "Market_Value_DKK"],
            ].copy()
            sector_data["Market_Value_DKK"] = pd.to_numeric(
                sector_data["Market_Value_DKK"], errors="coerce"
            ).fillna(0)
            sector_data = (
                sector_data.groupby("Sector", as_index=False)["Market_Value_DKK"]
                .sum()
                .loc[lambda df: df["Market_Value_DKK"] > 0]
                .sort_values("Market_Value_DKK", ascending=False)
            )

            st.markdown("#### Sektorfordeling – aktier")
            if sector_data.empty:
                st.info("Der er ikke tilstrækkelige sektordata.")
            else:
                sector_data = sector_data.rename(
                    columns={"Sector": "Sektor", "Market_Value_DKK": "Markedsværdi"}
                )
                fig = px.pie(
                    sector_data,
                    names="Sektor",
                    values="Markedsværdi",
                    title="Sektorfordeling – aktie-ASK",
                    hole=0.35,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

    show_position_section(position_source, "Aktie", "Aktier")

    st.divider()

    show_position_section(position_source, "ETF", "ETF'er")

    st.divider()
    st.markdown("### Samlet vægtning – hele porteføljen")
    st.caption(
        "Alle aktier og ETF'er anvender samme nævner: samlet porteføljeværdi "
        "ekskl. Grundfos. Derfor summerer de viste vægte til 100%."
    )

    overall_weights = position_source.loc[
        ~grundfos_portfolio_mask
        & position_source["Aktivklasse"].isin(["Aktie", "ETF"])
        & (position_source["Market_Value_DKK"] > 0),
        ["Name", "Aktivklasse", "Market_Value_DKK"],
    ].copy()

    if overall_weights.empty or portfolio_value_ex_grundfos <= 0:
        st.info("Der er ikke tilstrækkelige data til den samlede vægtning.")
    else:
        overall_weights["Vægt"] = (
            overall_weights["Market_Value_DKK"] / portfolio_value_ex_grundfos
        )
        overall_weights = overall_weights.sort_values(
            ["Vægt", "Name"], ascending=[False, True]
        ).reset_index(drop=True)

        stock_weight = overall_weights.loc[
            overall_weights["Aktivklasse"] == "Aktie", "Vægt"
        ].sum()
        etf_weight = overall_weights.loc[
            overall_weights["Aktivklasse"] == "ETF", "Vægt"
        ].sum()
        total_weight = overall_weights["Vægt"].sum()

        w1, w2, w3 = st.columns(3)
        w1.metric("Aktier", format_pct(stock_weight, 1))
        w2.metric("ETF'er", format_pct(etf_weight, 1))
        w3.metric("Samlet", format_pct(total_weight, 1))

        overall_chart = overall_weights.rename(columns={"Name": "Navn"})
        fig = px.bar(
            overall_chart,
            x="Navn",
            y="Vægt",
            color="Aktivklasse",
            title="Samlet positionsvægt – portefølje ekskl. Grundfos",
            text_auto=".1%",
        )
        fig.update_layout(
            height=max(430, min(760, 320 + len(overall_chart) * 18)),
            xaxis_title=None,
            yaxis_title="Vægt af samlet portefølje",
            yaxis_tickformat=".0%",
            legend_title_text="Aktivklasse",
        )
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=overall_chart["Navn"].tolist(),
            tickangle=-45 if len(overall_chart) > 8 else 0,
        )
        st.plotly_chart(fig, use_container_width=True)


with tab_rebalance:
    st.subheader("Rebalancering")
    st.caption(
        "Aktier og ETF'er vurderes separat, fordi de ligger på hver sin ASK. "
        "Hver tabel viser nuværende vægt, foreslået allokering og risikostatus."
    )

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Øg-signaler", rebalance_result.increase_count)
    r2.metric("Reducer-signaler", rebalance_result.reduce_count)
    r3.metric("Foreslåede handler", rebalance_result.trade_count)
    r4.metric("Brutto handel", compact_dkk(rebalance_result.gross_trade_dkk))

    rebalance = rebalance_result.data.copy()

    if rebalance.empty:
        st.success("Ingen rebalancering anbefales.")
    else:
        asset_type_lookup = analytics_portfolio[["Name", "Asset_Type"]].drop_duplicates(
            subset=["Name"]
        )
        rebalance = rebalance.merge(
            asset_type_lookup,
            left_on="Aktiv",
            right_on="Name",
            how="left",
        ).drop(columns=["Name"], errors="ignore")
        rebalance["Aktivklasse"] = rebalance["Asset_Type"].replace({
            "Stock": "Aktie",
            "Equity": "Aktie",
            "Fund": "ETF",
            "ETF": "ETF",
        })

        risk_lookup = (
            stop_loss_table[["Aktiv", "Risikohandling"]]
            .drop_duplicates(subset=["Aktiv"])
            if not stop_loss_table.empty
            else pd.DataFrame(columns=["Aktiv", "Risikohandling"])
        )
        rebalance = rebalance.merge(risk_lookup, on="Aktiv", how="left")
        rebalance["Risiko"] = rebalance["Risikohandling"].fillna("Ikke vurderet")

        def show_rebalance_section(
            source: pd.DataFrame,
            asset_class: str,
            heading: str,
        ) -> None:
            section = source.loc[source["Aktivklasse"] == asset_class].copy()
            st.markdown(f"### {heading}")

            if section.empty:
                st.info(f"Ingen {heading.lower()} indgår aktuelt i rebalanceringen.")
                return

            section = section.sort_values(
                ["Foreslået vægt", "Aktiv"],
                ascending=[False, True],
                na_position="last",
            ).reset_index(drop=True)

            chart_data = section[
                ["Aktiv", "Nuværende vægt", "Foreslået vægt"]
            ].copy()

            display = section[
                [
                    "Aktiv", "Nuværende vægt", "Foreslået vægt", "Ændring",
                    "Risiko", "Composite", "AI", "Decision Score", "Status", "Handling",
                ]
            ].copy()

            for col in ["Nuværende vægt", "Foreslået vægt", "Ændring", "Composite"]:
                display[col] = display[col].apply(lambda x: format_pct(x, 1))
            display["AI"] = display["AI"].apply(
                lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
            )
            display["Decision Score"] = display["Decision Score"].apply(
                lambda x: score_text(x, 0)
            )
            display = display.rename(columns={"Composite": "Momentum"})

            st.dataframe(
                table_style(display),
                use_container_width=True,
                hide_index=True,
                height=no_scroll_height(display),
            )

            st.markdown("#### Nuværende vægt vs. foreslået allokering")
            chart_long = chart_data.melt(
                id_vars="Aktiv",
                value_vars=["Nuværende vægt", "Foreslået vægt"],
                var_name="Allokering",
                value_name="Vægt",
            )
            fig = px.bar(
                chart_long,
                x="Aktiv",
                y="Vægt",
                color="Allokering",
                barmode="group",
                title=f"Nuværende vægt vs. foreslået allokering – {heading}",
                text_auto=".1%",
            )
            fig.update_layout(
                height=max(390, min(700, 300 + len(section) * 18)),
                xaxis_title=None,
                yaxis_title="Vægt",
                yaxis_tickformat=".0%",
                legend_title_text=None,
            )
            fig.update_xaxes(tickangle=-45 if len(section) > 8 else 0)
            st.plotly_chart(fig, use_container_width=True)

        show_rebalance_section(rebalance, "Aktie", "Aktier")

        st.divider()

        show_rebalance_section(rebalance, "ETF", "ETF'er")

    st.caption(
        f"Positionsloft {config.max_position_weight:.0%}. Handler under "
        f"{compact_dkk(MINIMUM_TRADE_DKK)} filtreres som støj."
    )

    with st.expander("Vis stop-loss og alarmniveauer"):
        s1, s2, s3 = st.columns(3)
        s1.metric("Stop brudt", stop_loss_metrics["Stop_Broken"])
        s2.metric("Alarmniveau", stop_loss_metrics["Alarm"])
        s3.metric("Stram stop", stop_loss_metrics["Tighten"])

        if stop_loss_table.empty:
            st.info("Ingen stop-loss-data.")
        else:
            stop_display = stop_loss_table.copy()
            for col in ["Kurs", "3M høj", "Stopkurs", "Alarmkurs"]:
                stop_display[col] = stop_display[col].apply(
                    lambda x: format_score(x, 2) if pd.notna(x) else "N/A"
                )
            for col in ["Stopafstand", "Afstand til stop"]:
                stop_display[col] = stop_display[col].apply(
                    lambda x: format_pct(x, 1)
                )
            stop_display = stop_display[
                [
                    "Aktiv", "Kurs", "3M høj", "Stopafstand", "Stopkurs",
                    "Alarmkurs", "Afstand til stop", "Modelhandling",
                    "Risikohandling",
                ]
            ]
            st.dataframe(
                table_style(stop_display), use_container_width=True,
                hide_index=True, height=no_scroll_height(stop_display),
            )


with tab_doctor:
    st.subheader("Portfolio Doctor")
    st.caption(
        "Tester moderate vægtændringer og viser, om de forbedrer den aktuelle "
        "Portfolio Health-model. Resultatet er beslutningsstøtte, ikke en ordre."
    )

    d1, d2, d3 = st.columns(3)
    d1.metric(
        "Porteføljesundhed nu",
        score_text(portfolio_doctor.current_health, 1),
        help=TOOLTIPS["portfolio_health"],
    )
    d2.metric(
        "Bedste simulation",
        score_text(portfolio_doctor.best_simulated_health, 1),
    )
    d3.metric("Handlingsforslag", portfolio_doctor.actionable_count)

    doctor_data = portfolio_doctor.data.copy()
    if doctor_data.empty:
        st.success("Ingen ændringer opfylder de aktuelle krav.")
    else:
        display = doctor_data[
            [
                "Aktiv", "Handling", "Anbefalet ændring", "Beløb DKK",
                "Health effekt", "Confidence", "Prioritet", "Begrundelse",
            ]
        ].copy()
        display["Anbefalet ændring"] = display["Anbefalet ændring"].apply(
            percentage_points
        )
        display["Beløb DKK"] = display["Beløb DKK"].apply(compact_dkk)
        display["Health effekt"] = display["Health effekt"].apply(
            lambda x: score_text(x, 1)
        )
        display["Confidence"] = display["Confidence"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
        )
        display = display.rename(columns={"Beløb DKK": "Beløb"})
        st.dataframe(
            table_style(display), use_container_width=True,
            hide_index=True, height=no_scroll_height(display),
        )

        with st.expander("Vis modeldetaljer"):
            detail = doctor_data[
                ["Aktiv", "Health før", "Health efter", "Health effekt"]
            ].copy()
            st.dataframe(
                table_style(detail), use_container_width=True, hide_index=True
            )


with tab_opportunity:
    st.subheader("Opportunities")
    st.caption(
        "Viser kun kandidater med status Stærk eller Meget stærk. "
        "Svagere signaler skjules som irrelevant støj."
    )

    opportunity_data = opportunity_result.data.copy()
    strong_statuses = {"Stærk", "Meget stærk"}
    if "Decision_Status" in opportunity_data.columns:
        opportunity_data = opportunity_data.loc[
            opportunity_data["Decision_Status"].isin(strong_statuses)
        ].copy()
    else:
        opportunity_data = opportunity_data.iloc[0:0].copy()

    opportunity_data = opportunity_data.sort_values(
        ["Decision_Score", "Name"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)

    o1, o2 = st.columns(2)
    if opportunity_data.empty:
        o1.metric("Bedste mulighed", "Ingen")
        o2.metric("Stærke kandidater", 0)
        st.info("Ingen kandidater har aktuelt status Stærk eller Meget stærk.")
    else:
        best_opportunity = opportunity_data.iloc[0]
        o1.metric(
            "Bedste mulighed",
            str(best_opportunity.get("Name", "N/A")),
            (
                f"{float(best_opportunity['Decision_Score']):.0f}/100"
                if pd.notna(best_opportunity.get("Decision_Score")) else None
            ),
            help=TOOLTIPS["opportunity_score"],
        )
        o2.metric("Stærke kandidater", len(opportunity_data))

        summary = opportunity_data[
            [
                "Decision Rank", "Name", "Handling",
                "Decision_Score", "Decision_Status",
            ]
        ].copy()
        summary.columns = ["Rank", "Aktiv", "Handling", "Score", "Status"]
        summary["Score"] = summary["Score"].apply(lambda x: score_text(x, 0))
        st.dataframe(
            table_style(summary), use_container_width=True,
            hide_index=True, height=no_scroll_height(summary),
        )

        with st.expander("Vis scorekomponenter"):
            details = opportunity_data[
                [
                    "Name", "Momentum Score", "AI Score", "RS Score",
                    "Trend Score", "Risk Score", "Data Score", "Position Score",
                ]
            ].copy()
            details.columns = [
                "Aktiv", "Momentum", "AI", "RS", "Trend",
                "Risiko", "Data", "Positionsbonus",
            ]
            for col in details.columns[1:]:
                details[col] = details[col].apply(lambda x: score_text(x, 0))
            st.dataframe(
                table_style(details), use_container_width=True,
                hide_index=True, height=no_scroll_height(details),
            )


with tab_compounders:
    st.subheader("Emerging Compounders")

    if compounder_error:
        st.warning(compounder_error)
    elif compounder_radar is None or not compounder_radar.exists:
        st.info(
            "Radarfilen mangler. Læg ugens resultat i "
            "`data/compounder_radar.xlsx` eller `data/compounder_radar.csv`."
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kandidater", compounder_summary["Candidate_Count"])
        c2.metric("AI ≥ 80%", compounder_summary["High_Confidence_Count"])
        c3.metric(
            "Gns. konfidens",
            (
                f"{compounder_summary['Average_Confidence']:.0f}%"
                if pd.notna(compounder_summary["Average_Confidence"]) else "N/A"
            ),
        )
        c4.metric("Topkandidat", compounder_summary["Top_Candidate"] or "N/A")

        for note in compounder_radar.notes:
            st.warning(note)

        radar = top_candidates(compounder_radar, limit=20)
        if radar.empty:
            st.info("Ingen kandidater.")
        else:
            radar = radar.rename(columns={
                "Name": "Selskab", "Composite_Score": "Composite",
                "AI_Confidence": "AI Confidence",
                "Revenue_CAGR_5Y": "Omsætning CAGR 5Y",
                "EPS_CAGR_5Y": "EPS CAGR 5Y",
                "Gross_Margin": "Bruttomargin", "Upside_Pct": "Upside",
                "Risk_Reward": "Risk/Reward", "Risk": "Risiko",
                "Reason": "Begrundelse",
            })
            st.dataframe(
                table_style(radar), use_container_width=True,
                hide_index=True, height=no_scroll_height(radar),
            )


with tab_watchlist:
    st.subheader("Watchlist")

    if watchlist_error:
        st.warning(watchlist_error)
    elif watchlist_result is None or watchlist_result.data.empty:
        st.info("Watchlist er tom.")
    else:
        w1, w2, w3 = st.columns(3)
        w1.metric("Kandidater", watchlist_metrics["Count"])
        w2.metric("AI ≥ 80%", watchlist_metrics["High_Confidence"])
        w3.metric("Topkandidat", watchlist_metrics["Top_Candidate"] or "N/A")

        for note in watchlist_result.notes:
            st.warning(note)

        watchlist_table = format_watchlist_table(watchlist_result)
        st.dataframe(
            table_style(watchlist_table), use_container_width=True,
            hide_index=True, height=no_scroll_height(watchlist_table),
        )


with tab_settings:
    st.subheader("Settings")
    st.caption(
        "Kontrolcenter for modellen. Sessionens ændringer nulstilles ved genstart."
    )

    with st.expander("Portfolio Health", expanded=True):
        factors = list(config.health_weights.keys())
        columns = st.columns(2)
        for index, factor in enumerate(factors):
            with columns[index % 2]:
                st.number_input(
                    factor, min_value=0.0, max_value=1.0, step=0.05,
                    format="%.2f", key=f"health_weight_{factor}",
                )
        total = sum(float(st.session_state[f"health_weight_{f}"]) for f in factors)
        st.caption(f"Indtastet vægtsum: {total:.2f}. Normaliseres automatisk.")
        if st.button("Nulstil Portfolio Health"):
            for factor, default in config.health_weights.items():
                st.session_state[f"health_weight_{factor}"] = float(default)
            st.rerun()

    with st.expander("Decision Engine"):
        factors = list(DECISION_WEIGHTS.keys())
        columns = st.columns(2)
        for index, factor in enumerate(factors):
            with columns[index % 2]:
                st.number_input(
                    factor, min_value=0.0, max_value=1.0, step=0.05,
                    format="%.2f", key=f"decision_weight_{factor}",
                )
        total = sum(
            float(st.session_state[f"opportunity_weight_{f}"]) for f in factors
        )
        st.caption(f"Indtastet vægtsum: {total:.2f}. Normaliseres automatisk.")
        if st.button("Nulstil Decision Engine"):
            for factor, default in DECISION_WEIGHTS.items():
                st.session_state[f"decision_weight_{factor}"] = float(default)
            st.rerun()

    with st.expander("Modeloversigt"):
        st.caption(
            "Redigér værdierne og vælg Anvend modelændringer. Derefter "
            "genberegnes hele modellen med de nye parametre."
        )
        m1, m2 = st.columns(2)
        with m1:
            st.text_input("Benchmark", key="draft_model_benchmark")
            st.number_input(
                "Maks. positionsvægt",
                min_value=0.01,
                max_value=1.00,
                step=0.01,
                format="%.2f",
                key="draft_model_max_position_weight",
                help="Angives som decimal. 0,12 svarer til 12 %.",
            )
            st.number_input(
                "Minimum handel (DKK)",
                min_value=0.0,
                step=500.0,
                format="%.0f",
                key="draft_model_minimum_trade_dkk",
            )
        with m2:
            st.number_input(
                "Maks. sektorvægt",
                min_value=0.01,
                max_value=1.00,
                step=0.01,
                format="%.2f",
                key="draft_model_max_sector_weight",
                help="Angives som decimal. 0,20 svarer til 20 %.",
            )
            st.number_input(
                "Risikofri rente",
                min_value=0.0,
                max_value=0.25,
                step=0.005,
                format="%.3f",
                key="draft_model_risk_free_rate",
                help="Angives som decimal. 0,02 svarer til 2 %.",
            )
            st.text_input("App-version", value=APP_VERSION, disabled=True)
            st.text_input(
                "Datakilde", value="AI_portfolio.xlsx + yfinance", disabled=True
            )

        active_settings = pd.DataFrame([
            {"Aktiv parameter": "Benchmark", "Værdi": config.benchmark},
            {
                "Aktiv parameter": "Maks. positionsvægt",
                "Værdi": format_pct(config.max_position_weight, 0),
            },
            {
                "Aktiv parameter": "Maks. sektorvægt",
                "Værdi": format_pct(config.max_sector_weight, 0),
            },
            {
                "Aktiv parameter": "Minimum handel",
                "Værdi": compact_dkk(MINIMUM_TRADE_DKK),
            },
            {
                "Aktiv parameter": "Risikofri rente",
                "Værdi": format_pct(config.risk_free_rate, 1),
            },
        ])
        st.dataframe(active_settings, use_container_width=True, hide_index=True)

        apply_col, reset_col = st.columns(2)
        with apply_col:
            if st.button("Anvend modelændringer", type="primary"):
                st.session_state["model_benchmark"] = (
                    str(st.session_state["draft_model_benchmark"]).strip()
                    or base_config.benchmark
                )
                st.session_state["model_max_position_weight"] = float(
                    st.session_state["draft_model_max_position_weight"]
                )
                st.session_state["model_max_sector_weight"] = float(
                    st.session_state["draft_model_max_sector_weight"]
                )
                st.session_state["model_minimum_trade_dkk"] = float(
                    st.session_state["draft_model_minimum_trade_dkk"]
                )
                st.session_state["model_risk_free_rate"] = float(
                    st.session_state["draft_model_risk_free_rate"]
                )
                st.rerun()

        with reset_col:
            if st.button("Nulstil Modeloversigt"):
                defaults = {
                    "model_benchmark": base_config.benchmark,
                    "model_max_position_weight": float(base_config.max_position_weight),
                    "model_max_sector_weight": float(base_config.max_sector_weight),
                    "model_minimum_trade_dkk": 5_000.0,
                    "model_risk_free_rate": float(base_config.risk_free_rate),
                }
                for key, value in defaults.items():
                    st.session_state[key] = value
                    st.session_state[f"draft_{key}"] = value
                st.rerun()

    with st.expander("Momentum-vægte"):
        st.caption(
            "Indtast rå vægte. De normaliseres automatisk, så den aktive sum er 100 %."
        )
        periods = list(base_config.momentum_weights.keys())
        columns = st.columns(len(periods))
        for index, period in enumerate(periods):
            with columns[index]:
                st.number_input(
                    period,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    format="%.2f",
                    key=f"momentum_weight_{period}",
                )

        active_momentum = pd.DataFrame({
            "Periode": periods,
            "Indtastet vægt": [
                format_pct(st.session_state[f"momentum_weight_{period}"], 0)
                for period in periods
            ],
            "Aktiv normaliseret vægt": [
                format_pct(momentum_weights[period], 0) for period in periods
            ],
        })
        st.dataframe(active_momentum, use_container_width=True, hide_index=True)
        st.caption(
            f"Indtastet vægtsum: {sum(raw_momentum_weights.values()):.2f}. "
            "Aktiv vægtsum: 1,00."
        )

        if st.button("Nulstil Momentum-vægte"):
            for period, default in base_config.momentum_weights.items():
                st.session_state[f"momentum_weight_{period}"] = float(default)
            st.rerun()
