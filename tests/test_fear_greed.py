from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from modules.fear_greed import fetch_fear_greed, parse_snapshot, sentiment_zone
from modules.gauge_components import build_fear_greed_gauge

NOW = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)


def payload(score=32.75, timestamp=None):
    return {"fear_and_greed": {"score": score, "timestamp": timestamp or NOW.isoformat(),
                              "rating": "wrong rating must not override score"}}


@pytest.mark.parametrize("score,label", [(0, "Extreme Fear"), (25, "Extreme Fear"),
    (25.1, "Fear"), (45, "Fear"), (45.1, "Neutral"), (55, "Neutral"),
    (55.1, "Greed"), (75, "Greed"), (75.1, "Extreme Greed"), (100, "Extreme Greed")])
def test_score_and_zone(score, label):
    snapshot = parse_snapshot(payload(score), now=NOW)
    assert snapshot.score == score
    assert snapshot.label == label
    figure = build_fear_greed_gauge(snapshot.score, snapshot.label)
    assert figure.data[0].gauge.threshold.value == score
    assert figure.data[0].number.suffix == "/100"
    assert len(figure.data[0].gauge.steps) == 5
    assert figure.layout.annotations[-1].font.color == sentiment_zone(score)[1]


@pytest.mark.parametrize("score", [None, True, "52", -1, 101, float("nan"), float("inf")])
def test_reject_invalid_scores(score):
    with pytest.raises(ValueError):
        parse_snapshot(payload(score), now=NOW)


@pytest.mark.parametrize("data", [{}, [], {"fear_and_greed_historical": {"score": 50}},
    {"fear_and_greed": []}, payload(timestamp="invalid"),
    payload(timestamp="2026-11-06T12:00:00"),
    payload(timestamp=(NOW - timedelta(days=6)).isoformat()),
    payload(timestamp=(NOW + timedelta(hours=1)).isoformat())])
def test_reject_bad_schema_or_timestamp(data):
    with pytest.raises(ValueError):
        parse_snapshot(data, now=NOW)


def test_weekend_and_holiday_age_allowed():
    assert parse_snapshot(payload(timestamp=(NOW - timedelta(days=4)).isoformat()), now=NOW).score == 32.75


@pytest.mark.parametrize("failure", [URLError("offline"), TimeoutError(),
    HTTPError("https://cnn.io", 418, "blocked", {}, None)])
def test_network_failure_has_no_invented_score(failure):
    with patch("modules.fear_greed.urlopen", side_effect=failure) as request:
        snapshot = fetch_fear_greed()
    assert request.call_count == 1
    assert request.call_args.kwargs["timeout"] == 5
    assert snapshot.score is None
    assert snapshot.error
    figure = build_fear_greed_gauge(snapshot.score, snapshot.label)
    assert figure.data[0].mode == "gauge"
    assert figure.data[0].gauge.threshold.value is None
    assert len(figure.data[0].gauge.steps) == 1
    assert any(a.text == "<b>N/A</b>" for a in figure.layout.annotations)


@pytest.mark.parametrize("body", [b"<html>blocked</html>", b"{}", b"x" * 1_000_001],
                         ids=["html", "missing-index", "oversized"])
def test_bad_response_fails_closed(body):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = body
    with patch("modules.fear_greed.urlopen", return_value=response):
        assert fetch_fear_greed().score is None


def test_valid_response():
    import json
    response = MagicMock()
    data = payload(0, datetime.now(timezone.utc).isoformat())
    response.__enter__.return_value.read.return_value = json.dumps(data).encode()
    with patch("modules.fear_greed.urlopen", return_value=response):
        assert fetch_fear_greed().score == 0
