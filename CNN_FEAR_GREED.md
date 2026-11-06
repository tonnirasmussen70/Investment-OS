# CNN Fear & Greed on Overblik

Only the overview data-quality gauge is replaced. Data-quality calculations,
decision weights, portfolio health, promotion gates and snapshots are unchanged.
CNN sentiment does not feed a trading/decision model.

Source: https://edition.cnn.com/markets/fear-and-greed

Optional public JSON: https://production.dataviz.cnn.io/index/fearandgreed/graphdata

Only `fear_and_greed.score` is accepted, as a finite number from 0 to 100.
The provider timestamp must include a timezone, be no more than five days old
(allowing weekends/holidays) and no more than five minutes in the future.
The source timestamp is displayed in UTC. Five labeled color zones cover
0–25, >25–45, >45–55, >55–75, >75–100. Sentiment is not a buy recommendation.

Streamlit caches results (including failures) for 15 minutes. Each cache miss
makes one request with a five-second timeout and a one-megabyte response limit.
HTTP errors, blocked access, malformed payloads and stale data show a gray N/A
gauge without a pointer. No neutral value, substitute provider or stale successful
response is silently passed off as current CNN data.

## Access and source-use check, 2026-11-06

A direct public endpoint request returned HTTP 418, “You're a bot”. The search
tool recognized JSON at that URL but exposed no payload. CNN's page and terms
at https://www.cnn.com/terms were blocked to the search tool by robots.txt.
Live payload compatibility and permission for automated reuse therefore could
not be confirmed. This endpoint is undocumented in this project and has no
assumed availability guarantee. The implementation does not impersonate a
browser, bypass access restrictions, use credentials, or retry blocked requests.
Source attribution is shown beside the gauge. Attribution does not confer a
reuse license; review CNN's applicable terms/permission before redistributing
CNN data or relying on this integration in a public deployment.

Tests use synthetic payloads and mocked requests, not live CNN availability.
