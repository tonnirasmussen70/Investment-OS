"""Optional daily VIX close from FRED, with Cboe as a fallback."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from http.client import HTTPException
from io import StringIO
import math
from urllib.error import URLError
from urllib.request import Request, urlopen

FRED_URL = "https://fred.stlouisfed.org/series/VIXCLS"
CBOE_URL = "https://www.cboe.com/tradable_products/vix/vix_historical_data"
FRED_DATA_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"
CBOE_DATA_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
MAX_AGE = timedelta(days=5)
# IOS display conventions, not official Cboe categories or trading gates.
ZONES = ((15, "Lav", "#46a79b"), (20, "Moderat", "#9ac568"),
         (30, "Forhøjet", "#e6c84f"), (40, "Høj", "#ee9955"),
         (math.inf, "Meget høj", "#e45756"))


@dataclass(frozen=True)
class VixSnapshot:
    value: float | None = None
    observed_on: date | None = None
    source: str | None = None
    source_url: str | None = None
    error: str | None = None

    @property
    def label(self) -> str:
        return vix_zone(self.value)[0] if self.value is not None else "Utilgængelig"


def vix_zone(value: float) -> tuple[str, str]:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Invalid VIX")
    for upper, label, color in ZONES:
        if value < upper:
            return label, color
    raise ValueError("Invalid VIX")


def parse_vix_csv(payload: str, source: str, *, today: date | None = None) -> VixSnapshot:
    today = today or datetime.now(timezone.utc).date()
    reader = csv.DictReader(StringIO(payload.lstrip("\ufeff")))
    if source == "FRED":
        date_column, value_column, source_url = "observation_date", "VIXCLS", FRED_URL
        if reader.fieldnames and "DATE" in reader.fieldnames:
            date_column = "DATE"
    elif source == "Cboe":
        date_column, value_column, source_url = "DATE", "CLOSE", CBOE_URL
    else:
        raise ValueError("Unknown VIX source")
    if not reader.fieldnames or not {date_column, value_column} <= set(reader.fieldnames):
        raise ValueError("Missing VIX CSV columns")
    observations = []
    for row in reader:
        text = row.get(value_column, "")
        if text is None or text.strip() in ("", "."):
            continue  # FRED missing observations (weekends/holidays).
        raw_date = row[date_column]
        observed = (datetime.strptime(raw_date, "%m/%d/%Y").date()
                    if source == "Cboe" else date.fromisoformat(raw_date))
        value = float(text)
        if not math.isfinite(value) or value <= 0 or observed > today:
            raise ValueError("Invalid VIX observation")
        observations.append((observed, value))
    if not observations:
        raise ValueError("No VIX observations")
    observed, value = max(observations, key=lambda item: item[0])
    if today - observed > MAX_AGE:
        raise ValueError("Stale VIX data")
    return VixSnapshot(value, observed, source, source_url)


def fetch_vix(*, today: date | None = None) -> VixSnapshot:
    today = today or datetime.now(timezone.utc).date()
    start = (today - timedelta(days=14)).isoformat()
    for source, url in (("FRED", FRED_DATA_URL + "&cosd=" + start), ("Cboe", CBOE_DATA_URL)):
        request = Request(url, headers={"Accept": "text/csv", "User-Agent": "Investment-OS/1.0"})
        try:
            with urlopen(request, timeout=5) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("VIX response too large")
            return parse_vix_csv(raw.decode("utf-8-sig"), source, today=today)
        except (URLError, OSError, HTTPException, ValueError, TypeError, OverflowError, csv.Error):
            continue
    return VixSnapshot(error="VIX-data fra FRED/Cboe kunne ikke hentes eller valideres.")
