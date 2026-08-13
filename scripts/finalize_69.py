from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Forventet tekst blev ikke fundet i {path}:\n{old}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "modules/decision_engine.py",
    '''def decision_summary(portfolio: pd.DataFrame) -> dict[str, object]:\n    """Kør Decision Engine og returnér dashboardets centrale signaler."""\n    decision_result = apply_decision_engine(portfolio, inplace=True)\n    scored = decision_result.data\n    ai_confidence = portfolio_ai_confidence(scored)\n    flow_label, positive_share = capital_flow_label(scored)\n\n    return {\n        "AI_Confidence": ai_confidence,\n        "AI_Confidence_Label": confidence_label(ai_confidence),\n        "Capital_Flow": flow_label,\n        "Positive_Momentum_Share": positive_share,\n        "Top_Decision_Asset": decision_result.top_asset,\n        "Top_Decision_Score": decision_result.top_score,\n        "Actions": build_action_table(scored),\n    }\n''',
    '''def decision_summary(portfolio: pd.DataFrame) -> dict[str, object]:\n    """Opsummér allerede beregnet Decision Engine-output til dashboardet."""\n    required = {"Decision_Score", "Decision_Status", "Handling"}\n    missing = required.difference(portfolio.columns)\n    if missing:\n        raise ValueError(\n            "decision_summary kræver autoritativt Decision Engine-output. "\n            f"Mangler kolonner: {sorted(missing)}"\n        )\n\n    scored = portfolio\n    ordered = scored.sort_values(\n        ["Decision_Score", "AI_Confidence", "Composite"],\n        ascending=[False, False, False],\n        na_position="last",\n    )\n    top = ordered.iloc[0] if not ordered.empty else None\n    ai_confidence = portfolio_ai_confidence(scored)\n    flow_label, positive_share = capital_flow_label(scored)\n\n    return {\n        "AI_Confidence": ai_confidence,\n        "AI_Confidence_Label": confidence_label(ai_confidence),\n        "Capital_Flow": flow_label,\n        "Positive_Momentum_Share": positive_share,\n        "Top_Decision_Asset": (\n            str(top.get("Name", "Ukendt")) if top is not None else None\n        ),\n        "Top_Decision_Score": (\n            float(top["Decision_Score"]) if top is not None else np.nan\n        ),\n        "Actions": build_action_table(scored),\n    }\n''',
)

replace_once(
    "app.py",
    '''    "decision_score": (\n        "Prioriterer mulige handlinger ud fra Portfolio Doctor, Opportunity "\n        "Score, AI Confidence og forventet forbedring af Portfolio Health."\n    ),\n''',
    '''    "decision_score": (\n        "Fælles score 0-100 fra Decision Engine baseret på momentum, AI "\n        "Confidence, relativ styrke, trend, risiko, datakvalitet og plads "\n        "under positionsloftet."\n    ),\n''',
)

replace_once(
    "app.py",
    '''        a1.metric(\n            "Overbevisning",\n            conviction_label(decision_score),\n            help="Styrken i selve investeringscasen og handlingens prioritet.",\n        )\n''',
    '''        a1.metric(\n            "Status",\n            str(best.get("Decision Label", "Datamangel")),\n            help="Den fælles status fra Decision Engine for denne investeringscase.",\n        )\n''',
)

print("Investment OS 6.9 final consolidation patch applied")
