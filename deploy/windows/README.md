# Jarvis på Windows — lokal-first deployment

Denne pakke installerer Jarvis API som en production-konfigureret, lokal service
på en Windows-pc. API'et bindes udelukkende til `127.0.0.1`; installationen
opretter ingen firewallregel og eksponerer ikke Jarvis på hjemmenetværket eller
internettet.

## Forudsætninger

- Windows 10 eller 11 med Windows PowerShell 5.1 eller nyere.
- Python 3.11 eller 3.12 installeret som `py.exe` eller `python.exe`.
- Repositoryet ligger i en permanent lokal mappe.
- Pc'en skal være tændt, vågen og brugeren logget ind, når Jarvis skal anvendes.

## Installation

Åbn en almindelig, ikke-administrator PowerShell som den Windows-bruger, der
skal køre Jarvis, gå til repositoryet, og kør:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\deploy\windows\Install-Jarvis.ps1
```

Installationen:

1. opretter eller genbruger `.venv` og installerer `requirements.txt`;
2. genererer et kryptografisk tilfældigt API-token;
3. gemmer konfiguration og audit-log under
   `%LOCALAPPDATA%\InvestmentOS\Jarvis`;
4. begrænser ACL-adgangen til konfigurationsfilen til den aktuelle bruger;
5. registrerer Scheduled Task `InvestmentOS-Jarvis` ved brugerlogon;
6. starter API'et og kører health-, readiness- og autentificeret smoke-test.

Tokenet genbruges ved senere installationer og udskrives aldrig. Et nyt token kan
oprettes ved kontrolleret at erstatte `JARVIS_API_TOKEN` i `jarvis.env` med en
tilfældig værdi på mindst 32 tegn og derefter genstarte opgaven.

## Drift

Kontrollér den kørende service:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\deploy\windows\Test-Jarvis.ps1
```

Genstart efter kode- eller konfigurationsændringer:

```powershell
Stop-ScheduledTask -TaskName "InvestmentOS-Jarvis"
Start-ScheduledTask -TaskName "InvestmentOS-Jarvis"
```

Efter en repositoryopdatering køres `Install-Jarvis.ps1` igen. Det opdaterer
afhængighederne, bevarer token og driftsgrænser, genregistrerer opgaven og kører
smoke-testen.

Standardadressen er:

```text
http://127.0.0.1:8000
```

Audit-loggen findes som standard under:

```text
%LOCALAPPDATA%\InvestmentOS\Jarvis\audit\jarvis_audit.jsonl
```

Procesopstart og tekniske serverfejl gemmes i `service.log` samme sted som
konfigurationen. Den aktive og tre tidligere startlogfiler bevares. Uvicorns rå
accesslog er deaktiveret, så URL-stier og query-parametre ikke optræder i
serviceloggen.

Scheduled Task-historikken bruges til at diagnosticere opstartsfejl. Hvis pc'en
går i slumretilstand eller brugeren ikke er logget ind, er den lokale service
ikke garanteret tilgængelig.

## Fjern opgaven

Følgende stopper og afregistrerer Scheduled Task, men bevarer konfiguration,
token og auditdata:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\deploy\windows\Remove-JarvisTask.ps1
```

## Senere netværksudvidelse

`Start-Jarvis.ps1` afviser bevidst enhver bind-adresse bortset fra `127.0.0.1`.
Du må derfor ikke blot ændre adressen til `0.0.0.0`. Adgang fra hjemmenetværk
eller internet kræver en separat sprint med TLS-terminering, reverse proxy,
Windows Firewall-regler, tokenrotation og en ny sikkerhedstest. Automatisk
porteføljeændring eller handel er fortsat ikke tilladt.
