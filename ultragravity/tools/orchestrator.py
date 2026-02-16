from __future__ import annotations

from typing import Any

from ultragravity.actions import Action
from ultragravity.gateway import ActionGateway

from .base import ToolExecutionResult
from .registry import ToolRegistry


class ToolOrchestrator:
    def __init__(self, registry: ToolRegistry, gateway: ActionGateway):
        self.registry = registry
        self.gateway = gateway

    def execute(
        self,
        tool_name: str,
        operation: str,
        params: dict[str, Any],
        scope: list[str] | None = None,
        reason: str = "",
    ) -> ToolExecutionResult:
        adapter = self.registry.get(tool_name)
        capability = adapter.capabilities().get(operation)
        if capability is None:
            return ToolExecutionResult(success=False, error=f"Unsupported operation '{operation}' for tool '{tool_name}'")

        action = Action(
            tool_name=tool_name,
            operation=operation,
            params=params,
            risk_level=capability.risk_level,
            scope=scope or [tool_name],
            reversible=capability.reversible,
            reason=reason or capability.description,
        )

        execution = self.gateway.execute(action, lambda: adapter.execute(operation, params))
        if not execution.allowed:
            return ToolExecutionResult(success=False, error=execution.error or "Denied by policy")
        if not execution.executed:
            return ToolExecutionResult(success=False, error=execution.error or "Execution failed")

        result = execution.result
        if isinstance(result, ToolExecutionResult):
            return result
        if isinstance(result, dict):
            return ToolExecutionResult(success=True, payload=result)
        return ToolExecutionResult(success=True, payload={"result": result})
