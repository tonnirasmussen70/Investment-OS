"""Local, read-only MCP stdio adapter for canonical Investment OS snapshots.

Run from the repository root: python -m jarvis.mcp_server

This is deliberately *not* a public HTTP endpoint. The MCP client starts this
process with the same file permissions as the local user. Never expose stdin/
stdout over an untrusted network.
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, TextIO

from api.service import (
    StockNotFoundError,
    build_investment_brief,
    build_portfolio_signals,
    build_portfolio_status,
    build_stock_status,
    build_system_status,
    load_snapshot,
)
from jarvis.operations import build_operational_service_indicators


PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_VERSIONS = {"2025-06-18", "2025-03-26", "2024-11-05"}
MAX_REQUEST_CHARS = 65536
TICKER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.^-]{0,19}$")

_NO_ARGS = {"type": "object", "properties": {}, "additionalProperties": False}
_TICKER_ARGS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Ticker present in the existing IOS snapshot",
            "minLength": 1,
            "maxLength": 20,
            "pattern": TICKER_PATTERN.pattern,
        }
    },
    "required": ["ticker"],
    "additionalProperties": False,
}

TOOLS: tuple[dict[str, Any], ...] = (
    {
        "name": "get_system_status",
        "description": "Read IOS snapshot freshness, application version and warnings.",
        "inputSchema": _NO_ARGS,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_operations_status",
        "description": "Read local Jarvis operational service indicators.",
        "inputSchema": _NO_ARGS,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_portfolio_status",
        "description": "Read canonical portfolio health, confidence and macro/rate risk.",
        "inputSchema": _NO_ARGS,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_portfolio_signals",
        "description": "Read existing IOS decision signals without recomputing them.",
        "inputSchema": _NO_ARGS,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_investment_brief",
        "description": "Read the existing IOS brief, decisions and opportunities.",
        "inputSchema": _NO_ARGS,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "get_stock_status",
        "description": "Read one ticker from positions, opportunities or watchlist.",
        "inputSchema": _TICKER_ARGS,
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
)
TOOL_NAMES = frozenset(tool["name"] for tool in TOOLS)


def _rpc_result(request_id: str | int, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(
    request_id: str | int | None, code: int, message: str
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    result = {
        "content": [
            {"type": "text", "text": json.dumps(payload, ensure_ascii=False, allow_nan=False)}
        ],
        "isError": is_error,
    }
    if not is_error:
        result["structuredContent"] = payload
    return result


class JarvisMCPServer:
    """Single-client stdio MCP session; no network, trade or write capabilities."""

    def __init__(self, snapshot_path: str | Path | None = None) -> None:
        self.snapshot_path = snapshot_path
        self.initialized = False

    def _snapshot(self) -> dict[str, Any]:
        # The caller cannot provide paths via MCP arguments.
        path = self.snapshot_path or os.getenv(
            "INVESTMENT_OS_SNAPSHOT", "data/portfolio_snapshot.json"
        )
        return load_snapshot(path)

    def _invoke(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name not in TOOL_NAMES:
            raise ValueError("Unknown MCP tool")
        if name == "get_stock_status":
            ticker = args.get("ticker")
            if (
                set(args) != {"ticker"}
                or not isinstance(ticker, str)
                or not TICKER_PATTERN.fullmatch(ticker)
            ):
                raise ValueError("Invalid ticker arguments")
        elif args:
            raise ValueError("This MCP tool takes no arguments")

        request_id = str(uuid.uuid4())
        if name == "get_operations_status":
            return build_operational_service_indicators(request_id=request_id)

        snapshot = self._snapshot()
        factories = {
            "get_system_status": build_system_status,
            "get_portfolio_status": build_portfolio_status,
            "get_portfolio_signals": build_portfolio_signals,
            "get_investment_brief": build_investment_brief,
        }
        if name == "get_stock_status":
            return build_stock_status(snapshot, args["ticker"], request_id=request_id)
        return factories[name](snapshot, request_id=request_id)

    def handle(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _rpc_error(None, -32600, "Invalid Request")
        method = message.get("method")
        request_id = message.get("id")
        if (
            not isinstance(method, str)
            or (request_id is not None and (type(request_id) not in (str, int)))
        ):
            return _rpc_error(None, -32600, "Invalid Request")

        # Never reply to notifications; this includes initialized and cancelled.
        if "id" not in message:
            return None
        if method == "ping":
            return _rpc_result(request_id, {})
        if method == "initialize":
            params = message.get("params")
            if not isinstance(params, dict) or not isinstance(
                params.get("protocolVersion"), str
            ):
                return _rpc_error(request_id, -32602, "Invalid initialize parameters")
            version = params["protocolVersion"]
            self.initialized = True
            return _rpc_result(
                request_id,
                {
                    "protocolVersion": (
                        version if version in SUPPORTED_VERSIONS else PROTOCOL_VERSION
                    ),
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "jarvis-ios-readonly", "version": "0.1.0"},
                    "instructions": (
                        "Local read-only snapshot data. Respect freshness warnings; "
                        "the tools cannot trade or change investment decisions."
                    ),
                },
            )
        if not self.initialized:
            return _rpc_error(request_id, -32000, "MCP session is not initialized")
        if method == "tools/list":
            params = message.get("params", {})
            if not isinstance(params, dict) or params.get("cursor") is not None:
                return _rpc_error(request_id, -32602, "Invalid pagination parameters")
            return _rpc_result(request_id, {"tools": list(TOOLS)})
        if method == "tools/call":
            params = message.get("params")
            if not isinstance(params, dict) or not isinstance(params.get("name"), str):
                return _rpc_error(request_id, -32602, "Invalid tool call")
            name = params["name"]
            if name not in TOOL_NAMES:
                return _rpc_error(request_id, -32602, "Unknown tool")
            args = params.get("arguments", {})
            if not isinstance(args, dict):
                return _rpc_error(request_id, -32602, "Invalid tool arguments")
            try:
                payload = self._invoke(name, args)
            except ValueError:
                return _rpc_error(request_id, -32602, "Invalid tool arguments")
            except StockNotFoundError:
                return _rpc_result(
                    request_id, _tool_result({"code": "TICKER_NOT_FOUND"}, is_error=True)
                )
            except RuntimeError:
                return _rpc_result(
                    request_id,
                    _tool_result({"code": "SNAPSHOT_UNAVAILABLE"}, is_error=True),
                )
            except Exception:
                # Do not leak filesystem paths, holdings or credentials on errors.
                return _rpc_result(
                    request_id,
                    _tool_result({"code": "TOOL_UNAVAILABLE"}, is_error=True),
                )
            return _rpc_result(request_id, _tool_result(payload))
        return _rpc_error(request_id, -32601, "Method not found")


def serve(
    in_stream: TextIO | None = None, out_stream: TextIO | None = None
) -> None:
    """Process newline-delimited JSON-RPC with stdout reserved for protocol data."""
    source = in_stream if in_stream is not None else sys.stdin
    sink = out_stream if out_stream is not None else sys.stdout
    server = JarvisMCPServer()
    for raw in source:
        if len(raw) > MAX_REQUEST_CHARS:
            answer = _rpc_error(None, -32600, "Request too large")
        else:
            try:
                message = json.loads(raw)
            except (ValueError, UnicodeError):
                answer = _rpc_error(None, -32700, "Parse error")
            else:
                answer = server.handle(message)
        if answer is not None:
            sink.write(json.dumps(answer, ensure_ascii=False, allow_nan=False) + "\n")
            sink.flush()


if __name__ == "__main__":
    serve()
