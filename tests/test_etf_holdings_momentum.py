import numpy as np
import pandas as pd
import pytest

from modules.etf_holdings_momentum import holdings_breadth


def sample_data():
    tickers = [f"T{i}" for i in range(12)]
    holdings = pd.DataFrame({"Ticker": tickers, "Weight": [0.05] * 12})
    prices = pd.DataFrame({t: [100 + d * (i + 1) / 100 for d in range(70)]
                           for i, t in enumerate(tickers)})
    return holdings, prices


def test_broad_positive_contribution():
    h, p = sample_data()
    result = holdings_breadth(h, p)
    assert result["status"] == "Bredt"
    assert result["priced_count"] == 12
    assert np.isclose(result["positive_weight_breadth"], 1)


def test_missing_prices_not_assumed_zero():
    h, p = sample_data()
    result = holdings_breadth(h, p.drop(columns=["T0", "T1", "T2", "T3"]))
    assert result["status"] == "Utilstrækkelige data"
    assert result["priced_count"] == 8


def test_reject_bad_weights():
    h, p = sample_data()
    h["Weight"] = 6.5
    with pytest.raises(ValueError):
        holdings_breadth(h, p)


def test_local_return_math():
    h, p = sample_data()
    result = holdings_breadth(h, p)
    row = result["table"].iloc[0]
    assert np.isclose(row["Contribution_1M"], row["Weight"] * row["1M"])
