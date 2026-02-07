from fastapi import APIRouter, HTTPException, Request
import json

from app.core.events import Event
from app.core.tool_broker import ToolRequest
from app.integrations.mcp_client import MCPClient
from app.db.models import ProjectSetting, Run
from sqlmodel import select
from app.db.session import get_session

router = APIRouter()


@router.get("/status")
async def mcp_status(request: Request) -> dict:
    registry = request.app.state.mcp_registry
    _apply_mcp_settings(request, registry)
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
    _apply_mcp_settings(request, registry)
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


@router.get("/endpoints")
async def mcp_endpoints(request: Request) -> dict:
    registry = request.app.state.mcp_registry
    settings = _get_mcp_settings(request)
    _apply_mcp_settings(request, registry)
    if not registry.endpoints:
        await registry.refresh()
    return {
        "manual_endpoints": settings["endpoints"],
        "ports": settings["ports"],
        "discovered": [
            {"url": endpoint.url, "tools": [tool.__dict__ for tool in endpoint.tools]}
            for endpoint in registry.endpoints
        ],
    }


@router.post("/endpoints")
async def add_mcp_endpoint(request: Request, payload: dict) -> dict:
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    with get_session() as session:
        setting = _get_or_create_setting(session, request.app.state.active_project_id)
        endpoints = _parse_json_list(setting.mcp_endpoints)
        if url not in endpoints:
            endpoints.append(url)
        setting.mcp_endpoints = json.dumps(endpoints)
        session.add(setting)
        session.commit()
    return {"status": "ok", "endpoints": endpoints}


@router.delete("/endpoints")
async def remove_mcp_endpoint(request: Request, url: str | None = None) -> dict:
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    with get_session() as session:
        setting = _get_or_create_setting(session, request.app.state.active_project_id)
        endpoints = _parse_json_list(setting.mcp_endpoints)
        endpoints = [item for item in endpoints if item != url]
        setting.mcp_endpoints = json.dumps(endpoints)
        session.add(setting)
        session.commit()
    return {"status": "ok", "endpoints": endpoints}


@router.post("/ports")
async def update_mcp_ports(request: Request, payload: dict) -> dict:
    ports = payload.get("ports")
    if not isinstance(ports, list):
        raise HTTPException(status_code=400, detail="ports must be a list")
    cleaned = [int(port) for port in ports if str(port).isdigit()]
    with get_session() as session:
        setting = _get_or_create_setting(session, request.app.state.active_project_id)
        setting.mcp_ports = json.dumps(cleaned)
        session.add(setting)
        session.commit()
    return {"status": "ok", "ports": cleaned}


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


def _parse_json_list(raw: str | None) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _get_or_create_setting(session, project_id: int | None) -> ProjectSetting:
    if project_id is None:
        project_id = 0
    setting = session.exec(
        select(ProjectSetting).where(ProjectSetting.project_id == project_id)
    ).first()
    if not setting:
        setting = ProjectSetting(project_id=project_id)
        session.add(setting)
        session.commit()
        session.refresh(setting)
    return setting


def _get_mcp_settings(request: Request) -> dict:
    project_id = request.app.state.active_project_id
    with get_session() as session:
        setting = _get_or_create_setting(session, project_id)
        endpoints = _parse_json_list(setting.mcp_endpoints)
        ports = _parse_json_list(setting.mcp_ports)
    if not ports:
        ports = list(request.app.state.settings.mcp_discovery_ports)
    return {"endpoints": endpoints, "ports": ports}


def _apply_mcp_settings(request: Request, registry) -> None:
    settings = _get_mcp_settings(request)
    endpoints = list(request.app.state.settings.mcp_endpoints)
    for item in settings["endpoints"]:
        if item not in endpoints:
            endpoints.append(item)
    registry.set_endpoints(endpoints)
    registry.set_ports(settings["ports"])
