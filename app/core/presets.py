from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from typing import List
import random
import hashlib
from urllib.parse import quote

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

DEFAULT_IDENTITIES: Dict[str, list[dict]] = {
    "Product Owner": [
        {"name": "Ava", "gender": "female", "pronouns": "she/her"},
        {"name": "Mia", "gender": "female", "pronouns": "she/her"},
        {"name": "Noah", "gender": "male", "pronouns": "he/him"},
    ],
    "Delivery Manager": [
        {"name": "Eli", "gender": "male", "pronouns": "he/him"},
        {"name": "Sage", "gender": "female", "pronouns": "she/her"},
        {"name": "Zoe", "gender": "female", "pronouns": "she/her"},
    ],
    "Tech Lead": [
        {"name": "Liam", "gender": "male", "pronouns": "he/him"},
        {"name": "Riley", "gender": "male", "pronouns": "he/him"},
        {"name": "Jules", "gender": "female", "pronouns": "she/her"},
    ],
    "Developer": [
        {"name": "Kai", "gender": "male", "pronouns": "he/him"},
        {"name": "Sam", "gender": "male", "pronouns": "he/him"},
        {"name": "Jordan", "gender": "male", "pronouns": "he/him"},
        {"name": "Alex", "gender": "male", "pronouns": "he/him"},
        {"name": "Taylor", "gender": "female", "pronouns": "she/her"},
    ],
    "QA Engineer": [
        {"name": "Quinn", "gender": "male", "pronouns": "he/him"},
        {"name": "Morgan", "gender": "male", "pronouns": "he/him"},
        {"name": "Casey", "gender": "female", "pronouns": "she/her"},
    ],
    "Release Manager": [
        {"name": "Parker", "gender": "male", "pronouns": "he/him"},
        {"name": "Casey", "gender": "female", "pronouns": "she/her"},
        {"name": "Rowan", "gender": "male", "pronouns": "he/him"},
    ],
}

GENERIC_IDENTITIES = [
    {"name": "Ari", "gender": "male", "pronouns": "he/him"},
    {"name": "Rene", "gender": "female", "pronouns": "she/her"},
    {"name": "Lee", "gender": "male", "pronouns": "he/him"},
    {"name": "Drew", "gender": "female", "pronouns": "she/her"},
]

AVATAR_STYLES = ["bottts", "adventurer", "lorelei", "thumbs"]


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


def build_agents(
    team_id: int,
    size: str,
    provider: str,
    model: str,
    role_counts: Optional[dict] = None,
    role_models: Optional[Dict[str, Tuple[str, str]]] = None,
) -> List[AgentConfig]:
    roles = _build_roles(size, role_counts)
    assigned_counts: Dict[str, int] = {}
    used_names: set[str] = set()
    agents: List[AgentConfig] = []
    for role in roles:
        assigned_counts[role] = assigned_counts.get(role, 0) + 1
        identity = _pick_identity(role, used_names)
        used_names.add(identity["name"])
        avatar_url = generate_avatar_url(identity["name"])
        picked_provider, picked_model = (
            role_models.get(role) if role_models and role in role_models else (provider, model)
        )
        agents.append(
            AgentConfig(
                team_id=team_id,
                display_name=identity["name"],
                role=role,
                gender=identity.get("gender"),
                pronouns=identity.get("pronouns"),
                personality=_random_personality(role),
                avatar_url=avatar_url,
                provider=picked_provider,
                model=picked_model,
            )
        )
    return agents


def generate_avatar_url(seed: str) -> str:
    safe_seed = quote(seed or "agent")
    digest = hashlib.sha256(safe_seed.encode("utf-8")).hexdigest()
    style = AVATAR_STYLES[int(digest[:2], 16) % len(AVATAR_STYLES)]
    return f"https://api.dicebear.com/7.x/{style}/png?seed={safe_seed}"


def pick_avatar_url(seed: str | None = None) -> str:
    if seed:
        return generate_avatar_url(seed)
    fallback = random.choice(GENERIC_IDENTITIES)["name"]
    return generate_avatar_url(fallback)


def is_broken_avatar_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return "/public/avatars/pixel_" in lowered or "/avatars/pixel_" in lowered


def _build_roles(size: str, role_counts: Optional[dict]) -> List[str]:
    if size == "custom" and role_counts:
        roles: List[str] = []
        for role, count in role_counts.items():
            try:
                count_int = max(0, int(count))
            except (TypeError, ValueError):
                count_int = 0
            roles.extend([role] * count_int)
        return roles or PRESETS["medium"].roles
    preset = PRESETS.get(size, PRESETS["medium"])
    return list(preset.roles)


def _pick_identity(role: str, used_names: set[str]) -> dict:
    pool = DEFAULT_IDENTITIES.get(role) or GENERIC_IDENTITIES
    available = [item for item in pool if item["name"] not in used_names]
    return random.choice(available or pool)
