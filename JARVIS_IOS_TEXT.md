# Jarvis – IOS tekstindgang

Åbn den eksisterende IOS-app som normalt. Vælg **Jarvis** i Streamlits sidemenu.

Eksempler:
- Hvordan er status på min portefølje?
- Vis porteføljens signaler
- Hvad er status på Investment OS?
- Analyser FRO (brug en ticker fra dit IOS-snapshot)

Dette er en afgrænset dansk tekstindgang, ikke en fri AI-samtale. Svaret bruger eksisterende IOS-beregninger. Ikke-understøttede spørgsmål afvises. Ekstern research er slået fra i denne brugerflade.

Data læses på ny for hvert spørgsmål fra `INVESTMENT_OS_SNAPSHOT` eller `data/portfolio_snapshot.json`. Advarsler og snapshot-tidspunkt vises ved svaret; svar opdateres først ved et nyt spørgsmål. Hvis snapshot mangler, åbn hovedsiden og opdatér IOS. Jarvis udløser ingen beregninger eller filskrivninger. Appen kan i øvrigt opdatere snapshot på sin hovedside som hidtil.

Siden bruger samme lokale Python-funktioner som den eksisterende Jarvis-adapter; den opretter ikke en MCP-klient eller netværksforbindelse. MCP-serveren fra Sprint 1 er uændret. API'ets HTTP-audit anvendes ikke af denne lokale side. Brug IOS' eksisterende adgangskontrol; gør ikke en lokal app offentligt tilgængelig uden en særskilt adgangsløsning.

Ingen nye API-nøgler, abonnementer eller HA-installation kræves. Kør den eksisterende app med `python -m streamlit run app.py` hvis den ikke allerede er startet. Kræver installation af projektets eksisterende requirements.

Test: `python -m pytest -q tests/test_jarvis_text_client.py tests/test_jarvis_mcp.py`.

Stemmeinput, fri samtale, Home Assistant og agentorkestrering er ikke implementeret her. Funktionen `jarvis.text_client.answer_question` kan senere genbruges som indgang til transskriberet tale. Det tilføjer ikke i sig selv stemmestyring.

## Automatisk oplæsning

Nye svar forsøges automatisk læst op på dansk. Slå **Læs nye svar op automatisk** fra for kun at få tekst. **Stop** afbryder oplæsningen, og **Læs svaret op** gentager svaret. Dataadvarsler læses før selve svaret. Et nyt spørgsmål erstatter den gamle afspiller; afspilningen afbrydes ved en opdatering af siden. En almindelig genkørsel genstarter ikke det eksisterende svar.

Browseren kan kræve et klik på **Læs svaret op**, før lyd er tilladt, særligt i den indlejrede afspiller. Ved manglende browserunderstøttelse vises en besked; tekstsvaret virker fortsat. Dansk stemme vælges, hvis browseren har en. En lokal dansk stemme foretrækkes; ellers bruges browserens tilgængelige stemme. Browser-/Windows-stemmer kan afhængigt af konfiguration bruge en onlinetjeneste. Der er ingen ny serverbaseret TTS-tjeneste, API-nøgle eller betalt afhængighed i IOS.

Test på Windows: åbn Jarvis i Edge eller Chrome, stil et spørgsmål og lyt. Hvis lyd blokeres, klik **Læs svaret op**. Prøv derefter **Stop** og et nyt spørgsmål. Prøv også at slå automatisk oplæsning fra. Faktisk lyd, installeret dansk stemme og browserens autoplay-politik skal kontrolleres på din pc; CI tester controllerens logik med en simuleret tale-API.
