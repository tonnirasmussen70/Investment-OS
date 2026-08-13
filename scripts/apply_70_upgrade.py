from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected block not found in {path}:\n{old}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old in text:
        file.write_text(text.replace(old, new), encoding="utf-8")


# Version 7.0.
replace_all("app.py", 'page_title="Investment OS 6.9"', 'page_title="Investment OS 7.0"')
replace_all("app.py", 'APP_VERSION = "6.9.0"', 'APP_VERSION = "7.0.0"')
replace_all("app.py", 'st.title("📈 Investment OS 6.9")', 'st.title("📈 Investment OS 7.0")')

# Rebalancering skal bygges før Decision Queue, så Overblik bruger de faktiske
# execution-beløb i stedet for Portfolio Doctors simulationsbeløb.
replace_once(
    "app.py",
    '''decision_queue = build_decision_queue(\n    portfolio_doctor.data,\n    opportunity_result.data,\n    max_items=5,\n)\n\nrebalance_result = build_rebalance_plan(\n    analytics_portfolio,\n    active_market_value_dkk=return_market_value,\n    max_position_weight=config.max_position_weight,\n    minimum_trade_dkk=MINIMUM_TRADE_DKK,\n)\n''',
    '''rebalance_result = build_rebalance_plan(\n    analytics_portfolio,\n    active_market_value_dkk=return_market_value,\n    max_position_weight=config.max_position_weight,\n    max_sector_weight=config.max_sector_weight,\n    minimum_trade_dkk=MINIMUM_TRADE_DKK,\n)\n\ndecision_queue = build_decision_queue(\n    rebalance_result.data,\n    max_items=5,\n)\n''',
)

# Hvis en tidligere delmigration allerede har tilføjet sektorloftet, håndtér
# også den rækkefølge idempotent.
replace_once(
    "app.py",
    '''decision_queue = build_decision_queue(\n    portfolio_doctor.data,\n    opportunity_result.data,\n    max_items=5,\n)\n\nrebalance_result = build_rebalance_plan(\n    analytics_portfolio,\n    active_market_value_dkk=return_market_value,\n    max_position_weight=config.max_position_weight,\n    max_sector_weight=config.max_sector_weight,\n    minimum_trade_dkk=MINIMUM_TRADE_DKK,\n)\n''',
    '''rebalance_result = build_rebalance_plan(\n    analytics_portfolio,\n    active_market_value_dkk=return_market_value,\n    max_position_weight=config.max_position_weight,\n    max_sector_weight=config.max_sector_weight,\n    minimum_trade_dkk=MINIMUM_TRADE_DKK,\n)\n\ndecision_queue = build_decision_queue(\n    rebalance_result.data,\n    max_items=5,\n)\n''',
)

# Overblik bygger en bred queue fra samme execution-plan.
replace_once(
    "app.py",
    '''    overview_queue = build_decision_queue(\n        portfolio_doctor.data,\n        opportunity_result.data,\n        max_items=max(20, len(analytics_portfolio)),\n    ).data.copy()\n''',
    '''    overview_queue = build_decision_queue(\n        rebalance_result.data,\n        max_items=max(20, len(analytics_portfolio)),\n    ).data.copy()\n''',
)
replace_once(
    "app.py",
    '''        action = str(best.get("Handling", "Afvent"))\n''',
    '''        action = str(best.get("Execution", best.get("Handling", "Afvent")))\n''',
)
replace_once(
    "app.py",
    '''            [["Prioritet", "Handling", "Aktiv", "Beløb DKK", "Decision Score", "Begrundelse"]]\n''',
    '''            [["Prioritet", "Execution", "Aktiv", "Beløb DKK", "Decision Score", "Begrundelse"]]\n''',
)
replace_once(
    "app.py",
    '''        action_table = action_table.rename(\n            columns={"Beløb DKK": "Beløb", "Decision Score": "Score"}\n        )\n''',
    '''        action_table = action_table.rename(\n            columns={\n                "Execution": "Handling",\n                "Beløb DKK": "Beløb",\n                "Decision Score": "Score",\n            }\n        )\n''',
)

# Rebalancering UI: execution summary.
replace_once(
    "app.py",
    '''    st.caption(\n        "Aktier og ETF'er vurderes separat, fordi de ligger på hver sin ASK. "\n        "Hver tabel viser nuværende vægt, foreslået allokering og risikostatus."\n    )\n\n    r1, r2, r3, r4 = st.columns(4)\n    r1.metric("Øg-signaler", rebalance_result.increase_count)\n    r2.metric("Reducer-signaler", rebalance_result.reduce_count)\n    r3.metric("Foreslåede handler", rebalance_result.trade_count)\n    r4.metric("Brutto handel", compact_dkk(rebalance_result.gross_trade_dkk))\n''',
    '''    st.caption(\n        "7.0 omsætter Decision Engine til dynamiske target weights og konkrete handler. "\n        "Aktier og ETF'er vises separat, mens positions- og sektorloft håndhæves som hard constraints."\n    )\n\n    r1, r2, r3, r4, r5 = st.columns(5)\n    r1.metric("Handler", rebalance_result.trade_count)\n    r2.metric("Køb", compact_dkk(rebalance_result.buy_dkk))\n    r3.metric("Salg", compact_dkk(rebalance_result.sell_dkk))\n    r4.metric("Kapitalbehov", compact_dkk(rebalance_result.cash_required_dkk))\n    r5.metric("Constraints", rebalance_result.constrained_count)\n''',
)

