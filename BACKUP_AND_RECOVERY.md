# Investment OS — Backup & Disaster Recovery v1.0

## Formål
Investment OS skal kunne genetableres, selv hvis den lokale PC eller Streamlit-miljøet går tabt.

## Backup-arkitektur

### Lag 1 — GitHub
GitHub er system of record for kildekode, konfiguration, dokumentation og versionshistorik.

- `main` er den godkendte produktionslinje.
- Ændringer skal commits/pushes løbende.
- Større stabile milepæle mærkes med versions-tags/releases.

### Lag 2 — Google Drive
Google Drive er den uafhængige off-site backup og skal indeholde:

1. En komplet Git mirror-backup (`Investment-OS.git`) med branches, tags og historik.
2. En læsbar ZIP/snapshot af den aktuelle produktionsversion.
3. Runtime-/historikdata, som ikke allerede er versionsstyret i GitHub.
4. Denne restore-procedure.

Google Drive-backuppen må ikke være eneste kopi af kildekoden; GitHub og Drive skal fungere som uafhængige lag.

## Mål

- RPO: maksimalt 24 timers tab af ikke-Git-versionerede data.
- RTO: mål om genetablering inden for 1 time, når nødvendige credentials og backupdata er tilgængelige.

## Backup-frekvens

### Ved hver godkendt ændring
Push til GitHub `main`.

### Dagligt
Backup af data, snapshots og andre filer, der ændrer sig uden et Git commit, til Google Drive.

### Ugentligt
Opret/refresh en komplet Git mirror-backup og en produktionssnapshot/ZIP på Google Drive.

### Ved større versioner
Opret et stable tag/release, fx `v7.x-stable`, før næste større udviklingssprint.

## Retention på Google Drive

- 7 daglige backups
- 4 ugentlige backups
- 6 månedlige backups

## Anbefalet Drive-struktur

```
Investment OS Backup/
├── daily/
├── weekly/
│   ├── repository-mirror/
│   └── production-snapshots/
├── monthly/
├── runtime-data/
└── recovery/
```

## Manuel repository-backup

```bash
git clone --mirror https://github.com/tonnirasmussen70/Investment-OS.git Investment-OS.git
```

Kopiér derefter hele `Investment-OS.git`-mappen til Google Drive under `weekly/repository-mirror/`.

En eksisterende mirror-backup kan opdateres med:

```bash
cd Investment-OS.git
git remote update --prune
```

## Restore — hvis den lokale PC går tabt

1. Installer Git og Python på den nye maskine.
2. Clone Investment OS fra GitHub.
3. Checkout den ønskede stabile version eller `main`.
4. Installer dependencies fra `requirements.txt`.
5. Restore eventuelle runtime-/historikdata fra Google Drive.
6. Kør projektets tests.
7. Start Streamlit.
8. Verificér portefølje, positioner, scores og centrale faner før normal brug.

```bash
git clone https://github.com/tonnirasmussen70/Investment-OS.git
cd Investment-OS
pip install -r requirements.txt
streamlit run app.py
```

## Restore — hvis GitHub bliver utilgængeligt eller ødelagt

Brug mirror-backuppen fra Google Drive:

```bash
git clone Investment-OS.git Investment-OS-restored
cd Investment-OS-restored
```

Et nyt remote repository kan efter kontrol genetableres fra mirror-backuppen med `git push --mirror`.

## Restore-verifikation

Mindst kvartalsvist gennemføres en restore-test i en separat mappe/maskine. Verificér at repository kan restores, dependencies installeres, tests køres, Streamlit starter, data indlæses og centrale portefølje-/beslutningsoutputs er konsistente med backupdatoen.

En backup regnes først som verificeret, når restore-testen er gennemført.

## Credentials og secrets

API-nøgler, tokens og passwords må ikke lægges ukrypteret i GitHub eller almindelige backupfiler. De håndteres separat via sikker credential-lagring.

## Næste automatiseringstrin

Backup v1.0 etablerer proceduren. Næste trin er at automatisere backup/snapshot-job, Google Drive-synkronisering, retention, backup-status/log og periodisk restore-test. Automatiseringen er først produktionsklar, når Google Drive-adgang og credentials er etableret sikkert.