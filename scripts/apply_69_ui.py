from pathlib import Path


def replace_once(path: str, old: str, new: str) -> bool:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return False
    if old not in text:
        raise SystemExit(f"Forventet tekst blev ikke fundet i {path}:\n{old}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


changed = False

# app.py: brug den centrale motor straks efter momentum-beregningen.
changed |= replace_once(
    "app.py",
    "from modules.decision_engine import decision_summary\n",
    "from modules.decision_engine import apply_decision_engine, decision_summary\n",
)

changed |= replace_once(
    "app.py",
    "analytics_portfolio = add_momentum(\n    analytics_portfolio,\n    history,\n    momentum_weights,\n    benchmark_ticker=benchmark_ticker,\n)\n\nprevious_history = history.iloc[:-1] if len(history) > 1 else history.iloc[0:0]\n",
    "analytics_portfolio = add_momentum(\n    analytics_portfolio,\n    history,\n    momentum_weights,\n    benchmark_ticker=benchmark_ticker,\n)\nanalytics_portfolio = apply_decision_engine(\n    analytics_portfolio,\n    factor_weights=opportunity_factor_weights,\n    max_position_weight=config.max_position_weight,\n).data\n\nprevious_history = history.iloc[:-1] if len(history) > 1 else history.iloc[0:0]\n",
)

changed |= replace_once(
    "app.py",
    "previous_analytics = (\n    add_momentum(\n        previous_source,\n        previous_history,\n        momentum_weights,\n        benchmark_ticker=benchmark_ticker,\n    )\n    if not previous_history.empty\n    else pd.DataFrame()\n)\n\nchange_result = build_change_engine(analytics_portfolio, previous_analytics)\n",
    "previous_analytics = (\n    add_momentum(\n        previous_source,\n        previous_history,\n        momentum_weights,\n        benchmark_ticker=benchmark_ticker,\n    )\n    if not previous_history.empty\n    else pd.DataFrame()\n)\nif not previous_analytics.empty:\n    previous_analytics = apply_decision_engine(\n        previous_analytics,\n        factor_weights=opportunity_factor_weights,\n        max_position_weight=config.max_position_weight,\n    ).data\n\nchange_result = build_change_engine(analytics_portfolio, previous_analytics)\n",
)

# decision_summary må kun aggregere et allerede scoret datasæt.
changed |= replace_once(
    "modules/decision_engine.py",
    "def decision_summary(portfolio: pd.DataFrame) -> dict[str, object]:\n    \"\"\"Kør Decision Engine og returnér dashboardets centrale signaler.\"\"\"\n    decision_result = apply_decision_engine(portfolio, inplace=True)\n    scored = decision_result.data\n    ai_confidence = portfolio_ai_confidence(scored)\n    flow_label, positive_share = capital_flow_label(scored)\n\n    return {\n        \"AI_Confidence\": ai_confidence,\n        \"AI_Confidence_Label\": confidence_label(ai_confidence),\n        \"Capital_Flow\": flow_label,\n        \"Positive_Momentum_Share\": positive_share,\n        \"Top_Decision_Asset\": decision_result.top_asset,\n        \"Top_Decision_Score\": decision_result.top_score,\n        \"Actions\": build_action_table(scored),\n    }\n",
    "def decision_summary(portfolio: pd.DataFrame) -> dict[str, object]:\n    \"\"\"Aggregér dashboard-signaler fra det allerede scorede Decision Engine-output.\"\"\"\n    required = {\"Decision_Score\", \"Decision_Status\", \"Handling\"}\n    if not required.issubset(portfolio.columns):\n        raise ValueError(\n            \"decision_summary kræver output fra apply_decision_engine først.\"\n        )\n\n    scored = portfolio\n    ordered = scored.sort_values(\n        [\"Decision_Score\", \"AI_Confidence\", \"Composite\"],\n        ascending=[False, False, False],\n        na_position=\"last\",\n    )\n    top_asset = str(ordered.iloc[0].get(\"Name\", \"Ukendt\")) if not ordered.empty else None\n    top_score = (\n        float(ordered.iloc[0][\"Decision_Score\"])\n        if not ordered.empty and pd.notna(ordered.iloc[0][\"Decision_Score\"])\n        else np.nan\n    )\n    ai_confidence = portfolio_ai_confidence(scored)\n    flow_label, positive_share = capital_flow_label(scored)\n\n    return {\n        \"AI_Confidence\": ai_confidence,\n        \"AI_Confidence_Label\": confidence_label(ai_confidence),\n        \"Capital_Flow\": flow_label,\n        \"Positive_Momentum_Share\": positive_share,\n        \"Top_Decision_Asset\": top_asset,\n        \"Top_Decision_Score\": top_score,\n        \"Actions\": build_action_table(scored),\n    }\n",
)

# Opportunities er nu kun et view/ranking af eksisterende Decision Engine-output.
changed |= replace_once(
    "modules/opportunity_engine.py",
    "    # Kør samme motor med de aktive Settings-vægte. Inplace sikrer, at alle\n    # efterfølgende faner (Portfolio Doctor/Rebalancering/Momentum) læser det\n    # samme autoritative output fra analytics_portfolio.\n    decision = apply_decision_engine(\n        portfolio,\n        factor_weights=factor_weights,\n        max_position_weight=max_position_weight,\n        inplace=True,\n    )\n    result = decision.data.copy()\n",
    "    required = {\"Decision_Score\", \"Decision_Status\", \"Handling\"}\n    if not required.issubset(portfolio.columns):\n        raise ValueError(\n            \"Opportunities kræver output fra den centrale Decision Engine først.\"\n        )\n    result = portfolio.copy()\n",
)

print("6.9 consolidation patch applied" if changed else "6.9 consolidation already applied")
