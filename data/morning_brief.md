# Investment OS – Morgenbrief
**Lørdag 24. oktober 2026 · ca. kl. 07.00 dansk tid · ingen handler udført**

## A. Executive view
**Markedsregime: defensivt, men ikke ensrettet.** Fredag faldt S&P 500 0,52 % og Nasdaq 0,21 %, mens den amerikanske energisektor steg 2,5 %. Halvledere stabiliserede sig efter torsdagens kraftige fald. Olie på 116,72 USD og en amerikansk 10-årig rente tæt på 5 % holder inflations- og værdiansættelsesrisikoen høj. citeturn3view1turn3view3

**Investment OS 7.3.3:** Portfolio Health **59,73**, AI Confidence **52,92 (moderat)** og Macro/Rate Risk **60,06 (høj)**. Snapshotet er **4 timer og 10 minutter gammelt**, altså ikke stale. Modellen foreslår **ingen køb og én reduktion på 13.214 kr.** som følge af positionsloft. **Vigtigste handling: afstem loftbruddet og de 18 brudte stopniveauer; ingen handler udføres.**

## B. Portfolio status
**Autoritativ kilde:** urlGitHub – portfolio_snapshot.json på mainhttps://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json. Læst direkte fra repositoriet; Excel og app.py er ikke anvendt til genberegning.

| Snapshotkontrol | Verificeret værdi |
|---|---:|
| `generated_at` | `2026-10-24T02:48:06.417905+02:00` |
| `source.commit_sha` | `8d7758a3c9f5bcf609de27193074293049565794` |
| `source.portfolio_file_sha256` | `ed0a9d38a61b777cadd171f3ac2679d3e14b89b3a2f3113a241e80f19b656702` |
| `data_quality.score` | **100/100** |
| Samlet porteføljeværdi | **1.180.646 kr.** |
| Aktiv markedsværdi | **748.526 kr.** |
| Modelafkast | **+3,16 %** |
| Portfolio Health | **59,73** |
| AI Confidence | **52,92 – moderat** |
| Macro/Rate Risk | **60,06 – høj** |
| Positionsloft | **14,00 %** |

**30 registrerede / 29 analyserede positioner.** Snapshotet er dannet efter fredagens amerikanske børslukning, men enkelte depotværdier er kurs-/valutafallbacks.

| Største positioner | Andel af aktiv markedsværdi |
|---|---:|
| NOVO-B.CO | **15,77 %** |
| NKT.CO | 7,66 % |
| MSF.DE | 7,49 % |
| ASML.AS | 7,03 % |
| VWCE.DE | 6,42 % |
| DANSKE.CO | 6,30 % |
| ALSYDB.CO | 5,45 % |
| SEC0.DE | 5,03 % |
| IS3Q.DE | 4,00 % |
| PNDORA.CO | 3,73 % |

**Koncentration:** NOVO-B overskrider positionsloftet med **1,77 procentpoint**. Direkte teknologiklassificerede positioner udgør **25,47 %**, eksklusive indirekte teknologi i verdens-ETF'er. Finans udgør **11,75 %**. Forskellen mellem total og aktiv værdi er **432.120 kr.**; beløbet er **ikke dokumenteret som disponible kontanter**.

## C. Markedsstatus og makro
**Seneste verificerede handelsdag: fredag 23. oktober.** Lørdag er de ordinære aktiemarkeder lukkede.

| Aktiv | Observation og tidspunkt |
|---|---:|
| S&P 500 | **7.623,68 (-0,52 %)**, fredagslukning |
| Nasdaq Composite | **25.955,34 (-0,21 %)**, fredagslukning |
| Dow Jones | **52.215,16 (-1,23 %)**, fredagslukning |
| SOX, halvledere | **+0,4 %**, fredag |
| USA 10-årig statsrente | **ca. 4,99 %**, fredag |
| EUR/USD | **1,1193**, ECB-reference 23/10 |
| EUR/DKK | **7,4748**, ECB-reference 23/10 |
| Brent | **116,72 USD/fad (+3,14 %)**, fredagsafregning |
| WTI | **103,27 USD/fad (+3,8 %)**, fredagsafregning |
| Spotguld | **3.998,35 USD/oz**, fredag kl. 15.20 GMT; **ikke slutkurs** |
| LME 3M kobber | **14.190 USD/ton (+0,8 %)**, fredag kl. 10.00 GMT; **ikke slutkurs** |

Aktier, renter og olie: Reuters 23/10. Valuta: ECB 23/10. Guld og kobber: tidsstemplede Reuters-observationer. Tallene er ikke samtidige livekurser. citeturn3view1turn3view3turn5view1turn5view0turn1search20

**Egen analyse:** Oliestigningen giver risiko for mere vedvarende inflation og færre rentenedsættelser. Samtidig kan lavere aktiekurser og højere finansieringsomkostninger presse AI-selskabers værdiansættelser. Fredagens stabilisering i halvledere er endnu ikke en dokumenteret trendvending. Makro-overlayet bruger US10Y **4,988 % pr. 23/10**, men dets datakvalitet er kun **45/100**.

