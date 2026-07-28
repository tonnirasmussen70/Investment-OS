from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WatchlistResult:
    """Valideret og klargjort watchlist."""

    data: pd.DataFrame
    notes: list[str]


def _first_existing_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for column in candidates:
        if column in dataframe.columns:
            return column
    return None


def prepare_watchlist(
    watchlist: pd.DataFrame,
) -> WatchlistResult:
    """
    Klargør watchlist fra masterfilen.

    Accepterer både danske og engelske kolonnenavne, så Excel-arket kan
    udvikles gradvist uden at dashboardet går ned.
    """
    if watchlist is None or watchlist.empty:
        return WatchlistResult(pd.DataFrame(), [])

    data = watchlist.dropna(how="all").copy()
    notes: list[str] = []

    name_col = _first_existing_column(
        data, ["Name", "Aktiv", "Selskab", "Company"]
    )
    ticker_col = _first_existing_column(
        data, ["Ticker", "Yahoo_Ticker"]
    )
    status_col = _first_existing_column(
        data, ["Status", "Vurdering", "Handling"]
    )
    ai_col = _first_existing_column(
        data, ["AI_Confidence", "AI", "AI Confidence"]
    )
    composite_col = _first_existing_column(
        data, ["Composite", "Composite_Score", "CompositeScore"]
    )
    momentum_col = _first_existing_column(
        data, ["Momentum", "1M", "3M"]
    )
    notes_col = _first_existing_column(
        data, ["Notes", "Note", "Begrundelse"]
    )

    if name_col is None and ticker_col is None:
        notes.append("Watchlist mangler både navn og ticker.")

    for column in [
        value
        for value in [ai_col, composite_col, momentum_col]
        if value is not None
    ]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    output_columns: list[str] = []
    rename_map: dict[str, str] = {}

    for source, target in [
        (name_col, "Aktiv"),
        (ticker_col, "Ticker"),
        (status_col, "Status"),
        (ai_col, "AI Confidence"),
        (composite_col, "Composite"),
        (momentum_col, "Momentum"),
        (notes_col, "Begrundelse"),
    ]:
        if source is not None and source not in output_columns:
            output_columns.append(source)
            rename_map[source] = target

    if not output_columns:
        return WatchlistResult(data, notes)

    result = data[output_columns].rename(columns=rename_map)

    sort_columns: list[str] = []
    ascending: list[bool] = []

    if "AI Confidence" in result.columns:
        sort_columns.append("AI Confidence")
        ascending.append(False)

    if "Composite" in result.columns:
        sort_columns.append("Composite")
        ascending.append(False)

    if sort_columns:
        result = result.sort_values(
            sort_columns,
            ascending=ascending,
            na_position="last",
        )

    return WatchlistResult(
        result.reset_index(drop=True),
        notes,
    )


def watchlist_summary(
    result: WatchlistResult,
) -> dict[str, object]:
    """Returnér få centrale watchlist-KPI'er."""
    if result.data.empty:
        return {
            "Count": 0,
            "High_Confidence": 0,
            "Top_Candidate": None,
        }

    data = result.data

    high_confidence = (
        int((data["AI Confidence"] >= 80).sum())
        if "AI Confidence" in data.columns
        else 0
    )

    top_candidate = None
    if "Aktiv" in data.columns:
        top_candidate = data.iloc[0]["Aktiv"]
    elif "Ticker" in data.columns:
        top_candidate = data.iloc[0]["Ticker"]

    return {
        "Count": int(len(data)),
        "High_Confidence": high_confidence,
        "Top_Candidate": top_candidate,
    }


def format_watchlist_table(
    result: WatchlistResult,
) -> pd.DataFrame:
    """Formatér watchlist til visning i Streamlit."""
    if result.data.empty:
        return pd.DataFrame()

    table = result.data.copy()

    if "AI Confidence" in table.columns:
        table["AI Confidence"] = table["AI Confidence"].apply(
            lambda value: (
                f"{value:.0f}%"
                if pd.notna(value)
                else "N/A"
            )
        )

    if "Composite" in table.columns:
        table["Composite"] = table["Composite"].apply(
            lambda value: (
                f"{value:.1f}"
                if pd.notna(value)
                else "N/A"
            )
        )

    if "Momentum" in table.columns:
        table["Momentum"] = table["Momentum"].apply(
            lambda value: (
                f"{value * 100:.1f}%"
                if pd.notna(value)
                else "N/A"
            )
        )

    return table
