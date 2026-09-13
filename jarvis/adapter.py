from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from api.contracts import response_metadata
from api.service import build_investment_brief, build_stock_status, build_system_status


class JarvisCommandError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _normalized(command: str) -> str:
    value = (command or "").translate(
        str.maketrans({"æ": "ae", "ø": "o", "å": "a", "Æ": "AE", "Ø": "O", "Å": "A"})
    )
    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def classify_intent(command: str) -> str:
    """Classify only the explicitly approved MVP commands."""
    normalized = _normalized(command)
    if not normalized:
        raise JarvisCommandError("COMMAND_MISSING", "Kommandoen mangler.")
    if "investeringsbrief" in normalized or (
        "portefolje" in normalized and any(word in normalized for word in ("status", "hvordan", "brief"))
    ):
        return "investment_brief"
    if "investment os" in normalized and any(
        word in normalized for word in ("status", "version", "drift")
    ):
        return "system_status"
    if any(word in normalized.split() for word in ("analyser", "analyze", "analyse")):
        return "stock_analysis"
    raise JarvisCommandError(
        "COMMAND_UNSUPPORTED",
        "Kommandoen matcher ikke en godkendt Jarvis MVP-funktion.",
    )


def _number(value: Any) -> str:
    try:
        return f"{float(value):.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return "N/A"


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%".replace(".", ",")
    except (TypeError, ValueError):
        return "N/A"


def extract_ticker(command: str) -> str:
    """Extract the final ticker-like token from an approved analysis command."""
    tokens = re.findall(r"[A-Za-z0-9.^-]+", command or "")
    ignored = {"jarvis", "analyser", "analyze", "analyse", "aktien", "aktie"}
    candidates = [token for token in tokens if token.lower() not in ignored]
    if not candidates:
        raise JarvisCommandError("TICKER_MISSING", "Angiv en ticker, der skal analyseres.")
    ticker = candidates[-1].upper()
    if len(ticker) > 20:
        raise JarvisCommandError("TICKER_INVALID", "Tickerformatet er ugyldigt.")
    return ticker


def _format_changes(changes: dict[str, Any]) -> str:
    if not changes.get("available"):
        return "Der er endnu ikke et gyldigt sammenligningsgrundlag."
    deltas = changes.get("kpi_deltas") or {}
    labels = {
        "portfolio_health": "porteføljesundhed",
        "confidence": "konfidens",
        "data_quality": "datakvalitet",
        "macro_rate_risk": "Macro/Rate Risk",
    }
    parts = [
        f"{labels[key]} {float(value):+.1f}".replace(".", ",")
        for key, value in deltas.items()
        if key in labels and value not in (None, 0, 0.0)
    ]
    decision_section = changes.get("decision_changes") or {}
    decision_items = decision_section.get("items") or []
    schema_transition = bool(decision_items) and all(
        field_change.get("from") is None
        for item in decision_items
        for field_change in (item.get("changes") or {}).values()
    )
    if schema_transition:
        return (
            "Historikgrundlaget indeholder nye beslutningsfelter; "
            "beslutningsændringer vises fra næste sammenlignelige snapshot."
        )
    decision_count = int(decision_section.get("count", 0))
    if decision_count:
        parts.append(f"{decision_count} registrerede beslutningsændringer")
    opportunity_changes = changes.get("opportunity_changes") or {}
    entered = len(opportunity_changes.get("entered") or [])
    exited = len(opportunity_changes.get("exited") or [])
    if entered or exited:
        parts.append(f"{entered} nye og {exited} udgåede opportunities")
    return "; ".join(parts) + "." if parts else "Ingen registrerede ændringer siden sidste snapshot."


