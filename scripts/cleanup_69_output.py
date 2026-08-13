from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected text not found in {path}:\n{old}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        return
    file.write_text(text.replace(old, new), encoding="utf-8")


# 1) Decision Engine: fjern legacy Opportunity aliases.
replace_once(
    "modules/decision_engine.py",
    '''    Outputkolonnerne er fælles for alle views:\n    Decision_Score, Decision_Status, Handling samt syv scorekomponenter.\n    Legacy Opportunity-kolonner oprettes som aliases, så resten af 6.8-UI'et\n    kan migreres gradvist uden parallel beregningslogik.\n''',
    '''    Outputkolonnerne er fælles for alle views:\n    Decision_Score, Decision_Status, Handling samt syv scorekomponenter.\n    Der oprettes ingen view-specifikke score- eller statusaliases.\n''',
)
replace_once(
    "modules/decision_engine.py",
    '''    # Compatibility aliases. Ingen separat Opportunity-beregning.\n    result["Opportunity Score"] = result["Decision_Score"]\n    result["Opportunity Label"] = result["Decision_Status"]\n    result["Opportunity Rank"] = result["Decision_Score"].rank(\n        ascending=False,\n        method="min",\n    ).astype("Int64")\n\n''',
    '''''',
)
replace_once(
    "modules/decision_engine.py",
    '''    status = row.get("Decision_Status", row.get("Opportunity Label", "Ukendt"))\n''',
    '''    status = row.get("Decision_Status", "Ukendt")\n''',
)

# 2) Opportunities: kun ranking/view oven på canonical Decision output.
replace_once(
    "modules/opportunity_engine.py",
    '''from modules.decision_engine import (\n    DECISION_WEIGHTS,\n    apply_decision_engine,\n    normalize_decision_weights,\n)\n\n\n# Behold navnet af hensyn til eksisterende Settings/UI-kompatibilitet.\n# Der findes ikke længere en separat Opportunity-scoredefinition.\nDEFAULT_OPPORTUNITY_WEIGHTS = DECISION_WEIGHTS.copy()\n''',
    '''''',
)
replace_once(
    "modules/opportunity_engine.py",
    '''\ndef normalize_opportunity_weights(\n    weights: dict[str, float] | None,\n) -> dict[str, float]:\n    """Legacy alias til den fælles vægtnormalisering."""\n    return normalize_decision_weights(weights)\n\n''',
    '''\n''',
)
replace_once(
    "modules/opportunity_engine.py",
    '''    Investment OS 6.9 bruger Decision_Score, Decision_Status og Handling fra\n    den centrale Decision Engine. Opportunity Score/Label er alene aliases,\n    så eksisterende UI kan fortsætte under migrationen.\n''',
    '''    Investment OS 6.9 bruger Decision_Score, Decision_Status og Handling fra\n    den centrale Decision Engine. Opportunities tilføjer kun en ranking.\n''',
)
replace_once(
    "modules/opportunity_engine.py",
    '''    result["Opportunity Score"] = result["Decision_Score"]\n    result["Opportunity Label"] = result["Decision_Status"]\n    result["Opportunity Rank"] = result["Decision_Score"].rank(\n''',
    '''    result["Decision Rank"] = result["Decision_Score"].rank(\n''',
)

# 3) Decision Queue: canonical Status, ingen Decision Label/Opportunity Score.
replace_once(
    "modules/decision_queue_engine.py",
    '''                "Decision Score",\n                "Decision Label",\n                "Opportunity Score",\n                "Confidence",\n''',
    '''                "Decision Score",\n                "Status",\n                "Confidence",\n''',
)
replace_once(
    "modules/decision_queue_engine.py",
    '''            "Handling",\n            "Opportunity Score",\n            "Opportunity Label",\n''',
    '''            "Handling",\n''',
)
replace_once(
    "modules/decision_queue_engine.py",
    '''            "Decision_Status",\n            "Opportunity Score",\n            "Opportunity Label",\n''',
    '''            "Decision_Status",\n''',
)
replace_once(
    "modules/decision_queue_engine.py",
    '''    queue["Decision Label"] = queue.get(\n        "Decision_Status",\n        pd.Series("Datamangel", index=queue.index),\n    )\n    queue["Opportunity Score"] = queue["Decision Score"]\n''',
    '''    queue["Status"] = queue.get(\n        "Decision_Status",\n        pd.Series("Datamangel", index=queue.index),\n    )\n''',
)
replace_once(
    "modules/decision_queue_engine.py",
    '''        "Decision Score",\n        "Decision Label",\n        "Opportunity Score",\n        "Confidence",\n''',
    '''        "Decision Score",\n        "Status",\n        "Confidence",\n''',
)

