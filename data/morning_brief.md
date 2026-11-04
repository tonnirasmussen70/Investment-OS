# Investment OS – Morgenbrief
**Onsdag 4. november 2026 · ca. 07.00 CET · ingen handler udført**

## A. Executive view
**Regime: forhøjet risiko for AI og datacentre.** Tirsdag steg S&P 500 0,36 % og Nasdaq 0,83 %, men onsdag morgen falder asiatiske chipaktier og Nasdaq-futures efter de amerikanske midtvejsvalg. Reuters rapporterer demokratisk flertal i begge kamre og investorbekymring for strammere AI-regulering. [Reuters 3/11](https://www.reuters.com/world/china/global-markets-wrapup-1-2026-11-03/) · [Reuters 4/11](https://www.reuters.com/world/china/global-markets-wrapup-1-2026-11-04/).

**Investment OS:** Portfolio Health **58,59**, AI Confidence **53,66 (moderat)**, Macro/Rate Risk **50,97 (høj)**. **Vigtigste prioritet:** Novo Nordisk ligger over positionsloftet, og AI-/halvledermomentum er svagt. Modellen har **ét køb (VGWD) og én loftbetinget reduktion (Novo)**; ingen handler udføres.

## B. Portfolio status
**Kilde:** [portfolio_snapshot.json på main](https://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json). Læst direkte, uden genberegning fra Excel.

| Kontrol | Værdi |
|---|---:|
| generated_at | `2026-11-04T03:26:29.451914+01:00` |
| source.commit_sha | `fb379a963e847209ba8a38775df124032616d3e3` |
| source.portfolio_file_sha256 | `5475e66d8c8a850e8e4efc68b5a46180513bbc9a8c8de25d567d2cbdf3f872ea` |
| data_quality.score | **100/100** (intern modelmåling) |
| Porteføljeværdi | **1.185.878 kr.** |
| Aktiv markedsværdi | **753.758 kr.** |
| Modelafkast | **+1,37 %** |
| Portfolio Health / AI Confidence | **58,59 / 53,66** |
| Macro/Rate Risk | **50,97 – høj** |
| Registrerede / analyserede positioner | **29 / 28** |

Snapshotet er **under 24 timer gammelt (ikke stale)**. Største vægte af aktiv værdi: **Novo 15,66 %**, **NKT 7,61 %**, **AL Sydbank 6,60 %**, **Microsoft 6,49 %**, **VWCE 6,38 %**, **ASML 5,58 %**, **SEC0 4,94 %**, **Danske Bank 4,76 %**, **Celestica 4,13 %**, **IS3Q 4,00 %**. Novo overskrider 14 %-loftet med **1,66 procentpoint**. Danske Bank og AL Sydbank vejer tilsammen **11,35 %**; teknologi-/AI-overlap findes også i globale ETF'er. Forskellen mellem samlet og aktiv værdi (**432.120 kr.**) er **ikke verificeret fri likviditet**.

## C. Markedsstatus og makro
| Indikator | Seneste verificerede observation |
|---|---|
| USA, lukning tirsdag 3/11 | **S&P 500 +0,36 %; Nasdaq +0,83 %; Dow -0,38 %** |
| USA-futures, tidlig onsdag | **Nasdaq ca. -0,8 %; S&P 500 ca. -0,6 %** (Reuters-observation) |
| Asien, onsdag morgen | **Nikkei ca. -3 %**; betydeligt pres på Samsung, SK Hynix og TSMC |
| USA 10-årig rente | **4,906 %** onsdag morgen; IOS pr. 3/11: **4,952 %** |
| USA 2-årig / rentekurve, IOS | **4,59 % / +0,304 procentpoint** |
| EUR/USD | **ca. 1,1249** onsdag morgen; EUR/DKK: **N/A** |
| Brent | **103,60 USD/fad** ved tirsdagens afregning; onsdagens præcise pris: **N/A** |
| Guld | **3.930,04 USD/oz** tirsdag; onsdagens præcise kurs: **N/A** |
| Kobber | Ny sammenlignelig verificeret kurs: **N/A** |

Markedsdata er fra forskellige tidspunkter, ikke samtidige livekurser. [Reuters, 3/11](https://www.reuters.com/world/china/global-markets-wrapup-1-2026-11-03/) · [Reuters, 4/11](https://www.reuters.com/world/china/global-markets-wrapup-1-2026-11-04/). IOS viser HY-spread **3,43 procentpoint** og inflationskomponent **2,30 %**. **Egen analyse:** Lavere langrente kan hjælpe værdiansættelser, men risiko for politisk regulering og svækket AI-capex gør den samlede situation mere usikker.

## D. Sektor- og kapitalstrømsrotation
**IOS-momentum – ikke dokumenterede nettofondstilstrømninger:**

| Tema | Ticker | Signal | 1M | 3M |
|---|---|---|---:|---:|
| Semiconductors | SEC0 | Reducer | -19,16 % | -7,91 % |
| Defense | DFEN | Hold | +0,60 % | -6,45 % |
| Uranium | URNU | Reducer | -15,71 % | -21,16 % |
| Clean energy | IQQH | Reducer | -7,03 % | -10,49 % |
| Mining | WMIN | Reducer | -7,97 % | -6,82 % |
| Copper miners | 4COP | Reducer | -11,96 % | -11,60 % |
| Rare earths | VVMX | Reducer | -17,43 % | -27,16 % |
| Infrastructure | 94VE | Øg (ikke eksekverbar) | +2,20 % | -3,80 % |

**Egen analyse:** Halvledere og rare earths har svagt momentum. Infrastruktur viser bedre 1M-modstandskraft, men 94VE's Øg blokeres af konfidensgate. Verificerede nettoflows for de konkrete ETF'er: **N/A**.

## E. Porteføljepåvirkning
**ASML:** **5,58 % · Reducer · score 53,99 · 1M -14,71 %**. Svagt kortsigtet momentum og eksponering mod AI-capex. **Microsoft:** **6,49 % · Hold · score 84,00 · 3M +10,48 %**. Relativ styrke, men aftagende acceleration. **TSMC:** **2,14 % · Reducer · score 50,92 · 1M -16,67 %**. Onsdagens asiatiske kursfald er endnu ikke nødvendigvis afspejlet i IOS.

**Novo Nordisk:** **15,66 % · Hold · score 42,70 · 1M +8,62 %**. Modellen angiver særskilt **loftbetinget salg på 12.482 kr.**, selv om aktiens primære signal er Hold. **Regnskab i dag 4/11**: følg guidance, Wegovy/Ozempic, marginer og konkurrencen med Eli Lilly. [Novo Nordisk IR](https://www.novonordisk.com/investors/financial-results.html).

**NKT:** **7,61 % · Reducer · score 39,14**, tidlig vending, men ingen modelhandel. **Vestas:** **2,44 % · Hold · score 69,90 · 3M +11,51 %**. **AL Sydbank:** **6,60 % · Hold · score 91,63**; **Danske Bank:** **4,76 % · Hold · score 61,61**. **Celestica:** **4,13 % · Reducer · score 14,78 · 1M -32,08 %**, markant svagt teknisk modelbillede. **Alphabet GOOG:XMIL:** Data Score **0**; teknisk vurdering er ikke pålidelig.

## F. Ændringer siden seneste brief
Sammenligning med tirsdagens brief, **ikke depotafstemt afkast**:

| KPI | 3/11 | 4/11 | Forskel |
|---|---:|---:|---:|
| Samlet værdi | 1.180.028 | **1.185.878 kr.** | **+5.850 kr.** |
| Aktiv værdi | 747.908 | **753.758 kr.** | **+5.850 kr.** |
| Modelafkast | +1,14 % | **+1,37 %** | +0,23 procentpoint |
| Portfolio Health | 59,02 | **58,59** | -0,43 |
| AI Confidence | 53,07 | **53,66** | +0,59 |
| Macro/Rate Risk | 48,60 | **50,97** | +2,37 |
| Stop_Broken / Alarm / Tighten | 15 / 3 / 1 | **15 / 1 / 0** | 0 / -2 / -1 |

Masterfil-SHA ændret **3057d497… → 5475e66d…**, så værdiforskellen kan ikke kaldes rent kursafkast. **AL Sydbank er ændret fra Øg/køb til Hold/ingen handel**, og Novo er ændret fra Reducer til Hold, men **positionsloftet udløser fortsat et reduktionsforslag**. VGWD-køb **22.587 → 22.770 kr.**; Novo-reduktion **13.301 → 12.482 kr.**. Snapshotets interne ændringslog sammenligner med **3/11 kl. 17.54**, ikke tirsdag morgen; den viser bl.a. AL Sydbank-score **+21,73** og Microsoft **+14,10**. Individuelle stopkurser: **N/A**.

## G. Dagens begivenheder
**4/11:** Novo Nordisks ni-månedersregnskab og guidance. Amerikanske midtvejsvalg er afholdt 3/11; markedsreaktionen på rapporterede demokratiske sejre kan påvirke AI-regulering, forsvar og sundhed. [Reuters 4/11](https://www.reuters.com/world/china/global-markets-wrapup-1-2026-11-04/). **Kommende:** Vestas Q3 **11/11** og NKT ni måneder **19/11**; bekræft seneste tider på [Vestas IR](https://www.vestas.com/en/investor) og [NKT IR](https://investors.nkt.com/calendar/).

## H. Køb / hold / reducer
**Direkte Investment OS-output fra decision_queue og rebalance:**

| Aktiv | Primært signal | Rebalance | Beløb |
|---|---|---|---:|
| Novo Nordisk | **Hold** | **Sælg** til 14 % pga. positionsloft | **-12.482 kr.** |
| VGWD | **Øg** | **Køb**; vægt 1,40 % → 4,42 % | **+22.770 kr.** |
| AL Sydbank | **Hold** | Ingen handel | **0 kr.** |
| 94VE | Øg | Ingen handel, konfidensgate | **0 kr.** |
| ASML, TSMC, NKT, SEC0, CLS og flere | Reducer | Ingen handel, konfidensgate | **0 kr.** |

**Execution summary:** **2 modelhandler**, brutto **35.251 kr.**, netto beregnet kontantbehov **10.288 kr.**, **16 constraint-markerede rækker**. **Egen vurdering:** Afvent begge dispositioner indtil Novo-regnskabet og kontrol af faktisk likviditet, minimumshandel og VGWD-overlap med VWCE/IS3Q. Novo-loftet er en konkret risikogrænse; det bør ikke overses, blot fordi det primære signal nu er Hold.

## I. Usikkerheder og datakvalitet
Snapshotet er **friskt**, men 100/100 er en intern score. **22 udenlandske positioner** bruger valutaneutralt afkast, **22** bruger Yahoo-kurs × FX som markedsværdifallback, og **GOOG:XMIL mangler markedskurs (Data Score 0)**. Faktisk likviditet, præcise stopkurser, fuldt ETF-look-through og tematiske nettoflows er **N/A**. Dagens Novo-regnskab er ikke indregnet i snapshotet, og amerikanske futures kan ændre sig før åbning.

### Dagens tre beslutningspunkter
1. **Ingen handler.** Vurder Novo-regnskabet og loftoverskridelsen **15,66 % mod 14 %**, før der træffes beslutning.
2. **Gennemgå 15 Stop_Broken og 1 Alarm**, især CLS, SEC0, ASML og TSMC; få rettet GOOG:XMIL.
3. **Afvent VGWD-køb på 22.770 kr.**, indtil likviditet, overlap, minimumshandel og omkostninger er dokumenteret.
