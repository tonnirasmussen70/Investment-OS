"""Tests for the informational ETF breadth Light indicator."""
import pandas as pd
import pytest

from modules.etf_holdings_momentum import holdings_breadth


def fixtures(positive=10):
    tickers = [f"T{i}" for i in range(10)]
    holdings = pd.DataFrame({"Ticker": tickers})
    dates = pd.bdate_range("2026-08-01", periods=30)
    prices = pd.DataFrame(
        {ticker: [100 + day if i < positive else 100 - day for day in range(30)]
         for i, ticker in enumerate(tickers)}, index=dates
    )
    return holdings, prices


@pytest.mark.parametrize("positive,status", [
    (10, "Bredt"), (7, "Bredt"), (6, "Blandet"),
    (4, "Blandet"), (3, "Smalt"), (0, "Smalt"),
])
def test_thresholds(positive, status):
    holdings, prices = fixtures(positive)
    result = holdings_breadth(holdings, prices)
    assert result["status"] == status
    assert result["positive"] == positive
    assert result["covered"] == 10


def test_missing_history_is_not_counted_as_negative():
    holdings, prices = fixtures()
    result = holdings_breadth(holdings, prices.drop(columns=["T0"]))
    assert result["status"] == "Ikke tilgængelig"
    assert result["covered"] == 9


def test_stale_history_is_unavailable():
    holdings, prices = fixtures()
    prices.loc[prices.index[-3]:, "T0"] = float("nan")
    prices.loc[prices.index[-8]:, "T1"] = float("nan")
    result = holdings_breadth(holdings, prices)
    assert result["status"] == "Ikke tilgængelig"
    assert result["covered"] == 9


@pytest.mark.parametrize("bad", [
    pd.DataFrame({"Ticker": ["T0"] * 10}),
    pd.DataFrame({"Ticker": [f"T{i}" for i in range(9)]}),
    pd.DataFrame({"Name": [f"T{i}" for i in range(10)]}),
])
def test_invalid_top_ten_lists_rejected(bad):
    _, prices = fixtures()
    with pytest.raises(ValueError):
        holdings_breadth(bad, prices)


def test_zero_return_is_not_positive():
    holdings, prices = fixtures(7)
    prices["T0"] = 100
    result = holdings_breadth(holdings, prices)
    assert result["status"] == "Blandet"
    assert result["positive"] == 6
