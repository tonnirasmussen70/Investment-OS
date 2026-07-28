from __future__ import annotations

import numpy as np
import pandas as pd


LOOKBACKS = {
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "12M": 252,
}


def period_return(series: pd.Series, lookback: int) -> float:
    """Beregn afkast over et fast antal handelsdage."""
    clean = series.dropna()
    if len(clean) <= lookback:
        return np.nan
    return float(clean.iloc[-1] / clean.iloc[-(lookback + 1)] - 1)


def add_momentum(
    portfolio: pd.DataFrame,
    price_history: pd.DataFrame,
    weights: dict[str, float],
) -> pd.DataFrame:
    """Tilføj momentum, volatilitet, drawdown, Composite og AI Confidence."""
    result = portfolio.copy()

    momentum_rows = []
    for ticker in result["Yahoo_Ticker"].dropna().astype(str).unique():
        row = {"Yahoo_Ticker": ticker}
        series = (
            price_history[ticker]
            if ticker in price_history.columns
            else pd.Series(dtype=float)
        )

        for label, lookback in LOOKBACKS.items():
            row[label] = period_return(series, lookback)

        returns = series.pct_change().dropna()

        row["Volatility"] = (
            float(returns.std() * np.sqrt(252))
            if len(returns) >= 20
            else np.nan
        )

        if len(series) >= 20:
            curve = series / series.iloc[0]
            drawdown = curve / curve.cummax() - 1
            row["Max_Drawdown"] = float(drawdown.min())
        else:
            row["Max_Drawdown"] = np.nan

        momentum_rows.append(row)

    momentum = pd.DataFrame(momentum_rows)
    result = result.merge(momentum, on="Yahoo_Ticker", how="left")

    result["Composite"] = sum(
        result[label].fillna(0) * float(weights.get(label, 0))
        for label in LOOKBACKS
    )

    valid_periods = result[list(LOOKBACKS)].notna().sum(axis=1)
    result["Momentum_Data_Quality"] = valid_periods / len(LOOKBACKS)

    rank = result["Composite"].rank(pct=True, method="average")

    risk_penalty = (
        result["Volatility"].fillna(0.35).clip(0, 0.70) / 0.70
    )

    trend_score = (
        (result["1W"].fillna(0) > 0).astype(float) * 0.20
        + (result["1M"].fillna(0) > 0).astype(float) * 0.20
        + (result["3M"].fillna(0) > 0).astype(float) * 0.30
        + (result["6M"].fillna(0) > 0).astype(float) * 0.30
    )

    result["AI_Confidence"] = (
        100
        * (
            0.55 * rank.fillna(0.5)
            + 0.30 * trend_score
            + 0.15 * (1 - risk_penalty)
        )
    ).clip(0, 100)

    result["Handling"] = np.select(
        [
            (
                result["Composite"]
                >= result["Composite"].quantile(0.75)
            )
            & (result["1W"] > 0)
            & (result["1M"] > 0),
            (
                (result["1W"] < 0)
                & (result["1M"] < 0)
                & (result["3M"] < 0)
            ),
            result["Composite"] < 0,
        ],
        ["Øg", "Reducer", "Afvent"],
        default="Hold",
    )

    return result


def portfolio_returns(
    portfolio: pd.DataFrame,
    price_history: pd.DataFrame,
) -> pd.Series:
    """Beregn vægtet dagligt porteføljeafkast."""
    if price_history.empty:
        return pd.Series(dtype=float)

    returns = price_history.pct_change().dropna(how="all")

    weights = (
        portfolio.groupby("Yahoo_Ticker")["Portfolio_Weight"]
        .sum()
        .reindex(returns.columns)
        .fillna(0)
    )

    valid = weights[weights > 0].index.intersection(returns.columns)

    if len(valid) == 0:
        return pd.Series(dtype=float)

    weights = weights.loc[valid]
    weights = weights / weights.sum()

    return returns[valid].fillna(0).dot(weights)


def rolling_sharpe(
    daily_returns: pd.Series,
    risk_free_rate: float,
    windows: tuple[int, ...] = (30, 90, 252),
) -> pd.DataFrame:
    """Beregn rullende Sharpe Ratio."""
    output = pd.DataFrame(index=daily_returns.index)

    for window in windows:
        rolling_mean = daily_returns.rolling(window).mean() * 252
        rolling_vol = (
            daily_returns.rolling(window).std() * np.sqrt(252)
        )

        output[f"Sharpe {window}D"] = (
            (rolling_mean - risk_free_rate)
            / rolling_vol.replace(0, np.nan)
        )

    return output.dropna(how="all")


