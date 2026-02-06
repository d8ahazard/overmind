from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.core.shell import execute_shell_tool, system_info
from app.core.tool_broker import ToolRequest

router = APIRouter()


@router.get("/info")
def get_system_info() -> dict:
    return system_info()


@router.post("/run")
def run_system_command(payload: dict, request: Request) -> dict:
    command = payload.get("command")
    cwd = payload.get("cwd")
    if not command:
        raise HTTPException(status_code=400, detail="command is required")

    allowed_roots = [request.app.state.active_project_root]
    if request.app.state.settings.allow_self_edit:
        allowed_roots.append(request.app.state.settings.repo_root)

    cwd_path = Path(cwd) if cwd else request.app.state.active_project_root
    broker = request.app.state.tool_broker
    if "system.run" not in broker.executors:
        broker.register("system.run", execute_shell_tool)
    tool_request = ToolRequest(
        tool_name="system.run",
        arguments={
            "command": command,
            "cwd": str(cwd_path),
            "allowed_roots": [str(path) for path in allowed_roots],
        },
        risk_level="high",
        required_scopes=["system:run"],
        actor=payload.get("actor", "system"),
        approved=bool(payload.get("approved")),
        approval_id=payload.get("approval_id"),
    )
    actor_scopes = payload.get("actor_scopes", [])
    if isinstance(actor_scopes, str):
        actor_scopes = [item.strip() for item in actor_scopes.split(",") if item.strip()]
    result = broker.execute(tool_request, actor_scopes)
    return {
        "success": result.success,
        "stdout": (result.output or {}).get("stdout", ""),
        "stderr": (result.output or {}).get("stderr", ""),
        "exit_code": (result.output or {}).get("exit_code", 1),
        "error": result.error,
    }
