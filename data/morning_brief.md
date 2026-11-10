# Investment OS – Morgenbrief
**Tirsdag 10. november 2026 · ca. 06.55 CET · ingen handler udført**

## A. Executive view
**Markedsregime: kraftigt rebound, men endnu ikke bekræftet ny optrend.** Mandag steg S&P 500 2,35 %, Nasdaq 2,74 % og halvlederindekset SOX 6,9 %. Faldende olie lettede inflationsbekymringerne, mens Nvidia faldt imod markedet. [Reuters, 9/11](https://www.reuters.com/business/wall-st-futures-rise-after-rough-week-nvidia-unsettles-investors-2026-11-09/).

**Investment OS:** Portfolio Health **54,17**, AI Confidence **52,88 (moderat)** og Macro/Rate Risk **50,29 (høj)** med kun **45/100** i makrodatakvalitet. Modellen foreslår tre køb for **60.002 kr.**, men ingen reduktion. **Prioritet: afvent køb og gennemgå koncentration, stop-signaler og likviditet.**

## B. Portfolio status
**Autoritativ kilde:** [portfolio_snapshot.json, main](https://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json), læst direkte.

| Snapshotkontrol | Værdi |
|---|---|
| generated_at | `2026-11-10T05:11:22.638708+01:00` |
| source.commit_sha | `aeabfd6c42a5916fb6fdbf11712e5cf72231b8cf` |
| source.portfolio_file_sha256 | `f70dce9a2a92c2f98f26d62eb3e63964056e5002c3bde9254929af2c8ddd3514` |
| data_quality.score | **100/100** |
| Porteføljeværdi | **1.167.269 kr.** |
| Aktiv markedsværdi | **735.149 kr.** |
| Modelafkast | **-2,88 %** |
| Portfolio Health / AI Confidence | **54,17 / 52,88** |
| Macro/Rate Risk | **50,29 – høj** |
| Positioner registreret / analyseret | **29 / 28** |
| Positionsloft | **16,00 %** |

Snapshotet er omkring 1 time og 45 minutter gammelt og **ikke stale**. Største positioner (% af aktiv værdi): Novo **16,05**, NKT **7,80**, Microsoft **6,86**, AL Sydbank **6,76**, VWCE **6,41**, ASML **5,22**, Danske Bank **4,88**, VGWD **4,52**, Celestica **4,44**, IS3Q **4,05**.

Novo overskrider loftet marginalt (**0,05 procentpoint**); modellen undlader reduktion på grund af **minimumshandel**. De to danske banker vejer **11,64 %** tilsammen. Teknologieksponeringen overlapper mellem direkte aktier og globale/tematiske ETF'er. Forskellen på **432.120 kr.** mellem total og aktiv værdi er **ikke dokumenteret fri likviditet**.

## C. Markedsstatus og makro
| Indikator | Seneste verificerede observation |
|---|---|
| S&P 500, 9/11 | **7.549,94 (+2,35 %)** |
| Nasdaq, 9/11 | **25.253,14 (+2,74 %)** |
| Dow, 9/11 | **52.389,75 (+2,15 %)** |
| SOX, 9/11 | **+6,9 %** |
| USA 10-årig rente, IOS pr. 9/11 | **4,864 %** |
| USA 2-årig rente | **N/A** |
| EUR/USD, EUR/DKK | **N/A** (ingen samtidig verificeret kurs) |
| Olie | **Faldende 9/11**; sammenlignelig aktuel Brent/WTI-kurs **N/A** |
| Guld, kobber | **N/A** (ingen verificeret samtidig morgenkurs) |

[Reuters, amerikansk lukning 9/11](https://www.reuters.com/business/wall-st-futures-rise-after-rough-week-nvidia-unsettles-investors-2026-11-09/). Den brede stigning støtter risikovilligheden, men er ikke tilstrækkelig dokumentation for et varigt trendskifte. Makromodellen mangler US2Y, rentekurve, inflation og kreditspænd.

## D. Sektor- og kapitalstrømsrotation
**IOS-momentum; dette er ikke målte ETF-nettoflows:**

| Tema | Ticker | 1M | 3M | IOS |
|---|---|---:|---:|---|
| Semiconductors | SEC0 | -27,2 % | -18,5 % | Reducer |
| Defense | DFEN | -3,1 % | -16,7 % | Reducer |
| Uranium | URNU | -17,7 % | -28,8 % | Reducer |
| Clean energy | IQQH | -3,1 % | -6,6 % | Hold |
| Mining | WMIN | -5,7 % | -7,9 % | Hold |
| Rare earths | VVMX | -14,4 % | -30,6 % | Reducer |
| Copper miners | 4COP | -13,2 % | -16,3 % | Reducer |
| Infrastructure | 94VE | -3,0 % | -9,6 % | Reducer |

Mandagens SOX-rebound på 6,9 % står i kontrast til det fortsat negative IOS-momentum. **Egen vurdering:** Ingen bred, bekræftet sektorrotation endnu. Nettoflows: **N/A**.

## E. Porteføljepåvirkning
| Aktiv | Vægt | Decision Score | IOS-signal | 1M |
|---|---:|---:|---|---:|
| ASML | 5,22 % | 27,65 | Reducer | -21,2 % |
| Microsoft | 6,86 % | 88,55 | Hold | +1,7 % |
| TSMC | 3,17 % | 38,46 | Reducer | -14,3 % |
| Novo Nordisk | 16,05 % | 42,07 | Hold | +7,8 % |
| Vestas | 3,65 % | 89,44 | Øg | +12,3 % |
| NKT | 7,80 % | 42,70 | Hold | -1,8 % |
| AL Sydbank | 6,76 % | 93,15 | Hold | +2,2 % |
| Danske Bank | 4,88 % | 75,45 | Øg | +0,6 % |
| Celestica | 4,44 % | 16,86 | Reducer | -38,4 % |

**Egen vurdering:** Microsoft er teknisk relativt robust; ASML, TSMC og især Celestica kræver risikogennemgang. Novo ligger lige over loftet, men den nødvendige justering er under modellens minimumshandel. Vestas og Pandora har stærke scores, men ingen automatisk købspligt. Alphabet `ABEA:XETR` har fortsat **Data Score 0**.

## F. Ændringer siden seneste brief
Sammenlignet med mandag 9/11 (ikke depotafstemt afkast):

| KPI | 9/11 | 10/11 | Ændring |
|---|---:|---:|---:|
| Porteføljeværdi | 1.136.301 kr. | **1.167.269 kr.** | **+30.968 kr.** |
| Modelafkast | -3,16 % | **-2,88 %** | +0,28 procentpoint |
| Portfolio Health | 55,91 | **54,17** | -1,74 |
| AI Confidence | 54,17 | **52,88** | -1,29 |
| Macro/Rate Risk | 50,03 | **50,29** | +0,26 |
| Stop_Broken / Alarm / Tighten | 15 / 4 / 0 | **15 / 4 / 0** | Uændret |

Masterfilens SHA er ændret fra `fc8e497d…` til `f70dce9a…`; værdiændringen kan **ikke** isoleres som markedsafkast. Modelkøbene er fortsat Vestas, Pandora og Danske Bank, men Novo-reduktionen er bortfaldet på grund af minimumshandel. Snapshotets interne sammenligningspunkt er **9/11 kl. 18.03**, ikke gårsdagens morgen: Health **-2,63** og AI Confidence **-0,33** mod dette tidspunkt. Opportunities-toppen er AL Sydbank, Vestas, 2B70, Pandora og Microsoft. Individuelle stopkursændringer: **N/A**.

## G. Dagens vigtigste begivenheder
**10/11:** Amerikanske inflationstal er dagens væsentligste planlagte makrokatalysator; udfaldet er endnu ukendt. **11/11:** Vestas' Q3-regnskab, centralt for margin, ordreindgang og guidance. **17/11:** Nvidia-regnskab er en vigtig test af AI-investeringstemaet. **19/11:** NKT-regnskab (bekræft præcist tidspunkt i selskabets kalender). [Reuters om AI-regulering og Nvidia](https://www.reuters.com/business/finance/wall-st-brokerages-say-ai-selloff-overdone-downplay-democrat-regulation-risks-2026-11-09/).

## H. Køb / hold / reducer
**Direkte Investment OS-output fra decision_queue/rebalance – ikke ordrer:**

| Aktiv | IOS | Rebalance | Beløb |
|---|---|---|---:|
| Vestas | Øg | Køb, 3,65 → 6,77 % | **+22.937 kr.** |
| Pandora | Øg | Køb, 3,80 → 6,89 % | **+22.702 kr.** |
| Danske Bank | Øg | Køb, 4,88 → 6,83 % | **+14.363 kr.** |
| Novo | Hold | Ingen handel; positionsloft + minimumshandel | **0 kr.** |
| ASML, TSMC, SEC0, Celestica | Reducer | Ingen handel; konfidensgate | **0 kr.** |

**Execution summary:** Tre modelkøb, brutto og nettokontantbehov **60.002 kr.**, ingen modelsalg, **17 constraint-markerede rækker**.

**Egen vurdering:** **Afvent alle tre køb.** Et køb i Danske Bank øger den direkte bankeksponering til omkring **13,6 %**, før andre vægtændringer. Vestas har regnskab i morgen, og Pandora har selskabsspecifik forbrugsrisiko. Likviditet, ETF-look-through, sektorlofter, minimumshandel og omkostninger skal afstemmes først.

## I. Usikkerheder og datakvalitet
Porteføljesnapshotet er friskt og har intern score **100/100**, men **22 udenlandske positioner** anvender valutaneutralt afkast og **22** bruger Yahoo-kurs × FX som markedsværdifallback. Alphabet-kursmapping er mangelfuld. Makrodatakvaliteten er **45/100**. Frie kontanter, konkrete ETF-nettoflows, individuelle stopkurser og samtidige valuta-/råvarekurser er **N/A**.

### Dagens tre beslutningspunkter
1. **Ingen handler.** Afstem porteføljestigning **30.968 kr.**, ændret masterfil-SHA og Novo **16,05 %** mod loftet **16 %**.
2. **Gennemgå 15 Stop_Broken og 4 Alarm**; prioritér Celestica, ASML, TSMC og SEC0 samt Alphabet- og makrodatamangler.
3. **Afvent modelkøb for 60.002 kr.**, indtil finansiering, sektoroverlap og Vestas-regnskabet er vurderet.
