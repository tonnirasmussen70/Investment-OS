# Investment OS – Morgenbrief
**Fredag 13. november 2026, ca. 07.00 CET. Ingen handler udført.**

## A. Executive view
**Markedsregime: forhøjet renterisiko og usikkerhed om AI-værdiansættelser.** Amerikanske aktier faldt moderat torsdag; S&P 500 ca. -0,35 %, Dow -0,36 % og Nasdaq-100 ca. -0,30 % (Barchart, 13/11). Reuters beskriver højere amerikanske renter, stærkere dollar og volatilitet i AI-aktier. IOS Macro/Rate Risk stiger til **67,03 (høj)**, mens Portfolio Health forbedres til **62,75**. **Prioritet: risikokontrol og likviditet før modellens tre køb på 65.337 kr.**

## B. Portfolio status
Autoritativt snapshot: https://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json
- generated_at: `2026-11-13T03:41:39.183189+01:00` (**friskt**, ca. 3 timer 20 minutter gammelt).
- source.commit_sha: `098695590f8f8034d4738670c0e19b134521ef09`.
- source.portfolio_file_sha256: `b48c392ed9367b64d9dc7c9b6ae06485b9e75f1f22144c597c6e7eb5064d405e`.
- data_quality.score: **100/100**.
- Samlet værdi **1.204.816 kr.**, aktiv markedsværdi **772.696 kr.**, modelafkast **-0,44 %**, Portfolio Health **62,75**, AI Confidence **53,36 (moderat)**, Macro/Rate Risk **67,03 (høj)**. Positioner 29, analyserede 28. Positionsloft 16 %.
- Største vægte af aktiv markedsværdi: Novo **15,27 %**, NKT **7,42 %**, AL Sydbank **7,26 %**, Microsoft **6,34 %**, VWCE **6,28 %**, ASML **5,43 %**, Celestica **4,89 %**, Danske Bank **4,64 %**, VGWD **4,39 %**, Pandora **4,16 %**.
- Direkte bankeksponering **11,90 %**. AI/teknologi-overlap via Microsoft, ASML, TSMC, Celestica og ETF'er. Differencen **432.120 kr.** mellem total og aktiv værdi er **ikke dokumenteret fri likviditet**.

## C. Markedsstatus og makro
- USA torsdag 12/11: S&P 500 ca. **-0,35 %**, Dow **-0,36 %**, Nasdaq-100 **-0,30 %** (Barchart, 13/11).
- IOS US10Y pr. 12/11 **5,103 %**, 1M-ændring **-0,087 procentpoint**, 3M **+0,407 procentpoint**. US2Y, kurve, inflations- og kreditkomponent **N/A** i IOS. Makrodatakvalitet **45/100**.
- Reuters 13/11 beskriver stærkere USD og højere obligationsrenter. Samtidigt verificerede EUR/USD, EUR/DKK, Brent, WTI, guld og kobber: **N/A**. Olie og energi er relevante for inflation og diskonteringsrenter, men præcise priser gættes ikke.
- Egen analyse: høj langrente øger diskonteringspresset på AI, grøn energi og infrastruktur. Et rebound alene er ikke et trendbrud.

## D. Sektor- og kapitalstrømsrotation
**IOS-modelmomentum, ikke verificerede nettoflows:**

| Tema | ETF | 1M | 3M | IOS |
|---|---|---:|---:|---|
| Semiconductors | SEC0 | -10,81 % | -9,28 % | Hold |
| Defense | DFEN | +2,45 % | -12,94 % | Hold |
| Uranium | URNU | -7,82 % | -23,93 % | Reducer |
| Clean energy | IQQH | -3,68 % | -7,12 % | Reducer |
| Mining | WMIN | -4,36 % | -3,81 % | Hold |
| Copper miners | 4COP | -11,22 % | -10,29 % | Reducer |
| Rare earths | VVMX | -5,32 % | -28,74 % | Reducer |
| Infrastructure | 94VE | +2,73 % | -3,88 % | Øg (blokeret) |

Egen analyse: defense og infrastructure viser relativ bedring på 1M, men de negative 3M-tal gør rotationen ubekræftet. Netto-ETF-flows: **N/A**.

## E. Porteføljepåvirkning
| Aktie | Vægt | IOS-score | IOS-signal | 1M |
|---|---:|---:|---|---:|
| ASML | 5,43 % | 54,53 | Hold | -6,88 % |
| Microsoft | 6,34 % | 69,90 | Hold | -4,04 % |
| TSMC | 3,19 % | 59,16 | Hold | -5,70 % |
| Novo Nordisk | 15,27 % | 31,03 | Reducer | +6,25 % |
| Vestas | 4,16 % | 45,27 | Hold | +0,82 % |
| NKT | 7,42 % | 48,19 | Hold | +2,67 % |
| AL Sydbank | 7,26 % | 94,22 | Hold | +6,56 % |
| Danske Bank | 4,64 % | 80,49 | Øg | +3,43 % |
| Celestica | 4,89 % | 23,72 | Reducer | -21,43 % |

