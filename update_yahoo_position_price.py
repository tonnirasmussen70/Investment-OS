from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

old_caption = '''    st.caption("Aktier og ETF'er vises separat. Dags kurs og markedsværdi følger Saxo/masterfilen, når de findes; Yahoo bruges til momentum og tekniske analyser samt som fallback. Vægten beregnes mod den samlede porteføljeværdi ekskl. Grundfos.")'''
new_caption = '''    st.caption("Aktier og ETF'er vises separat. Dags kurs hentes fra Yahoo, mens markedsværdi DKK følger Saxo/masterfilen, når den findes. Vægten beregnes mod den samlede porteføljeværdi ekskl. Grundfos.")'''
if old_caption not in text:
    raise RuntimeError("Kunne ikke finde Positioner-caption")
text = text.replace(old_caption, new_caption, 1)

old_price = '''    master_price = (\n        pd.to_numeric(position_source["Master_Current_Price"], errors="coerce")\n        if "Master_Current_Price" in position_source.columns\n        else pd.Series(np.nan, index=position_source.index)\n    )\n    live_price = pd.to_numeric(position_source["Current_Price"], errors="coerce")\n    position_source["Position_Display_Price"] = master_price.combine_first(live_price)\n    position_source["Position_Price_Source"] = np.where(\n        master_price.notna(), "Master/Saxo", "Yahoo live fallback"\n    )'''
new_price = '''    live_price = pd.to_numeric(position_source["Current_Price"], errors="coerce")\n    master_price = (\n        pd.to_numeric(position_source["Master_Current_Price"], errors="coerce")\n        if "Master_Current_Price" in position_source.columns\n        else pd.Series(np.nan, index=position_source.index)\n    )\n    position_source["Position_Display_Price"] = live_price.combine_first(master_price)\n    position_source["Position_Price_Source"] = np.where(\n        live_price.notna(), "Yahoo", "Master/Saxo fallback"\n    )'''
if old_price not in text:
    raise RuntimeError("Kunne ikke finde Positioner-prislogik")
text = text.replace(old_price, new_price, 1)

APP.write_text(text, encoding="utf-8")
print("Positioner dagskurs ændret til Yahoo")
