from pathlib import Path

APP_FILE = Path("app.py")

START_MARKER = "with tab_momentum:"
END_MARKER = "with tab_positions:"

REPLACEMENT = 'with tab_momentum:\n    st.subheader("Momentum")\n    st.caption(\n        "Aktier og ETF\'er vises separat, fordi de ligger på hver sin ASK og "\n        "derfor skal vurderes som to selvstændige investeringsuniverser."\n    )\n\n    momentum_source = analytics_portfolio[\n        [\n            "Asset_Type", "Name", "Portfolio_Weight", "1W", "1M", "3M",\n            "6M", "12M", "Composite", "Momentum_Acceleration",\n            "Relative_Strength_3M", "AI_Confidence", "Handling",\n        ]\n    ].copy()\n\n    momentum_source["Aktivklasse"] = momentum_source["Asset_Type"].replace({\n        "Stock": "Aktie",\n        "Equity": "Aktie",\n        "Fund": "ETF",\n        "ETF": "ETF",\n    })\n\n    def show_momentum_section(\n        source: pd.DataFrame,\n        asset_class: str,\n        heading: str,\n    ) -> None:\n        section = source.loc[source["Aktivklasse"] == asset_class].copy()\n\n        st.markdown(f"### {heading}")\n\n        if section.empty:\n            st.info(f"Ingen {heading.lower()} indgår aktuelt i momentum-analysen.")\n            return\n\n        section = section.sort_values(\n            ["Composite", "Name"],\n            ascending=[False, True],\n            na_position="last",\n        ).reset_index(drop=True)\n\n        # Behold numeriske værdier til grafen, før tabellen formateres.\n        chart_data = section[["Name", "Composite"]].copy()\n        chart_data["Composite"] = pd.to_numeric(\n            chart_data["Composite"], errors="coerce"\n        )\n        chart_data = chart_data.dropna(subset=["Composite"])\n\n        table = section[\n            [\n                "Name", "Portfolio_Weight", "1W", "1M", "3M", "6M", "12M",\n                "Composite", "Momentum_Acceleration",\n                "Relative_Strength_3M", "AI_Confidence", "Handling",\n            ]\n        ].copy()\n\n        table = table.rename(columns={\n            "Name": "Navn",\n            "Portfolio_Weight": "Vægt",\n            "Composite": "Momentum",\n            "Momentum_Acceleration": "Acceleration",\n            "Relative_Strength_3M": "RS 3M",\n            "AI_Confidence": "AI",\n        })\n\n        table["Vægt"] = table["Vægt"].apply(lambda x: format_pct(x, 1))\n        for col in [\n            "1W", "1M", "3M", "6M", "12M",\n            "Momentum", "Acceleration", "RS 3M",\n        ]:\n            table[col] = table[col].apply(lambda x: format_pct(x, 1))\n\n        table["AI"] = table["AI"].apply(\n            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"\n        )\n\n        st.dataframe(\n            table_style(table),\n            use_container_width=True,\n            hide_index=True,\n            height=no_scroll_height(table),\n        )\n\n        st.markdown(f"#### Samlet momentum pr. {asset_class.lower()}")\n        if chart_data.empty:\n            st.info("Der er ikke tilstrækkelige data til momentumgrafen.")\n        else:\n            chart_data = chart_data.rename(\n                columns={"Name": "Navn", "Composite": "Momentum"}\n            )\n            fig = px.bar(\n                chart_data,\n                x="Navn",\n                y="Momentum",\n                title=f"Samlet momentum – {heading}",\n                text_auto=".1%",\n            )\n            fig.update_layout(\n                height=max(390, min(700, 300 + len(chart_data) * 18)),\n                xaxis_title=None,\n                yaxis_title="Samlet momentum",\n                yaxis_tickformat=".0%",\n                showlegend=False,\n            )\n            fig.update_xaxes(\n                categoryorder="array",\n                categoryarray=chart_data["Navn"].tolist(),\n                tickangle=-45 if len(chart_data) > 8 else 0,\n            )\n            fig.add_hline(y=0, line_dash="dash")\n            st.plotly_chart(fig, use_container_width=True)\n\n    show_momentum_section(momentum_source, "Aktie", "Aktier")\n\n    st.divider()\n\n    show_momentum_section(momentum_source, "ETF", "ETF\'er")\n\n    st.caption(\n        "Grundfos kan vises i positionsoversigten, men indgår ikke i momentum, "\n        "aktiv vægtning eller rebalancering."\n    )\n\n\n'


def main() -> None:
    if not APP_FILE.exists():
        raise FileNotFoundError(
            "app.py blev ikke fundet. Læg denne fil i roden af Investment-OS."
        )

    original = APP_FILE.read_text(encoding="utf-8")

    start = original.find(START_MARKER)
    end = original.find(END_MARKER)

    if start == -1:
        raise RuntimeError("Kunne ikke finde starten på Momentum-fanen.")
    if end == -1 or end <= start:
        raise RuntimeError("Kunne ikke finde starten på Positioner-fanen.")

    updated = original[:start] + REPLACEMENT + original[end:]

    backup = APP_FILE.with_suffix(".py.bak")
    backup.write_text(original, encoding="utf-8")
    APP_FILE.write_text(updated, encoding="utf-8")

    print("app.py er opdateret.")
    print(f"Backup gemt som: {backup}")


if __name__ == "__main__":
    main()
