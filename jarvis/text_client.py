"""Snapshot-only entry point shared by the text UI and a future voice client."""
from __future__ import annotations

import os
import uuid

from api.service import load_snapshot
from jarvis.adapter import JarvisCommandError, execute_command

MAX_QUESTION_LENGTH = 500


def answer_question(question: str) -> dict:
    """Read one snapshot per question. Never fetch external research or write data."""
    if not isinstance(question, str) or not question.strip():
        raise JarvisCommandError("COMMAND_MISSING", "Skriv et spørgsmål.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise JarvisCommandError("COMMAND_TOO_LONG", "Spørgsmålet må højst være 500 tegn.")
    snapshot = load_snapshot(os.getenv("INVESTMENT_OS_SNAPSHOT", "data/portfolio_snapshot.json"))
    return execute_command(
        question.strip(), snapshot,
        request_id=str(uuid.uuid4()), research_loader=None,
    )
