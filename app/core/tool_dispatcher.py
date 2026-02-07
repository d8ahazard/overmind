import json
import asyncio
from pathlib import Path

from app.core.events import Event
from app.core.file_tools import execute_file_tool
from app.core.git_tools import execute_git_tool
from app.core.shell import execute_shell_tool, is_destructive_command
from app.core.tool_broker import ToolRequest, ToolResult
from app.integrations.mcp_client import MCPClient
from app.db.models import Approval, ProjectSetting, Run
from app.db.session import get_session
from sqlmodel import select


def extract_tool_call(text: str) -> dict | None:
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get("tool") and data.get("arguments"):
                return data
        except Exception:
            return None
    return None


def normalize_tool_response(text: str) -> str:
    if not text or not text.startswith("Tool execution blocked:"):
        return text
    reason = text.split(":", 1)[1].strip()
    if reason.startswith("approval_required"):
        parts = reason.split(":", 1)
        approval_id = parts[1] if len(parts) > 1 else None
        if approval_id:
            return f"Unable to run tool: approval required (ID {approval_id}). Please approve."
        return "Unable to run tool: approval required. Please approve."
    if reason == "file_edits_disabled":
        return "Unable to run tool: file edits are disabled for this role or project."
    if reason == "approval_required":
        return "Unable to run tool: approval required."
    return f"Unable to run tool: {reason}."


async def execute_tool_call(
    tool_call: dict,
    *,
    broker,
    agent,
    run_id: int,
    repo_root: Path,
    allow_self_edit: bool,
    extra_allowed_roots: list[Path] | None = None,
    allow_file_edits: bool = False,
    event_bus=None,
    artifact_store=None,
) -> str:
    tool_name = tool_call.get("tool")
    arguments = tool_call.get("arguments") or {}
    risk_level = "low"
    required_scopes: list[str] = []

    if tool_name == "system.run":
        if "system.run" not in broker.executors:
            broker.register("system.run", execute_shell_tool)
        if "cwd" not in arguments:
            arguments["cwd"] = str(repo_root)
        if "allowed_roots" not in arguments:
            allowed = [str(repo_root)]
            if allow_self_edit and extra_allowed_roots:
                allowed.extend([str(path) for path in extra_allowed_roots])
            arguments["allowed_roots"] = allowed
        destructive = is_destructive_command(arguments.get("command"))
        if destructive and not tool_call.get("approval_id"):
            return "Tool execution blocked: approval_required"
        risk_level = "critical" if destructive else "low"
        required_scopes = ["system:run"]
    elif tool_name and tool_name.startswith("git."):
        if tool_name not in broker.executors:
            broker.register(tool_name, lambda req: execute_git_tool(req, repo_root))
        required_scopes = [f"git:{tool_name.split('.', 1)[1]}"]
        risk_level = "high" if tool_name == "git.merge" else "low"
    elif tool_name and tool_name.startswith("file."):
        if not allow_file_edits and tool_name != "file.read":
            return "Tool execution blocked: file_edits_disabled"
        if tool_name not in broker.executors:
            broker.register(tool_name, lambda req: execute_file_tool(req, repo_root))
        required_scopes = ["file:write"] if tool_name != "file.read" else ["file:read"]
    elif tool_name == "mcp.call":
        if "mcp.call" not in broker.executors:
            async def _executor(tool_request: ToolRequest):
                client = MCPClient(tool_request.arguments["url"])
                await client.initialize()
                result = await client.call_tool(
                    tool_request.arguments["name"],
                    tool_request.arguments.get("arguments", {}),
                )
                return ToolResult(success=True, output=result)
            broker.register("mcp.call", _executor)
        required_scopes = ["mcp:call"]
    else:
        return f"Tool execution blocked: unknown tool {tool_name}."

    actor_scopes = [
        item.strip() for item in (agent.permissions or "").split(",") if item.strip()
    ]
    tool_request = ToolRequest(
        tool_name=tool_name,
        arguments=arguments,
        required_scopes=required_scopes,
        actor=agent.display_name or agent.role,
        risk_level=risk_level,
        approval_id=tool_call.get("approval_id"),
        run_id=run_id,
    )
    if tool_name == "git.create_pr":
        if _requires_pr_approval(run_id) and not tool_call.get("approval_id"):
            approval_id = _create_approval(
                run_id, agent.display_name or agent.role, tool_name, risk_level
            )
            _emit_event(
                event_bus,
                artifact_store,
                run_id,
                "approval.requested",
                {"approval_id": approval_id, "tool": tool_name, "actor": agent.display_name or agent.role},
            )
            return f"Tool execution blocked: approval_required:{approval_id}"

    result = await broker.execute_async(tool_request, actor_scopes)
    if not result.success:
        return f"Tool execution blocked: {result.error}"
    if tool_name == "git.create_pr":
        _emit_event(
            event_bus,
            artifact_store,
            run_id,
            "pr.requested",
            {
                "actor": agent.display_name or agent.role,
                "output": result.output or {},
                "status": "draft_ready",
            },
        )
    return json.dumps(result.output or {}, ensure_ascii=True)


def _requires_pr_approval(run_id: int) -> bool:
    if not run_id:
        return False
    with get_session() as session:
        run = session.get(Run, run_id)
        if not run:
            return False
        setting = session.exec(
            select(ProjectSetting).where(ProjectSetting.project_id == run.project_id)
        ).first()
        return bool(setting.require_pm_pr_approval) if setting else False


def _create_approval(run_id: int, actor: str, tool_name: str, risk_level: str) -> int:
    with get_session() as session:
        approval = Approval(
            run_id=run_id,
            actor=actor,
            tool_name=tool_name,
            risk_level=risk_level,
            status="pending",
        )
        session.add(approval)
        session.commit()
        session.refresh(approval)
        return approval.id or 0


def _emit_event(event_bus, artifact_store, run_id: int, event_type: str, payload: dict) -> None:
    if not run_id:
        return
    event = Event(type=event_type, payload=payload)
    if artifact_store:
        artifact_store.write_event(run_id, event.__dict__)
    if event_bus:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(event_bus.publish(event))
        except Exception:
            pass
