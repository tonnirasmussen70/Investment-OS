from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from api.contracts import response_metadata
from api.service import build_investment_brief, build_system_status


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
        raise JarvisCommandError(
            "INTENT_NOT_IMPLEMENTED",
            "Aktieanalyse er genkendt, men bliver implementeret i en senere sprint.",
            status_code=501,
        )
    result = response_metadata(
        request_id=request_id,
        run_id=str(data.get("run_id") or "unavailable"),
        generated_at=datetime.now(timezone.utc),
    )
    result.update({"intent": intent, "message": message, "data": data})
    return result
