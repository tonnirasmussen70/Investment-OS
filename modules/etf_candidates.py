"""Streamlit presentation for the automatically updated Yahoo ETF radar."""
from pathlib import Path

import pandas as pd

from modules.etf_radar import load_or_refresh_etf_radar, load_universe


CANDIDATE_LIMIT = 10


def render_etf_candidates(st, data_dir="data"):
    st.markdown("### ETF-kandidater — top 10")
    st.caption("UCITS-aktie-ETF'er rangeret efter momentum og risiko. Kurskilde: Yahoo Finance. justETF og udstederen bruges som fondreferencer.")
    cached_load = st.cache_data(ttl=3600, show_spinner=False)(load_or_refresh_etf_radar)
    force = st.button("Opdater ETF-radar", key="refresh_etf_radar")
    if force:
        cached_load.clear()
    with st.spinner("Indlæser ETF-radar …"):
        radar = cached_load(str(data_dir), force=force)
    for note in radar.notes:
        st.warning(note)
    if radar.data.empty:
        st.info("Ingen verificerede Yahoo-kursdata til ETF-rangeringen endnu. Prøv Opdater ETF-radar, når Yahoo-forbindelsen er tilgængelig.")
    else:
        st.caption(f"Viser {min(CANDIDATE_LIMIT, len(radar.data))} af {len(radar.data)} fonde i det valgte univers. Fælles kursdato: {radar.as_of}. Hentet: {pd.Timestamp(radar.generated_at).strftime('%Y-%m-%d %H:%M UTC')}.")
        if (pd.Timestamp.now(tz="UTC").normalize() - pd.Timestamp(radar.as_of, tz="UTC")).days > 7:
            st.warning("ETF-kurserne er mere end 7 dage gamle. Brug ikke listen som en aktuel rangering.")
        display = radar.data.head(CANDIDATE_LIMIT).copy()
        for column in ("Return_1M", "Return_3M", "Return_6M", "Volatility_3M", "Max_Drawdown_6M"):
            display[column] *= 100
        columns = ["Name", "Ticker", "Exposure", "Score", "Return_1M", "Return_3M", "Return_6M",
                   "Volatility_3M", "Max_Drawdown_6M", "Research_Status", "ISIN", "justETF", "Yahoo"]
        st.dataframe(display[columns], hide_index=True, use_container_width=True, column_config={
            "Name": "ETF", "Exposure": "Eksponering", "Score": st.column_config.NumberColumn("Score / 100", format="%.1f"),
            **{key: st.column_config.NumberColumn(label, format="%.2f %%") for key, label in (
                ("Return_1M", "1 md. EUR"), ("Return_3M", "3 mdr. EUR"), ("Return_6M", "6 mdr. EUR"),
                ("Volatility_3M", "Volatilitet, årlig"), ("Max_Drawdown_6M", "Maks. fald, 6 mdr."))},
            "Research_Status": "Researchstatus", "justETF": st.column_config.LinkColumn("justETF", display_text="Profil"),
            "Yahoo": st.column_config.LinkColumn("Yahoo", display_text="Kurser"),
        })
    with st.expander("ETF-metode og univers"):
        st.markdown("**Momentum 70 %:** 1 måned 20 %, 3 måneder 25 % og 6 måneder 25 %. **Risiko 30 %:** lavere volatilitet 15 % og mindre maksimalt kursfald 15 %.")
        st.caption("Hver faktor rangeres relativt til hele universet; score er ikke et forventet afkast. 1/3/6 måneder svarer til 21/63/126 fælles handelsdage. Volatilitet beregnes over 63 dage og omregnes til år; maksimalt fald måles over 126 dage. Justerede EUR-lukkekurser tager højde for udlodninger og split. Dagens kursbar bruges ikke.")
        st.caption("Automatisk opdatering forsøges efter 6 timer, når IOS kører (resultatet genbruges i op til 1 time mellem visninger). Opdater-knappen henter straks. Et ugentligt GitHub-workflow kan vedligeholde det gemte snapshot. Alle fonde skal have gyldige data, før seneste snapshot erstattes.")
        st.caption("Universet er et udvalgt research-univers, ikke hele ETF-markedet eller en diversificeret modelportefølje. ETF'er kan have overlappende beholdninger. EUR-notering er ikke det samme som valutaafdækning. Metoden er ikke backtestet og giver ikke købsordrer.")
        try:
            funds = pd.DataFrame(load_universe(Path(data_dir) / "etf_universe.json"))
        except (OSError, ValueError, TypeError, AttributeError):
            return
        funds["justETF"] = "https://www.justetf.com/en/etf-profile.html?isin=" + funds["ISIN"]
        st.dataframe(funds[["Name", "Ticker", "ISIN", "Exposure", "Issuer_Source", "justETF"]], hide_index=True,
                     use_container_width=True, column_config={"Name": "ETF", "Exposure": "Eksponering",
                     "Issuer_Source": st.column_config.LinkColumn("Udsteder", display_text="Fondreference"),
                     "justETF": st.column_config.LinkColumn("justETF", display_text="Profil")})
