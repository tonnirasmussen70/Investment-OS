from pathlib import Path

FILES = {
    "modules/portfolio_engine.py": Path("modules/portfolio_engine.py"),
    "app.py": Path("app.py"),
}


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Kunne ikke finde {label} i {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1) Bevar Saxo/master-kursen separat, før Yahoo live-data overskriver Current_Price.
replace_once(
    FILES["modules/portfolio_engine.py"],
    '''    # Yahoo ejer live kursdata og bruges til momentum/tekniske signaler samt som
    # fallback, hvis masterfilen ikke har en DKK-markedsværdi for en position.
    fetched_prices = df["Yahoo_Ticker"].map(snapshot.prices)
    manual_prices = (
        df["Current_Price"]
        if "Current_Price" in df.columns
        else pd.Series(np.nan, index=df.index)
    )
    df["Current_Price"] = fetched_prices.combine_first(manual_prices)
''',
    '''    # Yahoo ejer live kursdata til momentum/tekniske signaler. Saxo/master-
    # kursen bevares separat og bruges i Positioner, så depotvisningen matcher
    # den importerede Saxo-rapport.
    manual_prices = (
        pd.to_numeric(df["Current_Price"], errors="coerce")
        if "Current_Price" in df.columns
        else pd.Series(np.nan, index=df.index)
    )
    df["Master_Current_Price"] = manual_prices

    fetched_prices = df["Yahoo_Ticker"].map(snapshot.prices)
    df["Live_Current_Price"] = fetched_prices.combine_first(manual_prices)
    df["Current_Price"] = df["Live_Current_Price"]
''',
    "bevaring af master-kurs",
)


# 2) Positioner skal vise Saxo/master-kurs, mens analyser fortsat bruger Yahoo live.
replace_once(
    FILES["app.py"],
    '''    position_source["Market_Value_DKK"] = pd.to_numeric(position_source["Market_Value_DKK"], errors="coerce").fillna(0)
    grundfos_portfolio_mask = position_source["Name"].astype(str).str.contains("Grundfos", case=False, na=False)
''',
    '''    position_source["Market_Value_DKK"] = pd.to_numeric(position_source["Market_Value_DKK"], errors="coerce").fillna(0)
    master_price = (
        pd.to_numeric(position_source["Master_Current_Price"], errors="coerce")
        if "Master_Current_Price" in position_source.columns
        else pd.Series(np.nan, index=position_source.index)
    )
    live_price = pd.to_numeric(position_source["Current_Price"], errors="coerce")
    position_source["Position_Display_Price"] = master_price.combine_first(live_price)
    position_source["Position_Price_Source"] = np.where(
        master_price.notna(), "Master/Saxo", "Yahoo live fallback"
    )
    grundfos_portfolio_mask = position_source["Name"].astype(str).str.contains("Grundfos", case=False, na=False)
''',
    "positionskurs-kilde",
)

replace_once(
    FILES["app.py"],
    '''        table = section[["Name", "Quantity", "Purchase_Price", "Current_Price", "Sector", "Market_Value_DKK", "Portfolio_Weight_Ex_Grundfos", "Return_Pct", "Composite", "AI_Confidence"]].copy()
''',
    '''        table = section[["Name", "Quantity", "Purchase_Price", "Position_Display_Price", "Sector", "Market_Value_DKK", "Portfolio_Weight_Ex_Grundfos", "Return_Pct", "Composite", "AI_Confidence"]].copy()
''',
    "Positioner dagskurs",
)

replace_once(
    FILES["app.py"],
    '''    st.caption("Aktier og ETF'er vises separat, men vægten beregnes for begge tabeller mod den samlede porteføljeværdi ekskl. Grundfos. Grundfos vises uden vægt.")
''',
    '''    st.caption("Aktier og ETF'er vises separat. Dags kurs og markedsværdi følger Saxo/masterfilen, når de findes; Yahoo bruges til momentum og tekniske analyser samt som fallback. Vægten beregnes mod den samlede porteføljeværdi ekskl. Grundfos.")
''',
    "Positioner forklaring",
)

print("Saxo/master-kurser er nu autoritative i Positioner")
