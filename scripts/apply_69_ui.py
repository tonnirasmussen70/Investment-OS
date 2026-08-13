from pathlib import Path


APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

replacements = [
    (
        'from dataclasses import replace\nimport os\nfrom pathlib import Path\n',
        'from dataclasses import replace\nfrom datetime import datetime\nimport os\nfrom pathlib import Path\nfrom zoneinfo import ZoneInfo\n',
    ),
    ('page_title="Investment OS 6.8",', 'page_title="Investment OS 6.9",'),
    ('APP_VERSION = "6.8.0"', 'APP_VERSION = "6.9.0"'),
    (
        '@st.cache_data(ttl=3600, show_spinner=True)\ndef load_market_data(tickers, currencies):\n    return fetch_market_snapshot(tickers, currencies)\n',
        '@st.cache_data(ttl=3600, show_spinner=True)\ndef load_market_data(tickers, currencies):\n    snapshot = fetch_market_snapshot(tickers, currencies)\n    fetched_at = datetime.now(ZoneInfo("Europe/Copenhagen"))\n    return snapshot, fetched_at\n',
    ),
    (
        'st.title("📈 Investment OS 6.8")\nst.caption(\n    "Beslutningsstøtte til få, velbegrundede investeringsbeslutninger "\n    f"· Version {APP_VERSION}"\n)\n',
        'st.title("📈 Investment OS 6.9")\n',
    ),
    (
        'snapshot = load_market_data(tickers, currencies)\nportfolio = calculate_portfolio(model, snapshot)\n',
        'snapshot, data_updated_at = load_market_data(tickers, currencies)\nst.caption(\n    f"Version {APP_VERSION} · Data sidst opdateret: "\n    f"{data_updated_at:%d-%m-%Y kl. %H:%M}"\n)\nportfolio = calculate_portfolio(model, snapshot)\n',
    ),
    (
        '            "AI_Confidence", "Handling",\n',
        '            "AI_Confidence", "Decision_Score", "Decision_Status", "Handling",\n',
    ),
    (
        '                "AI_Confidence", "Handling",\n',
        '                "AI_Confidence", "Decision_Score", "Decision_Status", "Handling",\n',
    ),
    (
        '            "AI_Confidence": "AI",\n        })\n',
        '            "AI_Confidence": "AI",\n            "Decision_Score": "Score",\n            "Decision_Status": "Status",\n        })\n',
    ),
    (
        '                    "Risiko", "Composite", "AI", "Handling",\n',
        '                    "Risiko", "Composite", "AI", "Decision Score", "Status", "Handling",\n',
    ),
    (
        '        summary = opportunity_data[\n            [\n                "Opportunity Rank", "Name", "Handling",\n                "Opportunity Score", "Opportunity Label",\n            ]\n        ].copy()\n        summary.columns = ["Rank", "Aktiv", "Handling", "Score", "Status"]\n',
        '        summary = opportunity_data[\n            [\n                "Opportunity Rank", "Name", "Handling",\n                "Decision_Score", "Decision_Status",\n            ]\n        ].copy()\n        summary.columns = ["Rank", "Aktiv", "Handling", "Score", "Status"]\n',
    ),
    ('    with st.expander("Opportunity Score"):\n', '    with st.expander("Decision Engine"):\n'),
    ('        if st.button("Nulstil Opportunity Score"):\n', '        if st.button("Nulstil Decision Engine"):\n'),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"Forventet tekst blev ikke fundet:\n{old}")
    text = text.replace(old, new, 1)

APP.write_text(text, encoding="utf-8")
print("Investment OS 6.9 UI-opdatering anvendt på app.py")
