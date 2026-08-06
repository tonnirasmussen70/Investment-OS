from pathlib import Path

APP_FILE = Path("app.py")
START_MARKER = "with tab_rebalance:"
END_MARKER = "with tab_doctor:"

REPLACEMENT = '''with tab_rebalance:
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


'''


def main() -> None:
    original = APP_FILE.read_text(encoding="utf-8")
    start = original.find(START_MARKER)
    end = original.find(END_MARKER)
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("Kunne ikke finde Rebalancering-sektionen i app.py")
    updated = original[:start] + REPLACEMENT + original[end:]
    APP_FILE.write_text(updated, encoding="utf-8")
    print("Rebalancering opdelt i Aktier og ETF'er")


if __name__ == "__main__":
    main()
