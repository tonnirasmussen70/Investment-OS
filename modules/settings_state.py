"""Safe state-reset helpers for Streamlit settings widget callbacks.

Call these from button on_click callbacks, before the next widget creation;
never mutate an already-instantiated widget's session-state key in-line.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any


def reset_weight_settings(
    state: MutableMapping[str, Any],
    defaults: Mapping[str, float],
    prefix: str,
) -> None:
    """Restore raw numeric weight inputs without touching unrelated session state."""
    for factor, default in defaults.items():
        state[f"{prefix}_{factor}"] = float(default)


def reset_model_settings_state(
    state: MutableMapping[str, Any],
    defaults: Mapping[str, str | float],
) -> None:
    """Restore active model settings and their matching draft widget values."""
    for key, value in defaults.items():
        state[key] = value
        state[f"draft_{key}"] = value
