from __future__ import annotations

import copy
import math
import re
import threading
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote

import yfinance as yf

from api.contracts import warning


DEFAULT_RESEARCH_TTL_SECONDS = 6 * 60 * 60
EXPECTED_FIELDS = (
    "currentPrice",
    "marketCap",
    "totalRevenue",
    "trailingPE",
    "forwardPE",
    "priceToSalesTrailing12Months",
    "enterpriseToEbitda",
    "revenueGrowth",
    "earningsGrowth",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "returnOnEquity",
    "totalCash",
    "totalDebt",
    "operatingCashflow",
    "freeCashflow",
)
MEANINGFUL_FIELDS = (
    "currentPrice",
    "marketCap",
    "totalRevenue",
    "revenueGrowth",
    "profitMargins",
    "totalCash",
    "totalDebt",
)


class ResearchUnavailableError(RuntimeError):
    """Raised when the external provider cannot return meaningful research data."""


def unavailable_research(ticker: str, message: str) -> dict[str, Any]:
    """Return a machine-readable fallback without obscuring OS data."""
    requested = str(ticker or "").strip().upper()
    return {
        "research_type": "fundamental_snapshot",
        "ticker": requested,
        "status": "unavailable",
        "as_of": None,
        "source": {
            "provider": "Yahoo Finance",
            "adapter": "yfinance",
            "method": "Ticker.get_info",
            "url": f"https://finance.yahoo.com/quote/{quote(requested, safe='')}",
        },
        "data_quality": {
            "status": "unavailable",
            "coverage": 0.0,
            "available_fields": 0,
            "expected_fields": len(EXPECTED_FIELDS),
        },
        "freshness": {
            "status": "unavailable",
            "age_seconds": None,
            "ttl_seconds": DEFAULT_RESEARCH_TTL_SECONDS,
            "cache_hit": False,
        },
        "warnings": [
            warning("RESEARCH_UNAVAILABLE", message),
            warning(
                "RESEARCH_DOES_NOT_CHANGE_OS_SIGNALS",
                "Researchlaget ændrer ikke Investment OS-signaler, Decision Score eller handling.",
            ),
        ],
    }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _number(value: Any) -> int | float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _text(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _date_from_unix(value: Any) -> str | None:
    number = _number(value)
    if number is None:
        return None
    try:
        return datetime.fromtimestamp(number, tz=timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError):
        return None


class YahooFinanceResearchProvider:
    """Fetch a factual research snapshot without producing an investment signal."""

    def __init__(
        self,
        *,
        ttl_seconds: int = DEFAULT_RESEARCH_TTL_SECONDS,
        ticker_factory: Callable[[str], Any] = yf.Ticker,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.ttl_seconds = max(0, int(ttl_seconds))
        self._ticker_factory = ticker_factory
        self._now = now
        self._cache: dict[str, tuple[datetime, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def get_stock_research(self, ticker: str) -> dict[str, Any]:
        requested = str(ticker or "").strip().upper()
        if not requested:
            raise ResearchUnavailableError("Ticker mangler til researchopslaget.")
        if len(requested) > 20 or re.fullmatch(r"[A-Z0-9.^=-]+", requested) is None:
            raise ResearchUnavailableError("Tickerformatet er ugyldigt til researchopslaget.")

        now = self._now().astimezone(timezone.utc)
        with self._lock:
            cached = self._cache.get(requested)
        if cached is not None:
            fetched_at, payload = cached
            age_seconds = max(0, int((now - fetched_at).total_seconds()))
            if age_seconds <= self.ttl_seconds:
                result = copy.deepcopy(payload)
                result["freshness"] = {
                    "status": "fresh",
                    "age_seconds": age_seconds,
                    "ttl_seconds": self.ttl_seconds,
                    "cache_hit": True,
                }
                return result

        try:
            info = self._ticker_factory(requested).get_info()
        except Exception as exc:
            if cached is not None:
                fetched_at, payload = cached
                age_seconds = max(0, int((now - fetched_at).total_seconds()))
                result = copy.deepcopy(payload)
                result["freshness"] = {
                    "status": "stale",
                    "age_seconds": age_seconds,
                    "ttl_seconds": self.ttl_seconds,
                    "cache_hit": True,
                }
                result.setdefault("warnings", []).append(
                    warning(
                        "RESEARCH_STALE_CACHE",
                        "Researchkilden kunne ikke opdateres; seneste cachede snapshot vises.",
                        age_seconds=age_seconds,
                    )
                )
                return result
            raise ResearchUnavailableError(
                f"Researchdata kunne ikke hentes for {requested}."
            ) from exc
        if not isinstance(info, dict):
            raise ResearchUnavailableError(
                f"Researchkilden returnerede et ugyldigt svar for {requested}."
            )

        available = sum(info.get(field) is not None for field in EXPECTED_FIELDS)
        meaningful = sum(info.get(field) is not None for field in MEANINGFUL_FIELDS)
        if meaningful == 0:
            raise ResearchUnavailableError(
                f"Researchkilden har ingen brugbare nøgletal for {requested}."
            )

        coverage = available / len(EXPECTED_FIELDS)
        quality_status = "good" if coverage >= 0.7 else "partial"
        warnings = [
            warning(
                "EXTERNAL_RESEARCH_SOURCE",
                "Eksterne markedsdata kan være forsinkede eller ufuldstændige "
                "og bør verificeres før en beslutning.",
            ),
            warning(
                "RESEARCH_DOES_NOT_CHANGE_OS_SIGNALS",
                "Researchlaget ændrer ikke Investment OS-signaler, Decision Score eller handling.",
            ),
        ]
        if quality_status == "partial":
            warnings.append(
                warning(
                    "RESEARCH_PARTIAL",
                    "Researchkilden mangler en del af de forventede nøgletal.",
                    available_fields=available,
                    expected_fields=len(EXPECTED_FIELDS),
                )
            )

        fetched_at = now
        payload: dict[str, Any] = {
            "research_type": "fundamental_snapshot",
            "ticker": requested,
            "status": "available" if quality_status == "good" else "partial",
            "as_of": fetched_at.isoformat(),
            "reporting_period_end": _date_from_unix(info.get("mostRecentQuarter")),
            "source": {
                "provider": "Yahoo Finance",
                "adapter": "yfinance",
                "method": "Ticker.get_info",
                "url": f"https://finance.yahoo.com/quote/{quote(requested, safe='')}",
            },
            "identity": {
                "name": _text(info.get("longName") or info.get("shortName")),
                "sector": _text(info.get("sector")),
                "industry": _text(info.get("industry")),
                "country": _text(info.get("country")),
            },
            "market": {
                "currency": _text(info.get("currency")),
                "current_price": _number(info.get("currentPrice")),
                "market_cap": _number(info.get("marketCap")),
                "enterprise_value": _number(info.get("enterpriseValue")),
            },
            "valuation": {
                "trailing_pe": _number(info.get("trailingPE")),
                "forward_pe": _number(info.get("forwardPE")),
                "price_to_sales": _number(info.get("priceToSalesTrailing12Months")),
                "enterprise_to_ebitda": _number(info.get("enterpriseToEbitda")),
            },
            "growth": {
                "total_revenue": _number(info.get("totalRevenue")),
                "revenue_growth": _number(info.get("revenueGrowth")),
                "earnings_growth": _number(info.get("earningsGrowth")),
            },
            "profitability": {
                "gross_margin": _number(info.get("grossMargins")),
                "operating_margin": _number(info.get("operatingMargins")),
                "profit_margin": _number(info.get("profitMargins")),
                "return_on_equity": _number(info.get("returnOnEquity")),
            },
            "financial_strength": {
                "total_cash": _number(info.get("totalCash")),
                "total_debt": _number(info.get("totalDebt")),
                "operating_cashflow": _number(info.get("operatingCashflow")),
                "free_cashflow": _number(info.get("freeCashflow")),
            },
            "analyst_context": {
                "target_mean_price": _number(info.get("targetMeanPrice")),
                "recommendation_key": _text(info.get("recommendationKey")),
                "number_of_analyst_opinions": _number(info.get("numberOfAnalystOpinions")),
            },
            "data_quality": {
                "status": quality_status,
                "coverage": round(coverage, 3),
                "available_fields": available,
                "expected_fields": len(EXPECTED_FIELDS),
            },
            "freshness": {
                "status": "fresh",
                "age_seconds": 0,
                "ttl_seconds": self.ttl_seconds,
                "cache_hit": False,
            },
            "warnings": warnings,
        }
        with self._lock:
            self._cache[requested] = (fetched_at, copy.deepcopy(payload))
        return payload


_DEFAULT_PROVIDER = YahooFinanceResearchProvider()


def get_stock_research(ticker: str) -> dict[str, Any]:
    return _DEFAULT_PROVIDER.get_stock_research(ticker)
