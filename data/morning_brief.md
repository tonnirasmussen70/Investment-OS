# Investment OS – Morgenbrief | Mandag 23. november 2026

## A. Executive view
**Regime: markant risk-off.** Fredag faldt S&P 500 3,70 %, Nasdaq 5,28 % og Dow 1,93 %. AI- og halvlederaktier var særligt pressede (Reuters, 20/11: https://www.reuters.com/legal/transactional/wall-st-futures-slip-anthropic-debut-fails-reassure-ai-investors-2026-11-20/).
**Investment OS:** Portfolio Health **51,21**, AI Confidence **49,20 (lav)**, Macro/Rate Risk **64,22 (høj)**.
**Vigtigste ændring:** Modellen foreslår nu **to salg på samlet 28.489 kr.**, men Novo Nordisk er over positionsloftet, og AI-eksponeringen er under pres.
**Egen vurdering:** Afstem de to salg og stopbrud, men udfør ingen handler automatisk.

## B. Portfolio status
GitHub/main snapshot genereret **2026-11-23T03:54:33.592736+01:00**; **friskt** (under 24 timer).
- Samlet porteføljeværdi: **1.144.347 kr.**; aktiv markedsværdi **712.227 kr.**; modelafkast **-5,58 %**.
- Portfolio Health **51,21**; AI Confidence **49,20**; intern data_quality.score **100/100**; 27 positioner, 26 analyseret.
- source.commit_sha: `3d6ef9696f01e488aaa63a1c3807b15182a84251`
- source.portfolio_file_sha256: `f853d98e84f5c1d63c57f70b66a814eb211bebce78e16663c7758b537a8fa452`
- Største vægte: Novo **16,57 %**, NKT **8,05 %**, AL Sydbank **7,88 %**, Microsoft **6,57 %**, VWCE **6,35 %**, Danske Bank **5,03 %**, ASML **4,90 %**, VGWD **4,54 %**, Pandora **4,52 %**, Siemens Energy **4,47 %**.
- Novo overstiger positionsloftet **16 %** med ca. **0,57 procentpoint**. Direkte bankvægt **12,91 %**. Teknologi/AI-overlap omfatter Microsoft, ASML, TSMC, Celestica og SEC0.
- Forskellen **432.120 kr.** mellem samlet og aktiv værdi er **ikke dokumenteret som fri likviditet**.

## C. Markedsstatus og makro
Seneste verificerede amerikanske lukning **fredag 20/11**:
| Aktiv | Niveau | Ændring |
|---|---:|---:|
| S&P 500 | 6.910,39 | -3,70 % |
| Nasdaq Composite | 22.617,73 | -5,28 % |
| Dow | 48.147,33 | -1,93 % |
| USA 10-årig rente, IOS 20/11 | 4,912 % | — |
| USA 2-årig, ekstern 20/11 | ca. 4,63 % | — |
| Brent, sen fredag | ca. 92,63 USD/fad | +0,71 % |
| WTI, sen fredag | ca. 83,70 USD/fad | +1,53 % |
| Guld, sen fredag | ca. 3.538 USD/oz | -2,41 % |
| Kobber, sen fredag | ca. 5,464 USD/lb | -3,01 % |
| EUR/USD, EUR/DKK | N/A | — |

Aktieindeks: AP https://apnews.com/article/c10b797a17c2acf37924d834efebe135 ; renter: https://edgeconsultancykw.com/us-market-wrap-20-november-2026/ ; råvarer: https://investinglive.com/news/investinglive-americas-fx-news-wrap-20-nov-stocks-get-hammered-as-nasdaq-plunges-5-28/ . Råvarepriserne er ikke samtidige mandagskurser. Egen analyse: rentefaldet fredag var ikke tilstrækkeligt til at støtte vækstaktier; likviditet og AI-værdiansættelser dominerede.

## D. Sektor- og kapitalstrømsrotation
IOS-momentum fra snapshot, **ikke faktiske nettoflows**:
| Tema / ETF | 1M | 3M | IOS |
|---|---:|---:|---|
| Semiconductors SEC0 | -19,41 % | -22,46 % | Reducer |
| Defense DFEN | -8,53 % | -13,97 % | Reducer |
| Uranium URNU | -18,59 % | -41,54 % | Reducer |
| Clean energy IQQH | -10,98 % | -15,15 % | Reducer |
| Mining WMIN | -14,90 % | -29,51 % | Reducer |
| Rare earths VVMX | -15,47 % | -42,18 % | Reducer |
| Copper miners 4COP | -20,45 % | -35,95 % | Reducer |
| Infrastructure 94VE | -1,66 % | -5,02 % | Reducer |

Alle otte temaer har negativt 1M/3M-momentum. Reuters beskriver rotation væk fra AI-vækst mod obligationer og value; verificerede ETF-nettoflows **N/A**: https://www.reuters.com/business/finance/ai-tech-rout-prompts-us-investors-rush-into-value-stocks-2026-11-20/ .

## E. Porteføljepåvirkning
**Investment OS-output:** ASML **Reducer**, score **33,08**, 1M **-17,61 %**; Microsoft **Hold**, score **69,90**, 1M **-4,49 %**; TSMC **Reducer**, score **26,36**, 1M **-22,71 %**; Novo **Reducer**, score **39,41**, vægt **16,57 %**; Vestas **Reducer**, score **40,58**; NKT **Reducer**, score **38,83**; AL Sydbank **Hold**, score **90,67**; Danske Bank **Hold**, score **79,32**; Celestica **Reducer**, score **18,37**, 1M **-24,98 %**.
**Egen analyse:** Prioritér Celestica, TSMC og ASML i risikogennemgangen. For Celestica skal ordreindgang, hyperscaler-capex, kundekoncentration, konkurrence og marginer overvåges; kursfald alene beviser ikke fundamentalt forfald. Novo kræver særskilt positionsloftkontrol.

## F. Ændringer siden seneste brief
Mod fredagens 20/11-brief: samlet værdi **1.193.387 → 1.144.347 kr. (-49.040 kr.)**; aktiv værdi **761.267 → 712.227 kr.**; modelafkast **-3,81 → -5,58 %**; Portfolio Health **54,59 → 51,21**; AI Confidence **51,40 → 49,20**; Macro/Rate Risk **64,22 → 64,22**; Stop_Broken **13 → 18**, Alarm **6 → 5**, Tighten **0 → 1**. Disse ændringer er **ikke et depotafstemt afkast**: masterfilens SHA er ændret, og antal positioner er faldet fra 28 til 27.
Snapshotets indbyggede sammenligning med 22/11 viser kun mikroskopiske scoreændringer, ingen nye/udgåede opportunities eller rangændringer. Opportunities-top: AL Sydbank, Pandora, Danske Bank, Microsoft, 2B70. Historisk komplet 20/11-snapshot er ikke genlæst; ændringerne ovenfor bruger fredagens rapporterede værdier.

## G. Vigtigste begivenheder
Mandag: Følg amerikanske flash-PMI'er, markedsreaktionen efter fredagens fald og udviklingen i obligationsrenter. Ugen er præget af amerikansk Thanksgiving; torsdag **26/11** er amerikanske aktiemarkeder normalt lukket. Følg kommende amerikanske inflationsdata/PCE; præcis udgivelsesdato **N/A** uden officiel kalenderbekræftelse. Selskabsspecifikke kommende regnskabsdatoer **N/A**. Nvidia/AI-investeringer og eventuelle ændringer i guidance er vigtigere end kortvarige kursudsving.

## H. Køb / hold / reducer
**Direkte Investment OS decision_queue/rebalance:**
| Aktiv | Model | Nuværende → mål | Beløb |
|---|---|---|---:|
| 2B70, Nasdaq US Biotechnology ETF | Sælg/reducer | 3,95 % → 1,95 % | **-14.245 kr.** |
| VGWD, Vanguard High Dividend ETF | Sælg/reducer | 4,54 % → 2,54 % | **-14.245 kr.** |

**Execution summary:** 2 salg, brutto **28.489 kr.**, køb **0 kr.**, kontantbehov **0 kr.**, **20 constraints**. Andre reducer-signaler, herunder Novo, ASML, TSMC, NKT og Celestica, er **ikke godkendte modelhandler** på grund af gates. Novo har også positionsloft og minimumshandel som constraints.
**Egen vurdering:** Afvent automatisk eksekvering. Afstem først de to ETF-salg med depot, skat, spread, minimumshandel og porteføljens langsigtede udbytte-/diversifikationsmål. VGWD-salg bør vurderes særligt nøje, fordi udbyttestrategien kan være tilsigtet. Novo over 16 % skal vurderes, selv om modellen ikke har en eksekverbar handel.

## I. Usikkerheder og datakvalitet
Intern snapshot-score **100/100**, men **20 udenlandske positioner** anvender valutaneutralt DKK-afkast og **20** Yahoo × FX-fallback. Makrodatakvalitet **45/100**; US2Y, rentekurve, inflation og kreditspænd mangler i IOS. Stopkurser pr. position, fri likviditet, ETF-look-through, faktiske kapitalflows og aktuelle mandagspriser: **N/A**. Ingen handler udført.

## Dagens tre beslutningspunkter
1. **Gennemgå 18 Stop_Broken, 5 Alarm og 1 Tighten**, med Celestica, TSMC og ASML først.
2. **Afstem to foreslåede ETF-salg på samlet 28.489 kr.** mod strategi, skat og handelsomkostninger; ingen automatisk handel.
3. **Kontrollér Novo på 16,57 % mod 16 %-loftet**, og afvent forbedret markeds- og datakvalitet før nye køb.