from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


def _resolve_path(request: Request, raw_path: str) -> Path:
    if not raw_path:
        raise HTTPException(status_code=400, detail="path is required")
    root = Path(request.app.state.active_project_root).resolve()
    path = Path(raw_path)
    if not path.is_absolute():
        path = (root / path).resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(status_code=403, detail="path_outside_project")
    return path


@router.post("/read")
def read_file(payload: dict, request: Request) -> dict:
    path = _resolve_path(request, payload.get("path"))
    if not path.exists():
        raise HTTPException(status_code=404, detail="not_found")
    return {"path": str(path), "content": path.read_text(encoding="utf-8")}


@router.post("/write")
def write_file(payload: dict, request: Request) -> dict:
    path = _resolve_path(request, payload.get("path"))
    content = payload.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content), encoding="utf-8")
    return {"path": str(path), "status": "written"}


@router.post("/append")
def append_file(payload: dict, request: Request) -> dict:
    path = _resolve_path(request, payload.get("path"))
    content = payload.get("content")
    if content is None:
        raise HTTPException(status_code=400, detail="content is required")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(str(content))
    return {"path": str(path), "status": "appended"}


@router.post("/replace")
def replace_file(payload: dict, request: Request) -> dict:
    path = _resolve_path(request, payload.get("path"))
    old = payload.get("old")
    new = payload.get("new")
    if old is None or new is None:
        raise HTTPException(status_code=400, detail="old and new are required")
    if not path.exists():
        raise HTTPException(status_code=404, detail="not_found")
    content = path.read_text(encoding="utf-8")
    if old not in content:
        raise HTTPException(status_code=400, detail="old_not_found")
    content = content.replace(str(old), str(new), 1)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "status": "replaced"}
