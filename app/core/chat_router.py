import re
from typing import List, Optional

from sqlmodel import select

from app.db.models import AgentConfig
from app.db.session import get_session


MANAGER_ROLES = {"Product Owner", "Delivery Manager", "Release Manager"}
TEAM_MENTIONS = {"team", "all", "everyone"}


class ChatRouter:
    def __init__(self) -> None:
        self._mention_pattern = re.compile(r"@([\\w\\-]+)")

    def resolve_targets(
        self, team_id: int, message: str, policy: str = "managers"
    ) -> List[AgentConfig]:
        mention = self._extract_mention(message)
        with get_session() as session:
            agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team_id)))
        if mention:
            if mention in TEAM_MENTIONS:
                return agents
            for agent in agents:
                display = (agent.display_name or "").lower()
                role = agent.role.lower()
                if mention == display or mention == role.replace(" ", ""):
                    return [agent]
        if policy == "team":
            return agents
        return [agent for agent in agents if agent.role in MANAGER_ROLES]

    def _extract_mention(self, message: str) -> Optional[str]:
        match = self._mention_pattern.search(message or "")
        if not match:
            return None
        return match.group(1).lower().replace("@", "")
