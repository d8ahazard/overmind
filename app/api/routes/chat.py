from datetime import datetime
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlmodel import select

from app.core.chat_router import ChatRouter
from app.core.events import Event
from app.core.memory import MemoryStore
from app.core.artifacts import ArtifactStore
from app.core.orchestrator import Orchestrator
from app.core.project_registry import project_attachments_dir
from app.db.models import AgentConfig, Run, Team, Task
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

        targets = router_helper.resolve_targets(run.team_id, message)

    event_bus = request.app.state.event_bus
    artifacts = ArtifactStore(request.app.state.data_dir)
    agent_runtime = request.app.state.orchestrator.agent_runtime
    stakeholder_message = {
        "message_id": str(uuid.uuid4()),
        "agent": "Stakeholder",
        "role": "Stakeholder",
        "content": message,
        "timestamp": datetime.utcnow().isoformat(),
    }
    artifacts.write_chat(run.id, "Stakeholder", stakeholder_message)
    await event_bus.publish(
        Event(
            type="chat.message",
            payload={
                **stakeholder_message,
                "targets": [t.display_name or t.role for t in targets],
            },
        )
    )

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
        await event_bus.publish(
            Event(
                type="task.created",
                payload={
                    "task_id": task.id,
                    "title": task.title,
                    "assigned_role": task.assigned_role,
                },
            )
        )

    has_mention = "@" in message
    response_prompt = (
        "Incoming stakeholder message:\n"
        f"{message}\n\n"
        "If a response is required, reply with a concise response. "
        "If no response is needed, return exactly: NO_RESPONSE."
    )
    for agent in targets:
        if not agent.id:
            continue
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
        prompt = message if has_mention else response_prompt
        response = await agent_runtime.run_agent(run.id, agent, prompt)
        response_text = (response.get("content") or "").strip()
        if not has_mention and response_text.upper() == "NO_RESPONSE":
            continue
        agent_message = {
            "message_id": str(uuid.uuid4()),
            "agent": agent.display_name or agent.role,
            "role": agent.role,
            "content": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        artifacts.write_chat(run.id, agent.role, agent_message)
        await event_bus.publish(
            Event(
                type="agent.response",
                payload={"agent": agent.role, "content": response_text},
            )
        )
        await event_bus.publish(
            Event(
                type="chat.message",
                payload=agent_message,
            )
        )
        memory.append(run.id, agent.id, agent.role, f"Agent: {response_text}")

    return {
        "status": "ok",
        "run_id": run.id,
        "targets": [t.display_name or t.role for t in targets],
    }


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
