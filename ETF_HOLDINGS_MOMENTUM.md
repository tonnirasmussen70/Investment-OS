# ETF Holdings Momentum Attribution

In Overview > Next recommended action > Decision details, the ETF panel
shows an explanatory constituent breadth assessment when approved holdings
are available.

Input: data/etf_holdings/<Yahoo_Ticker>.csv with Ticker,Weight,Name;
Weight in decimal fractions, e.g. 0.065 means 6.5%. Yahoo-compatible symbols.
Preserve holdings source and as-of date in an adjacent note.

Shows top 20 constituents, 1W/1M/3M adjusted returns, contribution proxies,
price coverage, positive-weight breadth, top 3 share of positive contributions
and effective number of positive contributors.

Bredt: breadth >=70% and top3 <=50%.
Smalt: breadth <40% or top3 >=75%.
Blandet: remaining.
Utilstrækkelige data: fewer than ten valid constituents or <80% weight coverage.

Returns are in constituent quotation currencies. Results do not reflect
historical index weight drift, FX moves or rebalancing; they are diagnostic,
not official fund performance attribution. No impact on trading signals.
