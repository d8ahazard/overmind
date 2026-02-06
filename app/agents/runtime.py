from datetime import datetime
from typing import Any, Dict

import os

from sqlmodel import select

from app.core.memory import MemoryStore
from app.integrations.mcp_client import MCPRegistry
from app.providers.model_registry import ModelRegistry
from app.providers.base import ProviderError
from app.db.models import AgentConfig, ProjectBudget, Run
from app.db.session import get_session


class AgentRuntime:
    def __init__(self, registry: ModelRegistry, mcp_registry: MCPRegistry) -> None:
        self.registry = registry
        self.mcp_registry = mcp_registry
        self.memory = MemoryStore()

    async def run_agent(self, run_id: int, agent: AgentConfig, goal: str) -> Dict[str, Any]:
        budget_allowed = self._check_budget(run_id)
        if not budget_allowed:
            return {
                "role": agent.role,
                "content": "Budget limit reached for this project.",
                "timestamp": datetime.utcnow().isoformat(),
            }
        tools = []
        for endpoint in self.mcp_registry.endpoints:
            for tool in endpoint.tools:
                tools.append(tool.name)
        tools_note = "\nAvailable MCP tools: " + ", ".join(tools) if tools else ""
        persona = agent.personality or "Be clear, collaborative, and concise."
        name = agent.display_name or agent.role
        memories = []
        if agent.id:
            recent = self.memory.recent(run_id, agent.id, limit=5)
            memories = [entry.content for entry in reversed(recent)]
        memory_note = "\nRecent memory:\n" + "\n".join(memories) if memories else ""
        prompt = (
            f"Name: {name}\nRole: {agent.role}\nPersona: {persona}\n"
            f"Goal: {goal}{tools_note}{memory_note}\n"
        )
        payload = {"prompt": prompt, "role": agent.role}
        try:
            response = await self.registry.invoke(agent.provider, agent.model, payload)
        except ProviderError as exc:
            return {
                "role": agent.role,
                "content": f"Provider error: {exc}",
                "timestamp": datetime.utcnow().isoformat(),
            }

        self._increment_budget(run_id)

        return {
            "role": agent.role,
            "content": response.get("content", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _check_budget(self, run_id: int) -> bool:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return True
            budget = session.exec(
                select(ProjectBudget).where(ProjectBudget.project_id == run.project_id)
            ).first()
            if not budget:
                return True
            return budget.usd_spent < budget.usd_limit

    def _increment_budget(self, run_id: int) -> None:
        cost_per_call = float(os.getenv("AI_DEVTEAM_COST_PER_CALL", "0.01"))
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                return
            budget = session.exec(
                select(ProjectBudget).where(ProjectBudget.project_id == run.project_id)
            ).first()
            if not budget:
                return
            budget.usd_spent += cost_per_call
            session.add(budget)
            session.commit()
