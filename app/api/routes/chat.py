from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlmodel import select

from app.core.chat_router import ChatRouter
from app.core.events import Event
from app.core.memory import MemoryStore
from app.core.orchestrator import Orchestrator
from app.core.project_registry import project_attachments_dir
from app.db.models import AgentConfig, Run
from app.db.session import get_session

router = APIRouter()
router_helper = ChatRouter()
memory = MemoryStore()


@router.post("/send")
async def send_message(payload: dict, request: Request) -> dict:
    run_id = payload.get("run_id")
    message = payload.get("message")
    if not run_id or not message:
        raise HTTPException(status_code=400, detail="run_id and message are required")

    with get_session() as session:
        run = session.get(Run, int(run_id))
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        targets = router_helper.resolve_targets(run.team_id, message)

    event_bus = request.app.state.event_bus
    await event_bus.publish(
        Event(
            type="chat.message",
            payload={
                "agent": "Stakeholder",
                "role": "Stakeholder",
                "content": message,
                "timestamp": datetime.utcnow().isoformat(),
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

    for agent in targets:
        if agent.id:
            memory.append(run.id, agent, f"Stakeholder: {message}")
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

    return {"status": "ok", "targets": [t.display_name or t.role for t in targets]}


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
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")
    orchestrator = request.app.state.orchestrator
    await orchestrator.introduce_team(int(run_id))
    return {"status": "ok"}
