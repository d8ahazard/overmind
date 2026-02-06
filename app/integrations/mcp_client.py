from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class MCPTool:
    name: str
    description: str | None = None
    input_schema: Dict[str, Any] | None = None
    risk_level: str = "medium"
    required_scopes: List[str] | None = None


@dataclass
class MCPEndpoint:
    url: str
    tools: List[MCPTool]


class MCPClient:
    def __init__(self, url: str) -> None:
        self.url = url

    async def _rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self.url, json=payload)
            response.raise_for_status()
            data = response.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data["result"]

    async def initialize(self) -> Dict[str, Any]:
        return await self._rpc(
            "initialize",
            {
                "clientInfo": {"name": "overmind", "version": "0.1.0"},
                "capabilities": {},
            },
        )

    async def list_tools(self) -> List[MCPTool]:
        result = await self._rpc("tools/list")
        tools = result.get("tools", [])
        parsed: List[MCPTool] = []
        for tool in tools:
            parsed.append(
                MCPTool(
                    name=tool.get("name"),
                    description=tool.get("description"),
                    input_schema=tool.get("inputSchema"),
                    risk_level=tool.get("riskLevel", "medium"),
                    required_scopes=tool.get("requiredScopes", ["mcp:call"]),
                )
            )
        return parsed

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self._rpc("tools/call", {"name": name, "arguments": arguments})


class MCPRegistry:
    def __init__(self, endpoints: List[str], ports: List[int]) -> None:
        self._endpoints = endpoints
        self._ports = ports
        self._resolved: List[MCPEndpoint] = []
        self._last_refresh: Optional[str] = None

    @property
    def endpoints(self) -> List[MCPEndpoint]:
        return self._resolved

    @property
    def last_refresh(self) -> Optional[str]:
        return self._last_refresh

    async def refresh(self) -> List[MCPEndpoint]:
        urls = list(self._endpoints)
        urls.extend([f"http://localhost:{port}/mcp" for port in self._ports])
        resolved = await discover_endpoints(urls)
        self._resolved = resolved
        self._last_refresh = datetime.utcnow().isoformat()
        return resolved


async def discover_endpoints(urls: List[str]) -> List[MCPEndpoint]:
    endpoints: List[MCPEndpoint] = []
    tasks = [probe_endpoint(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, MCPEndpoint):
            endpoints.append(result)
    return endpoints


async def probe_endpoint(url: str) -> Optional[MCPEndpoint]:
    client = MCPClient(url)
    try:
        await client.initialize()
        tools = await client.list_tools()
    except Exception:
        return None
    if not tools:
        return None
    return MCPEndpoint(url=url, tools=tools)
