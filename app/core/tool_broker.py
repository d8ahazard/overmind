import inspect
import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable, Optional, Union

from app.core.approvals import ApprovalStore
from app.core.audit import AuditEntry, AuditLogger
from app.core.events import Event, EventBus
from app.core.policy import PolicyEngine


@dataclass
class ToolRequest:
    tool_name: str
    arguments: dict[str, Any]
    risk_level: str = "low"
    required_scopes: Iterable[str] = ()
    actor: str = "system"
    approved: bool = False
    approval_id: Optional[int] = None
    run_id: Optional[int] = None
    job_id: Optional[int] = None


@dataclass
class ToolResult:
    success: bool
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class ToolBroker:
    def __init__(
        self,
        policy: PolicyEngine,
        audit_logger: AuditLogger,
        approvals: ApprovalStore | None = None,
        event_bus: EventBus | None = None,
        event_writer: Callable[[int, dict], None] | None = None,
        executors: Optional[
            dict[str, Union[Callable[[ToolRequest], ToolResult], Callable[[ToolRequest], Awaitable[ToolResult]]]]
        ] = None,
    ) -> None:
        self.policy = policy
        self.audit_logger = audit_logger
        self.approvals = approvals
        self.event_bus = event_bus
        self.event_writer = event_writer
        self.executors = executors or {}

    def register(
        self,
        tool_name: str,
        executor: Union[Callable[[ToolRequest], ToolResult], Callable[[ToolRequest], Awaitable[ToolResult]]],
    ) -> None:
        self.executors[tool_name] = executor

    def execute(self, request: ToolRequest, actor_scopes: Iterable[str]) -> ToolResult:
        approved = request.approved
        if not approved and self.approvals:
            approved = self.approvals.is_approved(
                request.approval_id,
                tool_name=request.tool_name,
                risk_level=request.risk_level,
            )
        decision = self.policy.evaluate(
            actor_scopes=actor_scopes,
            required_scopes=request.required_scopes,
            risk_level=request.risk_level,
            approved=approved,
        )
        self.audit_logger.log(
            AuditEntry(
                actor=request.actor,
                action="tool.request",
                decision=decision.reason,
                tool_name=request.tool_name,
                risk_level=request.risk_level,
                request=request.arguments,
                run_id=request.run_id,
                job_id=request.job_id,
            )
        )
        self._emit_event(
            "tool.requested",
            {
                "tool": request.tool_name,
                "risk_level": request.risk_level,
                "decision": decision.reason,
                "actor": request.actor,
                "arguments": request.arguments,
                "run_id": request.run_id,
                "job_id": request.job_id,
            },
            run_id=request.run_id,
        )
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)

        executor = self.executors.get(request.tool_name)
        if not executor:
            return ToolResult(success=False, error="tool_not_registered")
        result = executor(request)
        self.audit_logger.log(
            AuditEntry(
                actor=request.actor,
                action="tool.result",
                decision="executed",
                tool_name=request.tool_name,
                risk_level=request.risk_level,
                request=request.arguments,
                result=result.output or {"error": result.error},
                run_id=request.run_id,
                job_id=request.job_id,
            )
        )
        self._emit_event(
            "tool.completed",
            {
                "tool": request.tool_name,
                "success": result.success,
                "error": result.error,
                "actor": request.actor,
                "arguments": request.arguments,
                "run_id": request.run_id,
                "job_id": request.job_id,
            },
            run_id=request.run_id,
        )
        return result

    async def execute_async(self, request: ToolRequest, actor_scopes: Iterable[str]) -> ToolResult:
        approved = request.approved
        if not approved and self.approvals:
            approved = self.approvals.is_approved(
                request.approval_id,
                tool_name=request.tool_name,
                risk_level=request.risk_level,
            )
        decision = self.policy.evaluate(
            actor_scopes=actor_scopes,
            required_scopes=request.required_scopes,
            risk_level=request.risk_level,
            approved=approved,
        )
        self.audit_logger.log(
            AuditEntry(
                actor=request.actor,
                action="tool.request",
                decision=decision.reason,
                tool_name=request.tool_name,
                risk_level=request.risk_level,
                request=request.arguments,
                run_id=request.run_id,
                job_id=request.job_id,
            )
        )
        self._emit_event(
            "tool.requested",
            {
                "tool": request.tool_name,
                "risk_level": request.risk_level,
                "decision": decision.reason,
                "actor": request.actor,
                "arguments": request.arguments,
                "run_id": request.run_id,
                "job_id": request.job_id,
            },
            run_id=request.run_id,
        )
        if not decision.allowed:
            return ToolResult(success=False, error=decision.reason)

        executor = self.executors.get(request.tool_name)
        if not executor:
            return ToolResult(success=False, error="tool_not_registered")
        if inspect.iscoroutinefunction(executor):
            result = await executor(request)
        else:
            result = executor(request)
        self.audit_logger.log(
            AuditEntry(
                actor=request.actor,
                action="tool.result",
                decision="executed",
                tool_name=request.tool_name,
                risk_level=request.risk_level,
                request=request.arguments,
                result=result.output or {"error": result.error},
                run_id=request.run_id,
                job_id=request.job_id,
            )
        )
        self._emit_event(
            "tool.completed",
            {
                "tool": request.tool_name,
                "success": result.success,
                "error": result.error,
                "actor": request.actor,
                "arguments": request.arguments,
                "run_id": request.run_id,
                "job_id": request.job_id,
            },
            run_id=request.run_id,
        )
        return result

    def _emit_event(self, event_type: str, payload: dict, run_id: int | None) -> None:
        if self.event_writer and run_id:
            try:
                self.event_writer(run_id, {"type": event_type, "payload": payload})
            except Exception:
                pass
        if not self.event_bus:
            return
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.event_bus.publish(Event(type=event_type, payload=payload)))
        except Exception:
            return
