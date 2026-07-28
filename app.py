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
from modules.compounder_engine import (
    load_compounder_radar,
    radar_summary,
    top_candidates,
)
from modules.config_engine import (
    load_investment_config,
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
    asset_type_summary,
    calculate_portfolio,
    data_quality_score,
    load_master_file,
    portfolio_summary,
)
from modules.report_engine import (
    format_report_timestamp,
    load_markdown_report,
)
from modules.watchlist_engine import (
    format_watchlist_table,
    prepare_watchlist,
    watchlist_summary,
)
from modules.styling import table_height, table_style


st.set_page_config(
    page_title="Investment OS 3.0",
    page_icon="📈",
    layout="wide",
)

DATA_FILE = Path("data/AI_portfolio.xlsx")
MORNING_BRIEF_FILE = Path("data/morning_brief.md")
APP_VERSION = "4.9.1"

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


def safe_optional_load(loader, fallback, label: str):
    """
    Kør en valgfri loader uden at stoppe hele dashboardet.

    Bruges kun til ikke-kritiske områder som morgenbrief, compounder-radar
    og watchlist. Fejl returneres som en kort tekst til den relevante fane.
    """
    try:
        return loader(), None
    except Exception as exc:
        return fallback, f"{label} kunne ikke indlæses: {exc}"


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

config = load_investment_config(model.settings)
momentum_weights = config.momentum_weights

history = load_history(tickers, "18mo")
analytics_portfolio = portfolio.loc[
    portfolio["Include_Analytics"].fillna(False)
].copy()
analytics_portfolio = add_momentum(
    analytics_portfolio,
    history,
    momentum_weights,
)

risk_free_rate = config.risk_free_rate
daily_returns = portfolio_returns(analytics_portfolio, history)
sharpe_history = rolling_sharpe(
    daily_returns,
    risk_free_rate=risk_free_rate,
)

quality_score, quality_notes = data_quality_score(portfolio, snapshot)
morning_brief_report, morning_brief_error = safe_optional_load(
    lambda: load_markdown_report(MORNING_BRIEF_FILE),
    None,
    "Morgenbrief",
)

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
    else {
        "Count": 0,
        "High_Confidence": 0,
        "Top_Candidate": None,
    }
)

