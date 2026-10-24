"""Contract, read-only, security and stdio transport tests for Jarvis MCP v0.1."""

from __future__ import annotations

import copy
import io
import json
import unittest
from unittest.mock import patch

from jarvis.mcp_server import (
    JarvisMCPServer,
    MAX_REQUEST_CHARS,
    TOOL_NAMES,
    serve,
)
from tests.test_jarvis_api import fixture_snapshot


def request(method: str, *, request_id: int = 1, params: dict | None = None) -> dict:
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def initialized_server() -> JarvisMCPServer:
    server = JarvisMCPServer()
    response = server.handle(
        request("initialize", params={"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})
    )
    assert response["result"]["capabilities"]["tools"] == {"listChanged": False}
    return server


class JarvisMCPTests(unittest.TestCase):
    def test_requires_initialize_and_negotiates_protocol(self) -> None:
        server = JarvisMCPServer()
        self.assertEqual(server.handle(request("tools/list"))["error"]["code"], -32000)
        self.assertEqual(
            server.handle(request("initialize", params={"protocolVersion": 42}))["error"]["code"],
            -32602,
        )
        result = server.handle(
            request("initialize", params={"protocolVersion": "2099-01-01"})
        )["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["serverInfo"]["version"], "0.1.0")

    def test_only_read_only_tools_are_advertised(self) -> None:
        tools = initialized_server().handle(request("tools/list"))["result"]["tools"]
        self.assertEqual({item["name"] for item in tools}, TOOL_NAMES)
        self.assertEqual(len(tools), 6)
        for tool in tools:
            self.assertTrue(tool["annotations"]["readOnlyHint"])
            self.assertFalse(tool["annotations"]["openWorldHint"])
            self.assertFalse(tool["inputSchema"]["additionalProperties"])

    def test_projects_existing_snapshot_without_mutating_it(self) -> None:
        snapshot = fixture_snapshot()
        before = copy.deepcopy(snapshot)
        server = initialized_server()
        with patch("jarvis.mcp_server.load_snapshot", return_value=snapshot) as loader:
            for tool_name in (
                "get_system_status",
                "get_portfolio_status",
                "get_portfolio_signals",
                "get_investment_brief",
            ):
                result = server.handle(
                    request("tools/call", params={"name": tool_name, "arguments": {}})
                )["result"]
                self.assertFalse(result["isError"])
                self.assertEqual(
                    json.loads(result["content"][0]["text"]), result["structuredContent"]
                )
                self.assertEqual(result["structuredContent"]["run_id"], "ios-test-run")
            self.assertEqual(loader.call_count, 4)
        self.assertEqual(snapshot, before)

    def test_portfolio_signals_are_authoritative_not_recomputed(self) -> None:
        snapshot = fixture_snapshot()
        server = initialized_server()
        with patch("jarvis.mcp_server.load_snapshot", return_value=snapshot):
            result = server.handle(
                request("tools/call", params={"name": "get_portfolio_signals"})
            )["result"]["structuredContent"]
        self.assertEqual(result["signals"][0]["decision"]["score"], 84.0)
        self.assertEqual(result["signals"][0]["decision"]["handling"], "Øg")

    def test_stock_status_only_uses_existing_ticker(self) -> None:
        server = initialized_server()
        with patch("jarvis.mcp_server.load_snapshot", return_value=fixture_snapshot()):
            good = server.handle(
                request(
                    "tools/call",
                    params={"name": "get_stock_status", "arguments": {"ticker": "FRO"}},
                )
            )["result"]
            self.assertEqual(good["structuredContent"]["identity"]["ticker"], "FRO")
            missing = server.handle(
                request(
                    "tools/call",
                    params={"name": "get_stock_status", "arguments": {"ticker": "MISSING"}},
                )
            )["result"]
            self.assertTrue(missing["isError"])
            self.assertIn("TICKER_NOT_FOUND", missing["content"][0]["text"])

    def test_rejects_paths_extra_args_and_unknown_tools_without_loading_data(self) -> None:
        server = initialized_server()
        cases = [
            {"name": "get_portfolio_status", "arguments": {"path": "/etc/passwd"}},
            {"name": "get_stock_status", "arguments": {"ticker": "../../secrets"}},
            {"name": "get_stock_status", "arguments": {"ticker": "FRO", "extra": "x"}},
            {"name": "get_stock_status", "arguments": {"ticker": 7}},
            {"name": "execute_trade", "arguments": {"ticker": "FRO"}},
            {"name": "get_portfolio_status", "arguments": ["x"]},
        ]
        with patch("jarvis.mcp_server.load_snapshot") as loader:
            for params in cases:
                response = server.handle(request("tools/call", params=params))
                self.assertEqual(response["error"]["code"], -32602)
            loader.assert_not_called()

    def test_snapshot_failure_is_sanitized(self) -> None:
        server = initialized_server()
        with patch(
            "jarvis.mcp_server.load_snapshot",
            side_effect=RuntimeError("secret path /home/private.json"),
        ):
            response = server.handle(
                request("tools/call", params={"name": "get_portfolio_status"})
            )["result"]
        self.assertTrue(response["isError"])
        self.assertIn("SNAPSHOT_UNAVAILABLE", response["content"][0]["text"])
        self.assertNotIn("secret path", str(response))

    def test_notifications_are_silent_and_methods_are_allowlisted(self) -> None:
        server = initialized_server()
        self.assertIsNone(
            server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        )
        self.assertEqual(server.handle(request("resources/list"))["error"]["code"], -32601)
        self.assertEqual(server.handle(request("ping"))["result"], {})

    def test_stdio_is_newline_json_rpc_only(self) -> None:
        source = io.StringIO(
            "not-json\n"
            + json.dumps(
                request("initialize", params={"protocolVersion": "2025-06-18"})
            )
            + "\n"
            + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
            + "\n"
            + json.dumps(request("tools/list", request_id=2))
            + "\n"
        )
        output = io.StringIO()
        serve(source, output)
        messages = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["error"]["code"], -32700)
        self.assertEqual(messages[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(len(messages[2]["result"]["tools"]), 6)

    def test_oversized_request_is_rejected_before_parsing(self) -> None:
        source = io.StringIO(" " * (MAX_REQUEST_CHARS + 1) + "\n")
        output = io.StringIO()
        serve(source, output)
        self.assertEqual(
            json.loads(output.getvalue())["error"]["message"], "Request too large"
        )


if __name__ == "__main__":
    unittest.main()
