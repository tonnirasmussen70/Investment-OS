from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
old = 'float(st.session_state[f"opportunity_weight_{f}"]) for f in factors'
new = 'float(st.session_state[f"decision_weight_{f}"]) for f in factors'
if old not in text:
    if new in text:
        print("main already fixed")
        raise SystemExit(0)
    raise SystemExit("Expected legacy Decision Engine key not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("main Decision Engine settings key fixed")
