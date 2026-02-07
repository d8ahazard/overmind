from typing import List

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from pathlib import Path

from app.core.project_registry import project_data_dir, project_db_url
from app.db.models import Project, ProjectSetting
from app.db.session import get_session, init_db

router = APIRouter()


def _get_setting(session, project_id: int) -> ProjectSetting:
    setting = session.exec(
        select(ProjectSetting).where(ProjectSetting.project_id == project_id)
    ).first()
    if not setting:
        setting = ProjectSetting(
            project_id=project_id,
            allow_all_tools=False,
            allow_high_risk=False,
            default_tool_scopes=None,
            role_tool_scopes=None,
            allow_pm_merge=False,
            model_defaults=None,
            memory_profiles=None,
            mcp_endpoints=None,
            mcp_ports=None,
            enabled_plugins=None,
            chat_target_policy="managers",
            task_retry_limit=3,
        )
        session.add(setting)
        session.commit()
        session.refresh(setting)
    return setting


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
            setting = _get_setting(session, 0)
            request.app.state.policy_engine.allow_all_tools = setting.allow_all_tools
            request.app.state.policy_engine.allow_high_risk = setting.allow_high_risk
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
        setting = _get_setting(session, entry.id)
        request.app.state.policy_engine.allow_all_tools = setting.allow_all_tools
        request.app.state.policy_engine.allow_high_risk = setting.allow_high_risk

    return {"status": "ok", "active_project_id": entry.id}


@router.get("/settings")
def get_project_settings(request: Request) -> dict:
    project_id = request.app.state.active_project_id
    if project_id is None:
        raise HTTPException(status_code=404, detail="No active project")
    with get_session() as session:
        setting = _get_setting(session, project_id)
    return {
        "project_id": project_id,
        "allow_all_tools": setting.allow_all_tools,
        "allow_high_risk": setting.allow_high_risk,
        "default_tool_scopes": setting.default_tool_scopes,
        "role_tool_scopes": setting.role_tool_scopes,
        "allow_pm_merge": setting.allow_pm_merge,
        "chat_target_policy": setting.chat_target_policy,
        "task_retry_limit": setting.task_retry_limit,
        "model_defaults": setting.model_defaults,
        "memory_profiles": setting.memory_profiles,
        "mcp_endpoints": setting.mcp_endpoints,
        "mcp_ports": setting.mcp_ports,
        "enabled_plugins": setting.enabled_plugins,
    }


@router.put("/settings")
def update_project_settings(payload: dict, request: Request) -> dict:
    project_id = request.app.state.active_project_id
    if project_id is None:
        raise HTTPException(status_code=404, detail="No active project")
    allow_all_tools = payload.get("allow_all_tools")
    allow_high_risk = payload.get("allow_high_risk")
    default_tool_scopes = payload.get("default_tool_scopes")
    role_tool_scopes = payload.get("role_tool_scopes")
    allow_pm_merge = payload.get("allow_pm_merge")
    chat_target_policy = payload.get("chat_target_policy")
    task_retry_limit = payload.get("task_retry_limit")
    model_defaults = payload.get("model_defaults")
    memory_profiles = payload.get("memory_profiles")
    mcp_endpoints = payload.get("mcp_endpoints")
    mcp_ports = payload.get("mcp_ports")
    enabled_plugins = payload.get("enabled_plugins")
    with get_session() as session:
        setting = _get_setting(session, project_id)
        if allow_all_tools is not None:
            setting.allow_all_tools = bool(allow_all_tools)
        if allow_high_risk is not None:
            setting.allow_high_risk = bool(allow_high_risk)
        if default_tool_scopes is not None:
            setting.default_tool_scopes = str(default_tool_scopes) or None
        if role_tool_scopes is not None:
            setting.role_tool_scopes = str(role_tool_scopes) or None
        if allow_pm_merge is not None:
            setting.allow_pm_merge = bool(allow_pm_merge)
        if chat_target_policy is not None:
            setting.chat_target_policy = str(chat_target_policy)
        if task_retry_limit is not None:
            try:
                setting.task_retry_limit = max(1, int(task_retry_limit))
            except (TypeError, ValueError):
                setting.task_retry_limit = 3
        if model_defaults is not None:
            setting.model_defaults = str(model_defaults) or None
        if memory_profiles is not None:
            setting.memory_profiles = str(memory_profiles) or None
        if mcp_endpoints is not None:
            setting.mcp_endpoints = str(mcp_endpoints) or None
        if mcp_ports is not None:
            setting.mcp_ports = str(mcp_ports) or None
        if enabled_plugins is not None:
            setting.enabled_plugins = str(enabled_plugins) or None
        session.add(setting)
        session.commit()
        session.refresh(setting)
    request.app.state.policy_engine.allow_all_tools = setting.allow_all_tools
    request.app.state.policy_engine.allow_high_risk = setting.allow_high_risk
    return {
        "project_id": project_id,
        "allow_all_tools": setting.allow_all_tools,
        "allow_high_risk": setting.allow_high_risk,
        "default_tool_scopes": setting.default_tool_scopes,
        "role_tool_scopes": setting.role_tool_scopes,
        "allow_pm_merge": setting.allow_pm_merge,
        "chat_target_policy": setting.chat_target_policy,
        "task_retry_limit": setting.task_retry_limit,
        "model_defaults": setting.model_defaults,
        "memory_profiles": setting.memory_profiles,
        "mcp_endpoints": setting.mcp_endpoints,
        "mcp_ports": setting.mcp_ports,
        "enabled_plugins": setting.enabled_plugins,
    }
