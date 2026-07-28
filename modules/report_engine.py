from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class MarkdownReport:
    """Indhold og metadata for en Markdown-rapport."""

    exists: bool
    content: str
    updated_at: pd.Timestamp | None
    is_empty: bool


def load_markdown_report(
    path: str | Path,
    timezone: str = "Europe/Copenhagen",
) -> MarkdownReport:
    """
    Indlæs en UTF-8 Markdown-fil og returnér indhold samt seneste ændringstid.

    Funktionen fejler ikke, hvis filen mangler. I stedet returneres en tom
    rapport med exists=False, så Streamlit kan vise en kontrolleret besked.
    """
    report_path = Path(path)

    if not report_path.exists():
        return MarkdownReport(
            exists=False,
            content="",
            updated_at=None,
            is_empty=True,
        )

    content = report_path.read_text(encoding="utf-8").strip()

    updated_at = pd.Timestamp(
        report_path.stat().st_mtime,
        unit="s",
        tz="UTC",
    ).tz_convert(timezone)

    return MarkdownReport(
        exists=True,
        content=content,
        updated_at=updated_at,
        is_empty=not bool(content),
    )


def format_report_timestamp(
    updated_at: pd.Timestamp | None,
) -> str:
    """Formatér rapportens tidspunkt til dansk visning."""
    if updated_at is None:
        return "Ikke tilgængelig"

    return updated_at.strftime("%d-%m-%Y kl. %H:%M")