# 4) app.py: Settings og views bruger Decision-navne hele vejen.
replace_once(
    "app.py",
    '''from modules.decision_engine import apply_decision_engine, decision_summary\n''',
    '''from modules.decision_engine import DECISION_WEIGHTS, apply_decision_engine, decision_summary\n''',
)
replace_once(
    "app.py",
    '''from modules.opportunity_engine import (\n    DEFAULT_OPPORTUNITY_WEIGHTS,\n    build_opportunity_scores,\n)\n''',
    '''from modules.opportunity_engine import build_opportunity_scores\n''',
)
replace_all("app.py", "opportunity_factor_weights", "decision_factor_weights")
replace_once(
    "app.py",
    '''for factor, default_value in DEFAULT_OPPORTUNITY_WEIGHTS.items():\n    key = f"opportunity_weight_{factor}"\n    st.session_state.setdefault(key, float(default_value))\n\ndecision_factor_weights = {\n    factor: float(st.session_state[f"opportunity_weight_{factor}"])\n    for factor in DEFAULT_OPPORTUNITY_WEIGHTS\n}\n''',
    '''for factor, default_value in DECISION_WEIGHTS.items():\n    key = f"decision_weight_{factor}"\n    st.session_state.setdefault(key, float(default_value))\n\ndecision_factor_weights = {\n    factor: float(st.session_state[f"decision_weight_{factor}"])\n    for factor in DECISION_WEIGHTS\n}\n''',
)
replace_once(
    "app.py",
    '''            str(best.get("Decision Label", "Datamangel")),\n''',
    '''            str(best.get("Status", "Datamangel")),\n''',
)
replace_once(
    "app.py",
    '''    if "Opportunity Label" in opportunity_data.columns:\n        opportunity_data = opportunity_data.loc[\n            opportunity_data["Opportunity Label"].isin(strong_statuses)\n        ].copy()\n    else:\n        opportunity_data = opportunity_data.iloc[0:0].copy()\n\n    opportunity_data = opportunity_data.sort_values(\n        ["Opportunity Score", "Name"],\n''',
    '''    if "Decision_Status" in opportunity_data.columns:\n        opportunity_data = opportunity_data.loc[\n            opportunity_data["Decision_Status"].isin(strong_statuses)\n        ].copy()\n    else:\n        opportunity_data = opportunity_data.iloc[0:0].copy()\n\n    opportunity_data = opportunity_data.sort_values(\n        ["Decision_Score", "Name"],\n''',
)
replace_once(
    "app.py",
    '''                f"{float(best_opportunity['Opportunity Score']):.0f}/100"\n                if pd.notna(best_opportunity.get("Opportunity Score")) else None\n''',
    '''                f"{float(best_opportunity['Decision_Score']):.0f}/100"\n                if pd.notna(best_opportunity.get("Decision_Score")) else None\n''',
)
replace_once(
    "app.py",
    '''                "Opportunity Rank", "Name", "Handling",\n''',
    '''                "Decision Rank", "Name", "Handling",\n''',
)
replace_once(
    "app.py",
    '''        factors = list(DEFAULT_OPPORTUNITY_WEIGHTS.keys())\n''',
    '''        factors = list(DECISION_WEIGHTS.keys())\n''',
)
replace_all("app.py", 'f"opportunity_weight_{factor}"', 'f"decision_weight_{factor}"')
replace_once(
    "app.py",
    '''            for factor, default in DEFAULT_OPPORTUNITY_WEIGHTS.items():\n                st.session_state[f"decision_weight_{factor}"] = float(default)\n''',
    '''            for factor, default in DECISION_WEIGHTS.items():\n                st.session_state[f"decision_weight_{factor}"] = float(default)\n''',
)

# 5) Snapshot: eksporter canonical Decision-felter også under opportunities.
replace_once(
    "modules/snapshot_engine.py",
    '''    opportunity_columns = [\n        "Aktiv",\n        "Ticker",\n        "Opportunity Score",\n        "AI_Confidence",\n''',
    '''    opportunity_columns = [\n        "Name",\n        "Yahoo_Ticker",\n        "Decision_Score",\n        "Decision_Status",\n        "AI_Confidence",\n''',
)

# 6) Standalone snapshot-generator skal score før summary/opportunities.
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''from modules.decision_engine import decision_summary\n''',
    '''from modules.decision_engine import DECISION_WEIGHTS, apply_decision_engine, decision_summary\n''',
)
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''from modules.opportunity_engine import DEFAULT_OPPORTUNITY_WEIGHTS, build_opportunity_scores\n''',
    '''from modules.opportunity_engine import build_opportunity_scores\n''',
)
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''    quality_score, quality_notes = data_quality_score(portfolio, market_snapshot)\n    metrics = portfolio_summary(portfolio)\n    decision = decision_summary(analytics_portfolio)\n''',
    '''    analytics_portfolio = apply_decision_engine(\n        analytics_portfolio,\n        factor_weights=DECISION_WEIGHTS,\n        max_position_weight=config.max_position_weight,\n    ).data\n\n    quality_score, quality_notes = data_quality_score(portfolio, market_snapshot)\n    metrics = portfolio_summary(portfolio)\n    decision = decision_summary(analytics_portfolio)\n''',
)
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''        factor_weights=DEFAULT_OPPORTUNITY_WEIGHTS,\n''',
    '''        factor_weights=DECISION_WEIGHTS,\n''',
)
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''    opportunity_columns = [\n        "Aktiv", "Ticker", "Opportunity Score", "AI_Confidence", "Composite",\n        "Relative_Strength_3M", "Portfolio_Weight", "Handling",\n    ]\n''',
    '''    opportunity_columns = [\n        "Name", "Yahoo_Ticker", "Decision_Score", "Decision_Status",\n        "AI_Confidence", "Composite", "Relative_Strength_3M",\n        "Portfolio_Weight", "Handling",\n    ]\n''',
)

# 7) Regressionstest: legacy outputkolonner må ikke komme tilbage.
replace_once(
    "tests/test_decision_engine_consistency.py",
    '''        pd.testing.assert_series_equal(\n            canonical["Handling"].sort_index(),\n            opportunities["Handling"].sort_index(),\n            check_names=False,\n        )\n''',
    '''        pd.testing.assert_series_equal(\n            canonical["Handling"].sort_index(),\n            opportunities["Handling"].sort_index(),\n            check_names=False,\n        )\n        self.assertNotIn("Opportunity Score", opportunities.columns)\n        self.assertNotIn("Opportunity Label", opportunities.columns)\n        self.assertIn("Decision Rank", opportunities.columns)\n''',
)

print("Investment OS 6.9 canonical output cleanup applied")
