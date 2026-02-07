from fastapi import APIRouter, HTTPException, Request
from sqlmodel import select

from app.core.git_tools import execute_git_tool
from app.core.tool_broker import ToolRequest
from app.db.models import Run
from app.db.session import get_session

router = APIRouter()


def _get_run_id(request: Request, payload: dict) -> int | None:
    run_id = payload.get("run_id")
    if run_id:
        return run_id
    with get_session() as session:
        latest = session.exec(
            select(Run)
            .where(Run.project_id == request.app.state.active_project_id)
            .order_by(Run.id.desc())
        ).first()
        return latest.id if latest else None


def _execute(request: Request, payload: dict, tool_name: str, risk_level: str) -> dict:
    broker = request.app.state.tool_broker
    if tool_name not in broker.executors:
        broker.register(
            tool_name, lambda tool_request: execute_git_tool(tool_request, request.app.state.active_project_root)
        )
    tool_request = ToolRequest(
        tool_name=tool_name,
        arguments=payload,
        required_scopes=[f"git:{tool_name.split('.', 1)[1]}"],
        risk_level=risk_level,
        actor=payload.get("actor", "system"),
        approved=bool(payload.get("approved")),
        approval_id=payload.get("approval_id"),
        run_id=_get_run_id(request, payload),
    )
    actor_scopes = payload.get("actor_scopes", [])
    if isinstance(actor_scopes, str):
        actor_scopes = [item.strip() for item in actor_scopes.split(",") if item.strip()]
    result = broker.execute(tool_request, actor_scopes)
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
    }


@router.post("/status")
def status(payload: dict, request: Request) -> dict:
    return _execute(request, payload, "git.status", "low")


@router.post("/diff")
def diff(payload: dict, request: Request) -> dict:
    return _execute(request, payload, "git.diff", "low")


@router.post("/branch")
def branch(payload: dict, request: Request) -> dict:
    if not payload.get("name") and not payload.get("branch"):
        raise HTTPException(status_code=400, detail="branch name is required")
    return _execute(request, payload, "git.branch", "low")


@router.post("/commit")
def commit(payload: dict, request: Request) -> dict:
    if not payload.get("message"):
        raise HTTPException(status_code=400, detail="commit message is required")
    return _execute(request, payload, "git.commit", "low")


@router.post("/merge")
def merge(payload: dict, request: Request) -> dict:
    if not payload.get("branch"):
        raise HTTPException(status_code=400, detail="merge branch is required")
    return _execute(request, payload, "git.merge", "high")


@router.post("/create-pr")
def create_pr(payload: dict, request: Request) -> dict:
    return _execute(request, payload, "git.create_pr", "low")
