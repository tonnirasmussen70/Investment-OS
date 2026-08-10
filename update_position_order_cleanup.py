from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise RuntimeError(f"Kunne ikke finde {label}")
    text = text.replace(old, new, 1)


# 1) Momentum: fjern vægt fra både datakilde og visning.
replace_once(
    '''    momentum_source = analytics_portfolio[\n        [\n            "Asset_Type", "Name", "Portfolio_Weight", "1W", "1M", "3M",\n            "6M", "12M", "Composite", "Momentum_Acceleration",\n            "Relative_Strength_3M", "AI_Confidence", "Handling",\n        ]\n    ].copy()''',
    '''    momentum_source = analytics_portfolio[\n        [\n            "Asset_Type", "Name", "1W", "1M", "3M", "6M", "12M",\n            "Composite", "Momentum_Acceleration", "Relative_Strength_3M",\n            "AI_Confidence", "Handling",\n        ]\n    ].copy()''',
    "Momentum datakilde",
)

replace_once(
    '''        table = section[\n            [\n                "Name", "Portfolio_Weight", "1W", "1M", "3M", "6M", "12M",\n                "Composite", "Momentum_Acceleration",\n                "Relative_Strength_3M", "AI_Confidence", "Handling",\n            ]\n        ].copy()\n\n        table = table.rename(columns={\n            "Name": "Navn",\n            "Portfolio_Weight": "Vægt",\n            "Composite": "Momentum",\n            "Momentum_Acceleration": "Acceleration",\n            "Relative_Strength_3M": "RS 3M",\n            "AI_Confidence": "AI",\n        })\n\n        table["Vægt"] = table["Vægt"].apply(lambda x: format_pct(x, 1))''',
    '''        table = section[\n            [\n                "Name", "1W", "1M", "3M", "6M", "12M", "Composite",\n                "Momentum_Acceleration", "Relative_Strength_3M",\n                "AI_Confidence", "Handling",\n            ]\n        ].copy()\n\n        table = table.rename(columns={\n            "Name": "Navn",\n            "Composite": "Momentum",\n            "Momentum_Acceleration": "Acceleration",\n            "Relative_Strength_3M": "RS 3M",\n            "AI_Confidence": "AI",\n        })''',
    "Momentum tabelvægt",
)

# 2) Positioner: fælles nævner = samlet porteføljeværdi ekskl. Grundfos.
replace_once(
    '''    position_source["Aktivklasse"] = position_source["Asset_Type"].replace({\n        "Stock": "Aktie",\n        "Equity": "Aktie",\n        "Fund": "ETF",\n        "ETF": "ETF",\n    })\n\n    def show_position_section(''',
    '''    position_source["Aktivklasse"] = position_source["Asset_Type"].replace({\n        "Stock": "Aktie",\n        "Equity": "Aktie",\n        "Fund": "ETF",\n        "ETF": "ETF",\n    })\n\n    # Alle viste positionsvægte bruger samme nævner: hele porteføljen ekskl. Grundfos.\n    position_source["Market_Value_DKK"] = pd.to_numeric(\n        position_source["Market_Value_DKK"], errors="coerce"\n    ).fillna(0)\n    grundfos_portfolio_mask = position_source["Name"].astype(str).str.contains(\n        "Grundfos", case=False, na=False\n    )\n    portfolio_value_ex_grundfos = position_source.loc[\n        ~grundfos_portfolio_mask, "Market_Value_DKK"\n    ].sum()\n\n    def show_position_section(''',
    "fælles porteføljeværdi ekskl. Grundfos",
)

replace_once(
    '''        include_weight = section["Include_Weight"].fillna(False)\n        # Grundfos skal altid holdes helt ude af aktiv vægtning, uanset datakilden.\n        grundfos_mask = section["Name"].astype(str).str.contains(\n            "Grundfos", case=False, na=False\n        )\n        include_weight = include_weight & ~grundfos_mask\n        active_value = pd.to_numeric(\n            section.loc[include_weight, "Market_Value_DKK"], errors="coerce"\n        ).fillna(0).sum()\n\n        section["ASK_Weight"] = np.where(\n            include_weight & (active_value > 0),\n            pd.to_numeric(section["Market_Value_DKK"], errors="coerce").fillna(0)\n            / active_value,\n            np.nan,\n        )\n        section = section.sort_values(\n            ["ASK_Weight", "Name"],''',
    '''        grundfos_mask = section["Name"].astype(str).str.contains(\n            "Grundfos", case=False, na=False\n        )\n        section["Portfolio_Weight_Ex_Grundfos"] = np.where(\n            ~grundfos_mask & (portfolio_value_ex_grundfos > 0),\n            section["Market_Value_DKK"] / portfolio_value_ex_grundfos,\n            np.nan,\n        )\n        section = section.sort_values(\n            ["Portfolio_Weight_Ex_Grundfos", "Name"],''',
    "positionsvægtberegning",
)

replace_once(
    '''                "Market_Value_DKK", "ASK_Weight", "Return_Pct", "Composite",''',
    '''                "Market_Value_DKK", "Portfolio_Weight_Ex_Grundfos", "Return_Pct", "Composite",''',
    "positionskolonne",
)

