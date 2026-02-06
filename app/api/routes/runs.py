from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlmodel import select

from app.agents.runtime import AgentRuntime
from app.core.artifacts import ArtifactStore
from app.core.events import Event
from app.core.orchestrator import Orchestrator
from app.db.models import Run
from app.db.session import get_session
from app.providers.model_registry import ModelRegistry

router = APIRouter()


def _get_orchestrator(request: Request) -> Orchestrator:
    settings = request.app.state.settings
    event_bus = request.app.state.event_bus
    mcp_registry = request.app.state.mcp_registry
    registry = ModelRegistry()
    runtime = AgentRuntime(registry, mcp_registry)
    artifacts = ArtifactStore(request.app.state.data_dir)
    return Orchestrator(event_bus, artifacts, runtime, request.app.state.active_project_root)


@router.post("/", response_model=Run)
def create_run(run: Run, request: Request) -> Run:
    if not run.project_id:
        run.project_id = request.app.state.active_project_id
    with get_session() as session:
        session.add(run)
        session.commit()
        session.refresh(run)
        return run


@router.get("/", response_model=List[Run])
def list_runs() -> List[Run]:
    with get_session() as session:
        return list(session.exec(select(Run)))


@router.get("/{run_id}", response_model=Run)
def get_run(run_id: int) -> Run:
    with get_session() as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run


@router.post("/{run_id}/start")
async def start_run(run_id: int, background: BackgroundTasks, request: Request) -> dict:
    orchestrator = _get_orchestrator(request)
    mcp_registry = request.app.state.mcp_registry
    endpoints = await mcp_registry.refresh()
    event_bus = request.app.state.event_bus
    await event_bus.publish(
        Event(
            type="mcp.discovered",
            payload={
                "endpoints": [
                    {"url": endpoint.url, "tools": [t.__dict__ for t in endpoint.tools]}
                    for endpoint in endpoints
                ]
            },
        )
    )
    background.add_task(orchestrator.start_run, run_id)
    return {"status": "started", "run_id": run_id}
