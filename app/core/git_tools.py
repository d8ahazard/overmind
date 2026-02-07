from pathlib import Path
from typing import Optional

from app.core.tool_broker import ToolRequest, ToolResult
from app.repo.workspace import WorkspaceManager


def execute_git_tool(request: ToolRequest, repo_root: Path) -> ToolResult:
    tool = request.tool_name
    args = request.arguments or {}
    manager = WorkspaceManager(repo_root)
    if tool == "git.status":
        result = manager.status()
        return ToolResult(success=result.success, output={"output": result.output})
    if tool == "git.diff":
        result = manager.diff(path=args.get("path"))
        return ToolResult(success=result.success, output={"output": result.output})
    if tool == "git.branch":
        name = args.get("name") or args.get("branch")
        if not name:
            return ToolResult(success=False, error="branch_name_required")
        result = manager.create_branch(str(name))
        return ToolResult(success=result.success, output={"output": result.output})
    if tool == "git.commit":
        message = args.get("message")
        if not message:
            return ToolResult(success=False, error="commit_message_required")
        result = manager.commit(str(message))
        return ToolResult(success=result.success, output={"output": result.output})
    if tool == "git.merge":
        branch = args.get("branch")
        if not branch:
            return ToolResult(success=False, error="merge_branch_required")
        result = manager.merge(str(branch))
        return ToolResult(success=result.success, output={"output": result.output})
    if tool == "git.create_pr":
        remote = str(args.get("remote") or "origin")
        branch = args.get("branch")
        if not branch:
            current = manager.current_branch()
            branch = current.output.strip() if current.success else None
        if not branch:
            return ToolResult(success=False, error="branch_required")
        remotes = manager.remotes()
        if not remotes.success or not remotes.output:
            return ToolResult(success=False, error="git_remote_not_configured")
        push_result = manager.push(remote, str(branch))
        if not push_result.success:
            return ToolResult(success=False, error=push_result.output)
        return ToolResult(
            success=True,
            output={
                "output": push_result.output,
                "note": "Branch pushed. Create PR in your git host UI.",
                "branch": branch,
                "remote": remote,
            },
        )
    return ToolResult(success=False, error="unknown_git_tool")
