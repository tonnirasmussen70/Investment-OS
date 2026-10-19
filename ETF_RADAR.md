# Emerging Compounders: stock top 10 and Yahoo ETF radar

The stock table, summary KPIs and Promotion Queue now use the first ten rows
of the existing Discovery Score ranking. Other consumers retain the full
underlying radar dataset.

The separate ETF list no longer requires CSV uploads. `data/etf_universe.json`
defines 16 curated UCITS equity ETFs with one EUR Xetra listing per ISIN,
exposure labels and issuer references. justETF remains a per-fund reference.
This is a deliberately limited starting universe, not whole-market discovery,
personal suitability screening or a diversified allocation proposal. It does
not certify tax classification, broker availability, TER or fund liquidity.

## Calculation

`yfinance.Ticker.history(period="1y", interval="1d", auto_adjust=True)` supplies
dividend/split-adjusted daily closing prices. Yahoo history metadata must
confirm EUR, ETF instrument type and the exact configured symbol. A EUR
trading currency does not imply that the underlying investments are hedged.
Fund identities are maintained against issuer references; Yahoo is the price
source, not the authoritative UCITS/ISIN reference.

All funds use the same completed session dates; today's bar is excluded.
At least 127 common price observations are required, with no gap exceeding
seven calendar days and no more than 195 calendar days spanning the last
126 common sessions. All funds must pass validation. A partial failure
retains the previous ranking instead of silently changing the peer group.

The first research model uses weighted cross-sectional percentile ranks:

| Factor | Definition | Weight | Preferred |
| --- | --- | --- | --- |
| 1-month momentum | Close / close 21 common sessions earlier - 1 | 20% | Higher |
| 3-month momentum | Close / close 63 common sessions earlier - 1 | 25% | Higher |
| 6-month momentum | Close / close 126 common sessions earlier - 1 | 25% | Higher |
| Volatility | Sample standard deviation of last 63 daily returns × sqrt(252) | 15% | Lower |
| Maximum drawdown | Lowest price / running peak - 1 in last 127 closes | 15% | Closer to zero |

Ranks are `(average_rank - 1) / (fund_count - 1)`, weighted and multiplied by
100. Equal factor values receive equal ranks (all equal -> 50). Ties in final
score use 6-month return descending, then ISIN ascending. All funds are scored
before the UI selects ten. The score is relative, not a probability, valuation
or expected return. Negative momentum is explicitly flagged even when a fund
has a high relative score. The model is not backtested; it issues no trades.

## Refresh and resilience

IOS attempts a refresh when the validated snapshot is at least six hours old.
Streamlit caches reads/results for one hour to avoid repeated failed downloads;
the refresh button clears this cache and forces a fetch. Visiting/rerunning IOS
triggers this check; it is not a background timer. Fresh calculated values can
be shown on a read-only deployment with a persistence warning.

`python scripts/generate_etf_radar.py` forces a refresh and atomically saves
`data/etf_radar.json`. The CLI exits nonzero on download, validation or storage
failure. Existing good bytes are retained on data failure. A malformed,
future-dated, incomplete or incompatible snapshot is never displayed. Genuine
old data may be displayed after network failure, with its original observation
and retrieval times and a stale warning after seven days. No example prices
or precomputed fabricated candidates are bundled.

`.github/workflows/etf_radar.yml` adds a weekly Sunday 07:15 UTC refresh plus
manual dispatch. The workflow becomes operational only after it is pushed to
GitHub; scheduled execution requires the default branch. Main-branch runs
commit only a successfully validated snapshot. Branch-dispatch runs calculate
without committing. The app itself can also initialize the snapshot when
Yahoo is reachable.

## Source and validation references

- yfinance history: https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html
- Metadata: https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.get_history_metadata.html
- Source use limitations: https://github.com/ranaroussi/yfinance
- ETF universe issuer URLs: `data/etf_universe.json` (reviewed 2026-10-19).
- justETF: https://www.justetf.com/en/search.html?search=ETFS&assetClass=class-equity

The tests cover known returns/risk, ranking, common dates, current-bar
exclusion, bad/insufficient histories, metadata checks, atomic last-good
fallback, incompatible/corrupt caches, read-only storage and UI top-ten output.
