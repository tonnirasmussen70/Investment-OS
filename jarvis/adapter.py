from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable

from api.contracts import response_metadata
from api.service import (
    build_investment_brief,
    build_portfolio_signals,
    build_stock_status,
    build_system_status,
)
from research.provider import (
    ResearchUnavailableError,
    get_stock_research,
    unavailable_research,
)


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
    if any("signal" in word for word in normalized.split()):
        return "portfolio_signals"
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


def _compact_amount(value: Any, currency: str | None = None) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"
    suffix = ""
    if abs(number) >= 1_000_000_000:
        number /= 1_000_000_000
        suffix = " mia."
    elif abs(number) >= 1_000_000:
        number /= 1_000_000
        suffix = " mio."
    rendered = f"{number:.1f}".replace(".", ",")
    return f"{rendered}{suffix}{' ' + currency if currency else ''}"


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
    """Format OS status first and label optional external research separately."""
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
    research = stock.get("research")
    if research and research.get("status") in {"available", "partial"}:
        source = research.get("source") or {}
        market = research.get("market") or {}
        valuation = research.get("valuation") or {}
        growth = research.get("growth") or {}
        profitability = research.get("profitability") or {}
        currency = market.get("currency")
        lines.append(
            f"Ekstern research ({source.get('provider') or 'ukendt kilde'} via "
            f"{source.get('adapter') or 'ukendt adapter'}, hentet "
            f"{research.get('as_of') or 'ukendt'}): "
            f"kurs {_number(market.get('current_price'))} {currency or ''}, "
            f"markedsværdi {_compact_amount(market.get('market_cap'), currency)}."
        )
        metrics = []
        if valuation.get("forward_pe") is not None:
            metrics.append(f"forward P/E {_number(valuation.get('forward_pe'))}")
        if valuation.get("enterprise_to_ebitda") is not None:
            metrics.append(f"EV/EBITDA {_number(valuation.get('enterprise_to_ebitda'))}")
        if growth.get("revenue_growth") is not None:
            metrics.append(f"omsætningsvækst {_percent(growth.get('revenue_growth'))}")
        if profitability.get("operating_margin") is not None:
            metrics.append(f"driftsmargin {_percent(profitability.get('operating_margin'))}")
        if metrics:
            lines.append("Fundamentale datapunkter: " + ", ".join(metrics) + ".")
        quality = research.get("data_quality") or {}
        freshness = research.get("freshness") or {}
        if freshness.get("status") == "stale":
            lines.append(
                "Researchsnapshot'et er cachet og markeret stale, fordi kilden "
                "ikke kunne opdateres."
            )
        lines.append(
            f"Research-datakvalitet {quality.get('status') or 'ukendt'} "
            f"({_percent(quality.get('coverage'))} feltdækning). "
            "Dataene er kontekst og ændrer ikke Investment OS' Decision Score eller handling."
        )
    elif research and research.get("status") == "unavailable":
        warning_items = research.get("warnings") or []
        reason = next(
            (
                item.get("message")
                for item in warning_items
                if item.get("code") == "RESEARCH_UNAVAILABLE"
            ),
            "Researchkilden er midlertidigt utilgængelig.",
        )
        lines.append(f"Ekstern fundamental research er ikke tilgængelig: {reason}")
        lines.append("Investment OS-dataene ovenfor er uændrede af researchfejlen.")
    else:
        lines.append(
            "Analysen omfatter kun eksisterende Investment OS-data og indeholder "
            "ikke ny fundamental research."
        )
    lines.append(f"Data pr. {stock.get('as_of') or 'ukendt'} · run {stock.get('run_id') or 'ukendt'}.")
    return "\n".join(lines)


def format_portfolio_signals(payload: dict[str, Any]) -> str:
    """Explain canonical signal outputs without creating a recommendation."""
    summary = payload.get("summary") or {}
    readiness = payload.get("decision_readiness") or {}
    handling_counts = summary.get("handling_counts") or {}
    signal_count = int(summary.get("signal_count") or 0)
    rendered_counts = [
        f"{handling} {int(count)}"
        for handling in ("Øg", "Reducer", "Hold", "Afvent", "Ukendt")
        if (count := handling_counts.get(handling))
    ]
    lines = [
        f"Investment OS har {signal_count} autoritative positionssignaler"
        + (": " + ", ".join(rendered_counts) if rendered_counts else "")
        + "."
    ]
    readiness_status = readiness.get("status") or "ukendt"
    if readiness_status == "insufficient":
        codes = ", ".join(readiness.get("blocking_warning_codes") or [])
        lines.append(
            "Beslutningsgrundlaget er utilstrækkeligt og bør ikke bruges til handling"
            + (f" ({codes})" if codes else "")
            + "."
        )
    elif readiness_status == "limited":
        lines.append(
            "Beslutningsfelterne er tilgængelige, men forklaringsgrundlaget er "
            "begrænset af manglende faktorscorer."
        )
    else:
        lines.append("Beslutningsgrundlaget er markeret klar.")

    queue = payload.get("decision_queue") or []
    if queue:
        items = [
            f"{item.get('Aktiv') or 'Ukendt'}: {item.get('Handling') or 'Ukendt'}"
            for item in queue[:3]
        ]
        lines.append("Aktuel Decision Queue: " + "; ".join(items) + ".")
    else:
        lines.append("Aktuel Decision Queue er tom.")
    lines.append(
        "Jarvis viser uændrede snapshotfelter; API'et beregner eller ændrer ingen signaler."
    )
    lines.append(
        f"Data pr. {payload.get('as_of') or 'ukendt'} · run "
        f"{payload.get('run_id') or 'ukendt'}."
    )
    return "\n".join(lines)


def execute_command(
    command: str,
    snapshot: dict[str, Any],
    *,
    request_id: str,
    research_loader: Callable[[str], dict[str, Any]] | None = get_stock_research,
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
    elif intent == "portfolio_signals":
        data = build_portfolio_signals(snapshot, request_id=request_id)
        message = format_portfolio_signals(data)
    else:
        ticker = extract_ticker(command)
        data = build_stock_status(snapshot, ticker, request_id=request_id)
        if research_loader is not None:
            try:
                data["research"] = research_loader(ticker)
            except ResearchUnavailableError as exc:
                data["research"] = unavailable_research(ticker, str(exc))
        message = format_stock_status(data)
    result = response_metadata(
        request_id=request_id,
        run_id=str(data.get("run_id") or "unavailable"),
        generated_at=datetime.now(timezone.utc),
    )
    result.update({"intent": intent, "message": message, "data": data})
    return result