def downside_deviation(
    daily_returns: pd.Series,
    minimum_acceptable_return: float = 0.0,
) -> float:
    """Beregn annualiseret downside deviation."""
    clean = daily_returns.dropna()

    if clean.empty:
        return np.nan

    daily_target = minimum_acceptable_return / 252
    downside = clean[clean < daily_target] - daily_target

    if downside.empty:
        return 0.0

    return float(
        np.sqrt((downside.pow(2)).mean()) * np.sqrt(252)
    )


def sortino_ratio(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    """Beregn annualiseret Sortino Ratio."""
    clean = daily_returns.dropna()

    if len(clean) < 20:
        return np.nan

    annual_return = clean.mean() * 252
    downside = downside_deviation(
        clean,
        minimum_acceptable_return=risk_free_rate,
    )

    if pd.isna(downside) or downside == 0:
        return np.nan

    return float((annual_return - risk_free_rate) / downside)


def maximum_drawdown(daily_returns: pd.Series) -> float:
    """Beregn maksimalt drawdown ud fra daglige afkast."""
    clean = daily_returns.dropna()

    if clean.empty:
        return np.nan

    equity_curve = (1 + clean).cumprod()
    drawdown = equity_curve / equity_curve.cummax() - 1

    return float(drawdown.min())


def annualized_return(daily_returns: pd.Series) -> float:
    """Beregn annualiseret geometrisk afkast."""
    clean = daily_returns.dropna()

    if len(clean) < 20:
        return np.nan

    total_return = float((1 + clean).prod())
    years = len(clean) / 252

    if years <= 0 or total_return <= 0:
        return np.nan

    return float(total_return ** (1 / years) - 1)


def calmar_ratio(daily_returns: pd.Series) -> float:
    """Beregn Calmar Ratio."""
    annual_return = annualized_return(daily_returns)
    max_drawdown = maximum_drawdown(daily_returns)

    if (
        pd.isna(annual_return)
        or pd.isna(max_drawdown)
        or max_drawdown == 0
    ):
        return np.nan

    return float(annual_return / abs(max_drawdown))


def beta(
    portfolio_returns_series: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Beregn beta mod benchmark."""
    aligned = pd.concat(
        [
            portfolio_returns_series.rename("portfolio"),
            benchmark_returns.rename("benchmark"),
        ],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 20:
        return np.nan

    benchmark_variance = aligned["benchmark"].var()

    if benchmark_variance == 0:
        return np.nan

    covariance = aligned["portfolio"].cov(aligned["benchmark"])

    return float(covariance / benchmark_variance)


def relative_strength(
    asset_prices: pd.Series,
    benchmark_prices: pd.Series,
    lookback: int = 63,
) -> float:
    """Beregn aktivets relative afkast mod benchmark."""
    aligned = pd.concat(
        [
            asset_prices.rename("asset"),
            benchmark_prices.rename("benchmark"),
        ],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) <= lookback:
        return np.nan

    asset_return = (
        aligned["asset"].iloc[-1]
        / aligned["asset"].iloc[-(lookback + 1)]
        - 1
    )

    benchmark_return = (
        aligned["benchmark"].iloc[-1]
        / aligned["benchmark"].iloc[-(lookback + 1)]
        - 1
    )

    return float(asset_return - benchmark_return)


def portfolio_risk_summary(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """
    Returnér få centrale risikomål til motorer og fremtidige rapporter.

    Målingerne beregnes centralt, men behøver ikke alle blive vist i UI.
    """
    return {
        "Annualized_Return": annualized_return(daily_returns),
        "Volatility": (
            float(daily_returns.dropna().std() * np.sqrt(252))
            if len(daily_returns.dropna()) >= 20
            else np.nan
        ),
        "Sortino": sortino_ratio(
            daily_returns,
            risk_free_rate=risk_free_rate,
        ),
        "Max_Drawdown": maximum_drawdown(daily_returns),
        "Calmar": calmar_ratio(daily_returns),
    }
