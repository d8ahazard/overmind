from pathlib import Path
import os
import platform

from fastapi import APIRouter, HTTPException, Request

from app.core.shell import execute_shell_tool, system_info
from app.core.tool_broker import ToolRequest
from app.db.models import Run
from sqlmodel import select

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

    command = _normalize_command(command)
    risk_level = payload.get("risk_level")
    if not risk_level:
        risk_level = "low" if _is_read_only_command(command) else "high"

    allowed_roots = [request.app.state.active_project_root]
    if request.app.state.settings.allow_self_edit:
        allowed_roots.append(request.app.state.settings.repo_root)

    cwd_path = Path(cwd) if cwd else request.app.state.active_project_root
    broker = request.app.state.tool_broker
    if "system.run" not in broker.executors:
        broker.register("system.run", execute_shell_tool)
    run_id = payload.get("run_id")
    if not run_id:
        with get_session() as session:
            latest = session.exec(
                select(Run)
                .where(Run.project_id == request.app.state.active_project_id)
                .order_by(Run.id.desc())
            ).first()
            run_id = latest.id if latest else None
    tool_request = ToolRequest(
        tool_name="system.run",
        arguments={
            "command": command,
            "cwd": str(cwd_path),
            "allowed_roots": [str(path) for path in allowed_roots],
        },
        risk_level=risk_level,
        required_scopes=["system:run"],
        actor=payload.get("actor", "system"),
        approved=bool(payload.get("approved")),
        approval_id=payload.get("approval_id"),
        run_id=run_id,
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
        "risk_level": risk_level,
    }


def _normalize_command(command):
    if not isinstance(command, str):
        return command
    parts = command.strip().split()
    if not parts:
        return command
    is_windows = os.name == "nt"
    mapping = {
        "ls": "dir",
        "pwd": "cd",
        "which": "where",
    }
    if is_windows and parts[0] in mapping:
        parts[0] = mapping[parts[0]]
        return " ".join(parts)
    return command


def _is_read_only_command(command) -> bool:
    if isinstance(command, list):
        cmd = command[0] if command else ""
    else:
        cmd = command.strip().split()[0] if command else ""
    if not cmd:
        return False
    is_windows = os.name == "nt"
    windows_read_only = {
        "dir",
        "type",
        "where",
        "whoami",
        "ver",
        "ipconfig",
        "systeminfo",
        "hostname",
    }
    posix_read_only = {
        "ls",
        "cat",
        "pwd",
        "whoami",
        "uname",
        "date",
        "df",
        "ps",
        "hostname",
    }
    return cmd.lower() in (windows_read_only if is_windows else posix_read_only)