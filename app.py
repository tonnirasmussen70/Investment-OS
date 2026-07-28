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
from modules.decision_engine import (
    decision_summary,
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
APP_VERSION = "4.1.1"

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
decision = decision_summary(analytics_portfolio)
avg_confidence = decision["AI_Confidence"]
capital_flow_label = decision["Capital_Flow"]



def quality_label(score: float) -> tuple[str, str]:
    """Returnér ikon og tekst for datakvalitet."""
    if score >= 90:
        return "🟢", "Høj"
    if score >= 75:
        return "🟡", "Acceptabel"
    return "🔴", "Lav"


def no_scroll_height(dataframe: pd.DataFrame, row_px: int = 38) -> int:
    """Vis hele tabellen uden intern scrolling."""
    return max(100, (len(dataframe) + 1) * row_px + 4)


tab_overview, tab_portfolio, tab_rebalance, tab_ai, tab_compounders, tab_watchlist = st.tabs([
    "🏠 Overblik",
    "📈 Momentum",
    "🔄 Rebalancering",
    "🤖 AI Insights",
    "🚀 Emerging Compounders",
    "👀 Watchlist",
])

with tab_overview:
    quality_icon, quality_text = quality_label(quality_score)

    st.subheader("Daglig morgenbrief")
    if MORNING_BRIEF_FILE.exists():
        brief_updated = pd.Timestamp(
            MORNING_BRIEF_FILE.stat().st_mtime,
            unit="s",
            tz="UTC",
        ).tz_convert("Europe/Copenhagen")

        st.caption(
            "Senest opdateret "
            f"{brief_updated.strftime('%d-%m-%Y kl. %H:%M')}"
        )

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

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Porteføljeværdi", format_dkk(portfolio_total))
    k2.metric("Samlet afkast", format_pct(total_return))
    k3.metric("Sharpe 12M", format_score(current_sharpe, 2))
    k4.metric(
        "AI Confidence",
        f"{avg_confidence:.0f}%" if pd.notna(avg_confidence) else "N/A",
        decision["AI_Confidence_Label"],
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

    actions = decision["Actions"].copy()

    if actions.empty:
        st.success(
            "Ingen positioner kræver handling ud fra den nuværende model."
        )
    else:
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

        st.dataframe(
            table_style(actions),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(actions),
        )

with tab_portfolio:
    st.subheader("Momentum")

    analysis_columns = [
        "1W",
        "1M",
        "3M",
        "6M",
        "12M",
        "Composite",
        "AI_Confidence",
        "Handling",
    ]

    merge_key = (
        "Asset_ID"
        if "Asset_ID" in portfolio.columns
        and "Asset_ID" in analytics_portfolio.columns
        else "Yahoo_Ticker"
    )

    analysis_lookup = analytics_portfolio[
        [merge_key, *analysis_columns]
    ].drop_duplicates(subset=[merge_key])

    portfolio_source = portfolio.merge(
        analysis_lookup,
        on=merge_key,
        how="left",
        suffixes=("", "_analysis"),
    )

    portfolio_source["Display_Market_Value_DKK"] = portfolio_source[
        "Market_Value_DKK"
    ]

    if "Market_value_DKK" in portfolio_source.columns:
        portfolio_source["Display_Market_Value_DKK"] = (
            portfolio_source["Display_Market_Value_DKK"].combine_first(
                pd.to_numeric(
                    portfolio_source["Market_value_DKK"],
                    errors="coerce",
                )
            )
        )

    portfolio_source["Handling"] = portfolio_source["Handling"].fillna(
        "Uden for analyse"
    )

    asset_type_normalized = (
        portfolio_source["Asset_Type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    stock_mask = asset_type_normalized.str.contains(
        r"aktie|stock|equity",
        regex=True,
    )
    etf_mask = asset_type_normalized.str.contains(
        r"etf|fund",
        regex=True,
    )

    stocks = portfolio_source.loc[stock_mask].copy()
    etfs = portfolio_source.loc[etf_mask].copy()

    stock_value = stocks["Display_Market_Value_DKK"].sum(skipna=True)
    etf_value = etfs["Display_Market_Value_DKK"].sum(skipna=True)

    stock_kpi, etf_kpi = st.columns(2)
    stock_kpi.metric(
        "Aktier",
        f"{len(stocks)} positioner",
        format_dkk(stock_value),
    )
    etf_kpi.metric(
        "ETF'er",
        f"{len(etfs)} positioner",
        format_dkk(etf_value),
    )

    def prepare_portfolio_table(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        table = dataframe[
            [
                "Name",
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

        table = table.rename(
            columns={
                "Name": "Aktiv",
                "Portfolio_Weight": "Vægt",
                "AI_Confidence": "AI",
            }
        )

        table = table.sort_values(
            ["Composite", "AI", "Vægt"],
            ascending=[False, False, False],
            na_position="last",
        )

        excluded_weight = table["Handling"].eq("Uden for analyse")

        table["Vægt"] = table["Vægt"].apply(
            lambda value: format_pct(value, 1)
        )
        table.loc[excluded_weight, "Vægt"] = "Ikke medtaget"

        for column in [
            "1W",
            "1M",
            "3M",
            "6M",
            "12M",
            "Composite",
        ]:
            table[column] = table[column].apply(
                lambda value: format_pct(value, 1)
            )

        table["AI"] = table["AI"].apply(
            lambda value: (
                f"{value:.0f}%"
                if pd.notna(value)
                else "N/A"
            )
        )

        return table

    st.markdown("### 📈 Aktie-momentum")
    if stocks.empty:
        st.info("Ingen aktier fundet i masterfilen.")
    else:
        stock_table = prepare_portfolio_table(stocks)
        st.dataframe(
            table_style(stock_table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(stock_table),
        )

    st.markdown("### 📊 ETF-momentum")
    if etfs.empty:
        st.info("Ingen ETF'er fundet i masterfilen.")
    else:
        etf_table = prepare_portfolio_table(etfs)
        st.dataframe(
            table_style(etf_table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(etf_table),
        )

    st.caption(
        "Momentum vises for 1W, 1M, 3M, 6M og 12M. "
        "Alle negative værdier vises med rød skrift. "
        "Grundfos vises i aktietabellen, men indgår ikke i aktiv vægtning, "
        "afkast, momentum eller rebalancering."
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