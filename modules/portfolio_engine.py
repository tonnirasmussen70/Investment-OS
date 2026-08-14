from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from modules.market_engine import MarketSnapshot


REQUIRED_PORTFOLIO_COLUMNS = {
    "Asset_ID",
    "Asset_Type",
    "Name",
    "Ticker",
    "Yahoo_Ticker",
    "Quantity",
    "Purchase_Price",
    "Currency",
    "Account",
    "Include_Analytics",
    "Include_Weight",
}


@dataclass
class PortfolioModel:
    portfolio: pd.DataFrame
    accounts: pd.DataFrame
    settings: dict
    fx: pd.DataFrame
    watchlist: pd.DataFrame
    cash: pd.DataFrame


def _read_optional_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    except ValueError:
        return pd.DataFrame()


def load_master_file(path: str | Path) -> PortfolioModel:
    workbook_path = Path(path)
    if not workbook_path.exists():
        raise FileNotFoundError(f"Masterfilen findes ikke: {workbook_path}")

    portfolio = pd.read_excel(
        workbook_path,
        sheet_name="Portfolio",
        engine="openpyxl",
    )
    missing = REQUIRED_PORTFOLIO_COLUMNS.difference(portfolio.columns)
    if missing:
        raise ValueError(f"Portfolio mangler kolonner: {sorted(missing)}")

    accounts = _read_optional_sheet(workbook_path, "Accounts")
    settings_df = _read_optional_sheet(workbook_path, "Settings")
    fx = _read_optional_sheet(workbook_path, "FX")
    watchlist = _read_optional_sheet(workbook_path, "Watchlist")
    cash = _read_optional_sheet(workbook_path, "Cash")

    settings = {}
    if {"Setting", "Value"}.issubset(settings_df.columns):
        settings = (
            settings_df.dropna(subset=["Setting"])
            .set_index("Setting")["Value"]
            .to_dict()
        )

    for col in [
        "Quantity",
        "Purchase_Price",
        "Purchase_FX_to_DKK",
        "Current_Price",
        "Current_FX_to_DKK",
    ]:
        if col in portfolio.columns:
            portfolio[col] = pd.to_numeric(portfolio[col], errors="coerce")

    for col in ["Include_Analytics", "Include_Weight"]:
        portfolio[col] = portfolio[col].fillna(False).astype(bool)

    return PortfolioModel(
        portfolio=portfolio,
        accounts=accounts,
        settings=settings,
        fx=fx,
        watchlist=watchlist,
        cash=cash,
    )


def calculate_portfolio(
    model: PortfolioModel,
    snapshot: MarketSnapshot,
) -> pd.DataFrame:
    df = model.portfolio.copy()

    # Current market data is owned by Investment OS. Values from the Excel
    # master are only used as fallback if the live market snapshot is missing.
    fetched_prices = df["Yahoo_Ticker"].map(snapshot.prices)
    manual_prices = (
        df["Current_Price"]
        if "Current_Price" in df.columns
        else pd.Series(np.nan, index=df.index)
    )
    df["Current_Price"] = fetched_prices.combine_first(manual_prices)

    fetched_fx = df["Currency"].map(snapshot.fx_to_dkk)
    manual_fx = (
        df["Current_FX_to_DKK"]
        if "Current_FX_to_DKK" in df.columns
        else pd.Series(np.nan, index=df.index)
    )
    df["Current_FX_to_DKK"] = fetched_fx.combine_first(manual_fx)
    df.loc[df["Currency"].eq("DKK"), "Current_FX_to_DKK"] = 1.0

    purchase_fx = df.get("Purchase_FX_to_DKK")
    if purchase_fx is None:
        purchase_fx = pd.Series(np.nan, index=df.index)

    # The master file stores average Purchase_Price, but not transaction dates.
    # Therefore a true historical FX return cannot be reconstructed reliably.
    # For foreign positions without Purchase_FX_to_DKK we use current FX only
    # to express the cost basis in DKK. The resulting DKK return is therefore
    # currency-neutral/estimated, while Local_Return_Pct remains exact.
    df["Purchase_FX_Effective"] = purchase_fx.combine_first(df["Current_FX_to_DKK"])
    df["FX_Fallback_Used"] = purchase_fx.isna() & ~df["Currency"].eq("DKK")
    df["Return_DKK_Is_Estimated"] = df["FX_Fallback_Used"]

    df["Cost_Value_DKK"] = (
        df["Quantity"]
        * df["Purchase_Price"]
        * df["Purchase_FX_Effective"]
    )
    df["Market_Value_DKK"] = (
        df["Quantity"]
        * df["Current_Price"]
        * df["Current_FX_to_DKK"]
    )

    df["Local_Return_Pct"] = np.where(
        df["Purchase_Price"] > 0,
        df["Current_Price"] / df["Purchase_Price"] - 1,
        np.nan,
    )

    # FX return is only known when an actual historical purchase FX exists.
    df["FX_Return_Pct"] = np.where(
        (~df["FX_Fallback_Used"]) & (df["Purchase_FX_Effective"] > 0),
        df["Current_FX_to_DKK"] / df["Purchase_FX_Effective"] - 1,
        np.nan,
    )

    df["Return_DKK"] = df["Market_Value_DKK"] - df["Cost_Value_DKK"]
    df["Return_Pct"] = np.where(
        df["Cost_Value_DKK"] > 0,
        df["Market_Value_DKK"] / df["Cost_Value_DKK"] - 1,
        np.nan,
    )

    # Én autoritativ porteføljevægt: investerbar markedsværdi ekskl. Grundfos.
    # Grundfos indgår fortsat i samlet porteføljeværdi, men aldrig i nævneren
    # for aktive positionsvægte eller efterfølgende analyser/rebalancering.
    included = df["Include_Weight"].fillna(False) & ~_is_grundfos(df["Name"])
    total_included = df.loc[included, "Market_Value_DKK"].sum(skipna=True)

    df["Portfolio_Weight"] = 0.0
    if total_included > 0:
        df.loc[included, "Portfolio_Weight"] = (
            df.loc[included, "Market_Value_DKK"] / total_included
        )

    return df


