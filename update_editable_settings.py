from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

text = text.replace(
    "from __future__ import annotations\n\nimport os",
    "from __future__ import annotations\n\nfrom dataclasses import replace\nimport os",
    1,
)

old_config = '''config = load_investment_config(model.settings)

for factor, default_value in config.health_weights.items():
'''
new_config = '''base_config = load_investment_config(model.settings)

# Redigerbare modelindstillinger for den aktuelle Streamlit-session.
st.session_state.setdefault("model_benchmark", base_config.benchmark)
st.session_state.setdefault(
    "model_max_position_weight", float(base_config.max_position_weight)
)
st.session_state.setdefault(
    "model_max_sector_weight", float(base_config.max_sector_weight)
)
st.session_state.setdefault("model_minimum_trade_dkk", float(MINIMUM_TRADE_DKK))
st.session_state.setdefault("model_risk_free_rate", float(base_config.risk_free_rate))

for period, default_value in base_config.momentum_weights.items():
    st.session_state.setdefault(f"momentum_weight_{period}", float(default_value))

raw_momentum_weights = {
    period: max(0.0, float(st.session_state[f"momentum_weight_{period}"]))
    for period in base_config.momentum_weights
}
momentum_total = sum(raw_momentum_weights.values())
momentum_session_weights = (
    {
        period: value / momentum_total
        for period, value in raw_momentum_weights.items()
    }
    if momentum_total > 0
    else base_config.momentum_weights.copy()
)

config = replace(
    base_config,
    benchmark=str(st.session_state["model_benchmark"]).strip() or base_config.benchmark,
    max_position_weight=float(st.session_state["model_max_position_weight"]),
    max_sector_weight=float(st.session_state["model_max_sector_weight"]),
    risk_free_rate=float(st.session_state["model_risk_free_rate"]),
    momentum_weights=momentum_session_weights,
)
MINIMUM_TRADE_DKK = float(st.session_state["model_minimum_trade_dkk"])

for factor, default_value in config.health_weights.items():
'''
if old_config not in text:
    raise RuntimeError("Kunne ikke finde config-sektionen")
text = text.replace(old_config, new_config, 1)

old_model = '''    with st.expander("Modeloversigt"):
        settings_table = pd.DataFrame([
            {"Indstilling": "Benchmark", "Værdi": config.benchmark},
            {
                "Indstilling": "Maks. positionsvægt",
                "Værdi": format_pct(config.max_position_weight, 0),
            },
            {
                "Indstilling": "Maks. sektorvægt",
                "Værdi": format_pct(config.max_sector_weight, 0),
            },
            {
                "Indstilling": "Minimum handel",
                "Værdi": compact_dkk(MINIMUM_TRADE_DKK),
            },
            {
                "Indstilling": "Risikofri rente",
                "Værdi": format_pct(config.risk_free_rate, 1),
            },
            {"Indstilling": "App-version", "Værdi": APP_VERSION},
            {"Indstilling": "Datakilde", "Værdi": "AI_portfolio.xlsx + yfinance"},
        ])
        st.dataframe(settings_table, use_container_width=True, hide_index=True)

'''
new_model = '''    with st.expander("Modeloversigt"):
        st.caption("Ændringer anvendes straks i den aktuelle session.")
        m1, m2 = st.columns(2)
        with m1:
            st.text_input("Benchmark", key="model_benchmark")
            st.number_input(
                "Maks. positionsvægt",
                min_value=0.01,
                max_value=1.00,
                step=0.01,
                format="%.2f",
                key="model_max_position_weight",
                help="Angives som decimal. 0,12 svarer til 12 %.",
            )
            st.number_input(
                "Minimum handel (DKK)",
                min_value=0.0,
                step=500.0,
                format="%.0f",
                key="model_minimum_trade_dkk",
            )
        with m2:
            st.number_input(
                "Maks. sektorvægt",
                min_value=0.01,
                max_value=1.00,
                step=0.01,
                format="%.2f",
                key="model_max_sector_weight",
                help="Angives som decimal. 0,20 svarer til 20 %.",
            )
            st.number_input(
                "Risikofri rente",
                min_value=0.0,
                max_value=0.25,
                step=0.005,
                format="%.3f",
                key="model_risk_free_rate",
                help="Angives som decimal. 0,02 svarer til 2 %.",
            )
            st.text_input("App-version", value=APP_VERSION, disabled=True)
            st.text_input(
                "Datakilde", value="AI_portfolio.xlsx + yfinance", disabled=True
            )

        if st.button("Nulstil Modeloversigt"):
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
if old_model not in text:
    raise RuntimeError("Kunne ikke finde Modeloversigt-sektionen")
text = text.replace(old_model, new_model, 1)

old_momentum = '''    with st.expander("Momentum-vægte"):
        momentum_settings = pd.DataFrame({
            "Periode": list(momentum_weights.keys()),
            "Aktiv vægt": [
                format_pct(momentum_weights[key], 0) for key in momentum_weights
            ],
        })
        st.dataframe(
            momentum_settings, use_container_width=True, hide_index=True
        )
'''
new_momentum = '''    with st.expander("Momentum-vægte"):
        st.caption(
            "Indtast rå vægte. De normaliseres automatisk, så den aktive sum er 100 %."
        )
        periods = list(base_config.momentum_weights.keys())
        columns = st.columns(len(periods))
        for index, period in enumerate(periods):
            with columns[index]:
                st.number_input(
                    period,
                    min_value=0.0,
                    max_value=1.0,
                    step=0.05,
                    format="%.2f",
                    key=f"momentum_weight_{period}",
                )

        active_momentum = pd.DataFrame({
            "Periode": periods,
            "Indtastet vægt": [
                format_pct(st.session_state[f"momentum_weight_{period}"], 0)
                for period in periods
            ],
            "Aktiv normaliseret vægt": [
                format_pct(momentum_weights[period], 0) for period in periods
            ],
        })
        st.dataframe(active_momentum, use_container_width=True, hide_index=True)
        st.caption(
            f"Indtastet vægtsum: {sum(raw_momentum_weights.values()):.2f}. "
            "Aktiv vægtsum: 1,00."
        )

        if st.button("Nulstil Momentum-vægte"):
            for period, default in base_config.momentum_weights.items():
                st.session_state[f"momentum_weight_{period}"] = float(default)
            st.rerun()
'''
if old_momentum not in text:
    raise RuntimeError("Kunne ikke finde Momentum-vægte-sektionen")
text = text.replace(old_momentum, new_momentum, 1)

APP.write_text(text, encoding="utf-8")
print("Settings gjort redigerbare")
