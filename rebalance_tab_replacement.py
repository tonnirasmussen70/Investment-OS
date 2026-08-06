with tab_rebalance:
    st.subheader("Rebalancering")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Øg-signaler", rebalance_result.increase_count)
    r2.metric("Reducer-signaler", rebalance_result.reduce_count)
    r3.metric("Foreslåede handler", rebalance_result.trade_count)
    r4.metric("Brutto handel", compact_dkk(rebalance_result.gross_trade_dkk))

    rebalance = rebalance_result.data.copy()
    if rebalance.empty:
        st.success("Ingen rebalancering anbefales.")
    else:
        risk_lookup = (
            stop_loss_table[["Aktiv", "Risikohandling"]]
            .drop_duplicates(subset=["Aktiv"])
            if not stop_loss_table.empty
            else pd.DataFrame(columns=["Aktiv", "Risikohandling"])
        )
        rebalance = rebalance.merge(risk_lookup, on="Aktiv", how="left")
        rebalance["Risiko"] = rebalance["Risikohandling"].fillna("Overvåg")

        chart_data = rebalance[
            ["Aktiv", "Nuværende vægt", "Foreslået vægt"]
        ].copy()
        chart_data["Nuværende vægt"] = pd.to_numeric(
            chart_data["Nuværende vægt"], errors="coerce"
        )
        chart_data["Foreslået vægt"] = pd.to_numeric(
            chart_data["Foreslået vægt"], errors="coerce"
        )
        chart_data = chart_data.dropna(
            subset=["Nuværende vægt", "Foreslået vægt"], how="all"
        )

        display = rebalance[
            [
                "Aktiv", "Nuværende vægt", "Foreslået vægt", "Ændring",
                "Risiko", "Composite", "AI", "Handling",
            ]
        ].copy()

        for col in ["Nuværende vægt", "Foreslået vægt", "Ændring", "Composite"]:
            display[col] = display[col].apply(lambda x: format_pct(x, 1))
        display["AI"] = display["AI"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"
        )
        display = display.rename(columns={"Composite": "Momentum"})

        st.dataframe(
            table_style(display),
            use_container_width=True,
            hide_index=True,
            height=no_scroll_height(display),
        )

        st.markdown("### Nuværende vægt vs. foreslået allokering")
        if chart_data.empty:
            st.info("Der er ikke tilstrækkelige data til allokeringsgrafen.")
        else:
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
                title="Nuværende vægt vs. foreslået allokering",
                text_auto=".1%",
            )
            fig.update_layout(
                height=max(420, min(760, 320 + len(chart_data) * 18)),
                xaxis_title=None,
                yaxis_title="Porteføljevægt",
                yaxis_tickformat=".0%",
                legend_title_text=None,
            )
            fig.update_xaxes(
                categoryorder="array",
                categoryarray=chart_data["Aktiv"].tolist(),
                tickangle=-45 if len(chart_data) > 8 else 0,
            )
            st.plotly_chart(fig, use_container_width=True)

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


