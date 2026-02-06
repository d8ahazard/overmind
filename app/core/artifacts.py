import json
from pathlib import Path
from typing import Any, Dict


class ArtifactStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def _run_dir(self, run_id: int) -> Path:
        return self.base_dir / "runs" / str(run_id)

    def _ensure_dirs(self, run_id: int) -> None:
        run_dir = self._run_dir(run_id)
        for folder in ("chats", "artifacts", "events", "snapshots"):
            (run_dir / folder).mkdir(parents=True, exist_ok=True)

    def write_event(self, run_id: int, event: Dict[str, Any]) -> Path:
        self._ensure_dirs(run_id)
        path = self._run_dir(run_id) / "events" / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")
        return path

    def write_chat(self, run_id: int, role: str, message: Dict[str, Any]) -> Path:
        self._ensure_dirs(run_id)
        path = self._run_dir(run_id) / "chats" / f"{role}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message, ensure_ascii=True) + "\n")
        return path

    def write_artifact(self, run_id: int, artifact: Dict[str, Any]) -> Path:
        self._ensure_dirs(run_id)
        name = artifact.get("type", "artifact").lower()
        path = self._run_dir(run_id) / "artifacts" / f"{name}.json"
        with path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(artifact, ensure_ascii=True, indent=2))
        return path

    def write_snapshot(self, run_id: int, file_path: str, contents: str) -> Path:
        self._ensure_dirs(run_id)
        safe_name = file_path.replace("/", "_").replace("\\", "_")
        path = self._run_dir(run_id) / "snapshots" / f"{safe_name}.txt"
        with path.open("w", encoding="utf-8") as handle:
            handle.write(contents)
        return path
