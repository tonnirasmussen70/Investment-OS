# Investment OS 3.0 – første fundament

Denne version indfører:

- Én masterfil: `data/AI_portfolio.xlsx`
- Automatisk pris- og valutahentning via yfinance
- DKK-kostpris, markedsværdi og valutaeffekt
- Momentum: 1W, 1M, 3M, 6M og 12M
- Grafisk Sharpe-udvikling: 30, 90 og 252 handelsdage
- Fokuseret fanestruktur uden heatmap
- Selvstændige faner til Emerging Compounders og Watchlist
- Fælles styling, hvor alle negative tabelværdier vises rødt

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Vigtig databegrænsning

Historisk valutakurs ved køb er endnu ikke udfyldt for alle udenlandske
positioner. Indtil den foreligger, anvender modellen den aktuelle FX-kurs
som fallback. Dashboardet markerer dette i datakvaliteten.
