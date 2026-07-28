from __future__ import annotations

import pandas as pd


def format_dkk(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):,.0f} kr.".replace(",", ".")


def format_number(value, decimals: int = 0) -> str:
    if pd.isna(value):
        return "N/A"
    if decimals == 0:
        return f"{float(value):,.0f}".replace(",", ".")
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_pct(value, decimals: int = 1) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value) * 100:.{decimals}f}%".replace(".", ",")


def format_score(value, decimals: int = 2) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.{decimals}f}".replace(".", ",")
