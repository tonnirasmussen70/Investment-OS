from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Forventet tekst blev ikke fundet i {path}:\n{old}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


# decision_summary er allerede read-only og må ikke genberegne score.
# Denne sidste patch fjerner de resterende alternative statusdefinitioner i UI.
replace_once(
    "app.py",
    '''    "decision_score": (\n        "Prioriterer mulige handlinger ud fra Portfolio Doctor, Opportunity "\n        "Score, AI Confidence og forventet forbedring af Portfolio Health."\n    ),\n''',
    '''    "decision_score": (\n        "Fælles score 0-100 fra Decision Engine baseret på momentum, AI "\n        "Confidence, relativ styrke, trend, risiko, datakvalitet og plads "\n        "under positionsloftet."\n    ),\n''',
)

replace_once(
    "app.py",
    '''        a1.metric(\n            "Overbevisning",\n            conviction_label(decision_score),\n            help="Styrken i selve investeringscasen og handlingens prioritet.",\n        )\n''',
    '''        a1.metric(\n            "Status",\n            str(best.get("Decision Label", "Datamangel")),\n            help="Den fælles status fra Decision Engine for denne investeringscase.",\n        )\n''',
)

print("Investment OS 6.9 final UI consolidation patch applied")
