from datetime import datetime
from typing import List

from sqlmodel import select

from app.db.models import AgentConfig, AgentMemory
from app.db.session import get_session


class MemoryStore:
    def append(self, run_id: int, agent: AgentConfig, content: str) -> AgentMemory:
        entry = AgentMemory(
            run_id=run_id,
            agent_id=agent.id or 0,
            role=agent.role,
            content=content[:1000],
            created_at=datetime.utcnow(),
        )
        with get_session() as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)
            self._update_summary(session, agent)
            session.commit()
        return entry

    def recent(self, run_id: int, agent_id: int, limit: int = 5) -> List[AgentMemory]:
        with get_session() as session:
            statement = (
                select(AgentMemory)
                .where(AgentMemory.run_id == run_id, AgentMemory.agent_id == agent_id)
                .order_by(AgentMemory.created_at.desc())
                .limit(limit)
            )
            return list(session.exec(statement))

    def _update_summary(self, session, agent: AgentConfig) -> None:
        statement = (
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent.id)
            .order_by(AgentMemory.created_at.desc())
            .limit(5)
        )
        recent = list(session.exec(statement))
        summary = " | ".join(entry.content[:160] for entry in reversed(recent))
        agent.memory_summary = summary if summary else agent.memory_summary
        session.add(agent)
