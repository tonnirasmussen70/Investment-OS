from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from modules.etf_candidates import render_etf_candidates
from modules.etf_radar import (
    ETFRadar, load_or_refresh_etf_radar, load_universe, rank_etfs, yahoo_history,
)


NOW = pd.Timestamp("2026-10-19T14:00:00Z")
DATES = pd.bdate_range(end="2026-10-16", periods=200)


def funds(count=2):
    return [{"Name": f"Fund {i} UCITS ETF", "Ticker": f"TEST{i}.DE", "ISIN": f"IE00TEST{i:03d}0",
             "Currency": "EUR", "Exposure": "Test", "Issuer_Source": "https://example.org/fund"}
            for i in range(count)]


def history(rate=.001):
    return pd.Series(100 * (1 + rate) ** np.arange(len(DATES)), index=DATES)


def prepare(tmp_path, count=2):
    universe = funds(count)
    (tmp_path / "etf_universe.json").write_text(json.dumps({"funds": universe}), encoding="utf-8")
    return universe


def fetch(fund):
    return history(.001 if fund["Ticker"] == "TEST0.DE" else -.001)


def test_known_returns_and_risk_have_correct_units():
    result = rank_etfs(funds(), {"TEST0.DE": history(), "TEST1.DE": history(-.001)}, now=NOW)
    up = result.set_index("Ticker").loc["TEST0.DE"]
    assert up["Return_1M"] == pytest.approx(1.001 ** 21 - 1)
    assert up["Return_3M"] == pytest.approx(1.001 ** 63 - 1)
    assert up["Return_6M"] == pytest.approx(1.001 ** 126 - 1)
    assert up["Volatility_3M"] == pytest.approx(0, abs=1e-12)
    assert up["Max_Drawdown_6M"] == 0
    down = result.set_index("Ticker").loc["TEST1.DE"]
    assert down["Max_Drawdown_6M"] == pytest.approx(.999 ** 126 - 1)
    assert result.iloc[0]["Ticker"] == "TEST0.DE"
    assert down["Research_Status"].startswith("Afvent")


def test_volatility_and_drawdown_penalise_an_oscillating_path():
    smooth = pd.Series(100.0, index=DATES)
    risky = smooth.copy()
    risky.iloc[::2] = 120.0
    result = rank_etfs(funds(), {"TEST0.DE": smooth, "TEST1.DE": risky}, now=NOW).set_index("Ticker")
    assert result.loc["TEST1.DE", "Max_Drawdown_6M"] == pytest.approx(-1 / 6)
    assert result.loc["TEST1.DE", "Volatility_3M"] > result.loc["TEST0.DE", "Volatility_3M"]
    assert result.loc["TEST1.DE", "Score"] < result.loc["TEST0.DE", "Score"]


def test_identical_funds_tie_at_50_and_sort_deterministically():
    result = rank_etfs(funds(), {"TEST0.DE": history(), "TEST1.DE": history()}, now=NOW)
    assert result["Score"].tolist() == [50, 50]
    assert result["ISIN"].tolist() == sorted(result["ISIN"])


def test_same_day_bar_is_excluded_and_dates_are_shared():
    first = history()
    first.loc[pd.Timestamp("2026-10-19")] = 1e9
    second = history().iloc[:-1]
    result = rank_etfs(funds(), {"TEST0.DE": first, "TEST1.DE": second}, now=NOW)
    assert result["As_Of"].unique().tolist() == ["2026-10-15"]
    assert result["Return_6M"].max() == pytest.approx(1.001 ** 126 - 1)


@pytest.mark.parametrize("invalid", ["missing", "short", "stale", "negative", "infinite", "gap", "duplicate"])
def test_incomplete_or_invalid_history_cannot_create_a_ranking(invalid):
    good = history()
    bad = good.copy()
    if invalid == "missing":
        bad = None
    elif invalid == "short":
        bad = bad.iloc[-100:]
    elif invalid == "stale":
        bad.index -= pd.Timedelta(days=14)
    elif invalid == "negative":
        bad.iloc[-1] = -1
    elif invalid == "infinite":
        bad.iloc[-1] = np.inf
    elif invalid == "gap":
        bad = bad.drop(bad.index[-20:-10])
    else:
        bad = pd.concat([bad, bad.iloc[-1:]])
    with pytest.raises(ValueError):
        rank_etfs(funds(), {"TEST0.DE": good, "TEST1.DE": bad}, now=NOW)


def test_refresh_saves_full_universe_and_fresh_snapshot_avoids_network(tmp_path):
    prepare(tmp_path, 12)
    result = load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=fetch)
    assert result.refreshed and result.persisted and len(result.data) == 12
    never_fetch = Mock(side_effect=AssertionError("Should use snapshot"))
    cached = load_or_refresh_etf_radar(tmp_path, now=NOW + pd.Timedelta(hours=1), fetch_history=never_fetch)
    assert not cached.refreshed and cached.persisted
    assert cached.generated_at == result.generated_at
    never_fetch.assert_not_called()


