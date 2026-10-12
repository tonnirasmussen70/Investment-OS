"""Validated publication of agent intelligence; does not calculate scores."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


def generated_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("generated_at must be an ISO timestamp with timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid generated_at timestamp") from exc
    if result.tzinfo is None:
        raise ValueError("generated_at must include timezone")
    return result


def validate_agent_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Agent JSON must be an object")
    timestamp = generated_time(payload.get("generated_at"))
    if timestamp > datetime.now(timezone.utc):
        raise ValueError("generated_at cannot be in the future")
    if not isinstance(payload.get("methodology_version"), str) or not payload["methodology_version"].strip():
        raise ValueError("methodology_version is required")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    seen = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("Each candidate must be an object")
        for key in ("ticker", "name"):
            if not isinstance(candidate.get(key), str) or not candidate[key].strip():
                raise ValueError(f"Candidate {key} is required")
        ticker = candidate["ticker"].strip().upper().replace(".", "-")
        if ticker in seen:
            raise ValueError(f"Duplicate ticker: {ticker}")
        seen.add(ticker)
        for key in ("agent_score", "agent_confidence", "growth_score", "earnings_score", "momentum_score", "capital_flow_score", "moat_score", "guidance_score", "news_score", "prior_score", "score_change"):
            value = candidate.get(key)
            if value is None and key not in ("agent_score", "agent_confidence"):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{ticker}: invalid {key}")
            low = -100 if key == "score_change" else 0
            if not low <= value <= 100:
                raise ValueError(f"{ticker}: {key} outside allowed range")
        if "is_new" in candidate and not isinstance(candidate["is_new"], bool):
            raise ValueError(f"{ticker}: is_new must be boolean")
        sources = candidate.get("sources", [])
        if not isinstance(sources, list) or any(not isinstance(s, str) or not s.startswith(("https://", "http://")) for s in sources):
            raise ValueError(f"{ticker}: sources must be a list of URLs")
    return payload


def publish_agent(source: Path, target: Path, expected_sha256: str) -> dict:
    """Compare, validate and atomically replace; preserve the submitted payload."""
    raw = source.read_bytes()
    payload = validate_agent_payload(json.loads(raw))
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_suffix(target.suffix + ".lock")
    lock_handle = lock.open("x")
    try:
        temporary = None
        try:
            previous = target.read_bytes() if target.exists() else b""
            if hashlib.sha256(previous).hexdigest() != expected_sha256:
                raise ValueError("Target changed; read it again before publishing")
            if previous:
                old = validate_agent_payload(json.loads(previous))
                if generated_time(payload["generated_at"]) <= generated_time(old["generated_at"]):
                    raise ValueError("Update must be newer than the published agent data")
                if payload["methodology_version"] != old["methodology_version"]:
                    raise ValueError("Methodology change requires a separate reviewed migration")
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            return {"candidate_count": len(payload["candidates"]), "generated_at": payload["generated_at"], "source": str(target), "sha256": hashlib.sha256(raw).hexdigest()}
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    finally:
        lock_handle.close()
        lock.unlink()


