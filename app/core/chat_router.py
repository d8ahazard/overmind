import re
from typing import List, Optional

from sqlmodel import select

from app.db.models import AgentConfig
from app.db.session import get_session


MANAGER_ROLES = {"Product Owner", "Delivery Manager", "Release Manager"}
TEAM_MENTIONS = {"team", "all", "everyone"}
ROLE_ALIASES = {
    "product owner": {"po", "productowner"},
    "delivery manager": {"dm", "deliverymanager"},
    "tech lead": {"tl", "techlead", "lead"},
    "developer": {"dev", "engineer", "frontend", "backend", "fe", "be"},
    "qa engineer": {"qa", "tester", "test"},
    "release manager": {"rm", "release"},
}


class ChatRouter:
    def __init__(self) -> None:
        self._mention_pattern = re.compile(r"@([\\w\\-]+)")

    def resolve_targets(
        self, team_id: int, message: str, policy: str = "managers"
    ) -> List[AgentConfig]:
        mentions = self._extract_mentions(message)
        with get_session() as session:
            agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team_id)))
        if mentions:
            if any(mention in TEAM_MENTIONS for mention in mentions):
                return agents
            selected: list[AgentConfig] = []
            for agent in agents:
                display = (agent.display_name or "").lower()
                role = agent.role.lower()
                aliases = ROLE_ALIASES.get(role, set())
                if any(
                    mention == display
                    or mention == role.replace(" ", "")
                    or mention in aliases
                    for mention in mentions
                ):
                    selected.append(agent)
            if selected:
                return selected
        if policy == "team":
            return agents
        return [agent for agent in agents if agent.role in MANAGER_ROLES]

    def _extract_mentions(self, message: str) -> List[str]:
        matches = self._mention_pattern.findall(message or "")
        return [match.lower().replace("@", "") for match in matches if match]
