from __future__ import annotations

import argparse
import math
import time
from io import StringIO
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import yfinance as yf

OUTPUT_COLUMNS = [
    "Name",
    "Ticker",
    "Composite_Score",
    "AI_Confidence",
    "Status",
    "Revenue_CAGR_5Y",
    "EPS_CAGR_5Y",
    "Gross_Margin",
    "ROIC",
    "Upside_Pct",
    "Downside_Pct",
    "Risk_Reward",
    "Market_Cap_USD",
    "Risk",
    "Reason",
    "Data_Quality",
    "Price_Above_200D",
    "Momentum_3M",
    "Momentum_6M",
    "Generated_UTC",
]

WIKIPEDIA_SOURCES = {
    "sp500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "nasdaq100": "https://en.wikipedia.org/wiki/Nasdaq-100",
}


def normalise_ticker(value: object) -> str:
    return str(value).strip().upper().replace(".", "-")


def read_html_tables(url: str) -> list[pd.DataFrame]:
    """Fetch HTML with browser-like headers to avoid HTTP 403 in GitHub Actions."""
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")

    return pd.read_html(StringIO(html))


def load_universe() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    sp500_tables = read_html_tables(WIKIPEDIA_SOURCES["sp500"])
    sp500 = next(
        table
        for table in sp500_tables
        if "Symbol" in table.columns and "Security" in table.columns
    )
    frames.append(
        pd.DataFrame(
            {
                "Ticker": sp500["Symbol"].map(normalise_ticker),
                "Name": sp500["Security"].astype(str).str.strip(),
                "Universe": "S&P 500",
            }
        )
    )

    nasdaq_tables = read_html_tables(WIKIPEDIA_SOURCES["nasdaq100"])
    nasdaq = next(table for table in nasdaq_tables if "Ticker" in table.columns)
    name_column = "Company" if "Company" in nasdaq.columns else nasdaq.columns[0]
    frames.append(
        pd.DataFrame(
            {
                "Ticker": nasdaq["Ticker"].map(normalise_ticker),
                "Name": nasdaq[name_column].astype(str).str.strip(),
                "Universe": "Nasdaq-100",
            }
        )
    )

    universe = pd.concat(frames, ignore_index=True)
    universe = universe.drop_duplicates("Ticker", keep="first")
    return universe.sort_values("Ticker").reset_index(drop=True)


