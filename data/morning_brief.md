# Investment OS – Morgenbrief
**Mandag 9. november 2026 · kl. ca. 07.00 CET · ingen handler udført**

## A. Executive view
**Markedsregime: forsigtigt rebound efter en hård AI-korrektion, ikke bekræftet ny optrend.** Fredag steg Nasdaq 1,09 % og S&P 500 0,31 %, men begge sluttede ugen i minus. Mandag morgen stiger asiatiske aktier og amerikanske futures. citeturn371327news10turn934458news0

**IOS:** Portfolio Health **55,91**, AI Confidence **54,17 (moderat)** og Macro/Rate Risk **50,03 (høj)**. Makrodatakvaliteten er kun **45/100**. Novo Nordisk ligger **16,76 %** mod modellens aktuelle positionsloft **16 %**. **Prioritet: risikokontrol og likviditetsafstemning frem for at gennemføre modellens tre køb.**

## B. Portfolio status
**Kilde:** [Autoritativt snapshot](https://github.com/tonnirasmussen70/Investment-OS/blob/main/data/portfolio_snapshot.json), branch main, læst direkte.

| Kontrol | Værdi |
|---|---:|
| generated_at | `2026-11-09T02:46:40.940400+01:00` |
| source.commit_sha | `834e979220bc06309600b5f28bd45dd31c54a3dd` |
| source.portfolio_file_sha256 | `fc8e497db9a7d37536a33da1191598153603543bf7967affd4bf2ab29f1d9da6` |
| data_quality.score | **100/100** |
| Samlet værdi | **1.136.301 kr.** |
| Aktiv markedsværdi | **704.181 kr.** |
| Modelafkast | **-3,16 %** |
| Portfolio Health / AI Confidence | **55,91 / 54,17** |
| Macro/Rate Risk | **50,03 – høj** |
| Positioner registreret / analyseret | **29 / 28** |
| Aktuelt modelpositionsloft | **16,00 %** |

Snapshotet er ca. 4 timer gammelt og **ikke stale**. Største positioner som andel af aktiv markedsværdi: Novo **16,76 %**, NKT **8,14 %**, Microsoft **7,16 %**, AL Sydbank **7,06 %**, VWCE **6,69 %**, ASML **5,45 %**, Danske Bank **5,09 %**, VGWD **4,72 %**, IS3Q **4,23 %**, 2B70 **4,13 %**. Novo overskrider loftet med **0,76 procentpoint**. Bankerne udgør **12,15 %** tilsammen, før foreslået køb. Forskellen på **432.120 kr.** mellem total og aktiv værdi er **ikke dokumenteret som fri likviditet**.

## C. Markedsstatus og makro
| Marked | Seneste verificerede observation |
|---|---|
| S&P 500, fredag 6/11 | **7.376,86 (+0,31 %)** |
| Nasdaq, fredag | **24.579,42 (+1,09 %)** |
| Dow, fredag | **51.285,73 (-0,46 %)** |
| Asien, mandag morgen | MSCI Asien ekskl. Japan **ca. +2 %**, Nikkei **ca. +3,5 %** |
| S&P 500-futures, mandag morgen | **ca. +0,6 %** |
| USA 10-årig, IOS pr. 6/11 | **4,859 %**; 2-årig **N/A** |
| EUR/USD, seneste daterede fredagsobservation | **ca. 1,1143**; aktuel morgenkurs **N/A** |
| Brent, mandag morgen | **ca. 98,20 USD/fad** |
| Guld, mandag morgen | **ca. 4.123 USD/oz** |
| Kobber, aktuel verificeret sammenlignelig kurs | **N/A** |

Kilder: Reuters 6.–9. november. citeturn371327news10turn934458news0turn934458news38

**Egen analyse:** Et rebound efter kraftige fald er ikke tilstrækkeligt til at bekræfte en trendvending. Stærkere amerikanske jobtal øger forventningerne om en renteforhøjelse i december, mens billigere olie dæmper noget af inflationspresset. IOS' rentemodel mangler 2-årig rente, rentekurve, inflations- og kreditkomponenter; den høje risikoklassifikation har derfor begrænset datadækning.

## D. Sektor- og kapitalstrømsrotation
**IOS-modelmomentum – ikke faktiske ETF-nettoflows:**

| Tema | Ticker | 1M | 3M | IOS |
|---|---|---:|---:|---|
| Semiconductors | SEC0 | -27,19 % | -18,48 % | Reducer |
| Defense | DFEN | -3,10 % | -16,67 % | Reducer |
| Uranium | URNU | -17,69 % | -28,82 % | Reducer |
| Clean energy | IQQH | -3,12 % | -6,55 % | Hold |
| Mining | WMIN | -5,68 % | -7,95 % | Hold |
| Copper miners | 4COP | -13,20 % | -16,29 % | Reducer |
| Rare earths | VVMX | -14,42 % | -30,57 % | Reducer |
| Infrastructure | 94VE | -3,04 % | -9,60 % | Reducer |

**Egen analyse:** Halvledertrenden er fortsat svag trods mandagens asiatiske rebound. Clean energy og mining viser relativ stabilisering, men ikke Øg-signaler. Verificerede nettoflows for de konkrete ETF'er: **N/A**.

## E. Porteføljepåvirkning
| Position | Vægt | IOS-score | Signal | 1M |
|---|---:|---:|---|---:|
| ASML | 5,45 % | 27,58 | Reducer | -21,18 % |
| Microsoft | 7,16 % | 88,46 | Hold | +1,67 % |
| TSMC | 1,43 % | 37,94 | Reducer | -18,02 % |
| Novo Nordisk | 16,76 % | 44,05 | Hold; loftreduktion | +7,82 % |
| Vestas | 2,61 % | 89,72 | Øg | +12,31 % |
| NKT | 8,14 % | 44,48 | Hold | -1,75 % |
| AL Sydbank | 7,06 % | 93,07 | Hold | +2,18 % |
| Danske Bank | 5,09 % | 77,37 | Øg | +0,65 % |
| Celestica | 3,54 % | 17,14 | Reducer | -42,03 % |

**Egen analyse:** Microsoft er relativt stærk, mens ASML, TSMC og Celestica kræver særlig risikogennemgang. Vestas har stærkt modelmomentum, men regnskab 11/11. Danske Bank-køb vil øge den samlede bankvægt fra **12,15 %** til omtrent **14,26 %** før eventuelle øvrige ændringer. Alphabet `ABEA:XETR` har **Data Score 0** og mangler kurs.

## F. Ændringer siden seneste brief
Sammenlignet med fredagens verificerede morgenbrief, **ikke depotafstemt afkast**:

| KPI | Fredag 6/11 | Mandag 9/11 | Forskel |
|---|---:|---:|---:|
| Samlet værdi | 1.188.646 kr. | **1.136.301 kr.** | **-52.345 kr.** |
| Modelafkast | -0,59 % | **-3,16 %** | -2,57 procentpoint |
| Portfolio Health | 64,70 | **55,91** | -8,79 |
| AI Confidence | 56,68 | **54,17** | -2,51 |
| Macro/Rate Risk | 48,29 | **50,03** | +1,74 |
| Stop_Broken / Alarm / Tighten | 14 / 3 / 0 | **15 / 4 / 0** | +1 / +1 / 0 |

Masterfilens SHA er **uændret** i forhold til fredagens brief (`fc85f720…`). Værdiforskellen er stadig **ikke verificeret som rent markedsafkast**. Modelkøen er nu **Vestas, Pandora og Danske Bank som køb** samt Novo-reduktion; fredagens VGWD-køb er udgået. Den interne sammenligning med **8/11 kl. 13.36** viser ingen nye opportunity-indgange eller rangændringer og kun marginale scorebevægelser. Individuelle stopkurser: **N/A**.

## G. Dagens begivenheder og kommende regnskaber
**9/11:** Markedets reaktion på sidste uges AI-salg og fredagens stærke amerikanske jobrapport. **10/11:** Amerikanske inflationstal (CPI) ventes; udfald endnu ukendt. **11/11:** Vestas Q3-regnskab, bekræftet i selskabets kalender. **19/11:** NKT-regnskab ifølge tidligere kalenderoplysninger; tidspunkt bør genbekræftes. citeturn934458news0turn934458search10

## H. Køb / hold / reducer
**Direkte Investment OS-output fra decision_queue/rebalance, ikke handelsordrer:**

| Aktiv | Primært signal | Rebalance-output | Beløb |
|---|---|---|---:|
| Novo Nordisk | Hold | **Sælg til 16 %**, positionsloft | **-5.339 kr.** |
| Vestas | Øg | Køb, 2,61 → 5,75 % | **+22.136 kr.** |
| Pandora | Øg | Køb, 3,97 → 7,05 % | **+21.726 kr.** |
| Danske Bank | Øg | Køb, 5,09 → 7,21 % | **+14.886 kr.** |
| ASML, TSMC, SEC0, CLS m.fl. | Reducer | Ingen handel – konfidensgate | 0 kr. |

**Execution summary:** 4 modelhandler, brutto **64.086 kr.**, netto kontantbehov **53.408 kr.**, **15 constraint-markerede rækker**.

**Egen vurdering:** Afvent de tre køb. Der er ikke verificeret fri likviditet, minimumshandel, handelsomkostninger eller fuldt sektor-/ETF-overlap. Novo-overskridelsen skal vurderes mod det **aktuelle 16 %-loft**; tidligere briefs anvendte 14 %, hvilket er en vigtig modelregelændring, der bør afklares før handling. Ingen handler udført.

## I. Usikkerheder og datakvalitet
Snapshotet er **friskt**, men porteføljens interne score **100/100** er ikke en depotafstemning. **22 udenlandske positioner** bruger valutaneutralt DKK-afkast, **22** bruger Yahoo-kurs × FX som fallback, og Alphabet mangler kurs. **Makrodatakvalitet 45/100**. Frie kontanter, præcise stopkurser, aktuelle kobber- og valutakurser og tematiske ETF-nettoflows: **N/A**.

### Dagens tre beslutningspunkter
1. **Ingen handler.** Afstem faldet i porteføljeværdi på **52.345 kr.**, den aktuelle Novo-vægt **16,76 %** og positionsloftet **16 %**.
2. **Gennemgå 15 Stop_Broken og 4 Alarm**, især Celestica, ASML, TSMC og SEC0; ret Alphabet-kursmapping og makrodatamangler.
3. **Afvent Vestas +22.136 kr., Pandora +21.726 kr. og Danske Bank +14.886 kr.**, indtil likviditet, overlap og Vestas-regnskabet er vurderet.