def format_investment_brief(brief: dict[str, Any]) -> str:
    """Render a compact Danish answer from structured, canonical fields."""
    kpis = brief.get("kpis") or {}
    decisions = brief.get("decisions") or {}
    opportunities = brief.get("opportunities") or {}
    decision_items = decisions.get("items") or []
    opportunity_items = opportunities.get("items") or []

    lines = [
        (
            f"Porteføljesundhed {_number(kpis.get('portfolio_health'))}/100. "
            f"Konfidens {_number(kpis.get('confidence'))}/100"
            f" ({kpis.get('confidence_label') or 'Ukendt'}). "
            f"Datakvalitet {_number(kpis.get('data_quality'))}/100. "
            f"Macro/Rate Risk {_number(kpis.get('macro_rate_risk'))}/100"
            f" ({kpis.get('macro_rate_level') or 'Ukendt'}); risiko-overlayet ændrer ikke køb/salg-logikken."
        ),
        "Ændringer: " + _format_changes(brief.get("changes") or {}),
    ]
    if decision_items:
        rendered = []
        for item in decision_items[:3]:
            asset = item.get("Aktiv") or item.get("Name") or "Ukendt aktiv"
            action = item.get("Handling") or "Ukendt handling"
            rendered.append(f"{asset}: {action}")
        lines.append(
            f"Decision Queue har {int(decisions.get('count', len(decision_items)))} punkt(er): "
            + "; ".join(rendered)
            + "."
        )
    else:
        lines.append("Decision Queue har ingen punkter.")

    if opportunity_items:
        names = [
            str(item.get("Name") or item.get("Yahoo_Ticker") or "Ukendt")
            for item in opportunity_items[:3]
        ]
        lines.append(
            f"Der er {int(opportunities.get('count', len(opportunity_items)))} opportunities. "
            "Top tre: " + ", ".join(names) + "."
        )
    else:
        lines.append("Der er ingen opportunities i snapshot'et.")
    lines.append(f"Data pr. {brief.get('as_of') or 'ukendt'} · run {brief.get('run_id') or 'ukendt'}.")
    return "\n".join(lines)


def format_stock_status(stock: dict[str, Any]) -> str:
    """Format a concise Danish OS-only stock analysis."""
    identity = stock.get("identity") or {}
    signals = stock.get("signals") or {}
    portfolio = stock.get("portfolio_context") or {}
    watchlist = stock.get("watchlist_context") or {}
    returns = signals.get("returns") or {}
    name = identity.get("name") or identity.get("ticker") or "Ukendt"
    ticker = identity.get("ticker") or "Ukendt"

    lines = [f"{name} ({ticker}) – Investment OS-status."]
    if any(signals.get(field) is not None for field in ("decision_score", "handling", "composite")):
        lines.append(
            f"Decision Score {_number(signals.get('decision_score'))}/100, "
            f"status {signals.get('decision_status') or 'Ukendt'}, "
            f"handling {signals.get('handling') or 'Ukendt'} og "
            f"AI Confidence {_number(signals.get('ai_confidence'))}/100."
        )
        lines.append(
            "Momentum: "
            + ", ".join(
                f"{period} {_percent(returns.get(period))}"
                for period in ("1W", "1M", "3M", "6M", "12M")
            )
            + f". RS 3M {_percent(signals.get('relative_strength_3m'))}."
        )
    else:
        lines.append(
            "Aktien har ingen beregnede momentum- eller Decision Engine-signaler i det aktuelle snapshot."
        )
    if portfolio.get("is_position"):
        lines.append(
            f"Porteføljevægt {_percent(portfolio.get('portfolio_weight'))}; "
            f"markedsværdi {_number(portfolio.get('market_value_dkk'))} DKK."
        )
    elif watchlist:
        lines.append(
            f"Watchlist-status {watchlist.get('Status') or 'Ukendt'}, "
            f"AI Confidence {_number(watchlist.get('AI_Confidence'))}/100, "
            f"target buy {_number(watchlist.get('Target_Buy'))} og "
            f"makspris {_number(watchlist.get('Max_Price'))} {watchlist.get('Currency') or ''}."
        )
        if watchlist.get("Notes"):
            lines.append(f"Watchlist-note: {watchlist['Notes']}.")
    lines.append(
        "Analysen omfatter kun eksisterende Investment OS-data og indeholder ikke ny fundamental research."
    )
    lines.append(f"Data pr. {stock.get('as_of') or 'ukendt'} · run {stock.get('run_id') or 'ukendt'}.")
    return "\n".join(lines)


def execute_command(
    command: str,
    snapshot: dict[str, Any],
    *,
    request_id: str,
) -> dict[str, Any]:
    intent = classify_intent(command)
    if intent == "investment_brief":
        data = build_investment_brief(snapshot, request_id=request_id)
        message = format_investment_brief(data)
    elif intent == "system_status":
        data = build_system_status(snapshot, request_id=request_id)
        message = (
            f"Investment OS {data.get('app_version')} har status {data.get('status')}. "
            f"Snapshot er {data.get('data_freshness', {}).get('status', 'ukendt')}."
        )
    else:
        ticker = extract_ticker(command)
        data = build_stock_status(snapshot, ticker, request_id=request_id)
        message = format_stock_status(data)
    result = response_metadata(
        request_id=request_id,
        run_id=str(data.get("run_id") or "unavailable"),
        generated_at=datetime.now(timezone.utc),
    )
    result.update({"intent": intent, "message": message, "data": data})
    return result
