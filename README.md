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
- `GET /v1/system/operations`
- `GET /v1/portfolio/status`
- `GET /v1/portfolio/signals`
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

`/v1/portfolio/signals` er Decision/Signal Layer v0.1. Endpointet projekterer
de autoritative `Decision_Score`, `Decision_Status`, `Handling`, confidence,
momentumfelter og faktorscorer direkte fra snapshot'et. Hvert signal har et
deterministisk signal-ID pr. snapshot, evidencereferencer og kildeangivelse.
API'et genberegner ikke felterne. Stale snapshots, manglende kernefelter eller
dublerede tickere giver `decision_readiness: insufficient`; manglende,
ikke-kritiske faktorscorer giver `limited`.

Den deterministiske Jarvis-kommando kan eksempelvis kaldes med:

```json
{"command": "Vis mine investeringssignaler"}
```

### Jarvis audit-log

Alle kald til `POST /v1/jarvis/command` registreres i en append-only JSONL-log.
Hvert event indeholder request/run ID, versioner, freshness, datakvalitet,
maskinlæsbare årsagskoder, latency og resultat. Kommandoens tekst, den fulde
API-payload, porteføljepositioner, fritekstbegrundelser, filstier og credentials
gemmes ikke. Logfilen oprettes med owner-only-rettigheder, hvor operativsystemet
understøtter det.

Standardplacering:

```text
logs/jarvis_audit.jsonl
```

Placeringen kan sættes uden for repositoryet med miljøvariablen
`JARVIS_AUDIT_LOG`. Hvis et event ikke kan gemmes, gennemføres det read-only
kald, og svaret markeres med `AUDIT_LOG_UNAVAILABLE`.

### API-sikkerhed

I standardtilstanden `development` kan API'et kun bruges uden token fra
localhost. Sættes `JARVIS_API_TOKEN`, kræves tokenet også lokalt. Alle `/v1/`
endpoints beskyttes; `/healthz` er en offentlig liveness-probe uden portefølje-,
versions- eller repositorydata.

Development uden token må kun bindes direkte til `127.0.0.1` og må ikke
eksponeres via `0.0.0.0` eller en reverse proxy. Brug production-konfigurationen
ved enhver netværkseksponering.

Production er fail-closed og kræver følgende miljøvariable:

```text
JARVIS_ENV=production
JARVIS_API_TOKEN=<tilfældigt token på mindst 32 tegn>
JARVIS_RATE_LIMIT_PER_MINUTE=<positivt heltal valgt for deploymentet>
JARVIS_AUDIT_LOG=/absolut/sti/på/persistent-volume/jarvis_audit.jsonl
JARVIS_AUDIT_PERSISTENT=true
```

Tokenet sendes som `Authorization: Bearer <token>`. Det gemmes ikke i kode,
API-svar eller audit-log. Rate-limit har bevidst ingen skjult production-default;
deploymentet skal vælge værdien eksplicit. Afviste adgangs- og rate-limit-kald
auditeres uden credentials, rå URL eller forespørgselsindhold.

Alle API-svar markeres `no-store` og får sikkerhedsheaders. En fejlagtig
production-konfiguration giver `SECURITY_CONFIGURATION_INVALID` frem for at
starte i en usikker fallback-tilstand.

### Production readiness og drift

`/healthz` er en offentlig liveness-probe, der alene bekræfter, at processen
svarer. `/readyz` er en offentlig, dataminimeret readiness-probe. Den svarer
først `200 ready`, når sikkerhedskonfigurationen er gyldig, snapshot-kontrakten
kan læses, og audit-loggen er konfigureret til en skrivbar persistent placering.
Ellers svarer den `503 not_ready`. Ingen af proberne viser secrets, filstier,
versionsnumre, commit-ID'er eller porteføljedata.

Auditmappen skal oprettes af deploymentet og være et persistent volume. Flaget
`JARVIS_AUDIT_PERSISTENT=true` er en eksplicit deployment-erklæring; Jarvis kan
kontrollere sti og skriveadgang, men kan ikke selv bevise storage-mediets
levetid.

Anbefalet production-proces for den nuværende single-user MVP:

```bash
uvicorn api.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Processen eksponeres gennem en TLS-terminerende reverse proxy. Ved ændringer i
miljøvariable eller mount genstartes den samme proces via deploymentets process
manager. Derefter køres smoke-testen:

```bash
JARVIS_BASE_URL=https://jarvis.example \
python scripts/smoke_test_jarvis_api.py
```

Smoke-testen bruger `JARVIS_API_TOKEN` fra miljøet og verificerer `/healthz`,
`/readyz` og det autentificerede `/v1/system/status` uden at udskrive tokenet.

### Operationelle serviceindikatorer

`GET /v1/system/operations` sammenfatter de seneste 24 timers privacy-minimerede
audit-events. Svaret viser observeret availability, p50/p95-latency samt antal
færdigbehandlede kommandoer, tekniske fejl, kommandoafvisninger og
adgangsafvisninger. Afviste kommandoer og adgangsforsøg tæller som behandlede
requests; kun tekniske fejl og 5xx-resultater reducerer availability.

Endpointet kontrollerer samtidig audit-schema, dublerede event-ID'er og tegn på
private payloadfelter. Privacy-målet er eksplicit nul hændelser. Der er endnu
ikke fastsat en availability-SLA, og status vises derfor som `unconfigured`
frem for at opfinde en tærskel. Indikatorerne er observerbarhed fra audit-loggen,
ikke ekstern uptime-monitorering, og rå audit-events returneres aldrig.

Alle autentificerede `/v1/`-kald registreres nu som privacy-minimeret
request-telemetry med en fast endpoint-scope, HTTP-status og latency. Rå stier,
query-parametre, request bodies og credentials gemmes ikke. Jarvis-kommandoer
bevarer deres mere detaljerede kommando-event og dobbeltauditeres derfor ikke.
Tekniske 5xx-svar registreres som `jarvis.request.failed`; øvrige gennemførte
API-kald registreres som `jarvis.request.completed`. Hvis telemetry ikke kan
gemmes, markeres svaret med headeren `X-Jarvis-Audit-Status: unavailable`.

## Vigtig databegrænsning

Historisk valutakurs ved køb er endnu ikke udfyldt for alle udenlandske
positioner. Indtil den foreligger, anvender modellen den aktuelle FX-kurs
som fallback. Dashboardet markerer dette i datakvaliteten.
