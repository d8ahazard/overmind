from typing import List

import json

from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.core.presets import PRESETS, build_agents
from app.providers.model_registry import ModelRegistry
from app.db.models import ProjectSetting, Team
from app.db.session import get_session

router = APIRouter()


async def _generate_profile(request: Request, role: str, provider: str, model: str) -> tuple[str | None, str | None]:
    registry = request.app.state.orchestrator.agent_runtime.registry
    broker = request.app.state.secrets_broker
    token = broker.issue_provider_token(provider) if broker else None
    prompt = (
        "You are generating a concise team member profile for a business-focused AI agent.\n"
        f"Role: {role}\n"
        "Return STRICT JSON with keys: display_name, personality.\n"
        "Personality should be 2-3 sentences. Avoid emojis.\n"
    )
    payload = {"prompt": prompt, "role": role}
    if token:
        payload["provider_token"] = token.token
    try:
        response = await registry.invoke(provider, model, payload)
        raw = response.get("content", "")
        data = json.loads(raw)
        return data.get("display_name"), data.get("personality")
    except Exception:
        return None, None


@router.get("/presets")
def list_presets() -> List[dict]:
    return [
        {"name": preset.name, "roles": preset.roles}
        for preset in PRESETS.values()
    ]


@router.post("/", response_model=Team)
def create_team(team: Team) -> Team:
    with get_session() as session:
        session.add(team)
        session.commit()
        session.refresh(team)
        return team


@router.get("/", response_model=List[Team])
def list_teams() -> List[Team]:
    with get_session() as session:
        return list(session.exec(select(Team)))


@router.get("/{team_id}", response_model=Team)
def get_team(team_id: int) -> Team:
    with get_session() as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return team


@router.post("/{team_id}/apply-preset")
async def apply_preset(team_id: int, payload: dict, request: Request) -> dict:
    size = payload.get("size", "medium")
    provider = payload.get("provider", "openai")
    model = payload.get("model", "gpt-4")
    generate_profiles = payload.get("generate_profiles")
    if generate_profiles is None:
        generate_profiles = request.app.state.settings.generate_profiles
    else:
        generate_profiles = str(generate_profiles).lower() == "true"
    with get_session() as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        agents = build_agents(team_id, size, provider, model)
        setting = session.exec(
            select(ProjectSetting).where(ProjectSetting.project_id == team.project_id)
        ).first()
        default_scopes = (setting.default_tool_scopes if setting else None) or "system:run"
        manager_model = await ModelRegistry(request.app.state.secrets_broker).suggest_manager_model(provider)
        for agent in agents:
            agent.permissions = default_scopes
            if manager_model and agent.role in {"Product Owner", "Delivery Manager", "Release Manager"}:
                agent.model = manager_model
        if generate_profiles:
            for agent in agents:
                display_name, personality = await _generate_profile(
                    request, agent.role, provider, model
                )
                if display_name:
                    agent.display_name = display_name
                if personality:
                    agent.personality = personality
        session.add_all(agents)
        session.commit()
    return {"status": "ok", "count": len(agents)}
