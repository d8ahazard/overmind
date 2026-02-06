from fastapi import APIRouter, Request

from app.core.events import Event
from app.integrations.mcp_client import MCPClient

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
    client = MCPClient(payload["url"])
    await client.initialize()
    return await client.call_tool(payload["name"], payload.get("arguments", {}))
