import os
from dataclasses import dataclass
from pathlib import Path
import secrets


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    db_url: str
    env: str
    default_project_root: Path
    mcp_endpoints: list[str]
    mcp_discovery_ports: list[int]
    encryption_key: str | None
    allow_self_edit: bool
    allow_self_project: bool
    generate_profiles: bool


def load_settings() -> Settings:
    repo_root = Path(os.getenv("AI_DEVTEAM_REPO_ROOT", Path.cwd())).resolve()
    data_dir = repo_root / ".ai_dev_team"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_url = os.getenv("AI_DEVTEAM_DB_URL", f"sqlite:///{data_dir / 'ai_dev_team.db'}")
    env = os.getenv("AI_DEVTEAM_ENV", "dev")
    default_project_root = Path(
        os.getenv("AI_DEVTEAM_DEFAULT_PROJECT_ROOT", r"E:\dev\StandYourGround")
    ).resolve()
    endpoints_raw = os.getenv("AI_DEVTEAM_MCP_ENDPOINTS", "")
    mcp_endpoints = [item.strip() for item in endpoints_raw.split(",") if item.strip()]
    ports_raw = os.getenv("AI_DEVTEAM_MCP_PORTS", "8765,8766,9000,8080,3000")
    mcp_discovery_ports = [
        int(port.strip())
        for port in ports_raw.split(",")
        if port.strip().isdigit()
    ]
    encryption_key = os.getenv("AI_DEVTEAM_MASTER_KEY")
    if not encryption_key:
        key_path = data_dir / "master.key"
        if key_path.exists():
            encryption_key = key_path.read_text(encoding="utf-8").strip()
        else:
            encryption_key = secrets.token_urlsafe(48)
            key_path.write_text(encryption_key, encoding="utf-8")
    allow_self_edit = os.getenv("AI_DEVTEAM_ALLOW_SELF_EDIT", "true").lower() == "true"
    allow_self_project = os.getenv("AI_DEVTEAM_ALLOW_SELF_PROJECT", "false").lower() == "true"
    generate_profiles = os.getenv("AI_DEVTEAM_GENERATE_PROFILES", "true").lower() == "true"
    return Settings(
        repo_root=repo_root,
        data_dir=data_dir,
        db_url=db_url,
        env=env,
        default_project_root=default_project_root,
        mcp_endpoints=mcp_endpoints,
        mcp_discovery_ports=mcp_discovery_ports,
        encryption_key=encryption_key,
        allow_self_edit=allow_self_edit,
        allow_self_project=allow_self_project,
        generate_profiles=generate_profiles,
    )
