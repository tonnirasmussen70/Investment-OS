from __future__ import annotations

import numpy as np
import pandas as pd


def stop_pct_from_volatility(volatility: float) -> float:
    """Konvertér annualiseret volatilitet til en stopafstand."""
    if pd.isna(volatility):
        return 0.10
    if volatility < 0.20:
        return 0.07
    if volatility < 0.30:
        return 0.10
    if volatility < 0.45:
        return 0.14
    return 0.18


def build_stop_loss_table(
    portfolio: pd.DataFrame,
    price_history: pd.DataFrame,
    lookback_days: int = 63,
    alarm_buffer: float = 0.03,
) -> pd.DataFrame:
    """
    Byg dynamiske trailing stop- og alarmniveauer.

    Stopkursen beregnes fra højeste kurs i lookback-perioden.
    """
    required = {
        "Name",
        "Yahoo_Ticker",
        "Current_Price",
        "Currency",
        "Volatility",
        "Handling",
        "Include_Analytics",
    }
    missing = required.difference(portfolio.columns)
    if missing:
        raise ValueError(
            f"Stop-loss modellen mangler kolonner: {sorted(missing)}"
        )

    rows: list[dict[str, object]] = []

    active = portfolio.loc[
        portfolio["Include_Analytics"].fillna(False)
    ].copy()

    for _, position in active.iterrows():
        ticker = str(position["Yahoo_Ticker"]).strip()
        current_price = pd.to_numeric(
            position["Current_Price"],
            errors="coerce",
        )
        volatility = pd.to_numeric(
            position["Volatility"],
            errors="coerce",
        )

        series = (
            price_history[ticker].dropna()
            if ticker in price_history.columns
            else pd.Series(dtype=float)
        )

        recent = series.tail(lookback_days)
        trailing_high = (
            float(recent.max())
            if not recent.empty
            else current_price
        )

        stop_pct = stop_pct_from_volatility(volatility)

        stop_price = (
            trailing_high * (1 - stop_pct)
            if pd.notna(trailing_high)
            else np.nan
        )
        alarm_price = (
            stop_price * (1 + alarm_buffer)
            if pd.notna(stop_price)
            else np.nan
        )

        distance_to_stop = (
            current_price / stop_price - 1
            if pd.notna(current_price)
            and pd.notna(stop_price)
            and stop_price > 0
            else np.nan
        )

        if (
            pd.notna(current_price)
            and pd.notna(stop_price)
            and current_price <= stop_price
        ):
            risk_action = "Stop brudt"
        elif (
            pd.notna(current_price)
            and pd.notna(alarm_price)
            and current_price <= alarm_price
        ):
            risk_action = "Alarm"
        elif position["Handling"] == "Reducer":
            risk_action = "Reducer / stram stop"
        else:
            risk_action = "Overvåg"

        rows.append(
            {
                "Aktiv": position["Name"],
                "Ticker": ticker,
                "Valuta": position["Currency"],
                "Kurs": current_price,
                "3M høj": trailing_high,
                "Stopafstand": stop_pct,
                "Stopkurs": stop_price,
                "Alarmkurs": alarm_price,
                "Afstand til stop": distance_to_stop,
                "Modelhandling": position["Handling"],
                "Risikohandling": risk_action,
            }
        )

    if not rows:
        return pd.DataFrame()

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["Risikohandling", "Afstand til stop"],
            ascending=[True, True],
            na_position="last",
        )
        .reset_index(drop=True)
    )


def stop_loss_summary(
    stop_table: pd.DataFrame,
) -> dict[str, int]:
    """Returnér centrale KPI'er for stop-loss-modellen."""
    if stop_table.empty:
        return {
            "Stop_Broken": 0,
            "Alarm": 0,
            "Tighten": 0,
        }

    return {
        "Stop_Broken": int(
            stop_table["Risikohandling"].eq("Stop brudt").sum()
        ),
        "Alarm": int(
            stop_table["Risikohandling"].eq("Alarm").sum()
        ),
        "Tighten": int(
            stop_table["Risikohandling"]
            .eq("Reducer / stram stop")
            .sum()
        ),
    }
