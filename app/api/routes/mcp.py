from fastapi import APIRouter, Request

from app.core.events import Event
from app.core.tool_broker import ToolRequest
from app.integrations.mcp_client import MCPClient
from app.db.models import Run
from sqlmodel import select

router = APIRouter()


@router.get("/status")
async def mcp_status(request: Request) -> dict:
    registry = request.app.state.mcp_registry
    if not registry.endpoints:
        await registry.refresh()
    return {
        "last_refresh": registry.last_refresh,
        "endpoints": [
            {
                "url": endpoint.url,
                "tools": [tool.__dict__ for tool in endpoint.tools],
            }
            for endpoint in registry.endpoints
        ],
    }


@router.post("/refresh")
async def mcp_refresh(request: Request) -> dict:
    registry = request.app.state.mcp_registry
    endpoints = await registry.refresh()
    event_bus = request.app.state.event_bus
    await event_bus.publish(
        Event(
            type="mcp.discovered",
            payload={
                "endpoints": [
                    {"url": endpoint.url, "tools": [t.__dict__ for t in endpoint.tools]}
                    for endpoint in endpoints
                ]
            },
        )
    )
    return {"status": "ok", "endpoints": len(endpoints)}


@router.post("/call")
async def mcp_call(request: Request, payload: dict) -> dict:
    broker = request.app.state.tool_broker

    async def _executor(tool_request: ToolRequest):
        client = MCPClient(tool_request.arguments["url"])
        await client.initialize()
        result = await client.call_tool(
            tool_request.arguments["name"], tool_request.arguments.get("arguments", {})
        )
        from app.core.tool_broker import ToolResult
        return ToolResult(success=True, output=result)

    if "mcp.call" not in broker.executors:
        broker.register("mcp.call", _executor)

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
        tool_name="mcp.call",
        arguments={
            "url": payload["url"],
            "name": payload["name"],
            "arguments": payload.get("arguments", {}),
        },
        risk_level=payload.get("risk_level", "medium"),
        required_scopes=payload.get("required_scopes", ["mcp:call"]),
        actor=payload.get("actor", "system"),
        approved=bool(payload.get("approved")),
        approval_id=payload.get("approval_id"),
        run_id=run_id,
    )
    actor_scopes = payload.get("actor_scopes", [])
    if isinstance(actor_scopes, str):
        actor_scopes = [item.strip() for item in actor_scopes.split(",") if item.strip()]
    result = await broker.execute_async(tool_request, actor_scopes)
    if result.output is not None:
        return result.output
    return {"error": result.error, "success": result.success}