Egen analyse: ASML og TSMC viser tidlig teknisk vending, men negativ 1M. Novo er under 16 %-loftet, men har et selvstændigt svagt IOS-signal. Celesticas 1W +23,53 % er et kraftigt rebound, ikke bekræftelse på afsluttet 3M-fald (-24,18 %). Vestas er Hold efter regnskabet. Alphabet `ABEC:XETR` har Data Score **0** og manglende kurs.

## F. Ændringer siden 12/11
| KPI | 12/11 | 13/11 | Ændring |
|---|---:|---:|---:|
| Samlet værdi | 1.196.391 | 1.204.816 kr. | +8.425 kr. |
| Modelafkast | -1,51 % | -0,44 % | +1,07 pp |
| Portfolio Health | 58,64 | 62,75 | +4,11 |
| AI Confidence | 55,31 | 53,36 | -1,94 |
| Macro/Rate Risk | 59,72 | 67,03 | +7,31 |
| Stop_Broken / Alarm / Tighten | 14 / 2 / 1 | 14 / 0 / 2 | 0 / -2 / +1 |

Værdiændringen er **ikke depotafstemt dagsafkast**. Masterfilens SHA er uændret fra 12/11, mens kilde-commit er ændret. IOS-ændringslog sammenligner direkte med 12/11 kl. 04.08: ASML **Reducer → Hold**, score +14,62; Novo **Hold → Reducer**, score -10,22; Microsoft-score -18,74; AL Sydbank **Øg → Hold**. VGWD kommer ind som modelkøb, AL Sydbank udgår. Opportunities-top: AL Sydbank, 2B70, Pandora, VGWD og IS3Q. 94VE kommer ind på listen, Vestas udgår. Individuelle stopkurser: **N/A**.

## G. Begivenheder
- **13/11:** Vurder rentestigningen, dollar og volatilitet i AI-aktier. Reuters 13/11: https://www.reuters.com/world/china/global-markets-global-markets-2026-11-13/
- **19/11:** NKT-regnskab ifølge tidligere kalenderoplysninger; tidspunkt ikke genbekræftet fra primær kilde.
- Kommende Nvidia-regnskab: **dato N/A** uden primærkildebekræftelse. Følg AI-capex og leverandørkæden.
- Vestas' Q3-regnskab fra 11/11 er allerede offentliggjort og bør indgå i langsigtet vurdering.

## H. Køb / hold / reducer
**Investment OS-output fra decision_queue/rebalance, ikke ordrer:**

| Aktiv | IOS-signal | Modelhandel | Beløb |
|---|---|---|---:|
| Pandora | Øg | Køb, 4,16 → 7,25 % | +23.847 kr. |
| VGWD | Øg | Køb, 4,39 → 7,38 % | +23.146 kr. |
| Danske Bank | Øg | Køb, 4,64 → 7,01 % | +18.344 kr. |
| AL Sydbank | Hold | Ingen handel | 0 |
| Novo | Reducer | Ingen handel, konfidensgate | 0 |
| Celestica | Reducer | Ingen handel, konfidensgate/sektorloft | 0 |
| 94VE | Øg | Ingen handel, konfidensgate | 0 |

Execution summary: **3 modelkøb**, brutto/netto **65.337 kr.**, **14** constraint-markerede rækker. Ingen modelsalg.

**Egen vurdering:** Afvent køb, indtil fri likviditet og minimumshandel er verificeret. Danske Bank-købet vil løfte den direkte bankvægt til omtrent **14,27 %** før andre vægtændringer. VGWD overlapper med VWCE og IS3Q; Pandora har høj selskabsspecifik volatilitet. Ingen handler udført.

## I. Usikkerheder og datakvalitet
Snapshotet er friskt og har intern score 100/100, men **22 udenlandske positioner** har valutaneutralt DKK-afkast, **22** anvender Yahoo × FX-fallback, og Alphabet mangler kurs. Makrodatakvaliteten er kun **45/100**. Frie kontanter, verificerede ETF-nettoflows, individuelt stopniveau, fuldt ETF-look-through og samtidige råvare-/valutakurser: **N/A**.

## Dagens tre beslutningspunkter
1. **Ingen handler:** afstem 65.337 kr. i modelkøb mod faktisk fri likviditet, sektorlofter og minimumshandel.
2. **Gennemgå 14 Stop_Broken og 2 Tighten**, især Novo, Celestica og AI-overlap; ret Alphabet og makrodatamangler.
3. **Afvent Pandora, VGWD og Danske Bank** indtil koncentration, ETF-overlap og renterisiko er vurderet.

Kilder: [IOS-snapshot](https://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json), [Reuters 13/11](https://www.reuters.com/world/china/global-markets-global-markets-2026-11-13/), [Barchart markedsafslutning 12/11](https://www.tradingview.com/news/barchart%3Aef2258a8e094b%3A0-stocks-settle-lower-on-nvidia-rout-and-higher-crude-and-bond-yields/).
