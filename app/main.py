from pathlib import Path
import os

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
from app.db.models import AgentConfig, Project, Team
from app.db.session import get_session, init_db
from sqlmodel import select
from app.core.orchestrator import Orchestrator
from app.core.manager_loop import ManagerLoop
from app.core.worker_loop import WorkerLoop
from app.core.artifacts import ArtifactStore
from app.agents.runtime import AgentRuntime
from app.providers.model_registry import ModelRegistry
from app.integrations.mcp_client import MCPRegistry


def create_app() -> FastAPI:
    settings = load_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    registry = ProjectRegistry(settings.data_dir)
    if settings.allow_self_project and os.getenv("AI_DEVTEAM_SELF_ACTIVE", "").lower() == "true":
        registry.set_active(0)
    active_id = registry.get_active_id()
    if active_id == 0 and settings.allow_self_project:
        active_root = settings.repo_root
        data_dir = project_data_dir(active_root)
        data_dir.mkdir(parents=True, exist_ok=True)
        init_db(project_db_url(active_root))
        with get_session() as session:
            existing = session.get(Project, 0)
            if not existing:
                session.add(
                    Project(
                        id=0,
                        name="Self",
                        repo_local_path=str(active_root),
                    )
                )
                session.commit()
            _ensure_manager_identity(session, 0)
    else:
        active = registry.get_active()
        if active is None:
            active = registry.add_project("Default Project", str(settings.default_project_root))
            registry.set_active(active.id)
        active_root = Path(active.repo_local_path)
        data_dir = project_data_dir(active_root)
        data_dir.mkdir(parents=True, exist_ok=True)
        init_db(project_db_url(active_root))
        with get_session() as session:
            _ensure_manager_identity(session, active.id)

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
    app.state.active_project_id = 0 if active_id == 0 and settings.allow_self_project else active.id
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
    app.state.orchestrator.agent_runtime.event_bus = app.state.event_bus
    app.state.orchestrator.agent_runtime.event_writer = (
        lambda run_id, event: ArtifactStore(app.state.data_dir).write_event(run_id, event)
    )
    app.state.manager_loop = ManagerLoop(
        app.state.event_bus,
        lambda: app.state.active_project_id,
        app.state.orchestrator.agent_runtime,
        app.state.tool_broker,
        ArtifactStore(app.state.data_dir),
    )
    app.state.worker_loop = WorkerLoop(
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
        app.state.worker_loop.start()

    return app


def _ensure_manager_identity(session, project_id: int) -> None:
    teams = list(session.exec(select(Team).where(Team.project_id == project_id)))
    for team in teams:
        agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team.id)))
        if not agents:
            continue
        manager = None
        for agent in agents:
            if (agent.display_name or "").lower() == "ava":
                manager = agent
                break
        if not manager:
            for role in ("Product Owner", "Delivery Manager", "Release Manager"):
                for agent in agents:
                    if agent.role == role:
                        manager = agent
                        break
                if manager:
                    break
        if manager:
            manager.display_name = "Ava"
            manager.gender = "female"
            manager.pronouns = "she/her"
            session.add(manager)
    session.commit()


app = create_app()
