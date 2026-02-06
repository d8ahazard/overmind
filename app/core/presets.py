from dataclasses import dataclass
from typing import List
import random

from sqlmodel import select

from app.db.models import AgentConfig, PersonalityTemplate
from app.db.session import get_session


@dataclass
class TeamPreset:
    name: str
    roles: List[str]


PRESETS = {
    "small": TeamPreset(
        name="small",
        roles=[
            "Product Owner",
            "Tech Lead",
            "Developer",
            "Developer",
            "QA Engineer",
            "Release Manager",
        ],
    ),
    "medium": TeamPreset(
        name="medium",
        roles=[
            "Product Owner",
            "Delivery Manager",
            "Tech Lead",
            "Developer",
            "Developer",
            "Developer",
            "Developer",
            "QA Engineer",
            "QA Engineer",
            "Release Manager",
        ],
    ),
    "large": TeamPreset(
        name="large",
        roles=[
            "Product Owner",
            "Delivery Manager",
            "Tech Lead",
            "Developer",
            "Developer",
            "Developer",
            "Developer",
            "Developer",
            "Developer",
            "Developer",
            "QA Engineer",
            "QA Engineer",
            "QA Engineer",
            "Release Manager",
        ],
    ),
}

DEFAULT_PERSONALITIES = {
    "Product Owner": "Customer-focused, decisive, and outcome-driven. Writes clear acceptance criteria.",
    "Delivery Manager": "Organized, risk-aware, and pragmatic. Keeps work unblocked and on schedule.",
    "Tech Lead": "Architectural, calm, and precise. Ensures quality and scalability.",
    "Developer": "Practical, curious, and focused on clean, working code.",
    "QA Engineer": "Skeptical, detail-oriented, and tests edge cases thoroughly.",
    "Release Manager": "Process-minded, cautious, and ensures safe releases.",
}

DEFAULT_NAMES = {
    "Product Owner": ["Ava", "Mia"],
    "Delivery Manager": ["Noah", "Eli"],
    "Tech Lead": ["Liam", "Zoe"],
    "Developer": ["Kai", "Riley", "Jules", "Sam", "Jordan", "Alex"],
    "QA Engineer": ["Taylor", "Morgan", "Quinn"],
    "Release Manager": ["Parker", "Casey"],
}


def _select_template(role: str) -> str:
    with get_session() as session:
        statement = select(PersonalityTemplate).where(PersonalityTemplate.role == role)
        templates = list(session.exec(statement))
        if templates:
            return templates[0].script
    return DEFAULT_PERSONALITIES.get(role, "Professional and concise.")


def _random_personality(role: str) -> str:
    tones = [
        "pragmatic", "curious", "direct", "empathetic", "systematic", "decisive",
        "patient", "analytical", "collaborative", "detail-oriented",
    ]
    focus = [
        "clear communication", "risk reduction", "quality", "speed with safety",
        "customer outcomes", "reliable delivery", "clean architecture",
        "test coverage", "operational readiness",
    ]
    cadence = [
        "short, crisp updates", "structured checklists", "succinct tradeoffs",
        "well-documented decisions",
    ]
    base = DEFAULT_PERSONALITIES.get(role, "Professional and concise.")
    return (
        f"{base} "
        f"Tone: {random.choice(tones)}. "
        f"Focus: {random.choice(focus)}. "
        f"Prefers {random.choice(cadence)}."
    )


def build_agents(team_id: int, size: str, provider: str, model: str) -> List[AgentConfig]:
    preset = PRESETS.get(size, PRESETS["medium"])
    role_counts = {}
    agents: List[AgentConfig] = []
    for role in preset.roles:
        role_counts[role] = role_counts.get(role, 0) + 1
        idx = role_counts[role] - 1
        name_pool = DEFAULT_NAMES.get(role, [role])
        display_name = name_pool[idx % len(name_pool)]
        agents.append(
            AgentConfig(
                team_id=team_id,
                display_name=display_name,
                role=role,
                personality=_random_personality(role),
                provider=provider,
                model=model,
            )
        )
    return agents