## D. Sektor- og kapitalstrømsrotation
**Investment OS-modelmomentum, ikke målte ETF-flowtal:**

| Tema | IOS-aktiv | Signal | 1M | 3M |
|---|---|---|---:|---:|
| Semiconductors | SEC0 | **Reducer** | -13,69 % | -2,77 % |
| Defense | DFEN | Hold | -3,86 % | -3,36 % |
| Uranium | URNU | **Reducer** | -21,36 % | N/A |
| Clean energy | IQQH | **Reducer** | -6,36 % | -6,81 % |
| Mining | WMIN | Hold | -10,37 % | +3,04 % |
| Copper miners | 4COP | **Reducer** | -13,76 % | -2,42 % |
| Rare earths | VVMX | **Reducer** | -24,12 % | -22,47 % |
| Infrastructure | ABB / 94VE | **Reducer / Reducer** | -16,87 % / -1,82 % | -11,87 % / -7,54 % |

**Verificerede kapitalstrømme:** Globale aktiefonde modtog **28,16 mia. USD** i ugen til 21/10. Teknologifonde fik **5,05 mia. USD ind**, efter udstrømning på 4,77 mia. USD ugen før; sundhedsfonde fik **1,83 mia. USD ind**, mens cykliske forbrugsfonde mistede **1,29 mia. USD**. Ædelmetalfonde fik **1,29 mia. USD ind** trods faldende guldpris. **Specifikke nettoflows for SEC0, DFEN, URNU, IQQH, WMIN, 4COP, VVMX og 94VE: N/A.** citeturn3view2

**Egen analyse:** Flowtallene viser fortsat kapitalinteresse for teknologi og sundhed, men IOS-momentum er svagt i flere smalle temaer. Positivt fondsflow er ikke tilstrækkeligt til at tilsidesætte sektoroverlap eller stop-loss.

