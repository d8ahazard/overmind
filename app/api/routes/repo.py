from fastapi import APIRouter, Request

from app.repo.workspace import WorkspaceManager

router = APIRouter()


@router.get("/status")
def repo_status(request: Request) -> dict:
    manager = WorkspaceManager(request.app.state.active_project_root)
    result = manager.status()
    return {"success": result.success, "output": result.output}


@router.get("/remotes")
def repo_remotes(request: Request) -> dict:
    manager = WorkspaceManager(request.app.state.active_project_root)
    result = manager.remotes()
    return {"success": result.success, "output": result.output}


@router.get("/branch")
def repo_branch(request: Request) -> dict:
    manager = WorkspaceManager(request.app.state.active_project_root)
    result = manager.current_branch()
    return {"success": result.success, "output": result.output}


@router.get("/github")
def repo_github(request: Request) -> dict:
    manager = WorkspaceManager(request.app.state.active_project_root)
    result = manager.remotes()
    is_github = "github.com" in result.output.lower()
    return {"github": is_github, "remotes": result.output}
