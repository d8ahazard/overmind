import json
from typing import Dict

from app.db.models import ProjectSetting

DEFAULT_ROLE_SCOPES: Dict[str, str] = {
    "Product Owner": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
    "Delivery Manager": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
    "Tech Lead": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
    "Developer": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
    "QA Engineer": "system:run,file:read,git:status,git:diff",
    "Release Manager": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
}


def parse_role_scopes(raw: str | None) -> Dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    results: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(value, str):
            continue
        results[str(key)] = value
    return results


def normalize_scopes(raw: str | None) -> str:
    items = [item.strip() for item in (raw or "").split(",") if item.strip()]
    seen = set()
    cleaned = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return ",".join(cleaned)


def resolve_role_scopes(role: str, setting: ProjectSetting | None) -> str:
    override = parse_role_scopes(setting.role_tool_scopes if setting else None)
    scopes = override.get(role) or DEFAULT_ROLE_SCOPES.get(role)
    if not scopes:
        scopes = (setting.default_tool_scopes if setting else None) or "system:run"
    scopes = normalize_scopes(scopes)
    if setting and setting.allow_pm_merge and role in {"Product Owner"}:
        scopes = normalize_scopes(f"{scopes},git:merge")
    return scopes
