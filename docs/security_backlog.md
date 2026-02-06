# Security Hardening Backlog (Prioritized)

## High
- Enforce allowlisted command sets in `system.run` with per-project policy.
- Add approval workflow persistence (who approved, why, timestamp).
- Encrypt audit log payload fields at rest.
- Implement network egress allowlist for tool execution.

## Medium
- Replace provider env keys with secrets broker integration.
- Add runtime prompt-injection filters on tool requests.
- Add tool manifest validation and static checks for MCP tools.

## Low
- Add WORM storage support for audit logs.
- Add periodic token rotation for secrets broker cache.
