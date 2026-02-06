from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.core.presets import PRESETS, build_agents
from app.db.models import Team
from app.db.session import get_session

router = APIRouter()


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


@router.get("/presets")
def list_presets() -> List[dict]:
    return [
        {"name": preset.name, "roles": preset.roles}
        for preset in PRESETS.values()
    ]


@router.post("/{team_id}/apply-preset")
def apply_preset(team_id: int, payload: dict) -> dict:
    size = payload.get("size", "medium")
    provider = payload.get("provider", "openai")
    model = payload.get("model", "gpt-4")
    with get_session() as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        agents = build_agents(team_id, size, provider, model)
        session.add_all(agents)
        session.commit()
    return {"status": "ok", "count": len(agents)}
