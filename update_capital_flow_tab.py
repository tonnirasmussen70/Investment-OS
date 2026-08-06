from pathlib import Path

APP_FILE = Path("app.py")

OLD_TABS = '''tabs = st.tabs([
    "🏠 Overblik",
    "📈 Momentum",
    "📋 Positioner",
    "🔄 Rebalancering",
    "🩺 Portfolio Doctor",
    "🎯 Opportunities",
    "🚀 Emerging Compounders",
    "👀 Watchlist",
    "⚙️ Settings",
])
(
    tab_overview, tab_momentum, tab_positions, tab_rebalance, tab_doctor,
    tab_opportunity, tab_compounders, tab_watchlist, tab_settings,
) = tabs
'''

NEW_TABS = '''tabs = st.tabs([
    "🏠 Overblik",
    "📈 Momentum",
    "💰 Kapitalflow",
    "📋 Positioner",
    "🔄 Rebalancering",
    "🩺 Portfolio Doctor",
    "🎯 Opportunities",
    "🚀 Emerging Compounders",
    "👀 Watchlist",
    "⚙️ Settings",
])
(
    tab_overview, tab_momentum, tab_capital_flow, tab_positions, tab_rebalance,
    tab_doctor, tab_opportunity, tab_compounders, tab_watchlist, tab_settings,
) = tabs
'''

CAPITAL_FLOW_BLOCK = '''with tab_capital_flow:
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


'''


def main() -> None:
    original = APP_FILE.read_text(encoding="utf-8")
    if OLD_TABS not in original:
        raise RuntimeError("Kunne ikke finde fanedefinitionen i app.py")
    updated = original.replace(OLD_TABS, NEW_TABS, 1)

    marker = "with tab_positions:"
    if marker not in updated:
        raise RuntimeError("Kunne ikke finde Positioner-fanen i app.py")
    updated = updated.replace(marker, CAPITAL_FLOW_BLOCK + marker, 1)

    APP_FILE.write_text(updated, encoding="utf-8")
    print("Kapitalflow-fane tilføjet")


if __name__ == "__main__":
    main()
