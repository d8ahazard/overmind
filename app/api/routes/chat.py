from datetime import datetime
import json
import uuid
import re

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlmodel import select

from app.core.chat_router import ChatRouter, MANAGER_ROLES
from app.core.events import Event
from app.core.memory import MemoryStore
from app.core.artifacts import ArtifactStore
from app.core.orchestrator import Orchestrator
from app.core.shell import execute_shell_tool, is_destructive_command
from app.core.git_tools import execute_git_tool
from app.integrations.mcp_client import MCPClient
from app.core.tool_broker import ToolRequest, ToolResult
from app.core.project_registry import project_attachments_dir
from app.db.models import AgentConfig, ProjectSetting, Run, Team, Task
from app.db.session import get_session

router = APIRouter()
router_helper = ChatRouter()
memory = MemoryStore()
@router.get("/history")
def chat_history(request: Request, run_id: int | None = None) -> dict:
    with get_session() as session:
        run = session.get(Run, int(run_id)) if run_id else None
        if not run:
            active_project_id = request.app.state.active_project_id
            if active_project_id is None:
                raise HTTPException(status_code=404, detail="Active project not set")
            run = session.exec(
                select(Run)
                .where(Run.project_id == active_project_id)
                .order_by(Run.id.desc())
            ).first()
        if not run:
            return {"run_id": None, "messages": []}
    store = ArtifactStore(request.app.state.data_dir)
    return {"run_id": run.id, "messages": store.read_chats(run.id)}