# Rebalance engine leverer nu Asset_Type direkte; behold fallback til ældre data.
replace_once(
    "app.py",
    '''        asset_type_lookup = analytics_portfolio[["Name", "Asset_Type"]].drop_duplicates(\n            subset=["Name"]\n        )\n        rebalance = rebalance.merge(\n            asset_type_lookup,\n            left_on="Aktiv",\n            right_on="Name",\n            how="left",\n        ).drop(columns=["Name"], errors="ignore")\n        rebalance["Aktivklasse"] = rebalance["Asset_Type"].replace({\n''',
    '''        if "Asset_Type" not in rebalance.columns:\n            asset_type_lookup = analytics_portfolio[["Name", "Asset_Type"]].drop_duplicates(\n                subset=["Name"]\n            )\n            rebalance = rebalance.merge(\n                asset_type_lookup,\n                left_on="Aktiv",\n                right_on="Name",\n                how="left",\n            ).drop(columns=["Name"], errors="ignore")\n        rebalance["Aktivklasse"] = rebalance["Asset_Type"].replace({\n''',
)

# Execution-tabel: modeltarget, eksekverbar target, handelsbeløb og constraints.
replace_once(
    "app.py",
    '''            display = section[\n                [\n                    "Aktiv", "Nuværende vægt", "Foreslået vægt", "Ændring",\n                    "Risiko", "Composite", "AI", "Decision Score", "Status", "Handling",\n                ]\n            ].copy()\n\n            for col in ["Nuværende vægt", "Foreslået vægt", "Ændring", "Composite"]:\n                display[col] = display[col].apply(lambda x: format_pct(x, 1))\n            display["AI"] = display["AI"].apply(\n                lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"\n            )\n            display["Decision Score"] = display["Decision Score"].apply(\n                lambda x: score_text(x, 0)\n            )\n            display = display.rename(columns={"Composite": "Momentum"})\n''',
    '''            display = section[\n                [\n                    "Aktiv", "Nuværende vægt", "Modelmålvægt", "Foreslået vægt",\n                    "Ændring", "Handel DKK", "Rebalance handling", "Risiko",\n                    "Decision Score", "Status", "Handling", "Constraint",\n                ]\n            ].copy()\n\n            for col in ["Nuværende vægt", "Modelmålvægt", "Foreslået vægt", "Ændring"]:\n                display[col] = display[col].apply(lambda x: format_pct(x, 1))\n            display["Handel DKK"] = display["Handel DKK"].apply(compact_dkk)\n            display["Decision Score"] = display["Decision Score"].apply(\n                lambda x: score_text(x, 0)\n            )\n            display = display.rename(\n                columns={\n                    "Modelmålvægt": "Model target",\n                    "Foreslået vægt": "Execution target",\n                    "Handel DKK": "Handel",\n                    "Rebalance handling": "Execution",\n                }\n            )\n''',
)

replace_once(
    "app.py",
    '''    st.caption(\n        f"Positionsloft {config.max_position_weight:.0%}. Handler under "\n        f"{compact_dkk(MINIMUM_TRADE_DKK)} filtreres som støj."\n    )\n''',
    '''    st.caption(\n        f"Hard constraints: positionsloft {config.max_position_weight:.0%} og "\n        f"sektorloft {config.max_sector_weight:.0%}. Handler under "\n        f"{compact_dkk(MINIMUM_TRADE_DKK)} eksekveres ikke."\n    )\n''',
)

# Standalone snapshot-generator bruger samme 7.0 execution chain.
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''    queue = build_decision_queue(doctor.data, opportunity_result.data, max_items=5)\n    rebalance = build_rebalance_plan(\n        analytics_portfolio,\n        active_market_value_dkk=active_value,\n        max_position_weight=config.max_position_weight,\n        minimum_trade_dkk=MINIMUM_TRADE_DKK,\n    )\n''',
    '''    rebalance = build_rebalance_plan(\n        analytics_portfolio,\n        active_market_value_dkk=active_value,\n        max_position_weight=config.max_position_weight,\n        max_sector_weight=config.max_sector_weight,\n        minimum_trade_dkk=MINIMUM_TRADE_DKK,\n    )\n    queue = build_decision_queue(rebalance.data, max_items=5)\n''',
)
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''    queue = build_decision_queue(doctor.data, opportunity_result.data, max_items=5)\n    rebalance = build_rebalance_plan(\n        analytics_portfolio,\n        active_market_value_dkk=active_value,\n        max_position_weight=config.max_position_weight,\n        max_sector_weight=config.max_sector_weight,\n        minimum_trade_dkk=MINIMUM_TRADE_DKK,\n    )\n''',
    '''    rebalance = build_rebalance_plan(\n        analytics_portfolio,\n        active_market_value_dkk=active_value,\n        max_position_weight=config.max_position_weight,\n        max_sector_weight=config.max_sector_weight,\n        minimum_trade_dkk=MINIMUM_TRADE_DKK,\n    )\n    queue = build_decision_queue(rebalance.data, max_items=5)\n''',
)

print("Investment OS 7.0 app integration applied")
