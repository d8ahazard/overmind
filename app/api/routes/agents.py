from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.db.models import AgentConfig
from app.db.session import get_session

router = APIRouter()


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
def update_agent(agent_id: int, data: AgentConfig) -> AgentConfig:
    with get_session() as session:
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        agent.display_name = data.display_name
        agent.role = data.role
        agent.personality = data.personality
        agent.provider = data.provider
        agent.model = data.model
        agent.permissions = data.permissions
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
