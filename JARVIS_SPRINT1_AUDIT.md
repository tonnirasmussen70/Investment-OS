# Sprint 1 source audit — Investment-OS main

Reviewed on **2026-10-24**, main SHA
`bb7c2c6394357fe53ad0cea6ce950529f68f6382`.
This is a source review, not a runtime or production attestation.

## Verified main-branch components

- `README.md` identifies Investment OS version **7.3.3**.
- `api/app.py` exposes Starlette HTTP endpoints for system, portfolio,
  signals, brief, stock status, research and constrained Danish commands.
- `api/service.py` reads `data/portfolio_snapshot.json`; signal endpoints
  project canonical Decision Engine values without recomputing them.
- `api/security.py` enforces production bearer tokens and positive rate
  limit, and development localhost access, for `/v1/` HTTP routes.
- `api/readiness.py` checks security configuration, snapshot and audit sink.
- `jarvis/audit.py` and `jarvis/operations.py` implement audit retention and
  operational reporting.
- `deploy/windows/` contains local Windows scheduled-task deployment.
- `.github/workflows/investment-os-quality-gate.yml` runs Python 3.12,
  compileall and pytest on pull requests and pushes to main.
- `tests/` includes existing Jarvis API, security, audit and readiness tests.
- `data/portfolio_snapshot.json` is available with positions and risk fields;
  observed generated time **2026-10-24T08:23:51+02:00** and **29 positions**.
- No MCP server existed on inspected main tree.
- No open pull requests were returned at audit time.

## Findings and control measures

| Severity | Finding | Sprint 1 treatment |
| --- | --- | --- |
| High | GitHub reported `main` is unprotected | Separate development branch; review PR before merge |
| High | Repo is public and contains portfolio workbook/snapshot | Flag data exposure to owner; do not alter repository visibility |
| High | HTTP bearer security does not protect new stdio transport | Local process only, with no network listener |
| Medium | Existing HTTP API has no MCP initialization/discovery | Implement read-only MCP adapter reusing projections |
| Medium | Data freshness/version mismatch is possible | Preserve existing warning and readiness indicators |
| Medium | Initial full suite result was not available | Add MCP tests, run CI via PR, record actual result |
| Medium | MCP calls do not generate persistent Jarvis HTTP audit events | Document limitation explicitly |
| Low | Some Python dependencies have broad version bounds | Keep scope limited; improve dependency pinning separately |

## Sprint 1 acceptance

- [x] Audit main source and identify security boundaries.
- [x] Add read-only MCP adapter in dedicated feature branch.
- [x] Add tests for protocol and denial/error cases.
- [x] Document local setup and limits.
- [ ] Review and confirm PR CI is passing.
- [ ] Human approval before merge.

No trading, portfolio mutation, agent orchestration, Home Assistant changes or
Sprint 2–3 work is included.
