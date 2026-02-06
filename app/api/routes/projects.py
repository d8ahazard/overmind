from typing import List

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from pathlib import Path

from app.core.project_registry import project_data_dir, project_db_url
from app.db.models import Project
from app.db.session import get_session, init_db

router = APIRouter()


@router.post("/")
def create_project(payload: dict, request: Request) -> dict:
    registry = request.app.state.project_registry
    name = payload.get("name")
    repo_local_path = payload.get("repo_local_path")
    team_framework = payload.get("team_framework")
    if not name or not repo_local_path:
        raise HTTPException(status_code=400, detail="name and repo_local_path are required")
    entry = registry.add_project(name, repo_local_path)
    with get_session() as session:
        project = Project(
            id=entry.id,
            name=entry.name,
            repo_local_path=entry.repo_local_path,
            team_framework=team_framework,
        )
        session.add(project)
        session.commit()
    return {
        "id": entry.id,
        "name": entry.name,
        "repo_local_path": entry.repo_local_path,
        "team_framework": team_framework,
    }


@router.get("/")
def list_projects(request: Request) -> List[dict]:
    registry = request.app.state.project_registry
    projects = [
        {"id": item.id, "name": item.name, "repo_local_path": item.repo_local_path}
        for item in registry.list_projects()
    ]
    if request.app.state.settings.allow_self_project:
        projects.insert(
            0,
            {
                "id": 0,
                "name": "Self",
                "repo_local_path": str(request.app.state.settings.repo_root),
                "kind": "self",
            },
        )
    return projects


@router.get("/active")
def get_active_project(request: Request) -> dict:
    registry = request.app.state.project_registry
    active_id = registry.get_active_id()
    if active_id == 0 and request.app.state.settings.allow_self_project:
        return {
            "id": 0,
            "name": "Self",
            "repo_local_path": str(request.app.state.settings.repo_root),
            "kind": "self",
        }
    active = registry.get_active()
    if not active:
        raise HTTPException(status_code=404, detail="No active project")
    return {"id": active.id, "name": active.name, "repo_local_path": active.repo_local_path}


@router.post("/{project_id}/activate")
def activate_project(project_id: int, request: Request) -> dict:
    registry = request.app.state.project_registry
    if project_id == 0 and request.app.state.settings.allow_self_project:
        registry.set_active(0)
        root = project_data_dir(request.app.state.settings.repo_root)
        root.mkdir(parents=True, exist_ok=True)
        init_db(project_db_url(request.app.state.settings.repo_root))
        request.app.state.active_project_id = 0
        request.app.state.active_project_root = request.app.state.settings.repo_root
        request.app.state.data_dir = root
        with get_session() as session:
            existing = session.exec(select(Project).where(Project.id == 0)).first()
            if not existing:
                session.add(
                    Project(
                        id=0,
                        name="Self",
                        repo_local_path=str(request.app.state.settings.repo_root),
                    )
                )
                session.commit()
        return {"status": "ok", "active_project_id": 0}
    entry = registry.get_project(project_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Project not found")
    registry.set_active(project_id)

    root = project_data_dir(Path(entry.repo_local_path))
    root.mkdir(parents=True, exist_ok=True)
    init_db(project_db_url(Path(entry.repo_local_path)))
    request.app.state.active_project_id = entry.id
    request.app.state.active_project_root = Path(entry.repo_local_path)
    request.app.state.data_dir = root

    with get_session() as session:
        existing = session.exec(select(Project).where(Project.id == entry.id)).first()
        if not existing:
            project = Project(
                id=entry.id,
                name=entry.name,
                repo_local_path=entry.repo_local_path,
            )
            session.add(project)
            session.commit()

    return {"status": "ok", "active_project_id": entry.id}
