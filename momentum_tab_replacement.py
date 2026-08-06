with tab_momentum:
    st.subheader("Momentum")
    st.caption(
        "Aktier og ETF'er vises separat, fordi de ligger på hver sin ASK og "
        "derfor skal vurderes som to selvstændige investeringsuniverser."
    )

    momentum_source = analytics_portfolio[
        [
            "Asset_Type", "Name", "Portfolio_Weight", "1W", "1M", "3M",
            "6M", "12M", "Composite", "Momentum_Acceleration",
            "Relative_Strength_3M", "AI_Confidence", "Handling",
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
                "Name", "Portfolio_Weight", "1W", "1M", "3M", "6M", "12M",
                "Composite", "Momentum_Acceleration",
                "Relative_Strength_3M", "AI_Confidence", "Handling",
            ]
        ].copy()

        table = table.rename(columns={
            "Name": "Navn",
            "Portfolio_Weight": "Vægt",
            "Composite": "Momentum",
            "Momentum_Acceleration": "Acceleration",
            "Relative_Strength_3M": "RS 3M",
            "AI_Confidence": "AI",
        })

        table["Vægt"] = table["Vægt"].apply(lambda x: format_pct(x, 1))
        for col in [
            "1W", "1M", "3M", "6M", "12M",
            "Momentum", "Acceleration", "RS 3M",
        ]:
            table[col] = table[col].apply(lambda x: format_pct(x, 1))

        table["AI"] = table["AI"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
        )

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


