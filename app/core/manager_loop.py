import asyncio
import json
import re
from datetime import datetime
from typing import Optional

from sqlmodel import select

from app.core.events import Event, EventBus
from app.core.chat_router import ChatRouter, MANAGER_ROLES
from app.core.tool_broker import ToolRequest
from app.core.git_tools import execute_git_tool
from app.core.shell import is_destructive_command
from app.db.models import AgentConfig, ProjectSetting, Run, Task, Team
from app.db.session import get_session


class ManagerLoop:
    def __init__(
        self,
        event_bus: EventBus,
        get_active_project_id,
        agent_runtime,
        tool_broker,
        artifact_store,
        repo_root,
    ) -> None:
        self.event_bus = event_bus
        self.get_active_project_id = get_active_project_id
        self.agent_runtime = agent_runtime
        self.tool_broker = tool_broker
        self.artifact_store = artifact_store
        self.chat_router = ChatRouter()
        self.repo_root = repo_root
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
                    .where(
                        Task.status == "pending",
                        (Task.assigned_role == None)  # noqa: E711
                        | (Task.assigned_role.in_(list(MANAGER_ROLES))),
                    )
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
            run = session.get(Run, task.run_id)
            if not run:
                return
            retry_limit = 3
            setting = session.exec(
                select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
            ).first()
            if setting and setting.task_retry_limit:
                retry_limit = max(1, int(setting.task_retry_limit))
            if task.attempts >= retry_limit:
                task.status = "failed"
                task.updated_at = datetime.utcnow()
                session.add(task)
                session.commit()
                await self._emit(
                    task.run_id,
                    "task.failed",
                    {"task_id": task.id, "reason": f"max_attempts:{retry_limit}"},
                )
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
            "Coordinate with teammates using @mentions when needed.\n"
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
        worker_message = {
            "agent": assigned.display_name or assigned.role,
            "role": assigned.role,
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.artifact_store.write_chat(run.id, assigned.role, worker_message)
        await self._emit(run.id, "chat.message", worker_message)

        review_text = response_text
        if manager:
            review_prompt = (
                f"Task: {task.title}\n"
                f"Assigned role: {assigned.role}\n"
                f"Worker output: {response_text}\n\n"
                "If acceptable, respond with ONLY: APPROVED.\n"
                "If rework is needed, respond with ONLY: RETRY and a brief reason.\n"
                "If delegating follow-up, mention teammates with @mentions."
            )
            review = await self.agent_runtime.run_agent(run.id, manager, review_prompt)
            review_text = (review.get("content") or "").strip()
            review_message = {
                "agent": manager.display_name or manager.role,
                "role": manager.role,
                "content": review_text,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.artifact_store.write_chat(run.id, manager.role, review_message)
            await self._emit(run.id, "chat.message", review_message)
            await self._emit(
                run.id,
                "task.reviewed",
                {"task_id": task.id, "reviewer": manager.role, "review": review_text},
            )
            if _has_mentions(review_text):
                await self._trigger_followups(run, manager, review_text)

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
        if tool_name == "system.run":
            if is_destructive_command(arguments.get("command")):
                return "Tool execution blocked: approval_required"
            required_scopes = ["system:run"]
        elif tool_name and tool_name.startswith("git."):
            if tool_name not in self.tool_broker.executors:
                self.tool_broker.register(
                    tool_name,
                    lambda tool_request: execute_git_tool(tool_request, self.repo_root),
                )
            required_scopes = [f"git:{tool_name.split('.', 1)[1]}"]
        else:
            required_scopes = ["mcp:call"]
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

    async def _trigger_followups(
        self, run: Run, manager: AgentConfig, message: str
    ) -> None:
        targets = self.chat_router.resolve_targets(run.team_id, message, "team")
        targets = [agent for agent in targets if agent.id and agent.id != manager.id]
        if not targets:
            return
        for agent in targets:
            prompt = (
                f"Manager directive:\n{message}\n\n"
                "Respond with your next actions. "
                "If you are blocked or done, ask @po or @dm what to do next."
            )
            response = await self.agent_runtime.run_agent(run.id, agent, prompt)
            response_text = (response.get("content") or "").strip()
            agent_message = {
                "agent": agent.display_name or agent.role,
                "role": agent.role,
                "content": response_text,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.artifact_store.write_chat(run.id, agent.role, agent_message)
            await self._emit(run.id, "chat.message", agent_message)


def _has_mentions(text: str) -> bool:
    return bool(re.search(r"@([\\w\\-]+)", text or ""))


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
    if not agents:
        return None
    for agent in agents:
        if (agent.display_name or "").lower() == "ava":
            return agent
    for role in ("Product Owner", "Delivery Manager", "Release Manager"):
        for agent in agents:
            if agent.role == role:
                return agent
    return agents[0]
