from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from app.db.models import AgentConfig
from app.db.session import get_session

router = APIRouter()


class AgentUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[str] = None
    personality: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    permissions: Optional[str] = None
    capabilities: Optional[str] = None


@router.post("/", response_model=AgentConfig)
def create_agent(agent: AgentConfig) -> AgentConfig:
    with get_session() as session:
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return agent


@router.get("/", response_model=List[AgentConfig])
def list_agents() -> List[AgentConfig]:
    with get_session() as session:
        return list(session.exec(select(AgentConfig)))


@router.put("/{agent_id}", response_model=AgentConfig)
def update_agent(agent_id: int, data: AgentUpdate) -> AgentConfig:
    with get_session() as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        if data.display_name is not None:
            agent.display_name = data.display_name
        if data.role is not None:
            agent.role = data.role
        if data.personality is not None:
            agent.personality = data.personality
        if data.avatar_url is not None:
            agent.avatar_url = data.avatar_url
        if data.provider is not None:
            agent.provider = data.provider
        if data.model is not None:
            agent.model = data.model
        if data.permissions is not None:
            agent.permissions = data.permissions
        if data.capabilities is not None:
            agent.capabilities = data.capabilities
        session.add(agent)
        session.commit()
        session.refresh(agent)
        return agent


@router.get("/{agent_id}", response_model=AgentConfig)
def get_agent(agent_id: int) -> AgentConfig:
    with get_session() as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: int) -> dict:
    with get_session() as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        session.delete(agent)
        session.commit()
        return {"status": "deleted", "agent_id": agent_id}
