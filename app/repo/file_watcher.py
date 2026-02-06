import asyncio
from pathlib import Path
from typing import Iterable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.core.artifacts import ArtifactStore
from app.core.events import Event, EventBus


class _RepoEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        event_bus: EventBus,
        artifact_store: ArtifactStore,
        run_id: int,
        loop: asyncio.AbstractEventLoop,
        ignore_dirs: Iterable[str],
    ) -> None:
        self.event_bus = event_bus
        self.artifact_store = artifact_store
        self.run_id = run_id
        self.loop = loop
        self.ignore_dirs = set(ignore_dirs)

    def _should_ignore(self, path: str) -> bool:
        for ignored in self.ignore_dirs:
            if ignored in path:
                return True
        return False

    def on_modified(self, event) -> None:
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._handle_event("file.modified", event.src_path)

    def on_created(self, event) -> None:
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._handle_event("file.created", event.src_path)

    def _handle_event(self, event_type: str, path: str) -> None:
        try:
            contents = Path(path).read_text(encoding="utf-8")
        except Exception:
            contents = ""
        self.artifact_store.write_snapshot(self.run_id, path, contents)
        event = Event(type=event_type, payload={"path": path})
        asyncio.run_coroutine_threadsafe(self.event_bus.publish(event), self.loop)


class FileWatcher:
    def __init__(
        self,
        repo_root: Path,
        event_bus: EventBus,
        artifact_store: ArtifactStore,
        run_id: int,
    ) -> None:
        self.repo_root = repo_root
        self.event_bus = event_bus
        self.artifact_store = artifact_store
        self.run_id = run_id
        self._observer: Optional[Observer] = None

    def start(self) -> None:
        if self._observer:
            return
        loop = asyncio.get_event_loop()
        handler = _RepoEventHandler(
            self.event_bus,
            self.artifact_store,
            self.run_id,
            loop,
            ignore_dirs=[".git", ".ai_dev_team", "node_modules"],
        )
        observer = Observer()
        observer.schedule(handler, str(self.repo_root), recursive=True)
        observer.start()
        self._observer = observer

    def stop(self) -> None:
        if not self._observer:
            return
        self._observer.stop()
        self._observer.join()
        self._observer = None
