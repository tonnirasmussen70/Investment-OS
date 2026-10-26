# Investment OS – Morgenbrief
**Mandag 26. oktober 2026 · ca. kl. 07.00 CET · ingen handler udført**

## A. Executive view
**Markedsregime: afventende og fortsat rentefølsomt.** Amerikanske aktier sluttede svagere fredag, og de asiatiske markeder er blandede mandag morgen. Brent er faldet fra fredagens top, men ligger fortsat omkring **114,48 USD/fad**. Den amerikanske 10-årige rente er omkring **4,97 %**. citeturn0news45turn0news46

**Investment OS-output:** Portfolio Health **60,58**, AI Confidence **54,02 (moderat)** og Macro/Rate Risk **60,06 (høj)**. Modellen har fortsat **ét køb i VGWD på 17.659 kr.** og **én reduktion i NOVO-B på 14.347 kr.** Der er **18 Stop_Broken og 2 Alarm**. **Dagens prioritet er risikokontrol og koncentration – ingen handler.**

## B. Portfolio status
**Autoritativ kilde:** urlGitHub: portfolio_snapshot.json på mainhttps://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json. Snapshotet er læst direkte; Excel og app.py er ikke brugt til genberegning.

| Kontrolpunkt | Verificeret snapshot |
|---|---:|
| `generated_at` | `2026-10-26T01:28:24.246720+01:00` |
| `source.commit_sha` | `917eb3ef4b64417a6f2edef79c8944b907e48755` |
| `source.portfolio_file_sha256` | `8370730267a363def58211a7c1838914a74c6ce44be507433955833a61eb6795` |
| `data_quality.score` | **100/100** |
| Samlet porteføljeværdi | **1.172.552 kr.** |
| Aktiv markedsværdi | **740.432 kr.** |
| Samlet modelafkast | **+3,24 %** |
| Portfolio Health | **60,58** |
| AI Confidence | **54,02 – moderat** |
| Macro/Rate Risk | **60,06 – høj** |
| Positionsloft | **14,00 %** |

**Friskhed:** ca. **5 timer og 31 minutter**; **ikke stale**. 30 registrerede og 29 analyserede positioner. Snapshotet er genereret mandag, men bygger i vidt omfang på fredagens markedskurser.

**Største positioner, vægt af aktiv markedsværdi:** NOVO-B **15,94 %**, NKT **7,74 %**, Microsoft/MSF **7,57 %**, ASML **7,10 %**, VWCE **6,49 %**, Danske Bank **6,37 %**, AL Sydbank **5,51 %**, SEC0 **5,09 %**, IS3Q **4,05 %** og Pandora **3,77 %**. NOVO-B ligger **1,94 procentpoint over 14 %-loftet**. De to danske bankpositioner udgør tilsammen **11,88 %**. Forskellen på **432.120 kr.** mellem samlet og aktiv værdi er **ikke verificeret som disponible kontanter**.

## C. Markedsstatus og makro
| Marked | Seneste daterede observation |
|---|---:|
| S&P 500, fredag 23/10 | **7.623,68 (-0,52 %)** |
| Nasdaq Composite, fredag | **25.955,34 (-0,21 %)** |
| Dow Jones, fredag | **52.215,16 (-1,23 %)** |
| Asien, tidlig mandag | **Blandet; Japan ca. -0,2 %, Sydkorea ca. -0,5 %** |
| USA 10-årig statsrente, tidlig mandag | **ca. 4,97 %** |
| EUR/USD, ECB-reference 23/10 | **1,1193** |
| EUR/DKK, ECB-reference 23/10 | **7,4748** |
| Brent, tidlig mandag | **ca. 114,48 USD/fad (-1,9 %)** |
| WTI, seneste verificerede fredagsafregning | **103,27 USD/fad** |
| Guld, tidlig mandag | **ca. 4.012 USD/oz (+0,4 %)** |
| Kobber, LME 3M | **14.355 USD/ton, 20/10**; nyere sikkert sammenlignelig kurs **N/A** |

Aktielukning og fredagsolie: AP/Reuters. Mandagens Asien, Brent, rente og guld: Reuters. Valuta: ECB. Kobber: dateret Reuters-observation; **ikke mandagskurs**. citeturn0news45turn0news47turn0news46turn1search0turn3search2

**Egen analyse:** Den lavere oliepris er en kortsigtet lettelse, ikke en normalisering af energirisikoen. Kombinationen af dyr energi, næsten 5 % amerikansk langrente og store AI-investeringer taler for at prioritere pengestrømme og porteføljerisiko over kortvarige kursrebound. Reuters' økonomundersøgelse peger på forventet rentepause ved ugens Fed-møde, men en mulig forhøjelse i december; dette er **forventninger, ikke en beslutning**. citeturn2news73

