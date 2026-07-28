from __future__ import annotations

import re

import numpy as np
import pandas as pd

ROW_DARK = "#101826"
ROW_LIGHT = "#162033"
NEGATIVE_RED = "#ff4b4b"


def _parse_display_number(value):
    if pd.isna(value):
        return None

    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text or text.upper() == "N/A":
        return None

    # Danish display formats:
    # -12,4%, -15.250 kr., (500)
    is_parenthesized = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    text = re.sub(r"[^0-9,.-]", "", text)

    if not text:
        return None

    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")

    try:
        number = float(text)
        return -abs(number) if is_parenthesized else number
    except ValueError:
        return None


def table_style(dataframe: pd.DataFrame) -> pd.io.formats.style.Styler:
    def style_row(row):
        background = ROW_DARK if row.name % 2 == 0 else ROW_LIGHT
        styles = []

        for value in row:
            style = f"background-color:{background};"
            number = _parse_display_number(value)

            if number is not None and number < 0:
                style += f"color:{NEGATIVE_RED};font-weight:600;"

            styles.append(style)

        return styles

    return (
        dataframe.style
        .apply(style_row, axis=1)
        .set_properties(**{
            "border-color": "#263247",
            "vertical-align": "middle",
        })
    )


def table_height(
    dataframe: pd.DataFrame,
    row_px: int = 38,
    max_height: int = 750,
) -> int:
    return min((len(dataframe) + 1) * row_px, max_height)
