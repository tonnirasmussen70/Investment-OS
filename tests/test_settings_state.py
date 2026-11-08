"""Regression tests for Streamlit settings reset buttons.

The original bug wrote to an existing number_input key after the widget was
instantiated in the same run, which raises StreamlitAPIException.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from modules.settings_state import reset_model_settings_state, reset_weight_settings


@pytest.mark.parametrize(
    ("prefix", "defaults"),
    [
        ("health_weight", {"Momentum": 0.30, "Diversification": 0.70}),
        ("decision_weight", {"Momentum": 0.40, "Risk": 0.60}),
    ],
)
def test_weight_reset_restores_defaults_without_touching_other_settings(prefix, defaults):
    state = {f"{prefix}_{key}": 0.99 for key in defaults}
    state["momentum_weight_1W"] = 0.40

    reset_weight_settings(state, defaults, prefix)

    for key, value in defaults.items():
        assert state[f"{prefix}_{key}"] == value
    assert state["momentum_weight_1W"] == 0.40


def test_model_reset_restores_active_and_draft_settings():
    defaults = {
        "model_benchmark": "SPY",
        "model_max_position_weight": 0.12,
        "model_minimum_trade_dkk": 5000.0,
    }
    state = {"unrelated": "keep"}
    for key in defaults:
        state[key] = "modified"
        state[f"draft_{key}"] = "modified"

    reset_model_settings_state(state, defaults)

    for key, value in defaults.items():
        assert state[key] == value
        assert state[f"draft_{key}"] == value
    assert state["unrelated"] == "keep"


@pytest.mark.parametrize(
    ("label", "callback"),
    [
        ("Nulstil Portfolio Health", "reset_health_weights"),
        ("Nulstil Decision Engine", "reset_decision_weights"),
        ("Nulstil Modeloversigt", "reset_model_overview"),
        ("Nulstil Momentum-vægte", "reset_momentum_weights"),
    ],
)
def test_app_reset_buttons_have_pre_widget_callbacks(label, callback):
    """Guard against reintroducing inline post-widget state mutations."""
    app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_source)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "button"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == label
    ]
    assert len(matches) == 1
    callbacks = [kw.value for kw in matches[0].keywords if kw.arg == "on_click"]
    assert len(callbacks) == 1
    assert isinstance(callbacks[0], ast.Name)
    assert callbacks[0].id == callback


def test_widget_reset_callback_does_not_raise_streamlit_api_exception():
    """Exercise the callback timing using a real Streamlit testing session."""
    app = AppTest.from_string(
        """
import streamlit as st
from modules.settings_state import reset_weight_settings

defaults = {"Momentum": 0.40, "Risk": 0.60}
for factor, value in defaults.items():
    st.session_state.setdefault(f"decision_weight_{factor}", value)

def reset_decision_weights():
    reset_weight_settings(st.session_state, defaults, "decision_weight")

for factor in defaults:
    st.number_input(factor, min_value=0.0, max_value=1.0, key=f"decision_weight_{factor}")

st.button("Nulstil Decision Engine", on_click=reset_decision_weights)
"""
    ).run()
    assert len(app.exception) == 0
    app.number_input[0].set_value(0.80).run()
    assert len(app.exception) == 0
    app.button[0].click().run()
    assert len(app.exception) == 0
    assert app.number_input[0].value == pytest.approx(0.40)
    assert app.number_input[1].value == pytest.approx(0.60)
