# Minimal Happy-Path Demo Scenario

1) Create a project and team via API.
2) Add agents (PM + Dev) with model providers set.
3) Create a run with a simple goal (e.g., “add a README note”).
4) Start the run:
   - JobEngine steps through scoping → planning → executing → verifying.
   - AgentRuntime produces responses and artifacts.
   - If a high-risk tool is requested, create an approval and pass `approval_id`.
5) Review:
   - Events and chats stored in `runs/<id>/` artifacts.
   - Audit logs include tool requests and results.

Expected outputs:
- Run status transitions in DB.
- Artifact snapshots for chat and events.
- Verification step records success.
