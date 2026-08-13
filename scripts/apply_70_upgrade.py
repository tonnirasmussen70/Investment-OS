from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Expected block not found in {path}:\n{old}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# Appen er allerede visuelt migreret til 7.0. Denne migration låser den
# autoritative execution-kæde fast:
# Decision Engine -> Rebalancering -> Decision Queue / Overblik.
replace_once(
    "app.py",
    '''decision_queue = build_decision_queue(\n    portfolio_doctor.data,\n    opportunity_result.data,\n    max_items=5,\n)\n\nrebalance_result = build_rebalance_plan(\n    analytics_portfolio,\n    active_market_value_dkk=return_market_value,\n    max_position_weight=config.max_position_weight,\n    max_sector_weight=config.max_sector_weight,\n    minimum_trade_dkk=MINIMUM_TRADE_DKK,\n)\n''',
    '''rebalance_result = build_rebalance_plan(\n    analytics_portfolio,\n    active_market_value_dkk=return_market_value,\n    max_position_weight=config.max_position_weight,\n    max_sector_weight=config.max_sector_weight,\n    minimum_trade_dkk=MINIMUM_TRADE_DKK,\n)\n\ndecision_queue = build_decision_queue(\n    rebalance_result.data,\n    max_items=5,\n)\n''',
)

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
    '''        action_table = queue_overview[\n            ["Prioritet", "Handling", "Aktiv", "Beløb DKK", "Decision Score", "Begrundelse"]\n        ].copy()\n''',
    '''        action_table = queue_overview[\n            ["Prioritet", "Execution", "Aktiv", "Beløb DKK", "Decision Score", "Begrundelse"]\n        ].copy()\n''',
)

replace_once(
    "app.py",
    '''        action_table = action_table.rename(\n            columns={"Beløb DKK": "Beløb", "Decision Score": "Score"}\n        )\n''',
    '''        action_table = action_table.rename(\n            columns={\n                "Execution": "Handling",\n                "Beløb DKK": "Beløb",\n                "Decision Score": "Score",\n            }\n        )\n''',
)

# Standalone snapshot-generator skal bruge samme execution-plan og queue.
replace_once(
    "scripts/generate_portfolio_snapshot.py",
    '''    queue = build_decision_queue(doctor.data, opportunity_result.data, max_items=5)\n    rebalance = build_rebalance_plan(\n        analytics_portfolio,\n        active_market_value_dkk=active_value,\n        max_position_weight=config.max_position_weight,\n        max_sector_weight=config.max_sector_weight,\n        minimum_trade_dkk=MINIMUM_TRADE_DKK,\n    )\n''',
    '''    rebalance = build_rebalance_plan(\n        analytics_portfolio,\n        active_market_value_dkk=active_value,\n        max_position_weight=config.max_position_weight,\n        max_sector_weight=config.max_sector_weight,\n        minimum_trade_dkk=MINIMUM_TRADE_DKK,\n    )\n    queue = build_decision_queue(rebalance.data, max_items=5)\n''',
)

print("Investment OS 7.0 execution chain integrated")