def batch_price_history(tickers: Iterable[str]) -> pd.DataFrame:
    ticker_list = list(tickers)
    raw = yf.download(
        tickers=ticker_list,
        period="15mo",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" not in raw.columns.get_level_values(0):
            return pd.DataFrame()
        close = raw["Close"].copy()
    else:
        close = raw[["Close"]].copy()
        close.columns = ticker_list[:1]

    return close.dropna(how="all")


def period_return(series: pd.Series, days: int) -> float:
    clean = series.dropna()
    if len(clean) <= days:
        return np.nan
    return float(clean.iloc[-1] / clean.iloc[-days - 1] - 1)


def momentum_shortlist(
    universe: pd.DataFrame,
    close: pd.DataFrame,
    limit: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for item in universe.itertuples(index=False):
        if item.Ticker not in close.columns:
            continue
        prices = close[item.Ticker].dropna()
        if len(prices) < 210:
            continue

        momentum_3m = period_return(prices, 63)
        momentum_6m = period_return(prices, 126)
        moving_average_200d = float(prices.tail(200).mean())
        current_price = float(prices.iloc[-1])
        above_200d = current_price > moving_average_200d

        score = (
            0.45 * np.nan_to_num(momentum_3m, nan=-1.0)
            + 0.55 * np.nan_to_num(momentum_6m, nan=-1.0)
            + (0.10 if above_200d else -0.10)
        )
        rows.append(
            {
                "Ticker": item.Ticker,
                "Name": item.Name,
                "Universe": item.Universe,
                "Current_Price": current_price,
                "Momentum_3M": momentum_3m,
                "Momentum_6M": momentum_6m,
                "Price_Above_200D": above_200d,
                "Momentum_Shortlist_Score": score,
            }
        )

    shortlist = pd.DataFrame(rows)
    if shortlist.empty:
        return shortlist

    eligible = shortlist.loc[
        shortlist["Price_Above_200D"]
        & (shortlist["Momentum_3M"] > 0)
        & (shortlist["Momentum_6M"] > 0)
    ].copy()
    if eligible.empty:
        eligible = shortlist.copy()

    return eligible.nlargest(limit, "Momentum_Shortlist_Score").reset_index(drop=True)


def safe_number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if math.isfinite(number) else np.nan


def annual_cagr(values: pd.Series) -> tuple[float, int]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if len(numeric) < 2:
        return np.nan, 0

    numeric = numeric.iloc[::-1]
    start = float(numeric.iloc[0])
    end = float(numeric.iloc[-1])
    years = len(numeric) - 1
    if start <= 0 or end <= 0 or years <= 0:
        return np.nan, years
    return float((end / start) ** (1 / years) - 1), years


def statement_row(statement: pd.DataFrame, labels: list[str]) -> pd.Series:
    for label in labels:
        if label in statement.index:
            return statement.loc[label]
    return pd.Series(dtype=float)


def calculate_fundamentals(ticker_symbol: str) -> dict[str, object]:
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info or {}

    revenue_cagr = np.nan
    eps_cagr = np.nan
    revenue_years = 0
    eps_years = 0
    try:
        statement = ticker.income_stmt
        if statement is not None and not statement.empty:
            revenue_cagr, revenue_years = annual_cagr(
                statement_row(statement, ["Total Revenue", "Operating Revenue"])
            )
            eps_cagr, eps_years = annual_cagr(
                statement_row(statement, ["Diluted EPS", "Basic EPS"])
            )
    except Exception:
        pass

    current_price = safe_number(
        info.get("currentPrice") or info.get("regularMarketPrice")
    )
    target_price = safe_number(info.get("targetMeanPrice"))
    upside = (
        target_price / current_price - 1
        if pd.notna(target_price) and pd.notna(current_price) and current_price > 0
        else np.nan
    )

    downside = safe_number(info.get("fiftyTwoWeekLow"))
    downside_pct = (
        downside / current_price - 1
        if pd.notna(downside) and pd.notna(current_price) and current_price > 0
        else np.nan
    )
    risk_reward = (
        upside / abs(downside_pct)
        if pd.notna(upside) and pd.notna(downside_pct) and downside_pct != 0
        else np.nan
    )

    return {
        "Name": str(info.get("shortName") or info.get("longName") or "").strip(),
        "Market_Cap_USD": safe_number(info.get("marketCap")),
        "Gross_Margin": safe_number(info.get("grossMargins")),
        "ROIC": safe_number(info.get("returnOnAssets")),
        "Upside_Pct": upside,
        "Downside_Pct": downside_pct,
        "Risk_Reward": risk_reward,
        "Revenue_CAGR_5Y": revenue_cagr,
        "EPS_CAGR_5Y": eps_cagr,
        "Revenue_History_Years": revenue_years,
        "EPS_History_Years": eps_years,
    }


def percentile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    ranked = values.rank(pct=True, method="average") * 100
    return ranked if higher_is_better else 100 - ranked


def risk_label(row: pd.Series) -> str:
    if row["Data_Quality"] < 55:
        return "High"
    if row["Downside_Pct"] < -0.35 or row["Gross_Margin"] < 0.25:
        return "High"
    if row["Downside_Pct"] < -0.25:
        return "Medium"
    return "Low"


def reason_text(row: pd.Series) -> str:
    strengths: list[str] = []
    if row["Revenue_CAGR_5Y"] >= 0.10:
        strengths.append("stærk omsætningsvækst")
    if row["EPS_CAGR_5Y"] >= 0.12:
        strengths.append("stærk EPS-vækst")
    if row["Gross_Margin"] >= 0.40:
        strengths.append("høj bruttomargin")
    if row["Momentum_3M"] > 0 and row["Momentum_6M"] > 0:
        strengths.append("positivt momentum")
    if row["Upside_Pct"] >= 0.20:
        strengths.append("analytiker-upside over 20 %")
    return ", ".join(strengths[:3]).capitalize() or "Blandet signalbillede"


def build_scores(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()

    quality_fields = [
        "Revenue_CAGR_5Y",
        "EPS_CAGR_5Y",
        "Gross_Margin",
        "ROIC",
        "Upside_Pct",
        "Downside_Pct",
        "Market_Cap_USD",
        "Momentum_3M",
        "Momentum_6M",
    ]
    result["Data_Quality"] = result[quality_fields].notna().mean(axis=1) * 100

    factor_scores = pd.DataFrame(index=result.index)
    factor_scores["revenue"] = percentile_score(result["Revenue_CAGR_5Y"])
    factor_scores["eps"] = percentile_score(result["EPS_CAGR_5Y"])
    factor_scores["margin"] = percentile_score(result["Gross_Margin"])
    factor_scores["roic"] = percentile_score(result["ROIC"])
    factor_scores["upside"] = percentile_score(result["Upside_Pct"])
    factor_scores["risk_reward"] = percentile_score(result["Risk_Reward"])
    factor_scores["momentum_3m"] = percentile_score(result["Momentum_3M"])
    factor_scores["momentum_6m"] = percentile_score(result["Momentum_6M"])

    weights = {
        "revenue": 0.16,
        "eps": 0.16,
        "margin": 0.12,
        "roic": 0.10,
        "upside": 0.12,
        "risk_reward": 0.08,
        "momentum_3m": 0.12,
        "momentum_6m": 0.14,
    }
    weighted_sum = sum(factor_scores[key].fillna(50) * weight for key, weight in weights.items())
    result["Composite_Score"] = weighted_sum.clip(0, 100).round(1)
    result["AI_Confidence"] = (
        result["Composite_Score"] * (0.55 + 0.45 * result["Data_Quality"] / 100)
    ).clip(0, 100).round(0)

    result["Status"] = np.select(
        [
            (result["Composite_Score"] >= 75) & (result["AI_Confidence"] >= 70),
            result["Composite_Score"] >= 60,
        ],
        ["High Conviction", "Watch"],
        default="Monitor",
    )
    result["Risk"] = result.apply(risk_label, axis=1)
    result["Reason"] = result.apply(reason_text, axis=1)
    return result.sort_values(
        ["Composite_Score", "AI_Confidence"],
        ascending=[False, False],
    ).reset_index(drop=True)


def write_excel(data: pd.DataFrame, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    export = data.reindex(columns=OUTPUT_COLUMNS).copy()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export.to_excel(writer, index=False, sheet_name="Compounder Radar")
        worksheet = writer.sheets["Compounder Radar"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for column_cells in worksheet.columns:
            width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 45)
            worksheet.column_dimensions[column_cells[0].column_letter].width = width


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Emerging Compounder Radar")
    parser.add_argument("--output", default="data/compounder_radar.xlsx")
    parser.add_argument("--shortlist", type=int, default=140)
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--sleep", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    universe = load_universe()
    print(f"Loaded {len(universe)} unique tickers")

    close = batch_price_history(universe["Ticker"])
    shortlist = momentum_shortlist(universe, close, args.shortlist)
    if shortlist.empty:
        raise RuntimeError("No tickers passed the price-history stage")
    print(f"Fetching fundamentals for {len(shortlist)} shortlisted tickers")

    rows: list[dict[str, object]] = []
    for index, item in enumerate(shortlist.itertuples(index=False), start=1):
        try:
            fundamentals = calculate_fundamentals(item.Ticker)
            row = item._asdict()
            if fundamentals.get("Name"):
                row["Name"] = fundamentals["Name"]
            row.update(fundamentals)
            rows.append(row)
        except Exception as exc:
            print(f"{item.Ticker}: skipped ({exc})")
        if index % 20 == 0:
            print(f"Processed {index}/{len(shortlist)}")
        time.sleep(args.sleep)

    if not rows:
        raise RuntimeError("No fundamental data could be collected")

    result = build_scores(pd.DataFrame(rows)).head(args.top).copy()
    result["Generated_UTC"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S")
    write_excel(result, Path(args.output))
    print(f"Wrote {len(result)} candidates to {args.output}")


if __name__ == "__main__":
    main()
