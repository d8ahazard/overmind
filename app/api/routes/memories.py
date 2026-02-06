from typing import List, Optional

from fastapi import APIRouter, Query
from sqlmodel import select

from app.db.models import AgentMemory
from app.db.session import get_session

router = APIRouter()


@router.get("/", response_model=List[AgentMemory])
def list_memories(
    run_id: Optional[int] = Query(default=None),
    agent_id: Optional[int] = Query(default=None),
) -> List[AgentMemory]:
    with get_session() as session:
        statement = select(AgentMemory)
        if run_id is not None:
            statement = statement.where(AgentMemory.run_id == run_id)
        if agent_id is not None:
            statement = statement.where(AgentMemory.agent_id == agent_id)
        return list(session.exec(statement))
