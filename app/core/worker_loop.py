import asyncio
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import select

from app.core.events import Event, EventBus
from app.core.tool_dispatcher import execute_tool_call, extract_tool_call
from app.db.models import AgentConfig, ProjectSetting, Run, Task, Team
from app.db.session import get_session
from app.core.chat_router import MANAGER_ROLES


class WorkerLoop:
    def __init__(
        self,
        event_bus: EventBus,
        get_active_project_id,
        agent_runtime,
        tool_broker,
        artifact_store,
        repo_root,
        allow_self_edit: bool,
    ) -> None:
        self.event_bus = event_bus
        self.get_active_project_id = get_active_project_id
        self.agent_runtime = agent_runtime
        self.tool_broker = tool_broker
        self.artifact_store = artifact_store
        self._running = False
        self._idle_prompted: dict[int, datetime] = {}
        self._manager_prompted: dict[int, datetime] = {}
        self._chat_seen: dict[int, list[str]] = {}
        self.repo_root = repo_root
        self.allow_self_edit = allow_self_edit

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
            run = session.exec(
                select(Run).where(Run.project_id == project_id).order_by(Run.id.desc())
            ).first()
            agents = (
                list(session.exec(select(AgentConfig).where(AgentConfig.team_id == run.team_id)))
                if run
                else []
            )
        for task in tasks[:5]:
            await self._handle_task(task.id)
        if run:
            if run.pause_mode:
                return
            await self._prompt_idle(run, agents)
            await self._process_chat(run, agents)

    async def _handle_task(self, task_id: int) -> None:
        with get_session() as session:
            task = session.get(Task, task_id)
            if not task or task.status != "pending":
                return
            run = session.get(Run, task.run_id)
            if not run:
                return
            team = session.get(Team, run.team_id)
            agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team.id)))
            setting = session.exec(
                select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
            ).first()
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

        tool_note = (
            "If you need to edit code, use ONLY JSON tool calls like:\n"
            '{"tool":"file.read","arguments":{"path":"src/app.ts"}}\n'
            '{"tool":"file.replace","arguments":{"path":"src/app.ts","old":"foo","new":"bar"}}\n'
            '{"tool":"file.write","arguments":{"path":"src/app.ts","content":"..."}}\n'
            "When done, create a branch/commit/PR:\n"
            '{"tool":"git.branch","arguments":{"name":"feature/short-desc"}}\n'
            '{"tool":"git.commit","arguments":{"message":"Describe change"}}\n'
            '{"tool":"git.create_pr","arguments":{"branch":"feature/short-desc"}}\n'
        )
        prompt = (
            f"Task: {task.title}\n"
            f"Details: {task.description or ''}\n"
            "Work autonomously and report progress. "
            "If blocked or done, ask @po or @dm for next steps.\n"
            "If a tool is required, respond with ONLY JSON:\n"
            '{\"tool\":\"system.run\",\"arguments\":{\"command\":\"whoami\"}}\n'
            + (tool_note if "developer" in assigned.role.lower() or "engineer" in assigned.role.lower() else "")
        )
        response = await self.agent_runtime.run_agent(run.id, assigned, prompt)
        response_text = (response.get("content") or "").strip()
        tool_call = extract_tool_call(response_text)
        if tool_call:
            allow_file_edits = bool(setting and setting.auto_execute_edits) and (
                "developer" in assigned.role.lower() or "engineer" in assigned.role.lower()
            )
            response_text = await execute_tool_call(
                tool_call,
                broker=self.tool_broker,
                agent=assigned,
                run_id=run.id,
                repo_root=self.repo_root,
                allow_self_edit=self.allow_self_edit,
                extra_allowed_roots=None,
                allow_file_edits=allow_file_edits,
                event_bus=self.event_bus,
                artifact_store=self.artifact_store,
            )

        worker_message = {
            "agent": assigned.display_name or assigned.role,
            "role": assigned.role,
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.artifact_store.write_chat(run.id, assigned.role, worker_message)
        await self._emit(run.id, "chat.message", worker_message)

        with get_session() as session:
            task = session.get(Task, task_id)
            if not task:
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
                "review": None,
            },
        )

    async def _prompt_idle(self, run: Run, agents: list[AgentConfig]) -> None:
        now = datetime.utcnow()
        cooldown = timedelta(minutes=3)
        idle_agents: list[str] = []
        for agent in agents:
            if agent.role in MANAGER_ROLES or not agent.id:
                continue
            last = self._idle_prompted.get(agent.id)
            if last and now - last < cooldown:
                continue
            message = {
                "message_id": f"idle-{agent.id}-{int(now.timestamp())}",
                "agent": agent.display_name or agent.role,
                "role": agent.role,
                "content": "I'm idle. @Ava, what should I tackle next?",
                "timestamp": now.isoformat(),
            }
            self.artifact_store.write_chat(run.id, agent.role, message)
            await self._emit(run.id, "chat.message", message)
            self._idle_prompted[agent.id] = now
            idle_agents.append(agent.display_name or agent.role)

        if idle_agents:
            manager = _pick_manager(agents)
            if manager:
                last_manager = self._manager_prompted.get(run.id)
                if not last_manager or now - last_manager >= cooldown:
                    assigned_role = (
                        manager.role if manager.role in MANAGER_ROLES else None
                    )
                    await self._create_manager_task(run, manager, idle_agents, assigned_role)
                    self._manager_prompted[run.id] = now

    async def _create_manager_task(
        self,
        run: Run,
        manager: AgentConfig,
        idle_agents: list[str],
        assigned_role: str | None,
    ) -> None:
        title = "Assign work to idle team members"
        description = (
            "Team members are idle and asking for work: "
            + ", ".join(idle_agents)
            + ". Provide next steps and assignments."
        )
        with get_session() as session:
            task = Task(
                run_id=run.id,
                title=title,
                description=description,
                assigned_role=assigned_role,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            await self._emit(
                run.id,
                "task.created",
                {"task_id": task.id, "title": task.title, "assigned_role": task.assigned_role},
            )

    async def _process_chat(self, run: Run, agents: list[AgentConfig]) -> None:
        messages = self.artifact_store.read_chats(run.id)
        if not messages:
            return
        with get_session() as session:
            setting = session.exec(
                select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
            ).first()
        for agent in agents:
            if not agent.id:
                continue
            seen = self._chat_seen.get(agent.id, [])
            processed = 0
            for msg in messages:
                message_id = msg.get("message_id") or f"{msg.get('agent')}:{msg.get('timestamp')}:{msg.get('content')}"
                if message_id in seen:
                    continue
                seen.append(message_id)
                if len(seen) > 200:
                    seen = seen[-200:]
                sender = str(msg.get("agent") or "")
                if sender.lower() in {
                    (agent.display_name or "").lower(),
                    agent.role.lower(),
                }:
                    continue
                prompt = (
                    "Incoming team message:\n"
                    f"From: {sender}\n"
                    f"Content: {msg.get('content')}\n\n"
                    "Decide if you should respond. If yes, respond with a concise update or action. "
                    "If not needed, respond with ONLY: NO_RESPONSE.\n"
                    "If you are blocked or done, ask @po or @dm what to do next. "
                    "Use role tags like @po, @dm, @tl, @dev, @qa, @rm when appropriate."
                )
                response = await self.agent_runtime.run_agent(run.id, agent, prompt)
                response_text = (response.get("content") or "").strip()
                tool_call = extract_tool_call(response_text)
                if tool_call:
                    allow_file_edits = bool(setting and setting.auto_execute_edits) and (
                        "developer" in agent.role.lower()
                        or "engineer" in agent.role.lower()
                    )
                    response_text = await execute_tool_call(
                        tool_call,
                        broker=self.tool_broker,
                        agent=agent,
                        run_id=run.id,
                        repo_root=self.repo_root,
                        allow_self_edit=self.allow_self_edit,
                        extra_allowed_roots=None,
                        allow_file_edits=allow_file_edits,
                        event_bus=self.event_bus,
                        artifact_store=self.artifact_store,
                    )
                if response_text.upper() == "NO_RESPONSE":
                    processed += 1
                    if processed >= 2:
                        break
                    continue
                agent_message = {
                    "message_id": f"auto-{agent.id}-{int(datetime.utcnow().timestamp())}",
                    "agent": agent.display_name or agent.role,
                    "role": agent.role,
                    "content": response_text,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                self.artifact_store.write_chat(run.id, agent.role, agent_message)
                await self._emit(run.id, "chat.message", agent_message)
                processed += 1
                if processed >= 2:
                    break
            self._chat_seen[agent.id] = seen

    async def _emit(self, run_id: int, event_type: str, payload: dict) -> None:
        event = Event(type=event_type, payload=payload)
        self.artifact_store.write_event(run_id, event.__dict__)
        await self.event_bus.publish(event)




def _pick_agent(agents: list[AgentConfig], task: Task) -> Optional[AgentConfig]:
    if not agents:
        return None
    if task.assigned_role:
        for agent in agents:
            if agent.role == task.assigned_role:
                return agent
    for agent in agents:
        if agent.role not in MANAGER_ROLES:
            return agent
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
