"""Streamlit component for user-initiated browser speech recognition."""
from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "jarvis_voice_input", path=str(Path(__file__).with_name("voice_input"))
)


def voice_input():
    return _component(key="jarvis_voice_input", default=None)