## D. Sektor- og kapitalstrømsrotation
**Investment OS-momentum fra snapshotet – ikke målte nettoflows:**

| Tema | IOS-aktiv | Modelsignal | 1M | 3M |
|---|---|---|---:|---:|
| Semiconductors | SEC0 | **Hold**, negativ rotation | -12,01 % | +1,33 % |
| Defense | DFEN | **Reducer** | -2,69 % | -4,30 % |
| Uranium | URNU | **Reducer** | -21,36 % | N/A |
| Clean energy | IQQH | **Reducer** | -3,97 % | -5,95 % |
| Mining | WMIN | **Hold** | -9,69 % | +2,92 % |
| Copper miners | 4COP | **Reducer** | -12,37 % | -2,16 % |
| Rare earths | VVMX | **Reducer** | -22,48 % | -21,01 % |
| Infrastructure | ABB / 94VE | **Reducer / Reducer** | -15,44 % / -0,65 % | -11,06 % / -7,80 % |

**Verificerede globale fondskapitalstrømme:** Ugen til 21/10 gav **28,16 mia. USD netto ind i aktiefonde**, heraf **5,05 mia. USD i teknologifonde**; cykliske forbrugsfonde havde **1,29 mia. USD ud**. Der er **ikke** verificeret særskilte nettoflows for de otte IOS-temaer. citeturn1news74

**Egen analyse:** Positivt flow til brede teknologifonde er ikke det samme som forbedret momentum i SEC0. Uranium, rare earths og kobberminer viser fortsat svage 1M-signaler. Ingen begrundelse for at øge disse temaer alene på grund af kursfald.

## E. Porteføljepåvirkning
**entity["company","ASML","Dutch semiconductor equipment company"]:** **7,10 % · Hold · Decision Score 65,51 · 1M -6,39 %**. Modellen registrerer negativ rotation; eksponeringen overlapper med SEC0 og TSMC. urlASML Investor Relationshttps://www.asml.com/en/investors

**entity["company","Microsoft","US technology company"]:** **7,57 % · Hold · score 86,19 · 3M +34,05 %**. Stærk relativ modelposition, men stigende fokus på AI-capex og afkast. Regnskab **28/10 efter amerikansk børslukning**. urlMicrosoft Investor Relationshttps://www.microsoft.com/en-us/Investor/

**entity["company","TSMC","Taiwan semiconductor foundry"]:** **3,01 % · Hold · score 69,90 · 1M -7,23 %**. Positivt 3M-momentum **+5,15 %**, men svagt 1M. Ingen modelhandel. urlTSMC Investor Relationshttps://investor.tsmc.com/

**entity["company","Novo Nordisk","Danish pharmaceutical company"]:** **15,94 % · Reducer · score 36,83 · 3M -21,45 %**. Rebalance foreslår **14.347 kr. reduktion** til **14,00 %**, med markeringerne `Konfidensgate, Positionsloft`. **Dette er modeloutput, ikke en ordre.** Regnskab **4/11**. urlNovo Nordisk regnskabskalenderturn1search2

**entity["company","NKT","Danish power cable manufacturer"]:** **7,74 % · Reducer · score 29,31 · 1M -11,38 %**. **entity["company","Vestas","Danish wind turbine manufacturer"]:** **2,48 % · Hold · score 61,43 · 1M -7,25 %**. Regnskaber **19/11** og **11/11**. urlNKT finanskalenderturn2search0 · urlVestas finanskalenderturn2search1

**Danske banker:** entity["company","Danske Bank","Danish banking group"] **6,37 % · Reducer · score 51,44**; entity["company","AL Sydbank","Danish banking group"] **5,51 % · Hold · score 69,90**. Samlet **11,88 %**; fælles rente- og kreditrisiko, men forskellige modelsignaler. urlDanske Bankhttps://danskebank.com/ · urlAL Sydbankhttps://www.al-sydbank.dk/

**Øvrige:** Frontline (**score 90,75**), 2B70 (**90,61**) og ServiceNow (**86,54**) topper opportunities, men alle har **Hold**. VGWD (**80,62**) har derimod et særskilt **Øg**-signal.

## F. Ændringer siden seneste brief
**Sammenligning med søndagens brief; ikke depotafstemt dagsafkast:**

