from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

old = '''        section = section.sort_values(["Portfolio_Weight_Ex_Grundfos", "Name"], ascending=[False, True], na_position="last").reset_index(drop=True)

        total_market_value = section["Market_Value_DKK"].sum(skipna=True)
        total_weight = section["Portfolio_Weight_Ex_Grundfos"].sum(skipna=True)
        stock_subtotal_value = section.loc[~grundfos_mask, "Market_Value_DKK"].sum(skipna=True)
        grundfos_value = section.loc[grundfos_mask, "Market_Value_DKK"].sum(skipna=True)
        stock_subtotal_weight = section.loc[~grundfos_mask, "Portfolio_Weight_Ex_Grundfos"].sum(skipna=True)
'''

new = '''        section = section.sort_values(["Portfolio_Weight_Ex_Grundfos", "Name"], ascending=[False, True], na_position="last").reset_index(drop=True)

        # Sortering/reset_index ændrer DataFrame-indekset. Masken skal derfor
        # oprettes igen, så boolean-indekseringen matcher section 1:1.
        grundfos_mask = section["Name"].astype(str).str.contains(
            "Grundfos", case=False, na=False
        )

        total_market_value = section["Market_Value_DKK"].sum(skipna=True)
        total_weight = section["Portfolio_Weight_Ex_Grundfos"].sum(skipna=True)
        stock_subtotal_value = section.loc[~grundfos_mask, "Market_Value_DKK"].sum(skipna=True)
        grundfos_value = section.loc[grundfos_mask, "Market_Value_DKK"].sum(skipna=True)
        stock_subtotal_weight = section.loc[~grundfos_mask, "Portfolio_Weight_Ex_Grundfos"].sum(skipna=True)
'''

if old not in text:
    raise RuntimeError("Kunne ikke finde subtotal-blokken i app.py")

text = text.replace(old, new, 1)
APP.write_text(text, encoding="utf-8")
print("Positioner subtotal-mask rettet")
