# Jarvis MCP v0.1 — local read-only transport

**Scope:** Sprint 1 only. No trading, automated agents, Home Assistant or remote MCP endpoint.

## Implemented

The adapter at `jarvis/mcp_server.py` implements MCP over newline-delimited
JSON-RPC **stdio**. It reuses Investment OS snapshot projection functions in
`api/service.py`, without recalculating signals or writing portfolio files.

| Tool | Source | Arguments |
| --- | --- | --- |
| `get_system_status` | `build_system_status` | none |
| `get_operations_status` | `build_operational_service_indicators` | none |
| `get_portfolio_status` | `build_portfolio_status` | none |
| `get_portfolio_signals` | `build_portfolio_signals` | none |
| `get_investment_brief` | `build_investment_brief` | none |
| `get_stock_status` | `build_stock_status` | `ticker` (existing IOS ticker) |

The snapshot comes from `data/portfolio_snapshot.json` or the operator's
`INVESTMENT_OS_SNAPSHOT` environment variable. MCP clients cannot choose
arbitrary file paths. Protocol versions: `2025-06-18`, `2025-03-26`,
`2024-11-05`. Methods are allowlisted; invalid requests, unknown tools,
extra arguments and invalid tickers are rejected. Tool errors are sanitized.
Only JSON-RPC messages may be written to stdout.

## Local setup

Run from repository root with Python 3.12:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_jarvis_mcp.py
python -m jarvis.mcp_server
```

Configure a compatible **local** MCP client to start the Python interpreter
with arguments `-m jarvis.mcp_server`, working directory set to the repository
root. Optionally set `INVESTMENT_OS_SNAPSHOT` to an absolute snapshot path.

Example one-line JSON-RPC requests in order:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test-client","version":"1"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_portfolio_status","arguments":{}}}
```

## Security boundary and known limitations

1. **Local only:** Stdio opens no HTTP listener and runs with the file-system
   permissions of the launching OS account. Trust the client and protect
   the local portfolio snapshot. Never proxy stdin/stdout to the internet.
2. **No HTTP authentication on stdio:** `JarvisSecurityMiddleware` protects
   the existing HTTP API, not this child process. Remote authenticated
   HTTPS/Streamable HTTP MCP is NOT part of this milestone.
3. **No MCP-specific audit-log writes:** Existing HTTP audit and operations
   data may be read, but stdio tool calls are not added to HTTP audit logs.
   Use local client logging if required.
4. **Privacy:** Tool results can contain actual holdings. Connect only
   trusted MCP clients; do not publish the raw results.
5. **Freshness:** Stale snapshots return existing freshness warnings.
   No refresh, computation, trade or write is triggered.
6. **Not an online ChatGPT connector:** Stdio cannot simply be used as a
   public ChatGPT MCP URL. Remote integration requires separate authorization,
   deployment, transport and security work.

## Quality gate

```bash
python -m compileall -q api jarvis modules research scripts tests app.py
PYTHONPATH=. python -m pytest -q
```

The existing `investment-os-quality-gate.yml` runs these checks on PRs.
New `tests/test_jarvis_mcp.py` covers handshake, discovery, canonical
projections, rejected calls, errors and stdio framing.

**Merge:** PR review is required; do not merge automatically.
**Deferred:** Sprint 2–3 wait for Home Assistant installation and new approval.
