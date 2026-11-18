# Investment OS – Morgenbrief
**Onsdag 18. november 2026 · ca. 07.00 CET · Ingen handler udført**

## A. Executive view
**Markedsregime: risk-off og usikkerhed om AI-afkast, men Nvidia har leveret et positivt regnskabssignal efter børslukning.** Tirsdag faldt S&P 500 1,03 %, Nasdaq 0,74 % og Dow 1,64 %. Nvidia steg i eftermarkedet efter bedre tal end forventet; bevægelsen er ikke en bekræftet handelsdagsstigning. Kilder: Reuters 17/11 og AP 17/11.
**Investment OS:** Portfolio Health **63,47**, AI Confidence **58,78 (moderat)**, Macro/Rate Risk **69,90 (høj)**. Modellen foreslår tre køb på **63.953 kr.** **Egen vurdering: afvent køb; prioritér likviditet og korrelationsrisiko.**

## B. Portfolio status
**Kilde:** [Autoritativt snapshot på main](https://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json).
- `generated_at`: `2026-11-18T04:44:59.785749+01:00` — frisk, ca. 2 timer gammelt.
- `source.commit_sha`: `6d092b9e1a41632debdefb8df83e743cb27a3d2c`
- `source.portfolio_file_sha256`: `018fb9f90478b920db31ae4c44ef1d8cafbe93bf9a570256fc9455d927ab08e2`
- `data_quality.score`: **100/100**; 28 registrerede, 27 analyserede positioner.
- Samlet værdi **1.203.677 kr.**; aktiv markedsværdi **771.557 kr.**; modelafkast **-2,50 %**.
- Portfolio Health **63,47**; AI Confidence **58,78**; positionsloft **16 %**.

**Største positioner (% af aktiv værdi):** Novo Nordisk 15,29; NKT 7,43; AL Sydbank 7,27; Microsoft 6,47; VWCE 6,22; Celestica 5,83; ASML 5,06; Danske Bank 4,65; VGWD 4,41; Pandora 4,17. Direkte bankeksponering **11,92 %**. AI/chip-overlap i ASML, TSMC, Celestica, Microsoft og ETF'er. Differencen på **432.120 kr.** mellem total og aktiv værdi er **ikke verificeret kontantbeholdning**.

## C. Markedsstatus og makro
| Indikator | Seneste verificerede værdi |
|---|---|
| S&P 500, 17/11 | 7.340,53 (-1,03 %) |
| Nasdaq Composite, 17/11 | 24.328,38 (-0,74 %) |
| Dow, 17/11 | 50.759,42 (-1,64 %) |
| USA 10Y, IOS 17/11 | 5,103 % |
| USA 2Y, EUR/USD, EUR/DKK | N/A – ingen samtidig verificeret kurs |
| Olie, guld | Steg tirsdag ifølge AP; sammenlignelig pris N/A |
| Kobber | N/A |

**Fakta:** Amerikanske aktier faldt bredt; Nvidia offentliggjorde bedre end ventede resultater efter lukning. Fed-kommentarer pegede på fortsat inflationspres. [Reuters 17/11](https://www.reuters.com/business/us-stock-futures-slip-ahead-nvidia-results-fed-speakers-focus-2026-11-17/), [AP 17/11](https://finance.yahoo.com/markets/world-indices/articles/major-us-stock-indexes-fared-214025410.html).
**Egen analyse:** Langrente over 5 % og usikkerhed om AI-investeringsafkast gør samtidige vækst- og infrastrukturoprustninger risikable.

## D. Sektor- og kapitalstrømsrotation
**IOS-momentum; ikke faktiske ETF-nettoflows:**

| Tema | ETF | 1M | 3M | IOS |
|---|---|---:|---:|---|
| Semiconductors | SEC0 | -12,19 % | -12,25 % | Hold |
| Defense | DFEN | -3,85 % | -13,36 % | Reducer |
| Uranium | URNU | -12,21 % | -28,95 % | Reducer |
| Clean energy | IQQH | -4,91 % | -7,82 % | Reducer |
| Mining | WMIN | -9,92 % | -14,18 % | Reducer |
| Rare earths | VVMX | -11,09 % | -33,47 % | Reducer |
| Copper miners | 4COP | -16,66 % | -20,42 % | Reducer |
| Infrastructure | 94VE | +0,99 % | -2,94 % | Øg |

**Egen analyse:** Infrastructure har relativ styrke på én måned, men ingen af disse temaer har dokumenteret bredt positivt 3M-momentum. Kapitalflows: N/A.

## E. Porteføljepåvirkning
| Selskab | Vægt | IOS-score | IOS-handling |
|---|---:|---:|---|
| ASML | 5,06 % | 35,85 | Reducer |
| Microsoft | 6,47 % | 85,26 | Hold |
| TSMC | 3,49 % | 29,45 | Reducer |
| Novo Nordisk | 15,29 % | 62,11 | Hold |
| Vestas | 4,16 % | 51,40 | Hold |
| NKT | 7,43 % | 48,76 | Hold |
| AL Sydbank | 7,27 % | 94,17 | Hold |
| Danske Bank | 4,65 % | 89,34 | Øg |
| Celestica | 5,83 % | 21,61 | Reducer |

**Egen analyse:** ASML, TSMC og Celestica er de vigtigste risikopositioner; Nvidia-regnskabet kan ændre kortsigtet sentiment, men ophæver ikke negative IOS-signaler. Novo ligger tæt på positionsloftet. Alphabet `1GOOG.MI` har datakvalitet 100, men instrumentmapping skal fortsat kontrolleres mod depotet.

## F. Ændringer siden seneste brief
| KPI | 17/11 | 18/11 | Ændring |
|---|---:|---:|---:|
| Samlet værdi | 1.208.688 kr. | 1.203.677 kr. | -5.011 kr. |
| Modelafkast | -1,87 % | -2,50 % | -0,63 procentpoint |
| Portfolio Health | 62,89 | 63,47 | +0,58 |
| AI Confidence | 56,50 | 58,78 | +2,28 |
| Macro/Rate Risk | 71,62 | 69,90 | -1,73 |
| Stop_Broken / Alarm / Tighten | 12 / 1 / 0 | 13 / 1 / 1 | +1 / 0 / +1 |

Masterfilens SHA er uændret; værdiforskellen er ikke et depotafstemt dagsafkast. **IOS-ændringer:** ASML Hold → Reducer, score -6,32; AL Sydbank Øg → Hold; Microsoft-score +15,36; Novo-score +12,76. AL Sydbank-købet udgår, og der er nu tre modelkøb. Opportunities-top: AL Sydbank, 2B70, VGWD, Danske Bank, Pandora. Individuelle stopniveauer: N/A.

## G. Dagens vigtigste begivenheder
**Nvidia:** Kvartalsregnskab offentliggjort efter amerikansk lukning 17/11 med bedre end ventede resultater; verificér den officielle guidance og markedets reaktion i ordinær handel, før AI-eksponering ændres. [Reuters 17/11](https://www.reuters.com/commentary/reuters-open-interest/global-markets-trading-day-graphic-2026-11-17/).
**Makro:** Følg Fed-kommentarer, lange renter og inflation. NKT's næste regnskabstidspunkt og øvrige konkrete kommende datoer er N/A uden primærkildeverifikation.

## H. Køb / hold / reducer
**Direkte Investment OS-output fra decision_queue/rebalance — ikke ordrer:**

| Aktiv | Modelhandling | Nuværende → målvægt | Beløb |
|---|---|---|---:|
| VGWD | Køb | 4,41 → 7,70 % | 25.352 kr. |
| Danske Bank | Køb | 4,65 → 7,76 % | 24.005 kr. |
| 94VE | Køb | 1,68 → 3,58 % | 14.595 kr. |
| AL Sydbank | Hold | 7,27 → 7,27 % | 0 kr. |
| ASML, TSMC, Celestica | Reducer-signal, ingen modelhandel | Konfidensgate | 0 kr. |

**Execution summary:** 3 modelkøb, **63.952,64 kr.** kontantbehov, 0 modelsalg, 14 constraints.
**Egen vurdering:** **Afvent alle køb.** Danske Bank vil løfte direkte bankeksponering til ca. **15,03 %** (AL Sydbank 7,27 % + Danske Bank målvægt 7,76 %), før ETF-overlap. VGWD overlapper med globale ETF'er; 94VE er rentefølsom. Afstem fri likviditet, sektorloft, minimumshandel og omkostninger.

## I. Usikkerheder og datakvalitet
Snapshotet er friskt med intern score 100/100, men 21 udenlandske positioner bruger valutaneutralt DKK-afkast og 21 bruger Yahoo-kurs × FX som markedsværdifallback. Makrodatakvalitet er **45/100**; 2Y-rente, rentekurve, inflation og kreditspænd mangler i IOS. Kontanter, fuldt ETF-look-through, individuelle stopkurser og verificerede nettoflows: N/A.

## Dagens tre beslutningspunkter
1. **Ingen handler:** afstem modelkøb på **63.953 kr.** mod kontanter og minimumshandel.
2. **Gennemgå 13 Stop_Broken, 1 Alarm og 1 Tighten**, særligt ASML, TSMC og Celestica.
3. **Afvent Danske Bank, VGWD og 94VE**, indtil bank-/ETF-overlap og Nvidias guidance er vurderet.
