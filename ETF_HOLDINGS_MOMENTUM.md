# ETF Momentum Breadth – Light

This is an **optional, diagnostic-only** indicator for the ETF recommended in
Investment OS > Overblik > Vis beslutningsdetaljer. It does not change the
Decision Engine score or KØB/HOLD/AFVENT actions.

For a covered ETF, manually save its *latest top 10 holdings* in
`data/etf_holdings/<Yahoo_Ticker>.csv` (e.g. `IS3Q.DE.csv`).
CSV schema: `Ticker` (required; 10 unique Yahoo Finance-compatible equity
symbols, ranked by holding size). Optional `Name` column is ignored.
Record the issuer/justETF source and holdings as-of date when updating the file.
Refresh approximately quarterly, or after a known index reconstitution.

The app loads adjusted Yahoo closing prices for the 10 stocks, compares the
most recent close with the close 21 trading days earlier, and counts strictly
positive returns. No weights, currencies, official attribution or new scheduled
downloader are required.

* Bredt: 7–10 positive stocks.
* Blandet: 4–6 positive stocks.
* Smalt: 0–3 positive stocks.
* Ikke tilgængelig: missing top-ten list, any missing/insufficient/stale prices,
  or invalid input. The app does **not** label incomplete top-ten data as Smalt.

This measures breadth of rising constituents, **not** breadth of weighted
contributions to the ETF's total return.