## E. Porteføljepåvirkning
**entity["company","ASML","Dutch semiconductor equipment manufacturer"]** (urlselskabets hjemmesidehttps://www.asml.com/): **7,03 %**, **Reducer**, Decision Score **57,66**, 1M **-6,35 %**. Fredagens SOX-stabilisering ændrer ikke det negative IOS-rotationssignal. Ingen modelhandel; konfidensgate.

**entity["company","Microsoft","US software and cloud company"]** (urlInvestor Relationsturn2search0): **7,49 %**, **Hold**, score **86,22**, 3M **+36,24 %**. Relativ modelstyrke, men AI-capex-risiko og overlap med SEC0 og verdens-ETF'er. Regnskab **28/10**.

**entity["company","TSMC","Taiwan semiconductor foundry"]** (urlInvestor Relationshttps://investor.tsmc.com/): **2,98 %**, **Hold**, score **61,11**, 1M **-7,66 %**. Kortsigtet svaghed, men ingen modelhandel.

**entity["company","Novo Nordisk","Danish pharmaceutical company"]** (urlregnskabskalenderturn2search2): **15,77 %**, positionssignal **Hold**, score **40,44**, 3M **-17,88 %**. **Rebalance foreslår Sælg 13.214 kr. til 14,00 %** udelukkende på grund af positionsloft. Det er modeloutput, ikke en ordre.

**entity["company","NKT","Danish power cable manufacturer"]** (urlselskabsmeddelelse 23/10turn4view0): **7,66 %**, **Reducer**, score **26,12**, 1M **-14,32 %**. Selskabet meddelte 23/10, at storaktionæren entity["company","BlackRock","US asset manager"] (urlofficiel hjemmesidehttps://www.blackrock.com/) samlet er oppe på **8,54 %** af kapital/stemmer. Det er en ejeroplysning, **ikke et dokumenteret positivt indtjeningssignal**.

**entity["company","Vestas","Danish wind turbine manufacturer"]** (urlfinanskalenderturn2search3): **3,14 %**, **Hold**, score **67,71**, 1M **-8,14 %**. Kort momentum svagt; regnskab **11/11**.

**Danske banker:** entity["company","Danske Bank","Danish banking group"] (urlhjemmesidehttps://danskebank.com/) **6,30 %**, **Reducer**, score **50,81**; entity["company","AL Sydbank","Danish banking group"] (urlhjemmesidehttps://www.al-sydbank.dk/) **5,45 %**, **Hold**, score **69,90**. Samlet finansvægt **11,75 %** og fælles følsomhed over for rentekurve og kreditkvalitet.

**Andre:** SEC0 **5,03 %**, Reducer. 2B70 **2,38 %**, Hold, score **91,37** og nr. 1 på opportunities; Frontline **3,59 %**, Hold, score **87,52**; ServiceNow **1,40 %**, Hold, score **86,53**. **Opportunity-score er ikke et købssignal.**

## F. Ændringer siden seneste brief
**Mod fredagens morgenbrief** (snapshotforskelle, **ikke afstemt dagsafkast**):

| Måling | Fredag | Lørdag | Ændring |
|---|---:|---:|---:|
| Samlet værdi | 1.181.195 kr. | **1.180.646 kr.** | **-549 kr.** |
| Aktiv værdi | 749.075 kr. | **748.526 kr.** | **-549 kr.** |
| Modelafkast | +3,25 % | **+3,16 %** | **-0,09 procentpoint** |
| Portfolio Health | 59,61 | **59,73** | +0,12 |
| AI Confidence | 52,79 | **52,92** | +0,13 |
| Macro/Rate Risk | 61,91 | **60,06** | -1,85 |
| Stop_Broken | 20 | **18** | -2 |
| Alarm | 0 | **2** | +2 |

**Porteføljefilens SHA er uændret** fra fredagens brief (`ed0a9d38…`), men den lille værdiændring er stadig ikke en depotafstemt performanceberegning. Modelkø: **0 køb og 1 reduktion**, som i går; foreslået Novo-reduktion **13.138 → 13.214 kr.**. De to nye Alarm-statusser kan ikke knyttes til bestemte positioner ud fra `stop_loss_summary` alene.

**Snapshotets interne `changes`** sammenligner med kørsel **23/10 kl. 09.02**, ikke direkte med fredagens brief: Health **-0,41**, Confidence **+1,38**, Macro Risk **+1,80**; Novo positionssignal **Reducer → Hold**, score **+6,88**. Et fuldt tidligere JSON-snapshot er ikke genindlæst, og individuelle stopkursændringer er **N/A**.

## G. Dagens begivenheder og kommende regnskaber
**Lørdag 24/10:** Ingen ordinær børsdag. Weekendens relevante overvågning er eventuelle dokumenterede ændringer i Mellemøstens olieforsyning og forventningerne til centralbankrenter; ingen lørdagskursreaktion kan måles.

**27.–28. oktober:** urlFederal Reserves FOMC-mødeturn2search11. **28. oktober:** urlMicrosoft FY27 Q1turn2search0. I samme regnskabsuge ventes også større AI-hyperscalere; præcise ikke-primærkildebekræftede datoer: **N/A**. **29. oktober:** Amerikansk PCE-inflation ifølge Reuters' økonomikalender. **4. november:** urlNovo Nordisk ni månederturn2search2. **11. november:** urlVestas Q3turn2search3. **19. november:** urlNKT Q1–Q3turn2search4. citeturn5view0

## H. Handlingsorienteret køb / hold / reducer
**Investment OS-output fra `decision_queue` og `rebalance` – ingen handler udført:**

| Aktiv | Positionssignal | Rebalance | Beløb |
|---|---|---|---:|
| NOVO-B.CO | **Hold** | **Sælg** til 14,00 %; constraint: Positionsloft | **-13.214 kr.** |
| ASML, NKT, SEC0, DANSKE, ABB | **Reducer** | Ingen handel; konfidensgate | 0 kr. |
| MSF, TSM, VWS, ALSYDB | **Hold** | Ingen handel | 0 kr. |
| 2B70, IS3Q, VGWD, VWCE | **Hold** | Ingen handel | 0 kr. |
| **Execution summary** | **0 køb / 1 reduktion** | **Brutto 13.214 kr.; 16 constraint-markerede rækker** | **Netto -13.214 kr.** |

**Egen vurdering:** **Afvent eksekvering**, men ignorér ikke loftbruddet. Bekræft faktisk depotvægt, minimumshandel, konto-/likviditetsforhold og de **18 Stop_Broken + 2 Alarm**. Konfidensgaten skal ikke omgås alene, fordi et positionssignal siger Reducer. Ingen nye køb foreslås, før overlap mellem direkte AI-aktier og teknologi-ETF'er er afstemt.

## I. Usikkerheder og datakvalitet
**Snapshotet er frisk**, og den interne porteføljedatakvalitet er **100/100**. Men **23 udenlandske positioner** har valutaneutralt DKK-afkast, og **23** anvender Yahoo-kurs × FX som markedsværdifallback. Makrodatakvalitet **45/100**; 2Y–10Y-kurve, inflationspres og kredit-/likviditetsstress mangler. URNU har individuel Data Score **40/100**. Fri likviditet, fuldt ETF-look-through, konkrete stopkurser og sammenlignelige temaflows er **N/A**. Offentlige markedspriser er dateret fredag, ikke lørdag.

### Dagens tre beslutningspunkter
1. **Ingen handler.** Bekræft NOVO-B's **15,77 %** mod loft **14 %** og modellens reduktionsforslag **13.214 kr.**.
2. **Gennemgå 18 Stop_Broken og 2 Alarm** på positionsniveau; prioriter NKT, SEC0, ASML og andre Reducer-signaler.
3. **Ingen ny kapitalallokering før Fed og Microsoft-regnskabet**; kontrollér især olie-/renterisiko og samlet AI-/ETF-overlap.