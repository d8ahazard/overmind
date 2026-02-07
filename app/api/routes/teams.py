from typing import List, Dict, Tuple
import json

import json

from fastapi import APIRouter, HTTPException, Query, Request
from sqlmodel import select

from app.core.presets import PRESETS, build_agents
from app.providers.model_registry import ModelRegistry
from app.providers.model_filters import (
    filter_chat_models,
    is_chat_model,
    pick_best_chat_model,
    pick_code_chat_model,
    pick_worker_chat_model,
)
from app.db.models import AgentConfig, ProjectSetting, ProviderKey, Team
from app.core.role_scopes import resolve_role_scopes
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
def list_teams(project_id: int | None = Query(default=None)) -> List[Team]:
    with get_session() as session:
        query = select(Team)
        if project_id is not None:
            query = query.where(Team.project_id == project_id)
        return list(session.exec(query))


@router.get("/{team_id}", response_model=Team)
def get_team(team_id: int) -> Team:
    with get_session() as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return team


@router.delete("/{team_id}")
def delete_team(team_id: int) -> dict:
    with get_session() as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team_id)))
        for agent in agents:
            session.delete(agent)
        session.delete(team)
        session.commit()
    return {"status": "deleted", "team_id": team_id}


@router.post("/{team_id}/apply-preset")
async def apply_preset(team_id: int, payload: dict, request: Request) -> dict:
    size = payload.get("size", "medium")
    provider = payload.get("provider")
    model = payload.get("model")
    role_counts = payload.get("role_counts")
    generate_profiles = payload.get("generate_profiles")
    if generate_profiles is None:
        generate_profiles = request.app.state.settings.generate_profiles
    else:
        generate_profiles = str(generate_profiles).lower() == "true"
    with get_session() as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        setting = session.exec(
            select(ProjectSetting).where(ProjectSetting.project_id == team.project_id)
        ).first()
        enabled = [item.provider for item in session.exec(select(ProviderKey))]
        registry = ModelRegistry(request.app.state.secrets_broker)
        provider = None if provider in {"auto", ""} else provider
        model = None if model in {"auto", ""} else model
        if provider and model and not is_chat_model(provider, model):
            models = await registry.list_models(provider=provider, enabled=[provider])
            chat_models = filter_chat_models(provider, [item.id for item in models])
            model = pick_worker_chat_model(chat_models) or model
        defaults = _parse_role_defaults(setting.model_defaults if setting else None)
        role_models = await _build_role_models(
            registry, enabled, provider, model, role_counts, defaults
        )
        fallback_provider = provider or (enabled[0] if enabled else "openai")
        fallback_model = model or "gpt-4"
        agents = build_agents(
            team_id,
            size,
            fallback_provider,
            fallback_model,
            role_counts=role_counts,
            role_models=role_models,
        )
        for agent in agents:
            agent.permissions = resolve_role_scopes(agent.role, setting)
        if generate_profiles:
            for agent in agents:
                display_name, personality = await _generate_profile(
                    request, agent.role, agent.provider, agent.model
                )
                if display_name:
                    agent.display_name = display_name
                if personality:
                    agent.personality = personality
        session.add_all(agents)
        session.commit()
    return {"status": "ok", "count": len(agents)}


async def _build_role_models(
    registry: ModelRegistry,
    enabled: List[str],
    provider: str | None,
    model: str | None,
    role_counts: dict | None,
    defaults: Dict[str, Dict[str, str]] | None = None,
) -> Dict[str, Tuple[str, str]]:
    if provider and model:
        return {}
    if not enabled:
        return {}
    role_models: Dict[str, Tuple[str, str]] = {}
    provider_models: Dict[str, List[str]] = {}
    provider_chat: Dict[str, List[str]] = {}
    for item in enabled:
        models = await registry.list_models(provider=item, enabled=[item])
        all_ids = [model.id for model in models]
        provider_models[item] = all_ids
        provider_chat[item] = filter_chat_models(item, all_ids)
    roles = set(role_counts.keys()) if isinstance(role_counts, dict) else set()
    roles.update(PRESETS["medium"].roles)
    for role in roles:
        if defaults and role in defaults:
            entry = defaults.get(role) or {}
            provider_name = entry.get("provider")
            model_id = entry.get("model")
            if provider_name and model_id:
                role_models[role] = (provider_name, model_id)
                continue
        role_lower = role.lower()
        needs_code = "developer" in role_lower or "engineer" in role_lower
        for provider_name in enabled:
            candidates = provider_models.get(provider_name, [])
            chat_candidates = provider_chat.get(provider_name, [])
            if not candidates and not chat_candidates:
                continue
            picked = None
            if needs_code:
                picked = pick_code_chat_model(candidates)
            if not picked:
                picked = pick_worker_chat_model(chat_candidates)
            if not picked:
                picked = pick_best_chat_model(chat_candidates)
            if picked:
                role_models[role] = (provider_name, picked)
                break
    return role_models


def _parse_role_defaults(raw: str | None) -> Dict[str, Dict[str, str]]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    results: Dict[str, Dict[str, str]] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        provider_name = value.get("provider")
        model_id = value.get("model")
        if provider_name and model_id:
            results[str(key)] = {"provider": str(provider_name), "model": str(model_id)}
    return results
