# Markedsuro – VIX on Overblik

The overview replaces the Datakvalitet gauge with raw VIX index points.
VIX reflects annualized expected 30-day S&P 500 volatility. It is not a 0–100
Fear & Greed score. The gauge defaults to 0–50 and expands for higher values;
values above 100 remain intact. It displays two decimals, without /100 or %.

IOS display zones (not official Cboe categories): <15 Lav, 15–<20 Moderat,
20–<30 Forhøjet, 30–<40 Høj, >=40 Meget høj. These are descriptive conventions,
not investment recommendations. Data quality, decision weights, health,
promotion gates and snapshots are unchanged; VIX is display-only.

Primary: https://fred.stlouisfed.org/series/VIXCLS
CSV: https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS
Fallback: https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv
Source notes: https://www.cboe.com/tradable_products/vix/vix_historical_data

Both feeds are daily closing observations, not realtime. The observation date
and actual selected source are shown beside the gauge. FRED's blank/dot rows
are skipped. The latest dated positive finite value is selected without assuming
row order. Future dates, malformed data and observations over five calendar
days old are rejected. The five-day allowance accommodates weekends/holidays.
A valid FRED response is used directly; Cboe is consulted only if FRED fails
or is stale, not to promise the freshest observation between the two feeds.

Streamlit caches success and failure for 15 minutes during app use (no background
scheduler). Each provider gets one five-second-timeout request with a 2 MB
response limit. If both fail, a gray N/A gauge has no pointer or invented value.
No API key, browser impersonation, access-control bypass or CNN dependency.

FRED identifies Cboe as the source and marks VIX data as copyrighted. Public
technical access is not a blanket redistribution license. Preserve source
attribution and review applicable Cboe/FRED terms for public redistribution.
Tests use synthetic CSV fixtures and mocked requests.
