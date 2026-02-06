from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.core.shell import run_command, system_info

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
    result = run_command(command, cwd=cwd_path, allowed_roots=allowed_roots)
    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    }
