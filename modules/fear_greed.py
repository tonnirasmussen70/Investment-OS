"""Optional CNN sentiment data. Never used as a portfolio decision input."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from http.client import HTTPException
from urllib.error import URLError
from urllib.request import Request, urlopen

SOURCE_URL = "https://edition.cnn.com/markets/fear-and-greed"
DATA_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
MAX_AGE = timedelta(days=5)  # Allow weekends and US market holidays.
ZONES = (
    (25, "Extreme Fear", "#e45756"),
    (45, "Fear", "#ee9955"),
    (55, "Neutral", "#e6c84f"),
    (75, "Greed", "#9ac568"),
    (100, "Extreme Greed", "#46a79b"),
)


@dataclass(frozen=True)
class FearGreedSnapshot:
    score: float | None = None
    updated_at: datetime | None = None
    error: str | None = None

    @property
    def label(self) -> str:
        return sentiment_zone(self.score)[0] if self.score is not None else "Utilgængelig"


def sentiment_zone(score: float) -> tuple[str, str]:
    # CNN categories: 0-25, >25-45, >45-55, >55-75, >75-100.
    for upper, label, color in ZONES:
        if score <= upper:
            return label, color
    raise ValueError("Score outside 0-100")


def parse_snapshot(payload: object, *, now: datetime | None = None) -> FearGreedSnapshot:
    """Validate the current index, not historical/component/previous-close data."""
    if not isinstance(payload, dict) or not isinstance(payload.get("fear_and_greed"), dict):
        raise ValueError("Missing current CNN index")
    current = payload["fear_and_greed"]
    score = current.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("Invalid CNN score")
    score = float(score)
    if not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("CNN score outside 0-100")
    timestamp = current.get("timestamp")
    if not isinstance(timestamp, str):
        raise ValueError("Missing CNN timestamp")
    updated = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if updated.tzinfo is None:
        raise ValueError("CNN timestamp must include timezone")
    updated = updated.astimezone(timezone.utc)
    now = now or datetime.now(timezone.utc)
    if updated > now + timedelta(minutes=5) or now - updated > MAX_AGE:
        raise ValueError("CNN timestamp is stale or in the future")
    return FearGreedSnapshot(score, updated)


def fetch_fear_greed() -> FearGreedSnapshot:
    """One bounded public request; no retries, browser impersonation or bypass."""
    request = Request(DATA_URL, headers={"Accept": "application/json", "User-Agent": "Investment-OS/1.0"})
    try:
        with urlopen(request, timeout=5) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("CNN response too large")
        return parse_snapshot(json.loads(raw))
    except (URLError, OSError, HTTPException, ValueError, TypeError, OverflowError):
        return FearGreedSnapshot(error="CNN-data kunne ikke hentes eller valideres.")
