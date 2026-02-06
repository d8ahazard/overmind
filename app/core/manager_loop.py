import asyncio
import json
from datetime import datetime
from typing import Optional

from sqlmodel import select

from app.core.events import Event, EventBus
from app.core.chat_router import MANAGER_ROLES
from app.core.tool_broker import ToolRequest
from app.db.models import AgentConfig, Run, Task, Team
from app.db.session import get_session


class ManagerLoop:
    def __init__(
        self,
        event_bus: EventBus,
        get_active_project_id,
        agent_runtime,
        tool_broker,
        artifact_store,
    ) -> None:
        self.event_bus = event_bus
        self.get_active_project_id = get_active_project_id
        self.agent_runtime = agent_runtime
        self.tool_broker = tool_broker
        self.artifact_store = artifact_store
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception:
                pass
            await asyncio.sleep(2)

    async def _tick(self) -> None:
        project_id = self.get_active_project_id()
        if project_id is None:
            return
        with get_session() as session:
            tasks = list(
                session.exec(
                    select(Task)
                    .where(Task.status == "pending")
                    .order_by(Task.created_at.asc())
                )
            )
        for task in tasks[:3]:
            await self._handle_task(task.id)

    async def _handle_task(self, task_id: int) -> None:
        with get_session() as session:
            task = session.get(Task, task_id)
            if not task or task.status != "pending":
                return
            if task.attempts >= 3:
                task.status = "failed"
                task.updated_at = datetime.utcnow()
                session.add(task)
                session.commit()
                await self._emit(
                    task.run_id,
                    "task.failed",
                    {"task_id": task.id, "reason": "max_attempts"},
                )
                return
            run = session.get(Run, task.run_id)
            if not run:
                return
            team = session.get(Team, run.team_id)
            agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team.id)))
            manager = _pick_manager(agents)
            assigned = _pick_agent(agents, task)
            if not assigned:
                return
            task.status = "in_progress"
            task.assigned_role = assigned.role
            task.attempts += 1
            task.updated_at = datetime.utcnow()
            session.add(task)
            session.commit()

        await self._emit(
            run.id,
            "task.started",
            {"task_id": task.id, "assigned_role": assigned.role, "title": task.title},
        )

        prompt = (
            f"Task: {task.title}\n"
            f"Details: {task.description or ''}\n"
            "If a tool is required, respond with ONLY JSON:\n"
            '{\"tool\":\"system.run\",\"arguments\":{\"command\":\"whoami\"}}'
        )
        response = await self.agent_runtime.run_agent(run.id, assigned, prompt)
        response_text = (response.get("content") or "").strip()
        tool_call = _extract_tool_call(response_text)
        if tool_call:
            response_text = await self._execute_tool_call(
                tool_call, assigned, run.id
            )

        review_text = response_text
        if manager:
            review_prompt = (
                f"Task: {task.title}\n"
                f"Assigned role: {assigned.role}\n"
                f"Worker output: {response_text}\n\n"
                "If acceptable, respond with ONLY: APPROVED.\n"
                "If rework is needed, respond with ONLY: RETRY and a brief reason."
            )
            review = await self.agent_runtime.run_agent(run.id, manager, review_prompt)
            review_text = (review.get("content") or "").strip()
            await self._emit(
                run.id,
                "task.reviewed",
                {"task_id": task.id, "reviewer": manager.role, "review": review_text},
            )

        with get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return
            if manager and review_text.startswith("RETRY"):
                task.status = "pending"
                task.updated_at = datetime.utcnow()
                session.add(task)
                session.commit()
                await self._emit(
                    run.id,
                    "task.requeued",
                    {"task_id": task.id, "reason": review_text},
                )
                return
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.updated_at = datetime.utcnow()
            session.add(task)
            session.commit()

        await self._emit(
            run.id,
            "task.completed",
            {
                "task_id": task.id,
                "summary": response_text,
                "assigned_role": assigned.role,
                "review": review_text if manager else None,
            },
        )

    async def _execute_tool_call(self, tool_call: dict, agent: AgentConfig, run_id: int) -> str:
        tool_name = tool_call.get("tool")
        arguments = tool_call.get("arguments") or {}
        required_scopes = ["system:run"] if tool_name == "system.run" else ["mcp:call"]
        actor_scopes = [
            item.strip() for item in (agent.permissions or "").split(",") if item.strip()
        ]
        tool_request = ToolRequest(
            tool_name=tool_name,
            arguments=arguments,
            required_scopes=required_scopes,
            actor=agent.display_name or agent.role,
            run_id=run_id,
        )
        result = await self.tool_broker.execute_async(tool_request, actor_scopes)
        if not result.success:
            return f"Tool execution blocked: {result.error}"
        return json.dumps(result.output or {}, ensure_ascii=True)

    async def _emit(self, run_id: int, event_type: str, payload: dict) -> None:
        event = Event(type=event_type, payload=payload)
        self.artifact_store.write_event(run_id, event.__dict__)
        await self.event_bus.publish(event)


def _extract_tool_call(text: str) -> dict | None:
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get("tool") and data.get("arguments"):
                return data
        except Exception:
            return None
    return None


def _pick_agent(agents: list[AgentConfig], task: Task) -> Optional[AgentConfig]:
    if not agents:
        return None
    if task.assigned_role:
        for agent in agents:
            if agent.role == task.assigned_role:
                return agent
    keywords = {
        "qa": ["test", "bug", "regression", "qa", "verify"],
        "devops": ["deploy", "ci", "pipeline", "infra", "release"],
        "docs": ["docs", "documentation", "readme", "guide"],
        "dev": ["code", "implement", "fix", "refactor", "build"],
        "pm": ["scope", "plan", "requirements", "roadmap"],
    }
    text = f"{task.title} {task.description or ''}".lower()
    scored: list[tuple[int, AgentConfig]] = []
    for agent in agents:
        role = agent.role.lower()
        score = 0
        for key, words in keywords.items():
            if key in role:
                score += sum(1 for w in words if w in text) * 2
            else:
                score += sum(1 for w in words if w in text)
        scored.append((score, agent))
    scored.sort(key=lambda item: item[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return agents[0]


def _pick_manager(agents: list[AgentConfig]) -> Optional[AgentConfig]:
    for agent in agents:
        if agent.role in MANAGER_ROLES:
            return agent
    return agents[0] if agents else None
