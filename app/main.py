from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import artifacts, models, projects, runs, tasks, teams
from app.api.routes import agents, approvals, avatars, budgets, chat, events, keys, mcp, memories, personalities, providers, repo, seed, system
from app.api.ws import router as ws_router
from app.config import load_settings
from app.core.approvals import ApprovalStore
from app.core.audit import AuditLogger
from app.core.events import EventBus
from app.core.job_engine import JobEngine
from app.core.policy import PolicyEngine
from app.core.secrets import SecretsBroker
from app.core.tool_broker import ToolBroker
from app.core.verification import NoopVerifier
from app.core.project_registry import ProjectRegistry, project_data_dir, project_db_url
from app.db.session import init_db
from app.core.orchestrator import Orchestrator
from app.core.manager_loop import ManagerLoop
from app.core.artifacts import ArtifactStore
from app.agents.runtime import AgentRuntime
from app.providers.model_registry import ModelRegistry
from app.integrations.mcp_client import MCPRegistry


def create_app() -> FastAPI:
    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    registry = ProjectRegistry(settings.data_dir)
    active = registry.get_active()
    if active is None:
        active = registry.add_project("Default Project", str(settings.default_project_root))
        registry.set_active(active.id)

    active_root = Path(active.repo_local_path)
    data_dir = project_data_dir(active_root)
    data_dir.mkdir(parents=True, exist_ok=True)
    init_db(project_db_url(active_root))

    app = FastAPI(title="Overmind Orchestrator")
    app.state.settings = settings
    app.state.event_bus = EventBus()
    app.state.mcp_registry = MCPRegistry(settings.mcp_endpoints, settings.mcp_discovery_ports)
    app.state.policy_engine = PolicyEngine()
    app.state.audit_logger = AuditLogger()
    app.state.approval_store = ApprovalStore()
    app.state.tool_broker = ToolBroker(
        app.state.policy_engine,
        app.state.audit_logger,
        app.state.approval_store,
        app.state.event_bus,
        lambda run_id, event: ArtifactStore(app.state.data_dir).write_event(run_id, event),
    )
    app.state.job_engine = JobEngine(app.state.event_bus)
    app.state.verifier = NoopVerifier()
    app.state.secrets_broker = SecretsBroker(settings.encryption_key)
    app.state.project_registry = registry
    app.state.active_project_id = active.id
    app.state.active_project_root = active_root
    app.state.data_dir = data_dir
    app.state.orchestrator = Orchestrator(
        app.state.event_bus,
        ArtifactStore(app.state.data_dir),
        AgentRuntime(
            ModelRegistry(app.state.secrets_broker),
            app.state.mcp_registry,
            app.state.secrets_broker,
        ),
        app.state.active_project_root,
        app.state.job_engine,
        app.state.verifier,
    )
    app.state.manager_loop = ManagerLoop(
        app.state.event_bus,
        lambda: app.state.active_project_id,
        app.state.orchestrator.agent_runtime,
        app.state.tool_broker,
        ArtifactStore(app.state.data_dir),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router, prefix="/projects", tags=["projects"])
    app.include_router(teams.router, prefix="/teams", tags=["teams"])
    app.include_router(runs.router, prefix="/runs", tags=["runs"])
    app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
    app.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
    app.include_router(events.router, prefix="/events", tags=["events"])
    app.include_router(models.router, prefix="/models", tags=["models"])
    app.include_router(agents.router, prefix="/agents", tags=["agents"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(seed.router, prefix="/seed", tags=["seed"])
    app.include_router(mcp.router, prefix="/mcp", tags=["mcp"])
    app.include_router(memories.router, prefix="/memories", tags=["memories"])
    app.include_router(personalities.router, prefix="/personalities", tags=["personalities"])
    app.include_router(keys.router, prefix="/keys", tags=["keys"])
    app.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
    app.include_router(providers.router, prefix="/providers", tags=["providers"])
    app.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
    app.include_router(avatars.router, prefix="/avatars", tags=["avatars"])
    app.include_router(repo.router, prefix="/repo", tags=["repo"])
    app.include_router(system.router, prefix="/system", tags=["system"])
    app.include_router(ws_router, prefix="/ws", tags=["ws"])

    ui_root = Path(__file__).resolve().parents[1] / "ui"
    ui_dist = ui_root / "dist"
    if ui_dist.exists():
        app.mount("/assets", StaticFiles(directory=ui_dist / "assets"), name="assets")

        @app.get("/")
        def ui_index() -> FileResponse:
            return FileResponse(ui_dist / "index.html")

        public_dir = ui_root / "public"
        if public_dir.exists():
            app.mount("/public", StaticFiles(directory=public_dir), name="public")

    @app.on_event("startup")
    async def _start_manager_loop() -> None:
        app.state.manager_loop.start()

    return app


app = create_app()
