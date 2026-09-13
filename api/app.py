from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from api.contracts import response_metadata
from api.service import (
    build_investment_brief,
    build_portfolio_status,
    build_system_status,
    load_snapshot,
)
from jarvis.adapter import JarvisCommandError, execute_command


def _snapshot_path() -> str:
    return os.getenv("INVESTMENT_OS_SNAPSHOT", "data/portfolio_snapshot.json")


def _unavailable_payload(request: Request, exc: RuntimeError) -> dict:
    payload = response_metadata(
        request_id=request.headers.get("x-request-id") or str(uuid.uuid4()),
        run_id="unavailable",
        generated_at=datetime.now(timezone.utc),
    )
    payload.update(
        {
            "status": "unavailable",
            "error": {"code": "SNAPSHOT_UNAVAILABLE", "message": str(exc)},
            "warnings": [],
        }
    )
    return payload


async def system_status(request: Request) -> JSONResponse:
    try:
        payload = build_system_status(
            load_snapshot(_snapshot_path()),
            request_id=request.headers.get("x-request-id"),
        )
    except RuntimeError as exc:
        return JSONResponse(_unavailable_payload(request, exc), status_code=503)
    return JSONResponse(payload)


async def portfolio_status(request: Request) -> JSONResponse:
    try:
        payload = build_portfolio_status(
            load_snapshot(_snapshot_path()),
            request_id=request.headers.get("x-request-id"),
        )
    except RuntimeError as exc:
        return JSONResponse(_unavailable_payload(request, exc), status_code=503)
    return JSONResponse(payload)


async def investment_brief(request: Request) -> JSONResponse:
    try:
        payload = build_investment_brief(
            load_snapshot(_snapshot_path()),
            request_id=request.headers.get("x-request-id"),
        )
    except RuntimeError as exc:
        return JSONResponse(_unavailable_payload(request, exc), status_code=503)
    return JSONResponse(payload)


async def jarvis_command(request: Request) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise JarvisCommandError("INVALID_REQUEST", "JSON-body skal være et objekt.")
        payload = execute_command(
            str(body.get("command") or ""),
            load_snapshot(_snapshot_path()),
            request_id=request_id,
        )
    except JarvisCommandError as exc:
        payload = response_metadata(
            request_id=request_id,
            run_id="unavailable",
            generated_at=datetime.now(timezone.utc),
        )
        payload.update(
            {
                "status": "rejected",
                "error": {"code": exc.code, "message": str(exc)},
                "warnings": [],
            }
        )
        return JSONResponse(payload, status_code=exc.status_code)
    except (RuntimeError, ValueError) as exc:
        return JSONResponse(_unavailable_payload(request, RuntimeError(str(exc))), status_code=503)
    return JSONResponse(payload)


app = Starlette(
    debug=False,
    routes=[
        Route("/v1/system/status", system_status, methods=["GET"]),
        Route("/v1/portfolio/status", portfolio_status, methods=["GET"]),
        Route("/v1/briefs/investment", investment_brief, methods=["GET"]),
        Route("/v1/jarvis/command", jarvis_command, methods=["POST"]),
    ],
)
