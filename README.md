# Investment OS 7.3.3

Denne version indfører:

- Én masterfil: `data/AI_portfolio.xlsx`
- Automatisk pris- og valutahentning via yfinance
- DKK-kostpris, markedsværdi og valutaeffekt
- Momentum: 1W, 1M, 3M, 6M og 12M
- Grafisk Sharpe-udvikling: 30, 90 og 252 handelsdage
- Fokuseret fanestruktur uden heatmap
- Selvstændige faner til Emerging Compounders og Watchlist
- Fælles styling, hvor alle negative tabelværdier vises rødt
- Gauges for porteføljesundhed, konfidens, datakvalitet og Macro/Rate Risk
- Macro/Rate Regime som forklarende risikofaktor i Decision Engine. Overlayet
  ændrer ikke `Decision_Score`, `Decision_Status`, `Handling` eller rebalancering.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Jarvis API

API'et er et read-only lag oven på `data/portfolio_snapshot.json`. Det
genberegner ikke signaler og ændrer ikke portefølje, beslutninger eller handler.

```bash
uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Første kontrakter:

- `GET /v1/system/status`
- `GET /v1/portfolio/status`
- `GET /v1/briefs/investment`
- `GET /v1/stocks/{ticker}`
- `GET /v1/research/stocks/{ticker}`

`/v1/briefs/investment` leverer det strukturerede grundlag for kommandoen
"Giv mig min investeringsbrief": KPI'er, eksisterende decision queue, de tre
højest rangerede opportunities, opmærksomhedspunkter og sporbarhed. Endpointet
formidler kun felter fra snapshot'et og ændrer ikke signaler eller handlinger.
Fra andet snapshot indeholder briefen også observerede KPI-deltaer, ændringer i
`Handling`, `Decision_Status` og `Decision_Score` samt ind- og udtræden eller
rangændringer blandt opportunities. Første snapshot markeres med
`NO_PREVIOUS_SNAPSHOT`.

Jarvis-kommandoadapteren kaldes med:

```http
POST /v1/jarvis/command
Content-Type: application/json

{"command": "Giv mig min investeringsbrief"}
```

Svaret indeholder et kort dansk `message` samt det komplette strukturerede
`data`-grundlag. Kommandoer uden for de godkendte MVP-intents afvises. Intentet
`stock_analysis` slår tickeren op i snapshot'ets positioner, opportunities og
watchlist og gengiver kun eksisterende Investment OS-data. Hvis en watchlistaktie
som CLS endnu ikke har momentum- og Decision Engine-signaler, oplyses dette
eksplicit i stedet for at estimere dem.

Aktieanalysen kan suppleres med et separat fundamentalt research-snapshot fra
Yahoo Finance via den installerede `yfinance`-adapter. Researchdata har egen
kilde, hentetid, feltdækning, warnings og en seks timers cache. De præsenteres
kun som kontekst og kan ikke ændre Investment OS' `Decision_Score`, `Handling`
eller andre signaler. Ved kildefejl leverer Jarvis fortsat OS-status og markerer
research som utilgængelig; findes et ældre cachet snapshot, returneres dette med
freshness `stale`.

API-svarene indeholder `schema_version`, `request_id`, `run_id`,
`generated_at`, data-freshness og maskinlæsbare warnings. Et indgående
`X-Request-ID` bevares, så Jarvis-kald kan spores gennem kæden.

## Vigtig databegrænsning

Historisk valutakurs ved køb er endnu ikke udfyldt for alle udenlandske
positioner. Indtil den foreligger, anvender modellen den aktuelle FX-kurs
som fallback. Dashboardet markerer dette i datakvaliteten.