def data_quality_score(
    portfolio: pd.DataFrame,
    snapshot: MarketSnapshot,
) -> tuple[float, list[str]]:
    notes: list[str] = []
    active = portfolio["Include_Analytics"].fillna(False)
    active_count = max(int(active.sum()), 1)

    price_ok = portfolio.loc[active, "Current_Price"].notna().sum() / active_count
    fx_ok = portfolio.loc[active, "Current_FX_to_DKK"].notna().sum() / active_count
    yahoo_ok = portfolio.loc[active, "Yahoo_Ticker"].notna().sum() / active_count

    score = 100 * (0.50 * price_ok + 0.30 * fx_ok + 0.20 * yahoo_ok)

    # Missing historical FX is intentional in the current master-file design
    # and must therefore not reduce the data-quality score.
    fallback_count = int(portfolio.loc[active, "FX_Fallback_Used"].sum())
    if fallback_count:
        notes.append(
            f"{fallback_count} udenlandske positioner anvender valutan neutralt DKK-afkast; "
            "historisk FX registreres ikke i masterfilen. Lokalt kursafkast og aktuel "
            "markedsværdi i DKK er upåvirket."
        )

    if snapshot.missing_prices:
        notes.append(f"Manglende markedskurs: {', '.join(snapshot.missing_prices[:5])}")
    if snapshot.missing_fx:
        notes.append(f"Manglende valuta: {', '.join(snapshot.missing_fx)}")

    return float(np.clip(score, 0, 100)), notes


def _is_grundfos(series: pd.Series) -> pd.Series:
    """Returnér maske for Grundfos-positioner."""
    return (
        series.astype(str)
        .str.strip()
        .str.casefold()
        .eq("grundfos")
    )


def return_inclusion_mask(portfolio: pd.DataFrame) -> pd.Series:
    """
    Returnér maske for positioner, der skal indgå i afkastberegningen.

    Grundfos udelukkes eksplicit, også hvis Excel-flaget ved en fejl står til True.
    """
    include_weight = portfolio["Include_Weight"].fillna(False)
    grundfos = _is_grundfos(portfolio["Name"])

    return include_weight & ~grundfos


def display_market_value(portfolio: pd.DataFrame) -> pd.Series:
    """
    Returnér markedsværdi til samlet porteføljevisning.

    Den beregnede Market_Value_DKK anvendes primært. Hvis masterfilen også
    indeholder en eksisterende Market_value_DKK-kolonne, bruges den som fallback.
    """
    values = pd.to_numeric(
        portfolio["Market_Value_DKK"],
        errors="coerce",
    )

    if "Market_value_DKK" in portfolio.columns:
        fallback = pd.to_numeric(
            portfolio["Market_value_DKK"],
            errors="coerce",
        )
        values = values.combine_first(fallback)

    return values


def portfolio_summary(portfolio: pd.DataFrame) -> dict[str, float]:
    """
    Beregn de centrale porteføljetal ét sted.

    - Porteføljeværdi inkluderer Grundfos.
    - Afkastprocent ekskluderer Grundfos.
    - Aktiv markedsværdi bruges til rebalancering.
    """
    market_values = display_market_value(portfolio)
    total_value = float(market_values.sum(skipna=True))

    return_mask = return_inclusion_mask(portfolio)

    active_market_value = float(
        pd.to_numeric(
            portfolio.loc[return_mask, "Market_Value_DKK"],
            errors="coerce",
        ).sum(skipna=True)
    )

    active_cost_value = float(
        pd.to_numeric(
            portfolio.loc[return_mask, "Cost_Value_DKK"],
            errors="coerce",
        ).sum(skipna=True)
    )

    total_return = (
        active_market_value / active_cost_value - 1
        if active_cost_value > 0
        else np.nan
    )

    return {
        "Portfolio_Value_DKK": total_value,
        "Active_Market_Value_DKK": active_market_value,
        "Active_Cost_Value_DKK": active_cost_value,
        "Total_Return_Pct": float(total_return)
        if pd.notna(total_return)
        else np.nan,
    }


def asset_type_summary(portfolio: pd.DataFrame) -> pd.DataFrame:
    """Returnér antal, markedsværdi og andel pr. aktivtype."""
    data = portfolio.copy()
    data["Display_Market_Value_DKK"] = display_market_value(data)

    normalized = (
        data["Asset_Type"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    data["Asset_Group"] = np.select(
        [
            normalized.str.contains(r"aktie|stock|equity", regex=True),
            normalized.str.contains(r"etf|fund", regex=True),
        ],
        [
            "Aktier",
            "ETF'er",
        ],
        default="Øvrige",
    )

    summary = (
        data.groupby("Asset_Group", dropna=False)
        .agg(
            Positioner=("Asset_ID", "count"),
            Markedsværdi_DKK=("Display_Market_Value_DKK", "sum"),
        )
        .reset_index()
    )

    total = summary["Markedsværdi_DKK"].sum()
    summary["Andel"] = np.where(
        total > 0,
        summary["Markedsværdi_DKK"] / total,
        np.nan,
    )

    return summary.sort_values(
        "Markedsværdi_DKK",
        ascending=False,
    ).reset_index(drop=True)
