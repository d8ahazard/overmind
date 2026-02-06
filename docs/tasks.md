# Concrete Task List (Issues)

## Phase 1
- Persist job state and steps (Job, JobStep, JobEvent).
- Orchestrator uses JobEngine loop with retries.
- ToolBroker mediates all tool execution.
- Verifier framework integration.
- Audit logging for tool requests/results.

## Phase 2
- Normalize MCP tool metadata (risk/scopes).
- Add connector interfaces and no-op adapters.

## Phase 3
- Policy engine enforcing scopes/risk/approvals.
- Secrets broker capability tokens.
- Sandboxed shell execution via ToolBroker.

## Phase 4
- Multi-job scheduler with SLA timers.
- Approval endpoints and UI wiring.
- Cross-agent handoffs and reporting.