@router.post("/send")
async def send_message(payload: dict, request: Request) -> dict:
    run_id = payload.get("run_id")
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    with get_session() as session:
        run = session.get(Run, int(run_id)) if run_id else None
        if not run:
            active_project_id = request.app.state.active_project_id
            if active_project_id is None:
                raise HTTPException(status_code=404, detail="Active project not set")
            run = session.exec(
                select(Run)
                .where(Run.project_id == active_project_id)
                .order_by(Run.id.desc())
            ).first()
        if not run:
            team = session.exec(
                select(Team)
                .where(Team.project_id == request.app.state.active_project_id)
                .order_by(Team.id.desc())
            ).first()
            if not team:
                raise HTTPException(status_code=404, detail="No team available for chat")
            run = Run(project_id=team.project_id, team_id=team.id, goal="Ad-hoc chat")
            session.add(run)
            session.commit()
            session.refresh(run)
        setting = session.exec(
            select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
        ).first()
        chat_policy = (setting.chat_target_policy if setting else None) or "managers"

        targets = router_helper.resolve_targets(run.team_id, message, chat_policy)
        if not message.strip().lower().startswith("@"):
            best_agent = _pick_best_agent(run.team_id, message)
            if best_agent and best_agent not in targets:
                targets.append(best_agent)

    event_bus = request.app.state.event_bus
    artifacts = ArtifactStore(request.app.state.data_dir)
    agent_runtime = request.app.state.orchestrator.agent_runtime
    tool_broker = request.app.state.tool_broker
    stakeholder_message = {
        "message_id": str(uuid.uuid4()),
        "agent": "Stakeholder",
        "role": "Stakeholder",
        "content": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    artifacts.write_chat(run.id, "Stakeholder", stakeholder_message)
    stakeholder_event = Event(
        type="chat.message",
        payload={
            **stakeholder_message,
            "targets": [t.display_name or t.role for t in targets],
        },
    )
    artifacts.write_event(run.id, stakeholder_event.__dict__)
    await event_bus.publish(stakeholder_event)

    await event_bus.publish(
        Event(
            type="notification.requested",
            payload={
                "title": "Stakeholder feedback",
                "body": message,
                "targets": [t.display_name or t.role for t in targets],
            },
        )
    )

    has_mention = "@" in message
    team_broadcast = bool(re.search(r"@(?:all|team|everyone)\\b", (message or "").lower()))
    manager = None
    manager_briefed = False
    if not has_mention:
        with get_session() as session:
            agents = list(
                session.exec(select(AgentConfig).where(AgentConfig.team_id == run.team_id))
            )
        manager = _pick_manager(agents)
        if manager and manager.id:
            await event_bus.publish(
                Event(
                    type="agent.thinking",
                    payload={
                        "agent": manager.display_name or manager.role,
                        "role": manager.role,
                        "reason": "manager_planning",
                    },
                )
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
                f"Stakeholder request:\n{message}\n"
            )
            manager_response = await agent_runtime.run_agent(run.id, manager, manager_prompt)
            manager_text = (manager_response.get("content") or "").strip()
            manager_payload = _extract_json_payload(manager_text)
            directive = None
            tasks_payload = []
            if manager_payload:
                directive = manager_payload.get("directive")
                tasks_payload = manager_payload.get("tasks") or []
            if directive:
                manager_message = {
                    "message_id": str(uuid.uuid4()),
                    "agent": manager.display_name or manager.role,
                    "role": manager.role,
                    "content": directive,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                artifacts.write_chat(run.id, manager.role, manager_message)
                await event_bus.publish(Event(type="chat.message", payload=manager_message))
                memory.append(run.id, manager.id, manager.role, f"Manager: {directive}")
                manager_briefed = True
                await _trigger_agent_followups(
                    run,
                    manager,
                    directive,
                    router_helper,
                    agent_runtime,
                    tool_broker,
                    artifacts,
                    event_bus,
                    memory,
                )

            created_tasks = 0
            with get_session() as session:
                for item in tasks_payload:
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
                    task_event = Event(
                        type="task.created",
                        payload={
                            "task_id": task.id,
                            "title": task.title,
                            "assigned_role": task.assigned_role,
                        },
                    )
                    artifacts.write_event(run.id, task_event.__dict__)
                    await event_bus.publish(task_event)

            if created_tasks == 0:
                with get_session() as session:
                    task = Task(
                        run_id=run.id,
                        title=f"Stakeholder request: {message[:80]}",
                        description=message,
                        assigned_role=targets[0].role if targets else None,
                    )
                    session.add(task)
                    session.commit()
                    session.refresh(task)
                    task_event = Event(
                        type="task.created",
                        payload={
                            "task_id": task.id,
                            "title": task.title,
                            "assigned_role": task.assigned_role,
                        },
                    )
                    artifacts.write_event(run.id, task_event.__dict__)
                    await event_bus.publish(task_event)

    if manager_briefed and manager:
        targets = [agent for agent in targets if agent.id != manager.id]
    response_prompt = (
        "Incoming stakeholder message:\n"
        f"{message}\n\n"
        "If a response is required, reply with a concise response. "
        "Address teammates with @mentions when coordinating work. "
        "Use role tags like @po, @dm, @tl, @dev, @qa, @rm when appropriate. "
        "If no response is needed, return exactly: NO_RESPONSE.\n"
        "If a tool is required, respond with ONLY a JSON object:\n"
        '{\"tool\":\"system.run\",\"arguments\":{\"command\":\"whoami\"}}'
    )

    async def _run_agent_response(agent: AgentConfig, prompt: str, allow_no_response: bool) -> str | None:
        if not agent.id:
            return None
        memory.append(run.id, agent.id, agent.role, f"Stakeholder: {message}")
        await event_bus.publish(
            Event(
                type="memory.updated",
                payload={
                    "agent_id": agent.id,
                    "agent": agent.display_name or agent.role,
                    "content": f"Stakeholder: {message}",
                },
            )
        )
        response = await agent_runtime.run_agent(run.id, agent, prompt)
        response_text = (response.get("content") or "").strip()
        tool_call = _extract_tool_call(response_text)
        if tool_call:
            tool_result = await _execute_tool_call(
                tool_call, request, tool_broker, agent, run.id
            )
            response_text = tool_result
        if allow_no_response and response_text.upper() == "NO_RESPONSE":
            return None
        agent_message = {
            "message_id": str(uuid.uuid4()),
            "agent": agent.display_name or agent.role,
            "role": agent.role,
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        artifacts.write_chat(run.id, agent.role, agent_message)
        agent_event = Event(
            type="agent.response",
            payload={"agent": agent.role, "content": response_text},
        )
        chat_event = Event(type="chat.message", payload=agent_message)
        artifacts.write_event(run.id, agent_event.__dict__)
        artifacts.write_event(run.id, chat_event.__dict__)
        await event_bus.publish(agent_event)
        await event_bus.publish(chat_event)
        memory.append(run.id, agent.id, agent.role, f"Agent: {response_text}")
        return response_text

    team_updates: list[str] = []
    for agent in targets:
        if has_mention:
            prompt = (
                f"{message}\n\n"
                "You must respond with a status update and next action. "
                "When responding, address teammates with @mentions as needed. "
                "Use role tags like @po, @dm, @tl, @dev, @qa, @rm when appropriate. "
                "If you are blocked or done, ask @po or @dm what to do next."
            )
            allow_no_response = False
        else:
            prompt = response_prompt
            allow_no_response = True
        response_text = await _run_agent_response(agent, prompt, allow_no_response)
        if response_text:
            team_updates.append(f"{agent.role}: {response_text}")

    if team_broadcast and manager and manager.id:
        for _ in range(2):
            await event_bus.publish(
                Event(
                    type="agent.thinking",
                    payload={
                        "agent": manager.display_name or manager.role,
                        "role": manager.role,
                        "reason": "manager_followup",
                    },
                )
            )
            followup_prompt = (
                "Review team updates and decide next steps.\n"
                "If no further action is needed, respond with ONLY: NO_FURTHER_ACTION.\n"
                "Otherwise, respond with a short directive that includes @mentions.\n\n"
                "Team updates:\n" + "\n".join(team_updates)
            )
            manager_response = await agent_runtime.run_agent(run.id, manager, followup_prompt)
            manager_text = (manager_response.get("content") or "").strip()
            if manager_text.upper().startswith("NO_FURTHER_ACTION"):
                break
            manager_message = {
                "message_id": str(uuid.uuid4()),
                "agent": manager.display_name or manager.role,
                "role": manager.role,
                "content": manager_text,
                "timestamp": datetime.utcnow().isoformat(),
            }
            artifacts.write_chat(run.id, manager.role, manager_message)
            await event_bus.publish(Event(type="chat.message", payload=manager_message))
            memory.append(run.id, manager.id, manager.role, f"Manager: {manager_text}")
            await _trigger_agent_followups(
                run,
                manager,
                manager_text,
                router_helper,
                agent_runtime,
                tool_broker,
                artifacts,
                event_bus,
                memory,
            )

            for agent in targets:
                if not agent.id or agent.id == manager.id:
                    continue
                agent_prompt = (
                    f"Manager directive:\n{manager_text}\n\n"
                    "Respond with your next actions. "
                    "If you are blocked or done, ask @po or @dm what to do next."
                )
                response_text = await _run_agent_response(agent, agent_prompt, False)
                if response_text:
                    team_updates.append(f"{agent.role}: {response_text}")

    return {
        "status": "ok",
        "run_id": run.id,
        "targets": [t.display_name or t.role for t in targets],
    }


async def _trigger_agent_followups(
    run: Run,
    manager: AgentConfig,
    message: str,
    router: ChatRouter,
    agent_runtime,
    tool_broker,
    artifacts,
    event_bus,
    memory_store,
) -> None:
    targets = router.resolve_targets(run.team_id, message, "team")
    targets = [agent for agent in targets if agent.id and agent.id != manager.id]
    if not targets:
        return
    for agent in targets:
        prompt = (
            f"Manager directive:\n{message}\n\n"
            "Respond with your next actions. "
            "If you are blocked or done, ask @po or @dm what to do next."
        )
        response = await agent_runtime.run_agent(run.id, agent, prompt)
        response_text = (response.get("content") or "").strip()
        agent_message = {
            "message_id": str(uuid.uuid4()),
            "agent": agent.display_name or agent.role,
            "role": agent.role,
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        artifacts.write_chat(run.id, agent.role, agent_message)
        agent_event = Event(
            type="agent.response",
            payload={"agent": agent.role, "content": response_text},
        )
        chat_event = Event(type="chat.message", payload=agent_message)
        artifacts.write_event(run.id, agent_event.__dict__)
        artifacts.write_event(run.id, chat_event.__dict__)
        await event_bus.publish(agent_event)
        await event_bus.publish(chat_event)
        memory_store.append(run.id, agent.id, agent.role, f"Agent: {response_text}")


def _pick_best_agent(team_id: int, message: str) -> AgentConfig | None:
    keywords = {
        "qa": ["test", "bug", "regression", "qa", "verify"],
        "devops": ["deploy", "ci", "pipeline", "infra", "release"],
        "docs": ["docs", "documentation", "readme", "guide"],
        "dev": ["code", "implement", "fix", "refactor", "build"],
        "pm": ["scope", "plan", "requirements", "roadmap"],
    }
    text = message.lower()
    with get_session() as session:
        agents = list(session.exec(select(AgentConfig).where(AgentConfig.team_id == team_id)))
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
    return None


def _pick_manager(agents: list[AgentConfig]) -> AgentConfig | None:
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
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        data = json.loads(snippet)
        if isinstance(data, dict) and data.get("tool") and data.get("arguments"):
            return data
    except Exception:
        return None
    return None


async def _execute_tool_call(
    tool_call: dict,
    request: Request,
    broker,
    agent: AgentConfig,
    run_id: int,
) -> str:
    tool_name = tool_call.get("tool")
    arguments = tool_call.get("arguments") or {}
    if tool_name not in {"system.run", "mcp.call"} and not tool_name.startswith("git."):
        return f"Tool execution blocked: unknown tool {tool_name}."

    if tool_name == "system.run":
        if "system.run" not in broker.executors:
            broker.register("system.run", execute_shell_tool)
        if "cwd" not in arguments:
            arguments["cwd"] = str(request.app.state.active_project_root)
        if "allowed_roots" not in arguments:
            allowed = [str(request.app.state.active_project_root)]
            if request.app.state.settings.allow_self_edit:
                allowed.append(str(request.app.state.settings.repo_root))
            arguments["allowed_roots"] = allowed
        required_scopes = ["system:run"]
        destructive = is_destructive_command(arguments.get("command"))
        if destructive and not tool_call.get("approval_id"):
            return "Tool execution blocked: approval_required"
        risk_level = "critical" if destructive else "low"
    elif tool_name.startswith("git."):
        if tool_name not in broker.executors:
            broker.register(
                tool_name,
                lambda tool_request: execute_git_tool(
                    tool_request, request.app.state.active_project_root
                ),
            )
        required_scopes = [f"git:{tool_name.split('.', 1)[1]}"]
        risk_level = "high" if tool_name == "git.merge" else "low"
    else:
        if "mcp.call" not in broker.executors:
            async def _executor(tool_request: ToolRequest):
                client = MCPClient(tool_request.arguments["url"])
                await client.initialize()
                result = await client.call_tool(
                    tool_request.arguments["name"],
                    tool_request.arguments.get("arguments", {}),
                )
                return ToolResult(success=True, output=result)
            broker.register("mcp.call", _executor)
        required_scopes = ["mcp:call"]
        risk_level = "low"

    actor_scopes = [
        item.strip() for item in (agent.permissions or "").split(",") if item.strip()
    ]
    tool_request = ToolRequest(
        tool_name=tool_name,
        arguments=arguments,
        required_scopes=required_scopes,
        actor=agent.display_name or agent.role,
        risk_level=risk_level,
        run_id=run_id,
    )
    result = await broker.execute_async(tool_request, actor_scopes)
    if not result.success:
        return f"Tool execution blocked: {result.error}"
    return json.dumps(result.output or {}, ensure_ascii=True)


@router.post("/upload")
async def upload_attachment(
    run_id: int,
    file: UploadFile = File(...),
    request: Request = None,
) -> dict:
    if not file or not run_id:
        raise HTTPException(status_code=400, detail="run_id and file are required")

    base = project_attachments_dir(request.app.state.active_project_root)
    base.mkdir(parents=True, exist_ok=True)
    dest = base / file.filename
    contents = await file.read()
    dest.write_bytes(contents)

    await request.app.state.event_bus.publish(
        Event(
            type="chat.attachment",
            payload={
                "run_id": run_id,
                "filename": file.filename,
                "path": str(dest),
            },
        )
    )

    return {"status": "ok", "filename": file.filename}


@router.post("/intro")
async def intro_team(payload: dict, request: Request) -> dict:
    run_id = payload.get("run_id")
    orchestrator = request.app.state.orchestrator
    with get_session() as session:
        run = session.get(Run, int(run_id)) if run_id else None
        if not run:
            active_project_id = request.app.state.active_project_id
            if active_project_id is None:
                raise HTTPException(status_code=404, detail="Active project not set")
            run = session.exec(
                select(Run)
                .where(Run.project_id == active_project_id)
                .order_by(Run.id.desc())
            ).first()
        if not run:
            team = session.exec(
                select(Team)
                .where(Team.project_id == request.app.state.active_project_id)
                .order_by(Team.id.desc())
            ).first()
            if not team:
                raise HTTPException(status_code=404, detail="No team available for chat")
            run = Run(project_id=team.project_id, team_id=team.id, goal="Team intro")
            session.add(run)
            session.commit()
            session.refresh(run)
    await orchestrator.introduce_team(int(run.id))
    return {"status": "ok", "run_id": run.id}
