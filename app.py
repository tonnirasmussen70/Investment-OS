from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from modules.analytics_engine import (
    add_momentum,
    portfolio_returns,
    rolling_sharpe,
)
from modules.formatting import (
    format_dkk,
    format_pct,
    format_score,
)
from modules.market_engine import (
    fetch_market_snapshot,
    fetch_price_history,
)
from modules.portfolio_engine import (
    calculate_portfolio,
    data_quality_score,
    load_master_file,
)
from modules.styling import table_height, table_style


st.set_page_config(
    page_title="Investment OS 3.0",
    page_icon="📈",
    layout="wide",
)

DATA_FILE = Path("data/AI_portfolio.xlsx")
MORNING_BRIEF_FILE = Path("data/morning_brief.md")
APP_VERSION = "3.0.2"

st.title("📈 Investment OS 3.0")
st.caption(
    f"Fælles portefølje-, momentum-, valuta- og beslutningsdashboard · Version {APP_VERSION}"
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(path: str):
    return load_master_file(path)


@st.cache_data(ttl=3600, show_spinner=True)
def load_market_data(tickers, currencies):
    return fetch_market_snapshot(tickers, currencies)


@st.cache_data(ttl=3600, show_spinner=True)
def load_history(tickers, period):
    return fetch_price_history(tickers, period=period)


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

snapshot = load_market_data(tickers, currencies)
portfolio = calculate_portfolio(model, snapshot)

settings = model.settings
momentum_weights = {
    "1W": float(settings.get("Momentum_1W", 0.20)),
    "1M": float(settings.get("Momentum_1M", 0.25)),
    "3M": float(settings.get("Momentum_3M", 0.25)),
    "6M": float(settings.get("Momentum_6M", 0.20)),
    "12M": float(settings.get("Momentum_12M", 0.10)),
}
weight_sum = sum(momentum_weights.values())
if weight_sum <= 0:
    momentum_weights = {"1W": 0.20, "1M": 0.25, "3M": 0.25, "6M": 0.20, "12M": 0.10}
else:
    momentum_weights = {
        key: value / weight_sum
        for key, value in momentum_weights.items()
    }

history = load_history(tickers, "18mo")
analytics_portfolio = portfolio.loc[
    portfolio["Include_Analytics"].fillna(False)
].copy()
analytics_portfolio = add_momentum(
    analytics_portfolio,
    history,
    momentum_weights,
)

risk_free_rate = float(settings.get("Risk_Free_Rate", 0.02))
daily_returns = portfolio_returns(analytics_portfolio, history)
sharpe_history = rolling_sharpe(
    daily_returns,
    risk_free_rate=risk_free_rate,
)

quality_score, quality_notes = data_quality_score(portfolio, snapshot)

# Samlet porteføljeværdi inkluderer alle positioner, herunder Grundfos.
# Hvis en position mangler en beregnet markedsværdi, bruges den eksisterende
# værdi fra masterfilen som fallback, når kolonnen findes.
portfolio_value_series = portfolio["Market_Value_DKK"].copy()

if "Market_value_DKK" in portfolio.columns:
    portfolio_value_series = portfolio_value_series.combine_first(
        pd.to_numeric(portfolio["Market_value_DKK"], errors="coerce")
    )

portfolio_total = portfolio_value_series.sum(skipna=True)

# Afkast beregnes kun på positioner med Include_Weight = True.
# Grundfos kan derfor indgå i porteføljeværdien uden at påvirke afkastprocenten.
return_mask = (
    portfolio["Include_Weight"].fillna(False)
    & ~portfolio["Name"].astype(str).str.strip().str.casefold().eq("grundfos")
)

return_market_value = portfolio.loc[
    return_mask,
    "Market_Value_DKK",
].sum(skipna=True)

return_cost_value = portfolio.loc[
    return_mask,
    "Cost_Value_DKK",
].sum(skipna=True)

total_return = (
    return_market_value / return_cost_value - 1
    if return_cost_value > 0
    else np.nan
)

current_sharpe = (
    sharpe_history["Sharpe 252D"].dropna().iloc[-1]
    if "Sharpe 252D" in sharpe_history and not sharpe_history["Sharpe 252D"].dropna().empty
    else np.nan
)
avg_confidence = np.average(
    analytics_portfolio["AI_Confidence"],
    weights=analytics_portfolio["Portfolio_Weight"],
) if analytics_portfolio["Portfolio_Weight"].sum() > 0 else np.nan

positive_momentum_share = (
    analytics_portfolio.loc[
        analytics_portfolio["Composite"] > 0,
        "Portfolio_Weight",
    ].sum()
)
capital_flow_label = (
    "Positiv"
    if positive_momentum_share >= 0.65
    else "Neutral"
    if positive_momentum_share >= 0.40
    else "Negativ"
)


def confidence_label(score: float) -> str:
    """Returnér en kort fortolkning af AI Confidence."""
    if pd.isna(score):
        return "Datamangel"
    if score >= 80:
        return "Høj"
    if score >= 65:
        return "Moderat-høj"
    if score >= 50:
        return "Moderat"
    if score >= 35:
        return "Lav"
    return "Meget lav"


def quality_label(score: float) -> tuple[str, str]:
    """Returnér ikon og tekst for datakvalitet."""
    if score >= 90:
        return "🟢", "Høj"
    if score >= 75:
        return "🟡", "Acceptabel"
    return "🔴", "Lav"


def action_reason(row: pd.Series) -> str:
    """Forklar kort hvorfor modellen foreslår en handling."""
    handling = row.get("Handling", "Hold")
    one_week = row.get("1W", np.nan)
    one_month = row.get("1M", np.nan)
    three_months = row.get("3M", np.nan)

    if handling == "Øg":
        return "Positivt kort momentum og stærk samlet score"
    if handling == "Reducer":
        return "Negativ kort og mellemfristet trend"
    if handling == "Afvent":
        if pd.notna(one_week) and pd.notna(one_month):
            if one_week > 0 and one_month < 0:
                return "Tidlig bedring, men endnu ikke bekræftet"
        return "Blandet signalbillede"
    if pd.notna(three_months) and three_months > 0:
        return "Positiv mellemfristet trend"
    return "Ingen væsentlig ændring"


tab_overview, tab_portfolio, tab_rebalance, tab_ai, tab_compounders, tab_watchlist = st.tabs([
    "🏠 Overblik",
    "📈 Portefølje",
    "🔄 Rebalancering",
    "🤖 AI Insights",
    "🚀 Emerging Compounders",
    "👀 Watchlist",
])

with tab_overview:
    quality_icon, quality_text = quality_label(quality_score)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Porteføljeværdi", format_dkk(portfolio_total))
    k2.metric("Samlet afkast", format_pct(total_return))
    k3.metric("Sharpe 12M", format_score(current_sharpe, 2))
    k4.metric(
        "AI Confidence",
        f"{avg_confidence:.0f}%" if pd.notna(avg_confidence) else "N/A",
        confidence_label(avg_confidence),
    )
    k5.metric("Capital Flow", capital_flow_label)
    k6.metric(
        "Datakvalitet",
        f"{quality_score:.0f}%",
        f"{quality_icon} {quality_text}",
    )

    if quality_notes:
        st.markdown("#### Datakvalitet")
        for note in quality_notes:
            st.warning(note)
    else:
        st.success("Alle centrale kurs-, valuta- og porteføljedata er tilgængelige.")

    st.subheader("Daglig morgenbrief")
    if MORNING_BRIEF_FILE.exists():
        morning_brief = MORNING_BRIEF_FILE.read_text(
            encoding="utf-8"
        ).strip()

        if morning_brief:
            st.markdown(morning_brief)
        else:
            st.info("Morgenbrief-filen er tom.")
    else:
        st.info(
            "Dagens morgenbrief er endnu ikke lagt i "
            "`data/morning_brief.md`. Når den planlagte opgave opdaterer "
            "filen, vises hele briefen automatisk her."
        )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Porteføljeudvikling")
        if not daily_returns.empty:
            portfolio_curve = (1 + daily_returns).cumprod() * 100
            curve_df = portfolio_curve.rename("Portefølje").reset_index()
            curve_df.columns = ["Dato", "Indeks"]
            fig_curve = px.line(
                curve_df,
                x="Dato",
                y="Indeks",
                title="Portefølje – indeks 100",
            )
            fig_curve.update_layout(height=430, yaxis_title="Indeks")
            st.plotly_chart(fig_curve, use_container_width=True)
        else:
            st.info("Porteføljeudviklingen kan ikke vises endnu.")

    with right:
        st.subheader("Sharpe-udvikling")
        if not sharpe_history.empty:
            sharpe_long = (
                sharpe_history.reset_index()
                .rename(
                    columns={
                        sharpe_history.index.name or "index": "Dato"
                    }
                )
                .melt(
                    id_vars="Dato",
                    var_name="Periode",
                    value_name="Sharpe",
                )
                .dropna()
            )
            fig_sharpe = px.line(
                sharpe_long,
                x="Dato",
                y="Sharpe",
                color="Periode",
                title="Rullende Sharpe – 30, 90 og 252 handelsdage",
            )
            fig_sharpe.add_hline(y=1.0, line_dash="dash")
            fig_sharpe.update_layout(height=430)
            st.plotly_chart(fig_sharpe, use_container_width=True)
        else:
            st.info("Sharpe-historikken kan ikke vises endnu.")

    st.subheader("Dagens vigtigste handlinger")

    action_columns = [
        "Name",
        "Handling",
        "Composite",
        "AI_Confidence",
        "1W",
        "1M",
        "3M",
    ]

    actions = analytics_portfolio.loc[
        analytics_portfolio["Handling"].ne("Hold"),
        action_columns,
    ].copy()

    if actions.empty:
        st.success(
            "Ingen positioner kræver handling ud fra den nuværende model."
        )
    else:
        actions["Begrundelse"] = actions.apply(action_reason, axis=1)

        actions["Prioritet"] = np.select(
            [
                actions["Handling"].eq("Reducer"),
                actions["Handling"].eq("Øg"),
                actions["Handling"].eq("Afvent"),
            ],
            [
                "🔴 Høj",
                "🟢 Mulighed",
                "🟡 Afvent",
            ],
            default="⚪ Neutral",
        )

        actions = (
            actions.sort_values(
                ["Handling", "AI_Confidence"],
                ascending=[True, False],
            )
            .head(5)
            .rename(
                columns={
                    "Name": "Aktiv",
                    "AI_Confidence": "AI Confidence",
                }
            )
        )

        actions["Composite"] = actions["Composite"].apply(
            lambda value: format_pct(value, 1)
        )
        actions["AI Confidence"] = actions["AI Confidence"].apply(
            lambda value: (
                f"{value:.0f}%"
                if pd.notna(value)
                else "N/A"
            )
        )

        actions = actions[
            [
                "Prioritet",
                "Aktiv",
                "Handling",
                "Composite",
                "AI Confidence",
                "Begrundelse",
            ]
        ]

        st.dataframe(
            table_style(actions),
            use_container_width=True,
            hide_index=True,
            height=table_height(actions, max_height=320),
        )

with tab_portfolio:
    st.subheader("Aktier og ETF'er")

    portfolio_table = analytics_portfolio[
        [
            "Name",
            "Asset_Type",
            "Portfolio_Weight",
            "1W",
            "1M",
            "3M",
            "6M",
            "12M",
            "Composite",
            "AI_Confidence",
            "Handling",
        ]
    ].copy()

    portfolio_table = portfolio_table.rename(columns={
        "Name": "Aktiv",
        "Asset_Type": "Type",
        "Portfolio_Weight": "Vægt",
        "Composite": "Composite",
        "AI_Confidence": "AI",
    }).sort_values("Composite", ascending=False)

    for column in ["Vægt", "1W", "1M", "3M", "6M", "12M", "Composite"]:
        portfolio_table[column] = portfolio_table[column].apply(
            lambda value: format_pct(value, 1)
        )
    portfolio_table["AI"] = portfolio_table["AI"].apply(
        lambda value: f"{value:.0f}%" if pd.notna(value) else "N/A"
    )

    st.dataframe(
        table_style(portfolio_table),
        use_container_width=True,
        hide_index=True,
        height=table_height(portfolio_table),
    )

    st.caption(
        "Alle negative værdier vises med rød skrift. "
        "Valutaafkast indgår i det samlede DKK-afkast."
    )

with tab_rebalance:
    st.subheader("Rebalanceringsindikation")
    rebalance = analytics_portfolio[
        [
            "Name",
            "Portfolio_Weight",
            "Composite",
            "AI_Confidence",
            "Handling",
        ]
    ].copy()
    rebalance["Foreslået vægt"] = rebalance["Portfolio_Weight"]

    top_mask = rebalance["Handling"].eq("Øg")
    reduce_mask = rebalance["Handling"].eq("Reducer")
    rebalance.loc[top_mask, "Foreslået vægt"] *= 1.10
    rebalance.loc[reduce_mask, "Foreslået vægt"] *= 0.75

    total_suggested = rebalance["Foreslået vægt"].sum()
    if total_suggested > 0:
        rebalance["Foreslået vægt"] /= total_suggested

    rebalance["Ændring"] = (
        rebalance["Foreslået vægt"] - rebalance["Portfolio_Weight"]
    )
    rebalance["Handel DKK"] = rebalance["Ændring"] * return_market_value

    rebalance = rebalance.rename(columns={
        "Name": "Aktiv",
        "Portfolio_Weight": "Nuværende vægt",
        "AI_Confidence": "AI",
    }).sort_values("Ændring", ascending=False)

    for column in ["Nuværende vægt", "Foreslået vægt", "Ændring", "Composite"]:
        rebalance[column] = rebalance[column].apply(lambda x: format_pct(x, 1))
    rebalance["AI"] = rebalance["AI"].apply(lambda x: f"{x:.0f}%")
    rebalance["Handel DKK"] = rebalance["Handel DKK"].apply(format_dkk)

    st.dataframe(
        table_style(rebalance),
        use_container_width=True,
        hide_index=True,
        height=table_height(rebalance),
    )

with tab_ai:
    st.subheader("AI Confidence")
    ai_table = analytics_portfolio[
        [
            "Name",
            "AI_Confidence",
            "Composite",
            "Volatility",
            "Max_Drawdown",
            "Handling",
        ]
    ].copy().sort_values("AI_Confidence", ascending=False)

    ai_table = ai_table.rename(columns={
        "Name": "Aktiv",
        "AI_Confidence": "AI Confidence",
        "Max_Drawdown": "Max drawdown",
    })

    ai_table["AI Confidence"] = ai_table["AI Confidence"].apply(lambda x: f"{x:.0f}%")
    for column in ["Composite", "Volatility", "Max drawdown"]:
        ai_table[column] = ai_table[column].apply(lambda x: format_pct(x, 1))

    st.dataframe(
        table_style(ai_table),
        use_container_width=True,
        hide_index=True,
        height=table_height(ai_table),
    )

with tab_compounders:
    st.subheader("Emerging Compounder Radar")
    st.info(
        "Fanen er oprettet som selvstændigt analyseområde. "
        "Den ugentlige radar kobles på i en senere fase, så resultaterne "
        "holdes adskilt fra den eksisterende portefølje."
    )

with tab_watchlist:
    st.subheader("Watchlist")
    if model.watchlist.empty:
        st.info("Watchlist er tom.")
    else:
        watchlist = model.watchlist.dropna(how="all").copy()
        st.dataframe(
            table_style(watchlist),
            use_container_width=True,
            hide_index=True,
            height=table_height(watchlist),
        )