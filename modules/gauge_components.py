from __future__ import annotations

from html import escape
import math


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
        return "#22c55e"
    if score >= 50:
        return "#facc15"
    return "#ef4444"


def build_kpi_gauge_html(
    title: str,
    value: float,
    display_value: str,
    status: str,
    help_text: str,
    *,
    inverse: bool = False,
    gauge_id: str,
) -> str:
    """Byg en kompakt, tilgængelig halvcirkel-gauge til KPI-rækken."""
    has_value = _is_number(value)
    clamped = min(100.0, max(0.0, float(value))) if has_value else 0.0
    active_length = f"{clamped:.1f}"
    gradient_stops = (
        ("#22c55e", "#facc15", "#ef4444")
        if inverse
        else ("#ef4444", "#facc15", "#22c55e")
    )
    status_color = gauge_status_color(value, inverse=inverse)
    opacity = "1" if has_value else "0"

    safe_title = escape(title)
    safe_display = escape(display_value)
    safe_status = escape(status)
    safe_help = escape(help_text, quote=True)
    safe_gauge_id = escape(gauge_id, quote=True)

    return f"""
    <div class="ios-kpi-gauge" role="img"
         aria-label="{safe_title}: {safe_display}, {safe_status}">
      <div class="ios-kpi-gauge__title">
        <span>{safe_title}</span>
        <span class="ios-kpi-gauge__help" title="{safe_help}"
              aria-label="Information om {safe_title}" tabindex="0">?</span>
      </div>
      <svg class="ios-kpi-gauge__svg" viewBox="0 0 160 103"
           aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="{safe_gauge_id}" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="{gradient_stops[0]}" />
            <stop offset="50%" stop-color="{gradient_stops[1]}" />
            <stop offset="100%" stop-color="{gradient_stops[2]}" />
          </linearGradient>
        </defs>
        <path d="M 20 78 A 60 60 0 0 1 140 78"
              pathLength="100" fill="none" stroke="#293241"
              stroke-width="11" stroke-linecap="round" />
        <path d="M 20 78 A 60 60 0 0 1 140 78"
              pathLength="100" fill="none" stroke="url(#{safe_gauge_id})"
              stroke-width="11" stroke-linecap="round"
              stroke-dasharray="{active_length} 100" opacity="{opacity}" />
        <text x="80" y="68" text-anchor="middle"
              class="ios-kpi-gauge__value">{safe_display}</text>
        <circle cx="80" cy="78" r="2.5" fill="{status_color}" />
        <text x="80" y="99" text-anchor="middle"
              class="ios-kpi-gauge__status" fill="{status_color}">{safe_status}</text>
      </svg>
    </div>
    <style>
      .ios-kpi-gauge {{
        width: 100%;
        min-height: 148px;
        color: var(--text-color, #f8fafc);
      }}
      .ios-kpi-gauge__title {{
        display: flex;
        align-items: center;
        gap: 0.35rem;
        min-height: 1.5rem;
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
        color: #aab3bf;
        font-size: 0.66rem;
        font-weight: 700;
        cursor: help;
      }}
      .ios-kpi-gauge__help:focus-visible {{
        outline: 2px solid #38bdf8;
        outline-offset: 2px;
      }}
      .ios-kpi-gauge__svg {{
        display: block;
        width: 100%;
        max-width: 176px;
        height: auto;
        margin: 0 auto;
        overflow: visible;
      }}
      .ios-kpi-gauge__value {{
        fill: currentColor;
        font-size: 24px;
        font-weight: 650;
        font-variant-numeric: tabular-nums;
      }}
      .ios-kpi-gauge__status {{
        font-size: 10.5px;
        font-weight: 650;
      }}
    </style>
    """
