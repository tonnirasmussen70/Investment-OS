from __future__ import annotations

from html import escape
import math

import plotly.graph_objects as go


def _is_number(value: float) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def gauge_status_color(value: float, inverse: bool = False) -> str:
    """Returnér semantisk statusfarve til en 0-100-gauge."""
    if not _is_number(value):
        return "#94a3b8"

    score = min(100.0, max(0.0, float(value)))
    if inverse:
        score = 100.0 - score

    if score >= 75:
        return "#00d084"
    if score >= 50:
        return "#ffcc33"
    return "#ff4b55"


def build_kpi_gauge_label_html(title: str, help_text: str) -> str:
    """Byg KPI-overskrift med tilgængelig hjælpetekst."""
    safe_title = escape(title)
    safe_help = escape(help_text, quote=True)

    return f"""
    <div class="ios-kpi-gauge__title">
      <span>{safe_title}</span>
      <span class="ios-kpi-gauge__help" title="{safe_help}"
            aria-label="Information om {safe_title}" tabindex="0">?</span>
    </div>
    <style>
      .ios-kpi-gauge__title {{
        display: flex;
        align-items: center;
        gap: 0.35rem;
        min-height: 1.5rem;
        color: var(--text-color, #f8fafc);
        font-size: 0.875rem;
        font-weight: 600;
        line-height: 1.2;
        white-space: nowrap;
      }}
      .ios-kpi-gauge__help {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 0.9rem;
        height: 0.9rem;
        border: 1px solid #8b949e;
        border-radius: 50%;
        color: #d1d5db;
        font-size: 0.66rem;
        font-weight: 700;
        cursor: help;
      }}
      .ios-kpi-gauge__help:focus-visible {{
        outline: 2px solid #38bdf8;
        outline-offset: 2px;
      }}
    </style>
    """


def build_kpi_gauge_figure(
    title: str,
    value: float,
    status: str,
    *,
    inverse: bool = False,
) -> go.Figure:
    """Byg en kompakt Plotly-gauge, som Streamlit renderer nativt."""
    has_value = _is_number(value)
    clamped = min(100.0, max(0.0, float(value))) if has_value else 0.0
    status_color = gauge_status_color(value, inverse=inverse)
    if inverse:
        steps = [
            {"range": [0, 25], "color": "#00d084"},
            {"range": [25, 50], "color": "#ffcc33"},
            {"range": [50, 100], "color": "#ff4b55"},
        ]
    else:
        steps = [
            {"range": [0, 50], "color": "#ff4b55"},
            {"range": [50, 75], "color": "#ffcc33"},
            {"range": [75, 100], "color": "#00d084"},
        ]

    number_suffix = "/100" if inverse else ("%" if title != "Porteføljesundhed" else "")
    mode = "gauge+number" if has_value else "gauge"

    figure = go.Figure(go.Indicator(
        mode=mode,
        value=clamped,
        number={
            "font": {"size": 26, "color": "#f8fafc"},
            "suffix": number_suffix,
            "valueformat": ".0f",
        },
        domain={"x": [0, 1], "y": [0.20, 1]},
        gauge={
            "shape": "angular",
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": "rgba(255,255,255,0.18)", "thickness": 0.32},
            "bgcolor": "#263244",
            "borderwidth": 0,
            "steps": steps,
            "threshold": {
                "line": {"color": "#ffffff", "width": 4},
                "thickness": 0.80,
                "value": clamped,
            },
        },
    ))

    if not has_value:
        figure.add_annotation(
            x=0.5,
            y=0.56,
            text="<b>N/A</b>",
            showarrow=False,
            font={"size": 25, "color": "#f8fafc"},
        )

    figure.add_annotation(
        x=0.5,
        y=0.02,
        text=f"<b>{escape(status)}</b>",
        showarrow=False,
        font={"size": 11, "color": status_color},
    )
    figure.update_layout(
        height=150,
        margin={"l": 2, "r": 2, "t": 2, "b": 2},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f8fafc"},
    )
    return figure
