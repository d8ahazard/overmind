from datetime import datetime
from typing import List, Optional

from sqlmodel import select

from pathlib import Path

from app.agents.runtime import AgentRuntime
from app.core.artifacts import ArtifactStore
from app.core.events import Event, EventBus
from app.core.memory import MemoryStore
from app.db.models import AgentConfig, Project, Run, Task
from app.db.session import get_session
from app.repo.file_watcher import FileWatcher


class Orchestrator:
    def __init__(
        self,
        event_bus: EventBus,
        artifact_store: ArtifactStore,
        agent_runtime: AgentRuntime,
        default_repo_root: Path,
    ) -> None:
        self.event_bus = event_bus
        self.artifact_store = artifact_store
        self.agent_runtime = agent_runtime
        self.default_repo_root = default_repo_root
        self.memory_store = MemoryStore()

    async def _emit(self, run_id: int, event_type: str, payload: dict) -> None:
        event = Event(type=event_type, payload=payload)
        await self.event_bus.publish(event)
        self.artifact_store.write_event(run_id, event.__dict__)

    def _get_agents(self, team_id: int) -> List[AgentConfig]:
        with get_session() as session:
            return list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team_id)))

    async def start_run(self, run_id: int) -> None:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                raise ValueError(f"Run {run_id} not found")
            project = session.get(Project, run.project_id)
            repo_root = (
                Path(project.repo_local_path).resolve()
                if project and project.repo_local_path
                else self.default_repo_root
            )
            run.status = "running"
            run.start_time = datetime.utcnow()
            session.add(run)
            session.commit()

        watcher = FileWatcher(repo_root, self.event_bus, self.artifact_store, run_id)
        await self._emit(run_id, "run.started", {"run_id": run_id, "repo_root": str(repo_root)})
        watcher.start()
        try:
            await self.plan(run_id)
            await self.execute(run_id)
            await self.test(run_id)
            await self.review(run_id)
            await self.release(run_id)
            await self.complete_run(run_id)
        finally:
            watcher.stop()

    async def plan(self, run_id: int) -> None:
        await self._emit(run_id, "phase.planning", {"run_id": run_id})

    async def execute(self, run_id: int) -> None:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return
            agents = self._get_agents(run.team_id)
            for agent in agents:
                response = await self.agent_runtime.run_agent(run_id, agent, run.goal)
                self.artifact_store.write_chat(run_id, agent.role, response)
                await self._emit(
                    run_id,
                    "agent.response",
                    {"agent": agent.role, "content": response.get("content")},
                )
                await self._emit(
                    run_id,
                    "chat.message",
                    {
                        "agent": agent.display_name or agent.role,
                        "role": agent.role,
                        "content": response.get("content"),
                    },
                )
                if agent.id:
                    entry = self.memory_store.append(run_id, agent, response.get("content", ""))
                    await self._emit(
                        run_id,
                        "memory.updated",
                        {
                            "agent_id": agent.id,
                            "agent": agent.display_name or agent.role,
                            "content": entry.content,
                            "entry_id": entry.id,
                        },
                    )

    async def introduce_team(self, run_id: int) -> None:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return
            agents = self._get_agents(run.team_id)
            for agent in agents:
                prompt = (
                    "Introduce yourself in one short paragraph. "
                    f"Name: {agent.display_name or agent.role}. "
                    f"Role: {agent.role}. "
                    f"Persona: {agent.personality or 'Professional and concise.'}"
                )
                response = await self.agent_runtime.run_agent(run_id, agent, prompt)
                self.artifact_store.write_chat(run_id, agent.role, response)
                await self._emit(
                    run_id,
                    "chat.message",
                    {
                        "agent": agent.display_name or agent.role,
                        "role": agent.role,
                        "content": response.get("content"),
                    },
                )

    async def test(self, run_id: int) -> None:
        await self._emit(run_id, "phase.testing", {"run_id": run_id})

    async def review(self, run_id: int) -> None:
        await self._emit(run_id, "phase.review", {"run_id": run_id})

    async def release(self, run_id: int) -> None:
        await self._emit(run_id, "phase.release", {"run_id": run_id})

    async def complete_run(self, run_id: int) -> None:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return
            run.status = "completed"
            run.end_time = datetime.utcnow()
            session.add(run)
            session.commit()
        await self._emit(run_id, "run.completed", {"run_id": run_id})

    def create_task(
        self,
        run_id: int,
        title: str,
        description: Optional[str] = None,
        assigned_role: Optional[str] = None,
    ) -> Task:
        with get_session() as session:
            task = Task(
                run_id=run_id,
                title=title,
                description=description,
                assigned_role=assigned_role,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task
