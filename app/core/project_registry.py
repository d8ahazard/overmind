import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ProjectEntry:
    id: int
    name: str
    repo_local_path: str


class ProjectRegistry:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.base_dir / "projects.json"
        if not self.path.exists():
            self._write({"active_id": None, "projects": []})

    def list_projects(self) -> List[ProjectEntry]:
        data = self._read()
        return [ProjectEntry(**item) for item in data.get("projects", [])]

    def get_project(self, project_id: int) -> Optional[ProjectEntry]:
        return next((p for p in self.list_projects() if p.id == project_id), None)

    def add_project(self, name: str, repo_local_path: str) -> ProjectEntry:
        data = self._read()
        projects = data.get("projects", [])
        normalized = str(Path(repo_local_path).resolve())
        for item in projects:
            existing_path = str(Path(item.get("repo_local_path", "")).resolve())
            if existing_path == normalized:
                return ProjectEntry(**item)
        next_id = max([p["id"] for p in projects], default=0) + 1
        entry = ProjectEntry(id=next_id, name=name, repo_local_path=repo_local_path)
        projects.append(asdict(entry))
        data["projects"] = projects
        self._write(data)
        return entry

    def set_active(self, project_id: int) -> None:
        data = self._read()
        data["active_id"] = project_id
        self._write(data)

    def get_active_id(self) -> Optional[int]:
        data = self._read()
        return data.get("active_id")

    def get_active(self) -> Optional[ProjectEntry]:
        active_id = self.get_active_id()
        if active_id is None:
            return None
        return self.get_project(active_id)

    def _read(self) -> dict:
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


def project_data_dir(root: Path) -> Path:
    return root / ".ai_dev_team"


def project_db_url(root: Path) -> str:
    return f"sqlite:///{project_data_dir(root) / 'ai_dev_team.db'}"


def project_attachments_dir(root: Path) -> Path:
    return project_data_dir(root) / "attachments"
