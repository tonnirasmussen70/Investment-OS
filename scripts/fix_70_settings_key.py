from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
old = 'float(st.session_state[f"opportunity_weight_{f}"]) for f in factors'
new = 'float(st.session_state[f"decision_weight_{f}"]) for f in factors'
if old not in text and new not in text:
    raise SystemExit("Expected settings key reference not found")
text = text.replace(old, new)
path.write_text(text, encoding="utf-8")
print("Fixed Decision Engine session-state key")
