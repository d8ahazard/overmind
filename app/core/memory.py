from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import json

from sqlmodel import select

from app.db.models import AgentConfig, AgentMemory, ProjectSetting, Run
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
            self._update_summary(session, run_id, agent_id, role)
            session.commit()
            entry_id = entry.id or 0
            entry_content = entry.content
        return MemoryEntry(id=entry_id, content=entry_content)

    def recent(
        self,
        run_id: int,
        agent_id: int,
        role: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[AgentMemory]:
        if limit is None:
            profile = self._get_profile(run_id, role)
            limit = max(1, int(profile.get("cap", 5)))
        with get_session() as session:
            statement = (
                select(AgentMemory)
                .where(AgentMemory.run_id == run_id, AgentMemory.agent_id == agent_id)
                .order_by(AgentMemory.created_at.desc())
                .limit(limit)
            )
            return list(session.exec(statement))

    def _update_summary(self, session, run_id: int, agent_id: int, role: str) -> None:
        if not agent_id:
            return
        profile = self._get_profile(run_id, role)
        strategy = str(profile.get("strategy", "rolling"))
        cap = max(1, int(profile.get("cap", 5)))
        if strategy == "none":
            agent = session.get(AgentConfig, agent_id)
            if agent:
                agent.memory_summary = ""
                session.add(agent)
            return
        limit = 1 if strategy == "latest" else cap
        statement = (
            select(AgentMemory)
            .where(AgentMemory.agent_id == agent_id)
            .order_by(AgentMemory.created_at.desc())
            .limit(limit)
        )
        recent = list(session.exec(statement))
        summary = " | ".join(entry.content[:160] for entry in reversed(recent))
        agent = session.get(AgentConfig, agent_id)
        if not agent:
            return
        agent.memory_summary = summary if summary else agent.memory_summary
        session.add(agent)

    def _get_profile(self, run_id: int, role: Optional[str]) -> dict:
        default = {"cap": 5, "strategy": "rolling"}
        if not run_id:
            return default
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return default
            setting = session.exec(
                select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
            ).first()
            if not setting or not setting.memory_profiles:
                return default
            try:
                data = json.loads(setting.memory_profiles)
            except Exception:
                return default
            if not isinstance(data, dict) or not role:
                return default
            profile = data.get(role)
            if isinstance(profile, dict):
                return profile
        return default
