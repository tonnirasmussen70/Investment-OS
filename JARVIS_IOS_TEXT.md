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

Stemmeinput og -output, fri samtale, Home Assistant og agentorkestrering er ikke implementeret her. Funktionen `jarvis.text_client.answer_question` kan senere genbruges som indgang til transskriberet tale. Det tilføjer ikke i sig selv stemmestyring.
