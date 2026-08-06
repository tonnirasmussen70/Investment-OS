from pathlib import Path

APP_FILE = Path("app.py")
START_MARKER = "with tab_opportunity:"
END_MARKER = "with tab_compounders:"

REPLACEMENT = '''with tab_opportunity:
    st.subheader("Opportunities")
    st.caption(
        "Viser kun kandidater med status Stærk eller Meget stærk. "
        "Svagere signaler skjules som irrelevant støj."
    )

    opportunity_data = opportunity_result.data.copy()
    strong_statuses = {"Stærk", "Meget stærk"}
    if "Opportunity Label" in opportunity_data.columns:
        opportunity_data = opportunity_data.loc[
            opportunity_data["Opportunity Label"].isin(strong_statuses)
        ].copy()
    else:
        opportunity_data = opportunity_data.iloc[0:0].copy()

    opportunity_data = opportunity_data.sort_values(
        ["Opportunity Score", "Name"],
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
                f"{float(best_opportunity['Opportunity Score']):.0f}/100"
                if pd.notna(best_opportunity.get("Opportunity Score")) else None
            ),
            help=TOOLTIPS["opportunity_score"],
        )
        o2.metric("Stærke kandidater", len(opportunity_data))

        summary = opportunity_data[
            [
                "Opportunity Rank", "Name", "Handling",
                "Opportunity Score", "Opportunity Label",
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


'''


def main() -> None:
    original = APP_FILE.read_text(encoding="utf-8")
    start = original.find(START_MARKER)
    end = original.find(END_MARKER)
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("Kunne ikke finde Opportunities-sektionen i app.py")
    updated = original[:start] + REPLACEMENT + original[end:]
    APP_FILE.write_text(updated, encoding="utf-8")
    print("Opportunities filtreret til Stærk og Meget stærk")


if __name__ == "__main__":
    main()
