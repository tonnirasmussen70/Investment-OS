from __future__ import annotations

import pandas as pd

from modules.market_engine import MarketSnapshot
from modules.portfolio_engine import PortfolioModel, calculate_portfolio


def test_zero_master_market_value_uses_live_fallback():
    portfolio = pd.DataFrame([
        {
            "Asset_ID": "CLS",
            "Asset_Type": "Stock",
            "Name": "Celestica",
            "Ticker": "CLS",
            "Yahoo_Ticker": "CLS",
            "Quantity": 10.0,
            "Purchase_Price": 100.0,
            "Currency": "USD",
            "Account": "Saxo",
            "Include_Analytics": True,
            "Include_Weight": True,
            "Current_Price": 0.0,
            "Current_FX_to_DKK": 0.0,
            "Market_Value_DKK": 0.0,
        }
    ])
    model = PortfolioModel(
        portfolio=portfolio,
        accounts=pd.DataFrame(),
        settings={},
        fx=pd.DataFrame(),
        watchlist=pd.DataFrame(),
        cash=pd.DataFrame(),
    )
    snapshot = MarketSnapshot(
        prices={"CLS": 200.0},
        fx_to_dkk={"USD": 6.5},
        updated_at=pd.Timestamp("2026-09-15T18:00:00Z"),
        price_dates={},
        missing_prices=[],
        missing_fx=[],
    )

    result = calculate_portfolio(model, snapshot)

    assert result.loc[0, "Market_Value_DKK"] == 13000.0
    assert result.loc[0, "Market_Value_Source"] == "Yahoo live fallback"