def test_partial_download_failure_retains_original_snapshot_bytes(tmp_path):
    prepare(tmp_path)
    first = load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=fetch)
    path = tmp_path / "etf_radar.json"
    original = path.read_bytes()

    def partial(fund):
        if fund["Ticker"] == "TEST1.DE":
            raise ConnectionError("Unavailable")
        return history(.01)

    result = load_or_refresh_etf_radar(tmp_path, force=True, now=NOW + pd.Timedelta(hours=1), fetch_history=partial)
    assert not result.refreshed and result.persisted
    assert result.generated_at == first.generated_at
    assert path.read_bytes() == original
    pd.testing.assert_frame_equal(result.data, first.data)
    assert any("seneste gyldige" in note for note in result.notes)


def test_initial_download_failure_never_seeds_example_candidates(tmp_path):
    prepare(tmp_path)
    result = load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=Mock(side_effect=ConnectionError))
    assert result.data.empty and not result.refreshed
    assert not (tmp_path / "etf_radar.json").exists()


def test_changed_universe_does_not_reuse_old_ranking(tmp_path):
    prepare(tmp_path)
    load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=fetch)
    prepare(tmp_path, 3)
    result = load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=Mock(side_effect=ConnectionError))
    assert result.data.empty
    assert any("ugyldigt" in note for note in result.notes)


@pytest.mark.parametrize("corruption", ["broken_json", "nan_score", "future_date", "nat_date", "identity", "missing_fund"])
def test_corrupt_cache_is_not_displayed(tmp_path, corruption):
    prepare(tmp_path)
    load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=fetch)
    path = tmp_path / "etf_radar.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if corruption == "nan_score":
        payload["candidates"][0]["Score"] = float("nan")
    elif corruption == "future_date":
        payload["as_of"] = "2099-01-01"
    elif corruption == "nat_date":
        payload["as_of"] = "NaT"
    elif corruption == "identity":
        payload["candidates"][0]["Ticker"] = "WRONG.DE"
    elif corruption == "missing_fund":
        payload["candidates"].pop()
    path.write_text("{" if corruption == "broken_json" else json.dumps(payload), encoding="utf-8")
    result = load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=Mock(side_effect=ConnectionError))
    assert result.data.empty


def test_read_only_snapshot_storage_still_returns_fresh_values(tmp_path):
    prepare(tmp_path)
    with patch("modules.etf_radar._save_snapshot", side_effect=PermissionError):
        result = load_or_refresh_etf_radar(tmp_path, now=NOW, fetch_history=fetch)
    assert result.refreshed and not result.persisted and len(result.data) == 2
    assert any("kunne ikke gemmes" in note for note in result.notes)


def test_yahoo_currency_symbol_and_instrument_are_checked():
    metadata = {"currency": "EUR", "instrumentType": "ETF", "symbol": "TEST0.DE"}
    with patch("modules.etf_radar.yf.Ticker") as ticker:
        ticker.return_value.history.return_value = pd.DataFrame({"Close": history()})
        ticker.return_value.get_history_metadata.return_value = metadata
        assert len(yahoo_history(funds()[0])) == 200
        assert ticker.return_value.history.call_args.kwargs["auto_adjust"] is True
        for key, value in (("currency", "USD"), ("instrumentType", "EQUITY"), ("symbol", "WRONG.DE")):
            ticker.return_value.get_history_metadata.return_value = {**metadata, key: value}
            with pytest.raises(ValueError):
                yahoo_history(funds()[0])


def test_configured_universe_has_unique_funds_and_eur_listings():
    universe = load_universe(Path(__file__).resolve().parents[1] / "data" / "etf_universe.json")
    assert len(universe) == 16
    assert len({fund["ISIN"] for fund in universe}) == 16
    assert all(fund["Currency"] == "EUR" for fund in universe)


def test_ui_shows_top_ten_and_converts_fractions_to_percent(tmp_path, monkeypatch):
    universe = prepare(tmp_path, 12)
    ranking = rank_etfs(universe, {fund["Ticker"]: fetch(fund) for fund in universe}, now=NOW)
    radar = ETFRadar(ranking, "2026-10-16", NOW.isoformat())
    monkeypatch.setattr("modules.etf_candidates.load_or_refresh_etf_radar", lambda *args, **kwargs: radar)
    tables = []
    st = SimpleNamespace(
        markdown=Mock(), caption=Mock(), warning=Mock(), info=Mock(), button=Mock(return_value=False),
        spinner=lambda *args: nullcontext(), expander=lambda *args: nullcontext(),
        cache_data=lambda **kwargs: lambda function: function,
        dataframe=lambda frame, **kwargs: tables.append(frame),
        column_config=SimpleNamespace(NumberColumn=Mock(), LinkColumn=Mock()),
    )
    render_etf_candidates(st, tmp_path)
    assert len(tables[0]) == 10 and len(tables[1]) == 12
    assert tables[0].iloc[0]["Return_1M"] == pytest.approx(ranking.iloc[0]["Return_1M"] * 100)
    assert "CSV" not in " ".join(str(call) for call in st.info.call_args_list)
