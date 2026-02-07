from pathlib import Path

from app.core.tool_broker import ToolRequest, ToolResult


def _resolve_path(path: str, repo_root: Path) -> Path:
    root = repo_root.resolve()
    target = Path(path)
    if not target.is_absolute():
        target = (root / target).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("path_outside_project")
    return target


def execute_file_tool(request: ToolRequest, repo_root: Path) -> ToolResult:
    tool = request.tool_name
    args = request.arguments or {}
    raw_path = args.get("path")
    if not raw_path:
        return ToolResult(success=False, error="path_required")
    try:
        path = _resolve_path(str(raw_path), repo_root)
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))

    if tool == "file.read":
        if not path.exists():
            return ToolResult(success=False, error="not_found")
        return ToolResult(success=True, output={"content": path.read_text(encoding="utf-8")})
    if tool == "file.write":
        content = args.get("content")
        if content is None:
            return ToolResult(success=False, error="content_required")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        return ToolResult(success=True, output={"status": "written"})
    if tool == "file.append":
        content = args.get("content")
        if content is None:
            return ToolResult(success=False, error="content_required")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(str(content))
        return ToolResult(success=True, output={"status": "appended"})
    if tool == "file.replace":
        old = args.get("old")
        new = args.get("new")
        if old is None or new is None:
            return ToolResult(success=False, error="old_new_required")
        if not path.exists():
            return ToolResult(success=False, error="not_found")
        content = path.read_text(encoding="utf-8")
        if str(old) not in content:
            return ToolResult(success=False, error="old_not_found")
        content = content.replace(str(old), str(new), 1)
        path.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output={"status": "replaced"})
    return ToolResult(success=False, error="unknown_file_tool")