portfolio_metrics = portfolio_summary(portfolio)
portfolio_total = portfolio_metrics["Portfolio_Value_DKK"]
return_market_value = portfolio_metrics["Active_Market_Value_DKK"]
return_cost_value = portfolio_metrics["Active_Cost_Value_DKK"]
total_return = portfolio_metrics["Total_Return_Pct"]

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
    if morning_brief_error:
        st.warning(morning_brief_error)
    elif morning_brief_report is not None and morning_brief_report.exists:
        st.caption(
            "Senest opdateret "
            f"{format_report_timestamp(morning_brief_report.updated_at)}"
        )

        if morning_brief_report.is_empty:
            st.info("Morgenbrief-filen er tom.")
        else:
            st.markdown(morning_brief_report.content)
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

    asset_summary = asset_type_summary(portfolio_source)

    stock_summary = asset_summary.loc[
        asset_summary["Asset_Group"].eq("Aktier")
    ]
    etf_summary = asset_summary.loc[
        asset_summary["Asset_Group"].eq("ETF'er")
    ]

    stock_count = (
        int(stock_summary["Positioner"].iloc[0])
        if not stock_summary.empty
        else 0
    )
    stock_value = (
        float(stock_summary["Markedsværdi_DKK"].iloc[0])
        if not stock_summary.empty
        else 0.0
    )
    etf_count = (
        int(etf_summary["Positioner"].iloc[0])
        if not etf_summary.empty
        else 0
    )
    etf_value = (
        float(etf_summary["Markedsværdi_DKK"].iloc[0])
        if not etf_summary.empty
        else 0.0
    )

    stock_kpi, etf_kpi = st.columns(2)
    stock_kpi.metric(
        "Aktier",
        f"{stock_count} positioner",
        format_dkk(stock_value),
    )
    etf_kpi.metric(
        "ETF'er",
        f"{etf_count} positioner",
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

    if compounder_error:
        st.warning(compounder_error)
    elif compounder_radar is None or not compounder_radar.exists:
        st.info(
            "Radarfilen mangler. Læg ugens resultat i "
            "`data/compounder_radar.xlsx` eller "
            "`data/compounder_radar.csv`."
        )
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Kandidater",
            compounder_summary["Candidate_Count"],
        )
        c2.metric(
            "AI ≥ 80%",
            compounder_summary["High_Confidence_Count"],
        )
        c3.metric(
            "Gns. AI Confidence",
            (
                f"{compounder_summary['Average_Confidence']:.0f}%"
                if pd.notna(
                    compounder_summary["Average_Confidence"]
                )
                else "N/A"
            ),
        )
        c4.metric(
            "Topkandidat",
            compounder_summary["Top_Candidate"] or "N/A",
        )

        if compounder_radar.notes:
            for note in compounder_radar.notes:
                st.warning(note)

        radar_table = top_candidates(
            compounder_radar,
            limit=20,
        )

        if radar_table.empty:
            st.info("Radarfilen indeholder ingen kandidater.")
        else:
            radar_table = radar_table.rename(
                columns={
                    "Name": "Selskab",
                    "Ticker": "Ticker",
                    "Composite_Score": "Composite",
                    "AI_Confidence": "AI Confidence",
                    "Status": "Status",
                    "Revenue_CAGR_5Y": "Omsætning CAGR 5Y",
                    "EPS_CAGR_5Y": "EPS CAGR 5Y",
                    "Gross_Margin": "Bruttomargin",
                    "ROIC": "ROIC",
                    "Upside_Pct": "Upside",
                    "Risk_Reward": "Risk/Reward",
                    "Risk": "Risiko",
                    "Reason": "Begrundelse",
                }
            )

            for column in [
                "Omsætning CAGR 5Y",
                "EPS CAGR 5Y",
                "Bruttomargin",
                "ROIC",
                "Upside",
            ]:
                if column in radar_table.columns:
                    radar_table[column] = radar_table[column].apply(
                        lambda value: format_pct(value, 1)
                    )

            if "Composite" in radar_table.columns:
                radar_table["Composite"] = radar_table[
                    "Composite"
                ].apply(
                    lambda value: format_score(value, 1)
                )

            if "AI Confidence" in radar_table.columns:
                radar_table["AI Confidence"] = radar_table[
                    "AI Confidence"
                ].apply(
                    lambda value: (
                        f"{value:.0f}%"
                        if pd.notna(value)
                        else "N/A"
                    )
                )

            if "Risk/Reward" in radar_table.columns:
                radar_table["Risk/Reward"] = radar_table[
                    "Risk/Reward"
                ].apply(
                    lambda value: (
                        format_score(value, 2)
                        if pd.notna(value)
                        else "N/A"
                    )
                )

            st.dataframe(
                table_style(radar_table),
                use_container_width=True,
                hide_index=True,
                height=no_scroll_height(radar_table),
            )

        st.caption(
            "Radaren er uafhængig af den nuværende portefølje. "
            "Den viser kun kandidater til videre analyse og udfører aldrig handler."
        )

with tab_watchlist:
    st.subheader("Watchlist")

    if watchlist_error:
        st.warning(watchlist_error)
    elif watchlist_result is None or watchlist_result.data.empty:
        st.info("Watchlist er tom.")
    else:
        w1, w2, w3 = st.columns(3)
        w1.metric(
            "Kandidater",
            watchlist_metrics["Count"],
        )
        w2.metric(
            "AI ≥ 80%",
            watchlist_metrics["High_Confidence"],
        )
        w3.metric(
            "Topkandidat",
            watchlist_metrics["Top_Candidate"] or "N/A",
        )

        for note in watchlist_result.notes:
            st.warning(note)

        watchlist_table = format_watchlist_table(
            watchlist_result
        )

        st.dataframe(
            table_style(watchlist_table),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(watchlist_table),
        )

        st.caption(
            "Watchlist viser kandidater til overvågning. "
            "Aktier flyttes ikke automatisk til porteføljen, "
            "og der udføres ingen handler."
        )
