with tab_positions:
    st.subheader("Positioner")
    st.caption(
        "Aktier og ETF'er vises separat, så beholdninger og vægte kan vurderes "
        "inden for hver sin ASK. Grundfos vises, men indgår ikke i aktiv vægtning."
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

        include_weight = section["Include_Weight"].fillna(False)
        active_value = pd.to_numeric(
            section.loc[include_weight, "Market_Value_DKK"], errors="coerce"
        ).fillna(0).sum()

        section["ASK_Weight"] = np.where(
            include_weight & (active_value > 0),
            pd.to_numeric(section["Market_Value_DKK"], errors="coerce").fillna(0)
            / active_value,
            np.nan,
        )
        section = section.sort_values(
            ["ASK_Weight", "Name"],
            ascending=[False, True],
            na_position="last",
        ).reset_index(drop=True)

        table = section[
            [
                "Name", "Quantity", "Purchase_Price", "Current_Price", "Sector",
                "Market_Value_DKK", "ASK_Weight", "Return_Pct", "Composite",
                "AI_Confidence",
            ]
        ].copy()
        table.columns = [
            "Navn", "Antal", "Åben kurs", "Dags kurs", "Sektor",
            "Markedsværdi", "Vægt", "Afkast", "Momentum", "AI",
        ]

        table["Antal"] = table["Antal"].apply(
            lambda x: f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notna(x) else "N/A"
        )
        for col in ["Åben kurs", "Dags kurs"]:
            table[col] = table[col].apply(
                lambda x: format_score(x, 2) if pd.notna(x) else "N/A"
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
            section["ASK_Weight"].notna(), ["Name", "ASK_Weight"]
        ].copy()
        st.markdown(f"#### Vægtning pr. {asset_class.lower()}")
        if chart_data.empty:
            st.info("Der er ikke tilstrækkelige data til vægtningsgrafen.")
        else:
            chart_data = chart_data.rename(
                columns={"Name": "Navn", "ASK_Weight": "Vægt"}
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
                yaxis_title="Vægt inden for ASK",
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
                section["ASK_Weight"].notna(), ["Sector", "Market_Value_DKK"]
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


