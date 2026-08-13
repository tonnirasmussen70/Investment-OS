from pathlib import Path

# One-off patch: keep engine precision, format visible scores as integers.
path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_momentum = '''        table["AI"] = table["AI"].apply(\n            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"\n        )\n\n        st.dataframe(\n'''
new_momentum = '''        table["AI"] = table["AI"].apply(\n            lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"\n        )\n        table["Score"] = table["Score"].apply(lambda x: score_text(x, 0))\n\n        st.dataframe(\n'''

old_rebalance = '''            display["AI"] = display["AI"].apply(\n                lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"\n            )\n            display = display.rename(columns={"Composite": "Momentum"})\n'''
new_rebalance = '''            display["AI"] = display["AI"].apply(\n                lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A"\n            )\n            display["Decision Score"] = display["Decision Score"].apply(\n                lambda x: score_text(x, 0)\n            )\n            display = display.rename(columns={"Composite": "Momentum"})\n'''

if new_momentum not in text:
    if old_momentum not in text:
        raise SystemExit("Momentum score formatting target not found")
    text = text.replace(old_momentum, new_momentum, 1)

if new_rebalance not in text:
    if old_rebalance not in text:
        raise SystemExit("Rebalance score formatting target not found")
    text = text.replace(old_rebalance, new_rebalance, 1)

path.write_text(text, encoding="utf-8")
print("Score displays formatted as integers")