| Måling | Søndag | Mandag | Ændring |
|---|---:|---:|---:|
| Samlet værdi | 1.172.616 kr. | **1.172.552 kr.** | **-64 kr.** |
| Aktiv værdi | 740.496 kr. | **740.432 kr.** | **-64 kr.** |
| Modelafkast | +3,24 % | **+3,24 %** | Afrundet uændret |
| Portfolio Health | 60,58 | **60,58** | Afrundet uændret |
| AI Confidence | 54,02 | **54,02** | Afrundet uændret |
| Macro/Rate Risk | 60,06 | **60,06** | Uændret |
| Stop_Broken / Alarm / Tighten | 18 / 2 / 0 | **18 / 2 / 0** | Uændret |

**Masterfilens SHA er uændret** fra søndag (`83707302…`). Snapshotets interne `changes` sammenligner direkte med **25/10 kl. 02.23 +02:00** og viser ingen ændringer i opportunity-rangering; kun ubetydelige scorejusteringer. **Ingen nye væsentlige modelhandlinger**. Købsforslag VGWD **17.660 → 17.659 kr.**, reduktion NOVO-B **14.339 → 14.347 kr.** Individuelle stopkursændringer: **N/A**. Det fulde tidligere snapshot er ikke genindlæst særskilt.

## G. Dagens begivenheder og kommende regnskaber
**Mandag 26/10:** Fokus på markedsåbningen efter olieprisens fald og fortsat geopolitisk usikkerhed. Ingen specifik porteføljerelevant selskabsmeddelelse fra i morges er verificeret.

**27.–28/10:** urlFOMC-rentemødehttps://www.federalreserve.gov/monetarypolicy/fomccalendars.htm; beslutning ventes **onsdag kl. 19.00 dansk tid**, fordi USA endnu har sommertid. **28/10:** Microsoft FY27 Q1 efter amerikansk lukning. **4/11:** Novo Nordisk ni-månedersregnskab. **11/11:** Vestas Q3. **19/11:** NKT Q1–Q3. citeturn2search5turn1search2turn2search1turn2search0

## H. Handlingsorienteret køb / hold / reducer
**Investment OS-output fra `decision_queue` og `rebalance` – ingen handler udført:**

| Aktiv | Modelsignal | Rebalance | Beløb |
|---|---|---|---:|
| NOVO-B | **Reducer** | **Sælg** til 14,00 %; konfidensgate + positionsloft | **-14.347 kr.** |
| VGWD | **Øg** | **Køb**; vægt 1,41 → 3,80 %; ingen angivet constraint | **+17.659 kr.** |
| NKT, DANSKE, ABB, DFEN, URNU m.fl. | **Reducer** | Ingen handel, primært konfidensgate | 0 kr. |
| ASML, MSF, TSM, SEC0, VWCE, IS3Q | **Hold** | Ingen handel | 0 kr. |
| **Execution summary** | **1 køb / 1 reduktion** | **Brutto 32.006 kr.; netto +3.311 kr.** | **15 constraint-markerede rækker** |

**Egen vurdering:** **Ingen nye handler nu.** NOVO-B's loftoverskridelse er den vigtigste konkrete risikofaktor. VGWD kan sprede stilrisikoen mod udbytteaktier, men overlapper med VWCE/IS3Q og kan øge den samlede aktieeksponering. Afstem faktisk depotvægt, minimumshandel, kontanter og ETF-look-through, før modelkøen eventuelt bruges som beslutningsgrundlag. **Netto +3.311 kr. er et modeltal, ikke verificeret likviditetsbehov.**

## I. Usikkerheder og datakvalitet
Snapshotets **100/100** er intern datakvalitet, ikke garanti for depotafstemning. **23 udenlandske positioner** anvender valutaneutralt DKK-afkast, og **23** bruger Yahoo-kurs × FX som fallback for markedsværdi. Makrooverlayets datakvalitet er kun **45/100**; 2Y–10Y-kurve, inflations- og kreditstresskomponenter mangler. URNU har individuel Data Score **40/100**. Fri likviditet, præcise stopkurser, fuldt ETF-look-through, individuelle temaflows og aktuel mandagskobberkurs: **N/A**. Markedsobservationerne har forskellige tidsstempler.

### Dagens tre beslutningspunkter
1. **Ingen handler.** Bekræft NOVO-B-vægten på **15,94 %** og risikoloftet på **14 %** mod faktisk depot.
2. **Gennemgå 18 Stop_Broken og 2 Alarm** på positionsniveau, især NKT, ABB og svage tema-ETF'er.
3. **Afvent VGWD-køb**, indtil finansiering, minimumshandel og overlap er kontrolleret; følg Fed og Microsoft-regnskabet onsdag.