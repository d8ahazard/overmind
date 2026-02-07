# OverMind Roadmap (Phases 1–4)

## Phase 1: Autonomy Engine + Core Boundaries
- Job state machine with persistent steps and events.
- Tool broker with policy mediation and audit logging.
- Verifier framework and retry loop.
- Baseline audit logs stored in DB.

## Phase 2: Integration Stubs
- MCP tool schema normalization with risk metadata.
- Connector interfaces for Git, issue tracker, notifications.
- No-op implementations to be replaced by real connectors.

## Phase 3: Security Boundaries
- Policy engine with scope/risk/approval checks.
- Secrets broker for capability tokens.
- Mediated shell execution with approvals.

## Phase 4: Virtual Office Maturity
- Multi-job coordination with SLA timers.
- Approval UI endpoints with diff/context.
- Cross-agent coordination and reporting.

## Team Commands
- `@break`: pauses all agent work for the active run.
- `@attention`: pauses work and calls a team meeting.
- `@resume`: resumes work (any stakeholder message also resumes).