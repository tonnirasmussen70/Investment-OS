from pathlib import Path

path = Path("modules/portfolio_engine.py")
text = path.read_text(encoding="utf-8")
old = '''    # Én autoritativ markedsværdi: Saxo/master først, Yahoo-estimat kun fallback.\n    df["Market_Value_DKK"] = df["Master_Market_Value_DKK"].combine_first(\n        df["Live_Market_Value_DKK"]\n    )\n    df["Market_Value_Source"] = np.where(\n        df["Master_Market_Value_DKK"].notna(),\n        "Master/Saxo",\n        "Yahoo live fallback",\n    )'''
new = '''    # Én autoritativ markedsværdi: Saxo/master først, Yahoo-estimat kun fallback.\n    # En nulværdi fra depot/master er ikke en gyldig markedsværdi for en aktiv\n    # position med positiv Quantity. Det forekommer bl.a. når en ny Saxo-position\n    # er oprettet uden beregnet DKK-værdi. Behandl derfor 0 som manglende i dette\n    # tilfælde, så Quantity × Yahoo-kurs × FX kan anvendes som fallback.\n    master_market_value = pd.to_numeric(\n        df["Master_Market_Value_DKK"], errors="coerce"\n    ).copy()\n    invalid_zero_master_value = (\n        pd.to_numeric(df["Quantity"], errors="coerce").fillna(0) > 0\n    ) & (master_market_value <= 0)\n    master_market_value = master_market_value.mask(invalid_zero_master_value)\n    df["Master_Market_Value_DKK"] = master_market_value\n\n    df["Market_Value_DKK"] = master_market_value.combine_first(\n        df["Live_Market_Value_DKK"]\n    )\n    df["Market_Value_Source"] = np.where(\n        master_market_value.notna(),\n        "Master/Saxo",\n        "Yahoo live fallback",\n    )'''
if old not in text:
    raise SystemExit("Target block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Updated modules/portfolio_engine.py")