replace_once(
    '''        chart_data = section.loc[\n            section["ASK_Weight"].notna(), ["Name", "ASK_Weight"]\n        ].copy()\n        st.markdown(f"#### Vægtning pr. {asset_class.lower()}")''',
    '''        chart_data = section.loc[\n            section["Portfolio_Weight_Ex_Grundfos"].notna(),\n            ["Name", "Portfolio_Weight_Ex_Grundfos"],\n        ].copy()\n        st.markdown(f"#### Vægtning pr. {asset_class.lower()}")''',
    "positionsgraf datakilde",
)

replace_once(
    '''            chart_data = chart_data.rename(\n                columns={"Name": "Navn", "ASK_Weight": "Vægt"}\n            )''',
    '''            chart_data = chart_data.rename(\n                columns={"Name": "Navn", "Portfolio_Weight_Ex_Grundfos": "Vægt"}\n            )''',
    "positionsgraf kolonnenavn",
)

replace_once(
    '''                yaxis_title="Vægt inden for ASK",''',
    '''                yaxis_title="Vægt af portefølje ekskl. Grundfos",''',
    "positionsgraf y-akse",
)

replace_once(
    '''            sector_data = section.loc[\n                section["ASK_Weight"].notna(), ["Sector", "Market_Value_DKK"]\n            ].copy()''',
    '''            sector_data = section.loc[\n                section["Portfolio_Weight_Ex_Grundfos"].notna(),\n                ["Sector", "Market_Value_DKK"],\n            ].copy()''',
    "sektorfilter",
)

# 3) Nederst i Positioner: samlet vægtning for hele porteføljen ekskl. Grundfos.
replace_once(
    '''    show_position_section(position_source, "ETF", "ETF'er")\n\n\nwith tab_rebalance:''',
    '''    show_position_section(position_source, "ETF", "ETF'er")\n\n    st.divider()\n    st.markdown("### Samlet vægtning – hele porteføljen")\n    st.caption(\n        "Alle aktier og ETF'er anvender samme nævner: samlet porteføljeværdi "\n        "ekskl. Grundfos. Derfor summerer de viste vægte til 100%."\n    )\n\n    overall_weights = position_source.loc[\n        ~grundfos_portfolio_mask\n        & position_source["Aktivklasse"].isin(["Aktie", "ETF"])\n        & (position_source["Market_Value_DKK"] > 0),\n        ["Name", "Aktivklasse", "Market_Value_DKK"],\n    ].copy()\n\n    if overall_weights.empty or portfolio_value_ex_grundfos <= 0:\n        st.info("Der er ikke tilstrækkelige data til den samlede vægtning.")\n    else:\n        overall_weights["Vægt"] = (\n            overall_weights["Market_Value_DKK"] / portfolio_value_ex_grundfos\n        )\n        overall_weights = overall_weights.sort_values(\n            ["Vægt", "Name"], ascending=[False, True]\n        ).reset_index(drop=True)\n\n        stock_weight = overall_weights.loc[\n            overall_weights["Aktivklasse"] == "Aktie", "Vægt"\n        ].sum()\n        etf_weight = overall_weights.loc[\n            overall_weights["Aktivklasse"] == "ETF", "Vægt"\n        ].sum()\n        total_weight = overall_weights["Vægt"].sum()\n\n        w1, w2, w3 = st.columns(3)\n        w1.metric("Aktier", format_pct(stock_weight, 1))\n        w2.metric("ETF'er", format_pct(etf_weight, 1))\n        w3.metric("Samlet", format_pct(total_weight, 1))\n\n        overall_chart = overall_weights.rename(columns={"Name": "Navn"})\n        fig = px.bar(\n            overall_chart,\n            x="Navn",\n            y="Vægt",\n            color="Aktivklasse",\n            title="Samlet positionsvægt – portefølje ekskl. Grundfos",\n            text_auto=".1%",\n        )\n        fig.update_layout(\n            height=max(430, min(760, 320 + len(overall_chart) * 18)),\n            xaxis_title=None,\n            yaxis_title="Vægt af samlet portefølje",\n            yaxis_tickformat=".0%",\n            legend_title_text="Aktivklasse",\n        )\n        fig.update_xaxes(\n            categoryorder="array",\n            categoryarray=overall_chart["Navn"].tolist(),\n            tickangle=-45 if len(overall_chart) > 8 else 0,\n        )\n        st.plotly_chart(fig, use_container_width=True)\n\n\nwith tab_rebalance:''',
    "samlet porteføljevægtning",
)

# Opdater forklaringen øverst i Positioner, så den matcher den nye logik.
replace_once(
    '''        "Aktier og ETF'er vises separat, så beholdninger og vægte kan vurderes "\n        "inden for hver sin ASK. Grundfos vises, men indgår ikke i aktiv vægtning."''',
    '''        "Aktier og ETF'er vises separat, men vægten beregnes for begge tabeller "\n        "mod den samlede porteføljeværdi ekskl. Grundfos. Grundfos vises uden vægt."''',
    "Positioner forklaring",
)

APP.write_text(text, encoding="utf-8")
print("Momentum og Positioner opdateret")
