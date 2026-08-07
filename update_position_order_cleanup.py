from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')

old_tabs = '''tabs = st.tabs([\n    "🏠 Overblik",\n    "📈 Momentum",\n    "💰 Kapitalflow",\n    "📋 Positioner",\n    "🔄 Rebalancering",\n    "🩺 Portfolio Doctor",\n    "🎯 Opportunities",\n    "🚀 Emerging Compounders",\n    "👀 Watchlist",\n    "⚙️ Settings",\n])\n(\n    tab_overview, tab_momentum, tab_capital_flow, tab_positions, tab_rebalance,\n    tab_doctor, tab_opportunity, tab_compounders, tab_watchlist, tab_settings,\n) = tabs'''

new_tabs = '''tabs = st.tabs([\n    "🏠 Overblik",\n    "📈 Momentum",\n    "📋 Positioner",\n    "🔄 Rebalancering",\n    "💰 Kapitalflow",\n    "🩺 Portfolio Doctor",\n    "🎯 Opportunities",\n    "🚀 Emerging Compounders",\n    "👀 Watchlist",\n    "⚙️ Settings",\n])\n(\n    tab_overview, tab_momentum, tab_positions, tab_rebalance, tab_capital_flow,\n    tab_doctor, tab_opportunity, tab_compounders, tab_watchlist, tab_settings,\n) = tabs'''

if old_tabs not in text:
    raise RuntimeError('Kunne ikke finde tabs-blokken')
text = text.replace(old_tabs, new_tabs, 1)

old_weight = '''        include_weight = section["Include_Weight"].fillna(False)\n        active_value = pd.to_numeric(\n            section.loc[include_weight, "Market_Value_DKK"], errors="coerce"\n        ).fillna(0).sum()'''
new_weight = '''        include_weight = section["Include_Weight"].fillna(False)\n        # Grundfos skal altid holdes helt ude af aktiv vægtning, uanset datakilden.\n        grundfos_mask = section["Name"].astype(str).str.contains(\n            "Grundfos", case=False, na=False\n        )\n        include_weight = include_weight & ~grundfos_mask\n        active_value = pd.to_numeric(\n            section.loc[include_weight, "Market_Value_DKK"], errors="coerce"\n        ).fillna(0).sum()'''
if old_weight not in text:
    raise RuntimeError('Kunne ikke finde vægtningsblokken')
text = text.replace(old_weight, new_weight, 1)

old_qty = '''        table["Antal"] = table["Antal"].apply(\n            lambda x: f"{float(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")\n            if pd.notna(x) else "N/A"\n        )\n        for col in ["Åben kurs", "Dags kurs"]:\n            table[col] = table[col].apply(\n                lambda x: format_score(x, 2) if pd.notna(x) else "N/A"\n            )'''
new_qty = '''        table["Antal"] = table["Antal"].apply(\n            lambda x: compact_dkk(x) if pd.notna(x) else "N/A"\n        )\n        for col in ["Åben kurs", "Dags kurs"]:\n            table[col] = table[col].apply(\n                lambda x: compact_dkk(x) if pd.notna(x) else "N/A"\n            )'''
if old_qty not in text:
    raise RuntimeError('Kunne ikke finde formateringsblokken')
text = text.replace(old_qty, new_qty, 1)

APP.write_text(text, encoding='utf-8')
print('Positioner og faner opdateret')
