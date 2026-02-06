from dataclasses import dataclass
from datetime import datetime
from typing import List

from sqlmodel import select

from app.db.models import AgentConfig, AgentMemory
from app.db.session import get_session


@dataclass
class MemoryEntry:
    id: int
    content: str


class MemoryStore:
    def append(self, run_id: int, agent_id: int, role: str, content: str) -> MemoryEntry:
        entry = AgentMemory(
            run_id=run_id,
            agent_id=agent_id,
            role=role,
            content=content[:1000],
            created_at=datetime.utcnow(),
        )
        with get_session() as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)
            self._update_summary(session, agent_id)
            session.commit()
            entry_id = entry.id or 0
            entry_content = entry.content
        return MemoryEntry(id=entry_id, content=entry_content)

    def recent(self, run_id: int, agent_id: int, limit: int = 5) -> List[AgentMemory]:
        with get_session() as session:
            statement = (
                select(AgentMemory)
                .where(AgentMemory.run_id == run_id, AgentMemory.agent_id == agent_id)
                .order_by(AgentMemory.created_at.desc())
                .limit(limit)
            )
            return list(session.exec(statement))

    def _update_summary(self, session, agent_id: int) -> None:
        if not agent_id:
            return
        statement = (
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(AgentMemory.created_at.desc())
            .limit(5)
        )
        recent = list(session.exec(statement))
        summary = " | ".join(entry.content[:160] for entry in reversed(recent))
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            return
        agent.memory_summary = summary if summary else agent.memory_summary
        session.add(agent)
