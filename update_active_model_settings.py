from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_init = '''st.session_state.setdefault("model_minimum_trade_dkk", float(MINIMUM_TRADE_DKK))
st.session_state.setdefault("model_risk_free_rate", float(base_config.risk_free_rate))

for period, default_value in base_config.momentum_weights.items():
'''
new_init = '''st.session_state.setdefault("model_minimum_trade_dkk", float(MINIMUM_TRADE_DKK))
st.session_state.setdefault("model_risk_free_rate", float(base_config.risk_free_rate))

# Redigeringsfelterne holdes adskilt fra de aktive modelværdier.
# Modellen ændres først, når brugeren vælger \"Anvend modelændringer\".
st.session_state.setdefault("draft_model_benchmark", st.session_state["model_benchmark"])
st.session_state.setdefault(
    "draft_model_max_position_weight",
    float(st.session_state["model_max_position_weight"]),
)
st.session_state.setdefault(
    "draft_model_max_sector_weight",
    float(st.session_state["model_max_sector_weight"]),
)
st.session_state.setdefault(
    "draft_model_minimum_trade_dkk",
    float(st.session_state["model_minimum_trade_dkk"]),
)
st.session_state.setdefault(
    "draft_model_risk_free_rate",
    float(st.session_state["model_risk_free_rate"]),
)

for period, default_value in base_config.momentum_weights.items():
'''
if old_init not in text:
    raise RuntimeError("Kunne ikke finde initialisering af modelindstillinger")
text = text.replace(old_init, new_init, 1)

replacements = {
    'st.text_input("Benchmark", key="model_benchmark")': 'st.text_input("Benchmark", key="draft_model_benchmark")',
    'key="model_max_position_weight",': 'key="draft_model_max_position_weight",',
    'key="model_minimum_trade_dkk",': 'key="draft_model_minimum_trade_dkk",',
    'key="model_max_sector_weight",': 'key="draft_model_max_sector_weight",',
    'key="model_risk_free_rate",': 'key="draft_model_risk_free_rate",',
}
for old, new in replacements.items():
    if old not in text:
        raise RuntimeError(f"Kunne ikke finde felt: {old}")
    text = text.replace(old, new, 1)

old_caption = 'st.caption("Ændringer anvendes straks i den aktuelle session.")'
new_caption = '''st.caption(
            "Redigér værdierne og vælg Anvend modelændringer. Derefter "
            "genberegnes hele modellen med de nye parametre."
        )'''
if old_caption not in text:
    raise RuntimeError("Kunne ikke finde Modeloversigt-caption")
text = text.replace(old_caption, new_caption, 1)

old_reset = '''        if st.button("Nulstil Modeloversigt"):
            st.session_state["model_benchmark"] = base_config.benchmark
            st.session_state["model_max_position_weight"] = float(
                base_config.max_position_weight
            )
            st.session_state["model_max_sector_weight"] = float(
                base_config.max_sector_weight
            )
            st.session_state["model_minimum_trade_dkk"] = 5_000.0
            st.session_state["model_risk_free_rate"] = float(
                base_config.risk_free_rate
            )
            st.rerun()
'''
new_reset = '''        active_settings = pd.DataFrame([
            {"Aktiv parameter": "Benchmark", "Værdi": config.benchmark},
            {
                "Aktiv parameter": "Maks. positionsvægt",
                "Værdi": format_pct(config.max_position_weight, 0),
            },
            {
                "Aktiv parameter": "Maks. sektorvægt",
                "Værdi": format_pct(config.max_sector_weight, 0),
            },
            {
                "Aktiv parameter": "Minimum handel",
                "Værdi": compact_dkk(MINIMUM_TRADE_DKK),
            },
            {
                "Aktiv parameter": "Risikofri rente",
                "Værdi": format_pct(config.risk_free_rate, 1),
            },
        ])
        st.dataframe(active_settings, use_container_width=True, hide_index=True)

        apply_col, reset_col = st.columns(2)
        with apply_col:
            if st.button("Anvend modelændringer", type="primary"):
                st.session_state["model_benchmark"] = (
                    str(st.session_state["draft_model_benchmark"]).strip()
                    or base_config.benchmark
                )
                st.session_state["model_max_position_weight"] = float(
                    st.session_state["draft_model_max_position_weight"]
                )
                st.session_state["model_max_sector_weight"] = float(
                    st.session_state["draft_model_max_sector_weight"]
                )
                st.session_state["model_minimum_trade_dkk"] = float(
                    st.session_state["draft_model_minimum_trade_dkk"]
                )
                st.session_state["model_risk_free_rate"] = float(
                    st.session_state["draft_model_risk_free_rate"]
                )
                st.rerun()

        with reset_col:
            if st.button("Nulstil Modeloversigt"):
                defaults = {
                    "model_benchmark": base_config.benchmark,
                    "model_max_position_weight": float(base_config.max_position_weight),
                    "model_max_sector_weight": float(base_config.max_sector_weight),
                    "model_minimum_trade_dkk": 5_000.0,
                    "model_risk_free_rate": float(base_config.risk_free_rate),
                }
                for key, value in defaults.items():
                    st.session_state[key] = value
                    st.session_state[f"draft_{key}"] = value
                st.rerun()
'''
if old_reset not in text:
    raise RuntimeError("Kunne ikke finde nulstilling af Modeloversigt")
text = text.replace(old_reset, new_reset, 1)

path.write_text(text, encoding="utf-8")
print("Aktive modelindstillinger er koblet til Anvend-knappen")
