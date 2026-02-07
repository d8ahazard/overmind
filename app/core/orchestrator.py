from datetime import datetime
import json
from typing import List, Optional

from sqlmodel import select

from pathlib import Path

from app.agents.runtime import AgentRuntime
from app.core.artifacts import ArtifactStore
from app.core.events import Event, EventBus
from app.core.job_engine import JobEngine, JobStepResult
from app.core.memory import MemoryStore
from app.core.verification import Verifier
from app.db.models import AgentConfig, Job, Project, ProjectSetting, Run, Task
from app.db.session import get_session
from app.repo.file_watcher import FileWatcher


class Orchestrator:
    def __init__(
        self,
        event_bus: EventBus,
        artifact_store: ArtifactStore,
        agent_runtime: AgentRuntime,
        default_repo_root: Path,
        job_engine: JobEngine,
        verifier: Verifier,
    ) -> None:
        self.event_bus = event_bus
        self.artifact_store = artifact_store
        self.agent_runtime = agent_runtime
        self.default_repo_root = default_repo_root
        self.memory_store = MemoryStore()
        self.job_engine = job_engine
        self.verifier = verifier

    async def _emit(self, run_id: int, event_type: str, payload: dict) -> None:
        event = Event(type=event_type, payload=payload)
        await self.event_bus.publish(event)
        self.artifact_store.write_event(run_id, event.__dict__)

    def _get_agents(self, team_id: int, session=None) -> List[AgentConfig]:
        if session is None:
            with get_session() as session:
                return list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team_id)))
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

        job_id = self.job_engine.create_job(run_id)
        watcher = FileWatcher(repo_root, self.event_bus, self.artifact_store, run_id)
        await self._emit(
            run_id,
            "run.started",
            {"run_id": run_id, "repo_root": str(repo_root), "job_id": job_id},
        )
        watcher.start()
        try:
            steps = ["scoping", "planning", "collaboration", "executing", "verifying"]
            handlers = {
                "scoping": lambda: self._phase_scoping(run_id),
                "planning": lambda: self._phase_planning(run_id),
                "collaboration": lambda: self._phase_collaboration(run_id),
                "executing": lambda: self._phase_executing(run_id),
                "verifying": lambda: self._phase_verifying(run_id, job_id),
            }
            await self.job_engine.run(job_id, steps, handlers)
            with get_session() as session:
                refreshed = session.get(Job, job_id)
                status = "failed" if refreshed and refreshed.status == "failed" else "completed"
            await self.complete_run(run_id, status=status)
        finally:
            watcher.stop()

    async def _phase_scoping(self, run_id: int) -> JobStepResult:
        await self._emit(run_id, "phase.scoping", {"run_id": run_id})
        return JobStepResult(True)

    async def _phase_planning(self, run_id: int) -> JobStepResult:
        await self._emit(run_id, "phase.planning", {"run_id": run_id})
        return JobStepResult(True)

    async def _phase_collaboration(self, run_id: int) -> JobStepResult:
        await self._emit(run_id, "phase.collaboration", {"run_id": run_id})
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return JobStepResult(False, "run_not_found")
            setting = session.exec(
                select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
            ).first()
            policy = (setting.chat_target_policy if setting else None) or "managers"
            if policy != "team":
                return JobStepResult(True)
            existing = session.exec(select(Task).where(Task.run_id == run.id)).first()
            if existing:
                return JobStepResult(True)
            agents = self._get_agents(run.team_id, session)
        manager = _pick_manager(agents)
        if not manager or not manager.id:
            return JobStepResult(True)
        roles = ", ".join(
            [agent.display_name or agent.role for agent in agents if agent.display_name or agent.role]
        )
        manager_prompt = (
            "You are the team manager. Provide a short directive that mentions "
            "relevant teammates with @mentions and outlines next steps.\n"
            "Then output a JSON object with this schema:\n"
            "{"
            '"directive": "string", '
            '"tasks": ['
            '{"title":"string","description":"string","acceptance_criteria":"string",'
            '"assigned_role":"string"}'
            "]"
            "}\n\n"
            f"Team members: {roles}\n"
            f"Run goal:\n{run.goal}\n"
        )
        response = await self.agent_runtime.run_agent(run.id, manager, manager_prompt)
        response_text = (response.get("content") or "").strip()
        payload = _extract_json_payload(response_text)
        directive = payload.get("directive") if payload else None
        tasks_payload = payload.get("tasks") if payload else []
        if directive:
            manager_message = {
                "agent": manager.display_name or manager.role,
                "role": manager.role,
                "content": directive,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.artifact_store.write_chat(run.id, manager.role, manager_message)
            await self._emit(run.id, "chat.message", manager_message)
        created_tasks = 0
        with get_session() as session:
            for item in tasks_payload or []:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "").strip()
                if not title:
                    continue
                task = Task(
                    run_id=run.id,
                    title=title,
                    description=str(item.get("description") or "") or None,
                    acceptance_criteria=str(item.get("acceptance_criteria") or "") or None,
                    assigned_role=str(item.get("assigned_role") or "") or None,
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                created_tasks += 1
                await self._emit(
                    run.id,
                    "task.created",
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "assigned_role": task.assigned_role,
                    },
                )
        if created_tasks == 0:
            return JobStepResult(True, "no_tasks_created")
        return JobStepResult(True)

    async def _phase_executing(self, run_id: int) -> JobStepResult:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return JobStepResult(False, "run_not_found")
            agents = self._get_agents(run.team_id, session)
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
                    entry = self.memory_store.append(
                        run_id,
                        agent.id,
                        agent.role,
                        response.get("content", ""),
                    )
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
        return JobStepResult(True)

    async def introduce_team(self, run_id: int) -> None:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return
            agents = self._get_agents(run.team_id, session)
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

    async def _phase_verifying(self, run_id: int, job_id: int) -> JobStepResult:
        await self._emit(run_id, "phase.verifying", {"run_id": run_id})
        result = await self.verifier.verify(run_id, job_id)
        return JobStepResult(result.success, result.details)

    async def complete_run(self, run_id: int, status: str = "completed") -> None:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return
            run.status = status
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


def _pick_manager(agents: list[AgentConfig]) -> AgentConfig | None:
    for agent in agents:
        if agent.role in {"Product Owner", "Delivery Manager", "Release Manager"}:
            return agent
    return agents[0] if agents else None


def _extract_json_payload(text: str) -> dict | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        data = json.loads(snippet)
        if isinstance(data, dict):
            return data
    except Exception:
        return None
    return None
